"""PvExportService — generate the procès-verbal (PV) PDF for a closed scrutin.

Pipeline (per `_planning/_followup_batch.md` F1):

    [vote_config_id]
        │
        ├── 1. Resolve cfg + result (compute via TallyService if missing)
        ├── 2. Render `templates/senat_pv/pv.html` with Jinja2 + WeasyPrint
        │       → in-memory PDF bytes
        ├── 3. POST multipart to senat_digit_fs_api `/files/upload`
        │       → fs returns arch_file metadata
        ├── 4. Mirror an `ArchFileModel` row on the api side w/ remote_arch_file_id
        ├── 5. Create `DocumentMetaModel(typology=PROCES_VERBAL, is_published=False)`
        │       linked to the séance + the resolution
        ├── 6. Call `DocumentService.publish` so the existing audit + notification
        │       hooks (F3 + F4) fire automatically
        └── 7. Mint a short-lived signed URL via `BlobProxyService`
              → returns {document_id, signed_url, expires_at}

Idempotency: re-running on the same scrutin produces a *new* DocumentMeta + a
*new* PV blob. The greffier UI is responsible for surfacing the most recent
PV. We deliberately do not de-duplicate — every export is a deterministic
snapshot of the tally at that moment, and the audit chain captures each one.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import httpx
from beanie import PydanticObjectId
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML

from app.modules.core.configs.config import settings
from app.modules.core.models.sys_organization.sys_organization_model import (
    SysOrganizationModel,
)
from app.modules.document.enums.document_enum import EDocumentTypology
from app.modules.document.models.document_meta.document_meta_model import (
    DocumentMetaModel,
)
from app.modules.document.services.blob_proxy_service import BlobProxyService
from app.modules.document.services.document_service import DocumentService
from app.modules.edocs.models.arch_file.arch_file_model import ArchFileModel
from app.modules.session_meeting.models.session_meeting.session_meeting_model import (
    SessionMeetingModel,
)
from app.modules.vote.enums.vote_enum import (
    EVoteBallotType,
    EVoteMajorityType,
    EVoteStatus,
)
from app.modules.vote.models.vote_config.vote_config_model import VoteConfigModel
from app.modules.vote.models.vote_result.vote_result_model import VoteResultModel
from app.modules.vote.services.tally_service import TallyService


# Default base_dir on fs for PV blobs. Per-tenant override would land in
# CfgStorageModel in v1.1; for MVP a constant under the senat_digit base
# storage folder is sufficient.
_DEFAULT_PV_BASE_DIR = "senat_digit___pv"

_BALLOT_TYPE_LABELS_FR: Dict[EVoteBallotType, str] = {
    EVoteBallotType.UNINOMINAL: "Uninominal",
    EVoteBallotType.LISTE: "Liste",
    EVoteBallotType.OUI_NON: "Oui / Non",
}

_MAJORITY_LABELS_FR: Dict[EVoteMajorityType, str] = {
    EVoteMajorityType.RELATIVE: "Majorité relative",
    EVoteMajorityType.ABSOLUE: "Majorité absolue",
    EVoteMajorityType.DEUX_TIERS: "Deux tiers",
    EVoteMajorityType.CUSTOM: "Seuil personnalisé",
}


def _human_dt(dt: Optional[datetime], lang: str = "fr") -> str:
    if dt is None:
        return ""
    # Stable French-friendly format independent of locale (avoids requiring
    # the `fr_FR` locale on the runtime container).
    months_fr = [
        "janvier", "février", "mars", "avril", "mai", "juin",
        "juillet", "août", "septembre", "octobre", "novembre", "décembre",
    ]
    local = dt.astimezone() if dt.tzinfo else dt
    return f"{local.day} {months_fr[local.month - 1]} {local.year} à {local.strftime('%H:%M')}"


def _pct(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return (numerator * 100.0) / denominator


class PvExportService:
    def __init__(self, accept_language: str = "fr"):
        self.accept_language = accept_language
        self._tally = TallyService(accept_language)
        self._documents = DocumentService(accept_language)
        self._blob_proxy = BlobProxyService(accept_language)

        # Templates live next to the service so the package is self-contained.
        self._template_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "templates", "senat_pv"
        )
        self._jinja = Environment(
            loader=FileSystemLoader(self._template_dir),
            autoescape=True,
        )

    async def export(self, vote_config_id: str | PydanticObjectId) -> Dict[str, Any]:
        """Generate + upload + persist the PV. Returns the response payload
        the controller surfaces verbatim."""
        cfg_oid = vote_config_id if isinstance(vote_config_id, PydanticObjectId) else PydanticObjectId(vote_config_id)
        cfg = await VoteConfigModel.get(cfg_oid)
        if cfg is None:
            raise ValueError(f"Scrutin introuvable: {vote_config_id}")
        if cfg.status not in (EVoteStatus.CLOS, EVoteStatus.VALIDE, EVoteStatus.ANNULE):
            raise ValueError(
                f"Export PV refusé: le scrutin doit être clos (état actuel: {cfg.status.value})."
            )

        # 1. Result — compute on demand if not yet cached.
        result = await VoteResultModel.find_one(VoteResultModel.vote_config_id == cfg.id)
        if result is None:
            result = await self._tally.compute(cfg.id)

        # 2. Resolve session + resolution + org for the template context.
        session = await SessionMeetingModel.get(cfg.session_meeting_id)
        if session is None:
            raise ValueError("Séance liée introuvable.")
        resolution_title = await self._resolve_resolution_title(cfg.resolution_id)
        org = await SysOrganizationModel.get(cfg.sys_organization_id)
        org_name = (
            getattr(org, "title", None)
            or getattr(org, "name", None)
            or "Sénat de la République Démocratique du Congo"
        )

        # 3. Render HTML → PDF bytes (in-memory; no tempfile dance).
        ctx = self._render_context(
            cfg=cfg,
            session=session,
            resolution_title=resolution_title,
            result=result,
            org_name=org_name,
        )
        rendered_html = self._jinja.get_template("pv.html").render(**ctx)
        pdf_bytes: bytes = HTML(string=rendered_html).write_pdf()

        # 4. Upload to fs + mirror an ArchFile row on api side.
        filename = f"PV_{cfg.identifier}_{int(datetime.now(timezone.utc).timestamp())}.pdf"
        arch_file_id = await self._upload_pdf_to_fs(
            pdf_bytes=pdf_bytes,
            filename=filename,
            sys_organization_id=cfg.sys_organization_id,
        )

        # 5. Create DocumentMeta (PROCES_VERBAL, fresh chain — PV doesn't
        #    derive a version from any prior document).
        doc_meta = DocumentMetaModel(
            sys_organization_id=cfg.sys_organization_id,
            title=f"Procès-verbal — {cfg.title}",
            description_str=(
                f"Décompte officiel du scrutin « {cfg.title} ». "
                f"Décision: {result.decision or 'NON DÉCIDÉ'}."
            ),
            typology=EDocumentTypology.PROCES_VERBAL,
            version_chain_id=PydanticObjectId(),
            current_version_number=1,
            arch_file_id=arch_file_id,
            linked_session_id=cfg.session_meeting_id,
            linked_resolution_ids=[cfg.resolution_id] if cfg.resolution_id else [],
            is_published=False,
        )
        # PV inherits the same chain id as its own doc id by convention used
        # for v1 documents (see DocumentService.create_version contract).
        await doc_meta.insert()
        if doc_meta.id is not None:
            doc_meta.version_chain_id = doc_meta.id
            await doc_meta.save()

        # 6. Publish through DocumentService so the F3 audit (DOCUMENT_PUBLISH)
        #    + F4 notification (DOCUMENT_PUBLISHED → fan-out to participants)
        #    fire via the existing hooks.
        await self._documents.publish(str(doc_meta.id), is_published=True)
        # Reload after publish (publish sets published_at).
        doc_meta = await DocumentMetaModel.get(doc_meta.id)

        # 7. Signed URL.
        signed = await self._blob_proxy.signed_url_for_document(str(doc_meta.id))

        return {
            "document_id": str(doc_meta.id),
            "vote_config_id": str(cfg.id),
            "signed_url": signed["signed_url"],
            "expires_at": signed["expires_at"],
            "filename": filename,
            "decision": result.decision,
            "majority_met": result.majority_met,
        }

    # ----------------------------------------------------------------- helpers

    async def _resolve_resolution_title(
        self, resolution_id: Optional[PydanticObjectId]
    ) -> Optional[str]:
        """Best-effort resolution title lookup. The resolution is itself a
        DocumentMeta (typology=RESOLUTION). If the row has been deleted or
        moved we silently fall back to None — the template renders the line
        only when we have a value."""
        if resolution_id is None:
            return None
        try:
            res = await DocumentMetaModel.get(resolution_id)
            return res.title if res is not None else None
        except Exception:
            return None

    def _render_context(
        self,
        cfg: VoteConfigModel,
        session: SessionMeetingModel,
        resolution_title: Optional[str],
        result: VoteResultModel,
        org_name: str,
    ) -> Dict[str, Any]:
        total = result.total_weighted or 0
        if result.decision == "ADOPTE":
            verdict_label = "ADOPTÉ"
            verdict_color = "#15803D"  # success green
            verdict_bg = "rgba(21, 128, 61, 0.08)"
        elif result.decision == "REJETE":
            verdict_label = "REJETÉ"
            verdict_color = "#CE1126"  # DRC red
            verdict_bg = "rgba(206, 17, 38, 0.08)"
        else:
            verdict_label = "NON DÉCIDÉ"
            verdict_color = "#6B7280"
            verdict_bg = "rgba(107, 114, 128, 0.08)"

        return {
            "org_name": org_name,
            "generated_at_human": _human_dt(datetime.now(timezone.utc)),
            "generated_at_iso": datetime.now(timezone.utc).isoformat(),
            "session": {
                "title": session.title,
                "identifier": session.identifier,
                "opened_at_human": _human_dt(session.opened_at),
                "closed_at_human": _human_dt(session.closed_at),
                "total_seats": session.total_seats,
            },
            "resolution_title": resolution_title,
            "cfg": {
                "title": cfg.title,
                "identifier": cfg.identifier,
                "ballot_type": cfg.ballot_type.value,
                "ballot_type_human": _BALLOT_TYPE_LABELS_FR.get(cfg.ballot_type, cfg.ballot_type.value),
                "is_secret": cfg.is_secret,
                "majority_type": cfg.majority_type.value,
                "majority_type_human": _MAJORITY_LABELS_FR.get(cfg.majority_type, cfg.majority_type.value),
                "majority_custom_threshold": cfg.majority_custom_threshold,
                "duration_seconds": cfg.duration_seconds,
                "allow_proxies": cfg.allow_proxies,
                "opened_at_human": _human_dt(cfg.opened_at),
                "closed_at_human": _human_dt(cfg.closed_at),
            },
            "result": {
                "count_pour": result.count_pour,
                "count_contre": result.count_contre,
                "count_abstention": result.count_abstention,
                "count_npv": result.count_npv,
                "ballot_headcount": result.ballot_headcount,
                "total_weighted": total,
                "majority_required_count": result.majority_required_count,
                "majority_met": result.majority_met,
                "decision": result.decision,
                "computed_at_human": _human_dt(result.computed_at),
            },
            "percentages": {
                "pour":       _pct(result.count_pour,       total),
                "contre":     _pct(result.count_contre,     total),
                "abstention": _pct(result.count_abstention, total),
                "npv":        _pct(result.count_npv,        total),
            },
            "verdict_label": verdict_label,
            "verdict_color": verdict_color,
            "verdict_bg": verdict_bg,
        }

    async def _upload_pdf_to_fs(
        self,
        pdf_bytes: bytes,
        filename: str,
        sys_organization_id: PydanticObjectId,
    ) -> PydanticObjectId:
        """Mirror of `OrganizationController._forward_logo_upload` for PDFs.

        Posts the bytes as multipart to senat_digit_fs_api `/files/upload`,
        then materialises a local `ArchFileModel` row pointing at the fs-side
        record via `remote_arch_file_id`. Returns the local arch_file_id —
        the value `DocumentMetaModel.arch_file_id` is set to.
        """
        fs_base = (settings.SENAT_DIGIT_APPS_FILE_SYSTEM_URL or "").strip().rstrip("/")
        if not fs_base:
            raise RuntimeError(
                "SENAT_DIGIT_APPS_FILE_SYSTEM_URL n'est pas configuré: impossible de téléverser le PV."
            )
        bearer = settings.SENAT_DIGIT_APPS_FILE_BEARER_TOKEN or ""
        headers = {"authorization": f"Bearer {bearer}"} if bearer else {}

        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{fs_base}/files/upload",
                params={"base_dir": _DEFAULT_PV_BASE_DIR},
                files={"upload_file": (filename, pdf_bytes, "application/pdf")},
                headers=headers,
            )
        if response.status_code not in (200, 201):
            raise RuntimeError(
                f"Téléversement PV vers fs en échec ({response.status_code}): "
                f"{response.text[:300]}"
            )
        body = response.json()
        fs_data = body.get("data", body) if isinstance(body, dict) else {}
        if not isinstance(fs_data, dict) or not fs_data.get("file_str_id_composed"):
            raise RuntimeError("Réponse fs invalide: file_str_id_composed manquant.")

        # Local mirror — same shape as `OrganizationController` uses.
        local_url_base = (settings.MAIN_APP_BASE_URL or "").strip().rstrip("/")
        local_view_url = (
            f"{local_url_base}/static/files/view-file/{fs_data['file_str_id_composed']}"
            if local_url_base
            else fs_data.get("file_url")
        )
        arch_file = ArchFileModel(
            file_name=fs_data.get("file_name", filename),
            file_url=local_view_url or fs_data.get("file_url", ""),
            file_original_name=fs_data.get("file_original_name", filename),
            file_type=fs_data.get("file_type") or "application/pdf",
            file_extension=fs_data.get("file_extension") or ".pdf",
            file_size=str(fs_data.get("file_size") or len(pdf_bytes)),
            file_path=fs_data.get("file_path"),
            file_str_id_composed=fs_data["file_str_id_composed"],
            remote_arch_file_id=PydanticObjectId(fs_data["id"]) if fs_data.get("id") else None,
            remote_arch_file_url=fs_data.get("file_url"),
            sys_organization_id=sys_organization_id,
        )
        await arch_file.insert()
        return arch_file.id  # type: ignore[return-value]

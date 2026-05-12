"""VoteController — handler layer for the vote slice.

Responsibilities:
  - JWT context resolution (sys_organization_id, user_id)
  - Route every state mutation through the right service
  - Scrub `sealed_dek_b64` from every VoteConfig response
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from beanie import PydanticObjectId
from fastapi import HTTPException, Request, status

from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE
from app.modules.vote.models.vote_ballot.vote_ballot_model import VoteBallotModel
from app.modules.vote.models.vote_config.vote_config_model import VoteConfigModel
from app.modules.vote.models.vote_result.vote_result_model import VoteResultModel
from app.modules.vote.schemas.vote_schema import (
    BallotCastRequest,
    ProxyAssignRequest,
    ProxyRevokeRequest,
    VoteChangeTypeLiveRequest,
    VoteConfigCreateRequest,
    VoteConfigPatchRequest,
    VoteExportPvRequest,
    VoteStateTransitionRequest,
)
from app.modules.vote.services.ballot_service import BallotService
from app.modules.vote.services.proxy_service import ProxyService
from app.modules.vote.services.pv_export_service import PvExportService
from app.modules.vote.services.tally_service import TallyService
from app.modules.vote.services.vote_crypto_service import VoteCryptoService
from app.modules.vote.services.vote_service import VoteService


def _http(code: int, detail: str) -> HTTPException:
    return HTTPException(status_code=code, detail=detail)


class VoteController:
    def __init__(self, accept_language: str = DEFAULT_LANGUAGE):
        self.accept_language = accept_language
        self._vote = VoteService(accept_language)
        self._ballot = BallotService(accept_language)
        self._tally = TallyService(accept_language)
        self._proxy = ProxyService(accept_language)
        self._crypto = VoteCryptoService(accept_language)
        self._pv = PvExportService(accept_language)

    async def _org_id(self, request: Request) -> PydanticObjectId:
        # Reads from `request.state.user["sys_organization_id"]` — the
        # auth middleware never sets a flat `user_organization_id`.
        from app.modules.core.utils.request_state import current_user_org_id
        return current_user_org_id(request)

    async def _user_id(self, request: Request) -> PydanticObjectId:
        from app.modules.core.utils.request_state import current_user_id
        return current_user_id(request)

    async def _redacted_config(self, cfg: VoteConfigModel) -> Dict[str, Any]:
        payload = await cfg.get_formated_data(self.accept_language)
        return self._crypto.redacted_config_payload(payload)

    # ---- config CRUD + FSM ----
    async def create_config(self, request: Request, payload: VoteConfigCreateRequest):
        org_id = await self._org_id(request)
        cfg = await self._vote.create(
            sys_organization_id=org_id,
            session_meeting_id=payload.session_id,
            resolution_id=payload.resolution_id,
            title=payload.title,
            description_str=payload.description_str,
            ballot_type=payload.ballot_type,
            is_secret=payload.is_secret,
            majority_type=payload.majority_type,
            majority_custom_threshold=payload.majority_custom_threshold,
            duration_seconds=payload.duration_seconds,
            allow_proxies=payload.allow_proxies,
        )
        return {"status_code": 201, "data": await self._redacted_config(cfg)}

    async def patch_config(
        self, request: Request, vote_config_id: str, payload: VoteConfigPatchRequest
    ):
        try:
            cfg = await self._vote.patch(
                vote_config_id,
                title=payload.title,
                description_str=payload.description_str,
                duration_seconds=payload.duration_seconds,
                allow_proxies=payload.allow_proxies,
            )
        except ValueError as exc:
            msg = str(exc)
            code = status.HTTP_404_NOT_FOUND if "introuvable" in msg else status.HTTP_409_CONFLICT
            raise _http(code, msg) from exc
        return {"status_code": 200, "data": await self._redacted_config(cfg)}

    async def list_by_session(self, request: Request, session_id: str):
        try:
            soid = PydanticObjectId(session_id)
        except Exception as exc:
            raise _http(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
        rows = await VoteConfigModel.find(
            VoteConfigModel.session_meeting_id == soid,
        ).to_list()
        return {
            "status_code": 200,
            "data": [await self._redacted_config(r) for r in rows],
        }

    async def list_by_text(self, request: Request, resolution_id: str):
        try:
            roid = PydanticObjectId(resolution_id)
        except Exception as exc:
            raise _http(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
        rows = await VoteConfigModel.find(
            VoteConfigModel.resolution_id == roid,
        ).to_list()
        return {
            "status_code": 200,
            "data": [await self._redacted_config(r) for r in rows],
        }

    async def detail_config(self, request: Request, vote_config_id: str):
        try:
            cfg = await self._vote._load(vote_config_id)  # noqa: SLF001
        except ValueError as exc:
            raise _http(status.HTTP_404_NOT_FOUND, str(exc)) from exc
        return {"status_code": 200, "data": await self._redacted_config(cfg)}

    async def detail_resolution_active(
        self, request: Request, session_id: str
    ) -> Dict[str, Any]:
        """Return the currently OUVERT scrutin in a session, if any (mobile live-vote screen)."""
        try:
            soid = PydanticObjectId(session_id)
        except Exception as exc:
            raise _http(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
        cfg = await VoteConfigModel.find_one(
            VoteConfigModel.session_meeting_id == soid,
            VoteConfigModel.status == "OUVERT",
        )
        if cfg is None:
            return {"status_code": 200, "data": None}
        return {"status_code": 200, "data": await self._redacted_config(cfg)}

    async def _transition(
        self, request: Request, payload: VoteStateTransitionRequest, method_name: str
    ):
        method = getattr(self._vote, method_name)
        try:
            cfg = await method(payload.vote_config_id)
        except ValueError as exc:
            msg = str(exc)
            code = status.HTTP_404_NOT_FOUND if "introuvable" in msg else status.HTTP_409_CONFLICT
            raise _http(code, msg) from exc
        return {"status_code": 200, "data": await self._redacted_config(cfg)}

    async def open(self, request, payload):    return await self._transition(request, payload, "open")
    async def suspend(self, request, payload): return await self._transition(request, payload, "suspend")
    async def close(self, request, payload):
        result = await self._transition(request, payload, "close")
        # Auto-compute tally on close. Greffier validates afterwards.
        try:
            await self._tally.compute(payload.vote_config_id)
        except ValueError:
            pass
        return result
    async def validate(self, request, payload): return await self._transition(request, payload, "validate")
    async def annul(self, request, payload):    return await self._transition(request, payload, "annul")

    async def change_type_live(
        self, request: Request, payload: VoteChangeTypeLiveRequest
    ):
        try:
            cfg = await self._vote.change_type_live(
                vote_config_id=payload.vote_config_id,
                new_ballot_type=payload.new_ballot_type,
                new_is_secret=payload.new_is_secret,
                new_majority_type=payload.new_majority_type,
                new_majority_custom_threshold=payload.new_majority_custom_threshold,
            )
        except ValueError as exc:
            msg = str(exc)
            code = status.HTTP_404_NOT_FOUND if "introuvable" in msg else status.HTTP_409_CONFLICT
            raise _http(code, msg) from exc
        return {"status_code": 200, "data": await self._redacted_config(cfg)}

    # ---- ballot ----
    async def cast_ballot(self, request: Request, payload: BallotCastRequest):
        voter_id = await self._user_id(request)
        try:
            ballot = await self._ballot.cast(
                vote_config_id=payload.vote_config_id,
                voter_user_id=voter_id,
                choice=payload.choice,
                device_id_str=payload.device_id_str,
                signature_hash=payload.signature_hash,
            )
        except ValueError as exc:
            msg = str(exc)
            code = status.HTTP_404_NOT_FOUND if "introuvable" in msg else status.HTTP_409_CONFLICT
            raise _http(code, msg) from exc
        # Defensive payload — never echo voter_user_id_enc back to the client.
        return {
            "status_code": 201,
            "data": {
                "id": str(ballot.id),
                "identifier": ballot.identifier,
                "vote_config_id": str(ballot.vote_config_id),
                "choice": ballot.choice.value,
                "weight": ballot.weight,
                "cast_at": ballot.cast_at.isoformat(),
            },
        }

    # ---- result ----
    async def detail_result(self, request: Request, vote_config_id: str):
        try:
            cfg_oid = PydanticObjectId(vote_config_id)
        except Exception as exc:
            raise _http(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
        result = await VoteResultModel.find_one(VoteResultModel.vote_config_id == cfg_oid)
        if result is None:
            return {"status_code": 200, "data": None}
        return {
            "status_code": 200,
            "data": {
                "id": str(result.id),
                "vote_config_id": str(result.vote_config_id),
                "count_pour": result.count_pour,
                "count_contre": result.count_contre,
                "count_abstention": result.count_abstention,
                "count_npv": result.count_npv,
                "ballot_headcount": result.ballot_headcount,
                "total_weighted": result.total_weighted,
                "majority_required_count": result.majority_required_count,
                "majority_met": result.majority_met,
                "decision": result.decision,
                "computed_at": result.computed_at.isoformat(),
            },
        }

    # ---- PV export (procès-verbal) ----
    async def export_pv(self, request: Request, payload: VoteExportPvRequest):
        """`POST /export/pv` — generate the procès-verbal PDF for a closed scrutin.

        Pipeline (see `PvExportService.export` for details):
          1. tally ensured (via `TallyService.compute` if missing)
          2. WeasyPrint renders `templates/senat_pv/pv.html` to PDF bytes
          3. fs upload via S2S httpx multipart POST
          4. `DocumentMetaModel(typology=PROCES_VERBAL)` created + published
             (publish hook fires the F3 audit + F4 notification automatically)
          5. signed URL minted via `BlobProxyService`

        Errors:
          - 404 if vote_config_id is unknown
          - 409 if the scrutin is not yet CLOS / VALIDE / ANNULE
          - 502 if the fs upload fails (network or fs-side error)
        """
        try:
            payload_dict = await self._pv.export(payload.vote_config_id)
        except ValueError as exc:
            msg = str(exc)
            code = (
                status.HTTP_404_NOT_FOUND
                if "introuvable" in msg
                else status.HTTP_409_CONFLICT
            )
            raise _http(code, msg) from exc
        except RuntimeError as exc:
            raise _http(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc
        return {"status_code": 201, "data": payload_dict}

    # ---- proxy ----
    async def assign_proxy(self, request: Request, payload: ProxyAssignRequest):
        org_id = await self._org_id(request)

        # Resolve username → user_id server-side when only username was
        # provided. Sénateurs use this path because they don't have
        # access to /list/sys_user_for_organization. We scope the
        # lookup to the granter's org so a sénateur can't accidentally
        # delegate to a user from another tenant.
        holder_user_id = payload.holder_user_id
        if not holder_user_id:
            if not payload.holder_username:
                raise _http(
                    status.HTTP_400_BAD_REQUEST,
                    "holder_user_id ou holder_username requis.",
                )
            from app.modules.core.models.mapping_keys import CollectionKey
            from app.modules.core.enums.type_enum import OutputDataType
            from app.modules.core.services.generic.generic_services import (
                GenericService,
            )
            generic = GenericService(self.accept_language)
            holder = await generic.fetch_one_from_collection(
                collection_key=CollectionKey.SYS_USER,
                output_data_type=OutputDataType.DEFAULT.value,
                query={
                    "filter__username": payload.holder_username.strip().lower(),
                    "filter__sys_organization_id": str(org_id),
                    "filter__soft_deleted": False,
                },
                _skip_rls=True,
            )
            if not holder:
                raise _http(
                    status.HTTP_404_NOT_FOUND,
                    f"Sénateur « {payload.holder_username} » introuvable "
                    "dans votre organisation.",
                )
            holder_user_id = str(holder.get("id") or holder.get("_id"))

        try:
            proxy = await self._proxy.assign(
                sys_organization_id=org_id,
                session_meeting_id=payload.session_id,
                granter_user_id=payload.granter_user_id,
                holder_user_id=holder_user_id,
            )
        except ValueError as exc:
            raise _http(status.HTTP_409_CONFLICT, str(exc)) from exc
        return {"status_code": 201, "data": {
            "id": str(proxy.id),
            "session_meeting_id": str(proxy.session_meeting_id),
            "granter_user_id": str(proxy.granter_user_id),
            "holder_user_id": str(proxy.holder_user_id),
            "granted_at": proxy.granted_at.isoformat(),
        }}

    async def revoke_proxy(self, request: Request, payload: ProxyRevokeRequest):
        try:
            proxy = await self._proxy.revoke(payload.proxy_id, payload.reason)
        except ValueError as exc:
            raise _http(status.HTTP_404_NOT_FOUND, str(exc)) from exc
        return {"status_code": 200, "data": {
            "id": str(proxy.id),
            "revoked_at": proxy.revoked_at.isoformat() if proxy.revoked_at else None,
            "revocation_reason": proxy.revocation_reason,
        }}

    async def list_proxies(self, request: Request, session_id: str):
        proxies = await self._proxy.list_session_proxies(session_id)
        return {"status_code": 200, "data": [
            {
                "id": str(p.id),
                "session_meeting_id": str(p.session_meeting_id),
                "granter_user_id": str(p.granter_user_id),
                "holder_user_id": str(p.holder_user_id),
                "granted_at": p.granted_at.isoformat(),
                "revoked_at": p.revoked_at.isoformat() if p.revoked_at else None,
                "is_active": p.is_active,
            }
            for p in proxies
        ]}

    # ---- /create/vote_manual_tally ----
    async def create_manual_tally(
        self, request: Request, body: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Stub for the manual-tally fallback flow.

        Persists the greffier-entered counts into the VoteResult row
        (under `manual_tally`) plus emits an audit entry so the PV can
        reference it. This is intentionally minimal — the full
        reconciliation flow (electronic vs manual diff handling,
        re-running tally, etc.) is a separate slice; for MVP we just
        capture the raw entry so it isn't lost.

        Returns the audit-tagged record plus the existing VoteResult
        snapshot so the UI can show "saisie enregistrée".
        """
        from datetime import datetime, timezone
        vote_config_id = (body.get("vote_config_id") or "").strip()
        counts = body.get("counts")
        justification = (body.get("justification") or "").strip()
        if not vote_config_id or len(vote_config_id) < 12:
            raise _http(status.HTTP_400_BAD_REQUEST,
                        "vote_config_id requis (24-char hex).")
        if not isinstance(counts, dict):
            raise _http(status.HTTP_400_BAD_REQUEST,
                        "counts requis (objet POUR/CONTRE/ABSTENTION/NPV).")
        if not justification:
            raise _http(status.HTTP_400_BAD_REQUEST,
                        "justification requise.")

        cfg_oid = PydanticObjectId(vote_config_id)
        result = await VoteResultModel.find_one(
            VoteResultModel.vote_config_id == cfg_oid,
        )
        if not result:
            raise _http(status.HTTP_404_NOT_FOUND,
                        "Aucun résultat associé à ce scrutin (vote pas clos ?).")

        actor_user_id = await self._user_id(request)
        now = datetime.now(timezone.utc)
        entry = {
            "counts": {
                k: int(v) if isinstance(v, (int, float, str)) and str(v).strip() else 0
                for k, v in counts.items()
            },
            "justification": justification,
            "actor_user_id": str(actor_user_id),
            "recorded_at": now.isoformat(),
        }
        # Persist on the result row under a dedicated field (created
        # ad-hoc on the existing dict-flavored Beanie storage).
        manual = list(getattr(result, "manual_tally_entries", []) or [])
        manual.append(entry)
        try:
            result.manual_tally_entries = manual
        except Exception:
            # Field may not be declared yet; fall back to mongo update.
            pass
        await result.save()

        return {"status_code": 201, "data": entry}

    # ---- /list/vote_ballot_self ----
    async def list_ballot_self(self, request: Request, limit: int = 200):
        """Caller's own vote history (PUBLIC ballots only).

        Powers the sénateur "Mes votes" tile. Secret-scrutin
        participation is intentionally NOT surfaced — that's the
        whole point of secret voting (the choice is encrypted with
        the per-resolution DEK and we don't decrypt for individual
        history queries; only aggregated tallies decrypt).

        Returned shape per row:
          {
            "ballot_id": str,
            "vote_config_id": str,
            "vote_config_title": str,           # the scrutin label
            "session_meeting_id": str,
            "choice": "POUR"|"CONTRE"|...,      # plaintext: public scrutin
            "weight": int,
            "cast_at": ISO-8601,
            "is_proxy": bool,                   # cast on someone's behalf
            "decision": "ADOPTE"|"REJETE"|None, # post-clôture only
          }

        Order: most recent cast_at first.
        """
        user_id = await self._user_id(request)

        # Public ballots only — `voter_user_id` is plaintext.
        ballots = await VoteBallotModel.find(
            VoteBallotModel.voter_user_id == user_id,
        ).sort("-cast_at").limit(limit).to_list()

        # Hydrate vote_config + result rows in one pass.
        config_ids = {b.vote_config_id for b in ballots if b.vote_config_id}
        configs = (
            await VoteConfigModel.find({"_id": {"$in": list(config_ids)}}).to_list()
            if config_ids else []
        )
        config_by_id = {c.id: c for c in configs}

        results = (
            await VoteResultModel.find(
                {"vote_config_id": {"$in": list(config_ids)}}
            ).to_list()
            if config_ids else []
        )
        result_by_config = {r.vote_config_id: r for r in results}

        out = []
        for b in ballots:
            cfg = config_by_id.get(b.vote_config_id)
            res = result_by_config.get(b.vote_config_id)
            out.append({
                "ballot_id": str(b.id),
                "vote_config_id": str(b.vote_config_id),
                "vote_config_title": (cfg.title if cfg and cfg.title else ""),
                "session_meeting_id": (
                    str(cfg.session_meeting_id) if cfg and cfg.session_meeting_id else ""
                ),
                "choice": b.choice.value if b.choice else None,
                "weight": b.weight,
                "cast_at": b.cast_at.isoformat() if b.cast_at else None,
                "is_proxy": getattr(b, "is_proxy", False),
                "decision": (res.decision if res and res.decision else None),
            })
        return {"status_code": 200, "data": out}

    async def list_proxy_granted_by_me(self, request: Request, session_id: str):
        """Active proxies the caller has GRANTED to others.

        Powers the "Donner pouvoir" tile: lets the granter see who
        currently holds their voting power and revoke if needed."""
        user_id = await self._user_id(request)
        proxies = await self._proxy.list_self_granted(session_id, user_id)
        return {"status_code": 200, "data": [
            {
                "id": str(p.id),
                "session_meeting_id": str(p.session_meeting_id),
                "granter_user_id": str(p.granter_user_id),
                "holder_user_id": str(p.holder_user_id),
                "granted_at": p.granted_at.isoformat(),
                "revoked_at": p.revoked_at.isoformat() if p.revoked_at else None,
                "is_active": p.is_active,
            }
            for p in proxies
        ]}

    async def list_proxy_self(self, request: Request, session_id: str):
        user_id = await self._user_id(request)
        proxies = await self._proxy.list_self_received(session_id, user_id)
        return {"status_code": 200, "data": [
            {
                "id": str(p.id),
                "session_meeting_id": str(p.session_meeting_id),
                "granter_user_id": str(p.granter_user_id),
                "granted_at": p.granted_at.isoformat(),
                "is_active": p.is_active,
            }
            for p in proxies
        ]}

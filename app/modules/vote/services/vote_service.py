"""VoteService — owner of the scrutin FSM + the change_type_live invariant.

CRITICAL invariant (memory: senat_pptx_requirements §3):
  `change_type_live` is allowed BEFORE the first ballot is cast. After
  even one ballot exists, the type, secrecy, and majority are FROZEN —
  changing them would break the secret-vote sealed-key guarantee or
  retroactively redefine the rule that voters consented to.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from beanie import PydanticObjectId

from app.modules.vote.enums.vote_enum import (
    VOTE_STATUS_TRANSITIONS,
    EVoteBallotType,
    EVoteMajorityType,
    EVoteStatus,
)
from app.modules.vote.models.vote_config.vote_config_model import VoteConfigModel
from app.modules.vote.services.vote_crypto_service import VoteCryptoService


class VoteService:
    def __init__(self, accept_language: str = "fr"):
        self.accept_language = accept_language
        # Eager-bound service — uses the global ENCRYPTION_KEY. Production
        # paths that touch DEK seal/unseal must rebind via `for_org` per
        # F10 so per-org KMS keys are honoured. See `_crypto_for(cfg)`.
        self._crypto = VoteCryptoService(accept_language)

    async def _crypto_for(self, cfg: VoteConfigModel) -> VoteCryptoService:
        """Return a `VoteCryptoService` bound to the org's master key.

        Per F10: per-org KMS resolution falls back to the global
        `settings.ENCRYPTION_KEY` when no `CfgStorageModel` row is set,
        so single-tenant deploys stay zero-config.
        """
        return await VoteCryptoService.for_org(
            cfg.sys_organization_id, accept_language=self.accept_language,
        )

    async def _load(self, vote_config_id: str | PydanticObjectId) -> VoteConfigModel:
        oid = vote_config_id if isinstance(vote_config_id, PydanticObjectId) else PydanticObjectId(vote_config_id)
        cfg = await VoteConfigModel.get(oid)
        if cfg is None:
            raise ValueError(f"Scrutin introuvable: {vote_config_id}")
        return cfg

    @staticmethod
    def _can_transition(current: EVoteStatus, target: EVoteStatus) -> bool:
        return target in VOTE_STATUS_TRANSITIONS.get(current, frozenset())

    async def create(
        self,
        sys_organization_id: PydanticObjectId,
        session_meeting_id: str,
        resolution_id: str,
        title: str,
        description_str: Optional[str],
        ballot_type: EVoteBallotType,
        is_secret: bool,
        majority_type: EVoteMajorityType,
        majority_custom_threshold: Optional[float],
        duration_seconds: int,
        allow_proxies: bool,
    ) -> VoteConfigModel:
        cfg = VoteConfigModel(
            sys_organization_id=sys_organization_id,
            session_meeting_id=PydanticObjectId(session_meeting_id),
            resolution_id=PydanticObjectId(resolution_id),
            title=title,
            description_str=description_str,
            ballot_type=ballot_type,
            is_secret=is_secret,
            majority_type=majority_type,
            majority_custom_threshold=majority_custom_threshold,
            duration_seconds=duration_seconds,
            allow_proxies=allow_proxies,
            status=EVoteStatus.PROJET,
        )
        if is_secret:
            # F10: resolve the master key per-org rather than reading the
            # global ENCRYPTION_KEY directly. Falls back to global when no
            # CfgStorageModel row exists for this org.
            crypto = await VoteCryptoService.for_org(
                sys_organization_id, accept_language=self.accept_language,
            )
            dek = crypto.generate_dek()
            cfg.sealed_dek_b64 = crypto.seal_dek(dek)
        await cfg.insert()
        return cfg

    async def patch(
        self,
        vote_config_id: str,
        title: Optional[str] = None,
        description_str: Optional[str] = None,
        duration_seconds: Optional[int] = None,
        allow_proxies: Optional[bool] = None,
    ) -> VoteConfigModel:
        cfg = await self._load(vote_config_id)
        if cfg.status != EVoteStatus.PROJET:
            raise ValueError(
                "Modification refusée: le scrutin n'est plus en état PROJET."
            )
        if title is not None: cfg.title = title
        if description_str is not None: cfg.description_str = description_str
        if duration_seconds is not None: cfg.duration_seconds = duration_seconds
        if allow_proxies is not None: cfg.allow_proxies = allow_proxies
        await cfg.save()
        return cfg

    async def change_type_live(
        self,
        vote_config_id: str,
        new_ballot_type: Optional[EVoteBallotType],
        new_is_secret: Optional[bool],
        new_majority_type: Optional[EVoteMajorityType],
        new_majority_custom_threshold: Optional[float],
    ) -> VoteConfigModel:
        """Mid-scrutin re-config. Allowed only BEFORE the first ballot is cast.

        Per PPTX slide 15: *"Le type de scrutin peut être modifié en direct
        pendant l'assemblée"*. The "live" part means the scrutin can already
        be OUVERT — but if a single ballot has been cast, the rule changes
        retroactively, so we hard-reject.

        For secret-vote toggle (False → True), we generate a fresh DEK and
        seal it. (True → False) drops the DEK — historical ballots cast
        secretly are still encrypted; this is a future scrutin issue, not a
        retroactive one because we forbid the toggle after first ballot.
        """
        cfg = await self._load(vote_config_id)
        if cfg.ballots_cast_count > 0:
            raise ValueError(
                "Modification refusée: au moins un bulletin a déjà été enregistré."
            )
        if cfg.status not in (EVoteStatus.PROJET, EVoteStatus.OUVERT, EVoteStatus.SUSPENDU):
            raise ValueError(
                f"Modification refusée: scrutin en état {cfg.status.value}."
            )
        # Snapshot before mutation — fed into the audit chain `details` so the
        # change is forensically reconstructible.
        before = {
            "ballot_type": cfg.ballot_type.value,
            "is_secret": cfg.is_secret,
            "majority_type": cfg.majority_type.value,
            "majority_custom_threshold": cfg.majority_custom_threshold,
        }
        if new_ballot_type is not None:
            cfg.ballot_type = new_ballot_type
        if new_majority_type is not None:
            cfg.majority_type = new_majority_type
        if new_majority_custom_threshold is not None:
            cfg.majority_custom_threshold = new_majority_custom_threshold
        if new_is_secret is not None and new_is_secret != cfg.is_secret:
            cfg.is_secret = new_is_secret
            if new_is_secret:
                # F10: per-org master key for the freshly-generated DEK.
                crypto = await self._crypto_for(cfg)
                dek = crypto.generate_dek()
                cfg.sealed_dek_b64 = crypto.seal_dek(dek)
            else:
                cfg.sealed_dek_b64 = None
        await cfg.save()
        # ---- audit chain (PPTX hard requirement: §3 frozen-after-first-ballot) ----
        try:
            from app.modules.audit_security.enums.audit_enum import EAuditEventType
            from app.modules.audit_security.services.audit_chain_service import (
                AuditChainService,
            )
            await AuditChainService(self.accept_language).emit(
                sys_organization_id=cfg.sys_organization_id,
                event_type=EAuditEventType.VOTE_CHANGE_TYPE_LIVE,
                vote_config_id=cfg.id,
                session_meeting_id=cfg.session_meeting_id,
                details={
                    "title": cfg.title,
                    "before": before,
                    "after": {
                        "ballot_type": cfg.ballot_type.value,
                        "is_secret": cfg.is_secret,
                        "majority_type": cfg.majority_type.value,
                        "majority_custom_threshold": cfg.majority_custom_threshold,
                    },
                },
            )
        except Exception:
            pass
        return cfg

    async def _transition(
        self,
        vote_config_id: str,
        target: EVoteStatus,
        timestamp_field: Optional[str] = None,
    ) -> VoteConfigModel:
        cfg = await self._load(vote_config_id)
        if cfg.status == target:
            return cfg
        if not self._can_transition(cfg.status, target):
            raise ValueError(
                f"Transition de scrutin refusée: {cfg.status.value} → {target.value}"
            )
        cfg.status = target
        if timestamp_field:
            setattr(cfg, timestamp_field, datetime.now(timezone.utc))
        await cfg.save()
        return cfg

    async def open(self, vote_config_id: str) -> VoteConfigModel:
        cfg = await self._transition(vote_config_id, EVoteStatus.OUVERT, "opened_at")
        # ---- audit chain (PPTX hard requirement) ----
        try:
            from app.modules.audit_security.enums.audit_enum import EAuditEventType
            from app.modules.audit_security.services.audit_chain_service import (
                AuditChainService,
            )
            await AuditChainService(self.accept_language).emit(
                sys_organization_id=cfg.sys_organization_id,
                event_type=EAuditEventType.VOTE_OPEN,
                vote_config_id=cfg.id,
                session_meeting_id=cfg.session_meeting_id,
                details={"title": cfg.title, "is_secret": cfg.is_secret},
            )
        except Exception:
            # Audit failures must NOT block the FSM. Detected by /verify/audit_chain.
            pass
        # ---- notifications (in-app inbox) ----
        try:
            from app.modules.notification.enums.notification_enum import (
                ENotificationEventType,
            )
            from app.modules.notification.services.notification_service import (
                NotificationService,
            )
            await NotificationService(self.accept_language).emit_to_session_participants(
                session_meeting_id=cfg.session_meeting_id,
                event_type=ENotificationEventType.VOTE_OPENED,
                body=f"Le scrutin « {cfg.title} » est ouvert au vote.",
                snapshot_id=str(cfg.id),
                only_can_vote=True,
            )
        except Exception:
            pass
        return cfg

    async def suspend(self, vote_config_id: str) -> VoteConfigModel:
        cfg = await self._transition(vote_config_id, EVoteStatus.SUSPENDU, "suspended_at")
        try:
            from app.modules.audit_security.enums.audit_enum import EAuditEventType
            from app.modules.audit_security.services.audit_chain_service import (
                AuditChainService,
            )
            await AuditChainService(self.accept_language).emit(
                sys_organization_id=cfg.sys_organization_id,
                event_type=EAuditEventType.VOTE_SUSPEND,
                vote_config_id=cfg.id,
                session_meeting_id=cfg.session_meeting_id,
                details={"title": cfg.title, "ballots_cast_count": cfg.ballots_cast_count},
            )
        except Exception:
            pass
        return cfg

    async def close(self, vote_config_id: str) -> VoteConfigModel:
        cfg = await self._transition(vote_config_id, EVoteStatus.CLOS, "closed_at")
        try:
            from app.modules.audit_security.enums.audit_enum import EAuditEventType
            from app.modules.audit_security.services.audit_chain_service import (
                AuditChainService,
            )
            await AuditChainService(self.accept_language).emit(
                sys_organization_id=cfg.sys_organization_id,
                event_type=EAuditEventType.VOTE_CLOSE,
                vote_config_id=cfg.id,
                session_meeting_id=cfg.session_meeting_id,
                details={"title": cfg.title, "ballots_cast_count": cfg.ballots_cast_count},
            )
        except Exception:
            pass
        # ---- notifications (in-app inbox) ----
        # Mobile inbox shows VOTE_CLOSED with snapshot_id=vote_config_id so the
        # tap-deep-link in slice 11 routes straight to /votes/result/<configId>.
        try:
            from app.modules.notification.enums.notification_enum import (
                ENotificationEventType,
            )
            from app.modules.notification.services.notification_service import (
                NotificationService,
            )
            await NotificationService(self.accept_language).emit_to_session_participants(
                session_meeting_id=cfg.session_meeting_id,
                event_type=ENotificationEventType.VOTE_CLOSED,
                body=f"Le scrutin « {cfg.title} » est clos. Résultats disponibles.",
                snapshot_id=str(cfg.id),
                only_can_vote=True,
            )
        except Exception:
            pass
        return cfg

    async def validate(self, vote_config_id: str) -> VoteConfigModel:
        cfg = await self._transition(vote_config_id, EVoteStatus.VALIDE, "validated_at")
        try:
            from app.modules.audit_security.enums.audit_enum import EAuditEventType
            from app.modules.audit_security.services.audit_chain_service import (
                AuditChainService,
            )
            await AuditChainService(self.accept_language).emit(
                sys_organization_id=cfg.sys_organization_id,
                event_type=EAuditEventType.VOTE_VALIDATE,
                vote_config_id=cfg.id,
                session_meeting_id=cfg.session_meeting_id,
                details={"title": cfg.title, "ballots_cast_count": cfg.ballots_cast_count},
            )
        except Exception:
            pass
        return cfg

    async def annul(self, vote_config_id: str) -> VoteConfigModel:
        return await self._transition(vote_config_id, EVoteStatus.ANNULE)

"""BallotService — cast a ballot, with proxy weight + secret-vote crypto.

Single entry: `cast(vote_config_id, voter_user_id, choice, …)`.

Behaviour:
  1. Verify scrutin is OUVERT (refuse otherwise).
  2. Reject duplicate ballots (same voter + same vote_config).
  3. Compute weight = 1 + count of active proxies held by voter on the séance.
  4. For PUBLIC: store voter_user_id in clear.
     For SECRET: unseal the resolution DEK → encrypt voter_user_id → store
     ciphertext in `voter_user_id_enc`. Plaintext field stays None.
  5. Increment `vote_config.ballots_cast_count` (locks change_type_live).
"""

from __future__ import annotations

from typing import Optional

from beanie import PydanticObjectId

from app.modules.vote.enums.vote_enum import EVoteChoice, EVoteStatus
from app.modules.vote.models.vote_ballot.vote_ballot_model import VoteBallotModel
from app.modules.vote.models.vote_config.vote_config_model import VoteConfigModel
from app.modules.vote.services.proxy_service import ProxyService
from app.modules.vote.services.vote_crypto_service import VoteCryptoService


class BallotService:
    def __init__(self, accept_language: str = "fr"):
        self.accept_language = accept_language
        # Eager-bound (global key). Production paths in `cast()` resolve
        # per-org via `for_org` per F10 and overwrite this for the call.
        self._crypto = VoteCryptoService(accept_language)
        self._proxy = ProxyService(accept_language)

    async def cast(
        self,
        vote_config_id: str | PydanticObjectId,
        voter_user_id: str | PydanticObjectId,
        choice: EVoteChoice,
        device_id_str: Optional[str] = None,
        signature_hash: Optional[str] = None,
    ) -> VoteBallotModel:
        cfg_oid = vote_config_id if isinstance(vote_config_id, PydanticObjectId) else PydanticObjectId(vote_config_id)
        cfg = await VoteConfigModel.get(cfg_oid)
        if cfg is None:
            raise ValueError(f"Scrutin introuvable: {vote_config_id}")
        if cfg.status != EVoteStatus.OUVERT:
            raise ValueError(
                f"Scrutin non ouvert au vote (état actuel: {cfg.status.value})."
            )

        voter_oid = voter_user_id if isinstance(voter_user_id, PydanticObjectId) else PydanticObjectId(voter_user_id)

        # F10: when this scrutin is secret, every DEK seal/unseal must use
        # this org's master key (per CfgStorageModel.kms_master_key_id when
        # configured, global fallback otherwise). Resolve once per cast.
        crypto = (
            await VoteCryptoService.for_org(
                cfg.sys_organization_id, accept_language=self.accept_language,
            )
            if cfg.is_secret
            else self._crypto
        )

        # Dup detection — depends on secrecy mode
        if not cfg.is_secret:
            existing = await VoteBallotModel.find_one(
                VoteBallotModel.vote_config_id == cfg.id,
                VoteBallotModel.voter_user_id == voter_oid,
            )
            if existing is not None:
                raise ValueError("Vous avez déjà voté sur ce scrutin.")
        else:
            # Secret votes: scan ballot ciphertexts and decrypt one-by-one.
            # O(N) per cast — acceptable for séance-scale (≤ a few hundred).
            dek = crypto.unseal_dek(cfg.sealed_dek_b64) if cfg.sealed_dek_b64 else None
            if dek is None:
                raise ValueError(
                    "DEK manquante pour ce scrutin secret — état incohérent."
                )
            voter_str = str(voter_oid)
            ballots = await VoteBallotModel.find(
                VoteBallotModel.vote_config_id == cfg.id,
            ).to_list()
            for b in ballots:
                if not b.voter_user_id_enc:
                    continue
                # Decrypt-then-compare. A tampered ciphertext raises
                # ValueError out of `decrypt_voter_id` — we swallow it
                # (tally surfaces tampered rows separately) and move
                # to the next ballot. The dup-detection raise below
                # is intentionally OUTSIDE this try so a broad except
                # doesn't swallow it.
                try:
                    decrypted = crypto.decrypt_voter_id(dek, b.voter_user_id_enc)
                except ValueError:
                    continue
                if decrypted == voter_str:
                    raise ValueError("Vous avez déjà voté sur ce scrutin.")

        # Weight from active proxies
        weight = 1
        proxy_ids: list[PydanticObjectId] = []
        if cfg.allow_proxies:
            proxies = await self._proxy.active_for_holder(cfg.session_meeting_id, voter_oid)
            weight += len(proxies)
            proxy_ids = [p.granter_user_id for p in proxies]

        ballot = VoteBallotModel(
            sys_organization_id=cfg.sys_organization_id,
            vote_config_id=cfg.id,
            choice=choice,
            weight=weight,
            proxy_grantor_user_ids=proxy_ids,
            device_id_str=device_id_str,
            signature_hash=signature_hash,
        )
        if cfg.is_secret:
            dek = crypto.unseal_dek(cfg.sealed_dek_b64)
            ballot.voter_user_id_enc = crypto.encrypt_voter_id(dek, str(voter_oid))
        else:
            ballot.voter_user_id = voter_oid

        await ballot.insert()
        cfg.ballots_cast_count += 1
        await cfg.save()

        # ---- audit chain (PPTX hard requirement) ----
        # We log the cast event but NEVER include voter_user_id for secret votes.
        # Public votes log the voter id; secret votes log only weight + choice.
        try:
            from app.modules.audit_security.enums.audit_enum import EAuditEventType
            from app.modules.audit_security.services.audit_chain_service import (
                AuditChainService,
            )
            audit_details: dict = {
                "choice": ballot.choice.value,
                "weight": ballot.weight,
                "is_secret": cfg.is_secret,
            }
            await AuditChainService(self.accept_language).emit(
                sys_organization_id=cfg.sys_organization_id,
                event_type=EAuditEventType.VOTE_CAST,
                # For SECRET votes, deliberately omit actor_user_id from the
                # audit row — the chain proves "a ballot was cast" without
                # binding it to a sénateur. PPTX slide 15 invariant.
                actor_user_id=(None if cfg.is_secret else voter_oid),
                vote_config_id=cfg.id,
                session_meeting_id=cfg.session_meeting_id,
                actor_device_id_str=device_id_str,
                details=audit_details,
            )
        except Exception:
            pass

        return ballot

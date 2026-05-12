"""TallyService — compute the aggregated VoteResultModel for a scrutin.

Idempotent: re-running on the same scrutin overwrites the result row.
Per-voter mappings NEVER surface — only weighted counts.
"""

from __future__ import annotations

import math
from typing import NamedTuple, Optional

from beanie import PydanticObjectId

from app.modules.session_meeting.models.session_meeting.session_meeting_model import (
    SessionMeetingModel,
)
from app.modules.vote.enums.vote_enum import EVoteChoice, EVoteMajorityType
from app.modules.vote.models.vote_ballot.vote_ballot_model import VoteBallotModel
from app.modules.vote.models.vote_config.vote_config_model import VoteConfigModel
from app.modules.vote.models.vote_result.vote_result_model import VoteResultModel


class _Decision(NamedTuple):
    """Output of the pure decision math.

    Carved out of `compute()` so the rule semantics (each PPTX-anchored
    majority type + the NPV/ABSTENTION exclusion) can be unit-tested
    without standing up Mongo. `compute()` owns I/O; this owns the math.
    """
    denominator: int
    required_count: int
    majority_met: bool
    decision: Optional[str]  # "ADOPTE" | "REJETE" | None (no ballots yet)


class TallyService:
    def __init__(self, accept_language: str = "fr"):
        self.accept_language = accept_language

    @staticmethod
    def _required_count(
        majority_type: EVoteMajorityType,
        custom_threshold: Optional[float],
        denominator: int,
    ) -> int:
        if denominator <= 0:
            return 0
        if majority_type == EVoteMajorityType.RELATIVE:
            return 1  # at least one POUR more than CONTRE — checked separately below
        if majority_type == EVoteMajorityType.ABSOLUE:
            return (denominator // 2) + 1
        if majority_type == EVoteMajorityType.DEUX_TIERS:
            return math.ceil(denominator * 2 / 3)
        if majority_type == EVoteMajorityType.CUSTOM:
            ratio = custom_threshold if custom_threshold is not None else 0.5
            return math.ceil(denominator * ratio)
        return 0

    @staticmethod
    def _decision(
        *,
        count_pour: int,
        count_contre: int,
        count_abstention: int,
        count_npv: int,
        majority_type: EVoteMajorityType,
        custom_threshold: Optional[float],
        total_seats: Optional[int],
    ) -> _Decision:
        """Pure decision math — no I/O.

        Denominator selection (règlement intérieur convention):
          - RELATIVE        → expressed votes only (POUR + CONTRE).
                              Tie = REJETÉ (`cp > cc`, strict).
          - ABSOLUE / 2/3 / CUSTOM → seats from the parent session.
                              `total_seats=None` falls back to (POUR+CONTRE)
                              so a missing-session edge case still yields
                              an answer rather than crashing.

        ABSTENTION + NPV count toward `ballot_headcount` (handled by the
        caller) but NEVER toward majority — for ABSOLUE/2-3/CUSTOM the
        denominator is `total_seats` so they don't dilute; for RELATIVE
        the denominator is just (POUR+CONTRE) so they're auto-excluded.

        Decision: returns None if `total_weighted == 0` (no ballots yet
        — neither ADOPTE nor REJETE applies).
        """
        cp, cc = count_pour, count_contre
        total_weighted = cp + cc + count_abstention + count_npv

        if majority_type == EVoteMajorityType.RELATIVE:
            denominator = cp + cc
            required = TallyService._required_count(
                majority_type, custom_threshold, denominator,
            )
            majority_met = cp > cc
        else:
            denominator = total_seats if total_seats is not None else (cp + cc)
            required = TallyService._required_count(
                majority_type, custom_threshold, denominator,
            )
            majority_met = cp >= required

        decision: Optional[str] = None
        if total_weighted > 0:
            decision = "ADOPTE" if majority_met else "REJETE"

        return _Decision(
            denominator=denominator,
            required_count=required,
            majority_met=majority_met,
            decision=decision,
        )

    async def compute(self, vote_config_id: str | PydanticObjectId) -> VoteResultModel:
        cfg_oid = vote_config_id if isinstance(vote_config_id, PydanticObjectId) else PydanticObjectId(vote_config_id)
        cfg = await VoteConfigModel.get(cfg_oid)
        if cfg is None:
            raise ValueError(f"Scrutin introuvable: {vote_config_id}")

        ballots = await VoteBallotModel.find(
            VoteBallotModel.vote_config_id == cfg.id,
        ).to_list()

        # Weighted counts
        cp = cc = ca = cn = 0
        for b in ballots:
            w = max(1, b.weight)
            if b.choice == EVoteChoice.POUR:
                cp += w
            elif b.choice == EVoteChoice.CONTRE:
                cc += w
            elif b.choice == EVoteChoice.ABSTENTION:
                ca += w
            elif b.choice == EVoteChoice.NE_PREND_PAS_PART_AU_VOTE:
                cn += w
        total_weighted = cp + cc + ca + cn

        # Resolve the seat count for ABSOLUE/2-3/CUSTOM denominators. RELATIVE
        # ignores it (uses POUR+CONTRE), so we skip the I/O hop in that case.
        total_seats: Optional[int] = None
        if cfg.majority_type != EVoteMajorityType.RELATIVE:
            session = await SessionMeetingModel.get(cfg.session_meeting_id)
            total_seats = session.total_seats if session else None

        # Pure decision math (règlement intérieur conventions live in
        # `_decision`; tests in tests/unit/test_tally_decision.py).
        d = self._decision(
            count_pour=cp,
            count_contre=cc,
            count_abstention=ca,
            count_npv=cn,
            majority_type=cfg.majority_type,
            custom_threshold=cfg.majority_custom_threshold,
            total_seats=total_seats,
        )
        denominator = d.denominator
        required_count = d.required_count
        majority_met = d.majority_met
        decision = d.decision

        existing = await VoteResultModel.find_one(
            VoteResultModel.vote_config_id == cfg.id,
        )
        if existing is None:
            result = VoteResultModel(
                sys_organization_id=cfg.sys_organization_id,
                vote_config_id=cfg.id,
                count_pour=cp,
                count_contre=cc,
                count_abstention=ca,
                count_npv=cn,
                ballot_headcount=len(ballots),
                total_weighted=total_weighted,
                majority_required_count=required_count,
                majority_met=majority_met,
                decision=decision,
            )
            await result.insert()
        else:
            existing.count_pour = cp
            existing.count_contre = cc
            existing.count_abstention = ca
            existing.count_npv = cn
            existing.ballot_headcount = len(ballots)
            existing.total_weighted = total_weighted
            existing.majority_required_count = required_count
            existing.majority_met = majority_met
            existing.decision = decision
            await existing.save()
            result = existing
        return result

"""Security-questions service.

Owns the read/write side of the `cfg_user_question_response`
collection: the user picks N questions and supplies an answer per
question. The plaintext answer is normalised (`.strip().lower()`)
and hashed with Argon2 before persisting. Plaintext NEVER touches
the database — `response_hash` is the canonical field; the legacy
`response` field is left untouched (and unset for new rows).

Two consumer flows:

  1. Authenticated set (`POST /auth/security-questions/set`):
     the logged-in user enrolls or re-enrolls. `replace_user_answers`
     wipes any prior rows for the user and writes the new set
     atomically (best-effort — Mongo doesn't give us a tx without a
     replica set; the wipe-then-write window is small).

  2. Unauthenticated forgot-password verify (step 2 of 3):
     the caller has already proven they own the `username`
     (step 1 returned the questions + a scope token). They send
     the same N answers; `verify_user_answers` hashes-and-compares
     each. ALL N must match — partial matches are NOT a quorum.

Note on lockout: lockout for the forgot-password Q&A check lives
ABOVE this service, in the controller, because it composes with
IP rate-limiting + username-targeting heuristics that are
session-scoped, not user-scoped. This service only owns the
cryptographic compare.
"""

from __future__ import annotations

from typing import Iterable, Optional

from beanie import PydanticObjectId
from beanie.operators import In

from app.modules.auth.models.cfg_user_question_response.cfg_user_question_response_model import (
    CfgUserQuestionResponseModel,
)
from app.modules.auth.services.password.password_service import PasswordService


# ── Errors ──────────────────────────────────────────────────────────


class SecurityQuestionsError(Exception):
    """Base class for security-questions domain errors."""


class SecurityQuestionsNotSetException(SecurityQuestionsError):
    """User has not enrolled any answers yet — /forgot-password/start
    surfaces this so the client knows to fall back to "contact
    administrator" instead of asking unanswerable questions."""


class SecurityQuestionsMismatchException(SecurityQuestionsError):
    """One or more provided answers did not hash-match the stored
    `response_hash`. Carries `matched`/`total` so the controller can
    decide whether to count this as one failed attempt or many."""

    def __init__(self, matched: int, total: int):
        super().__init__(
            f"Réponses incorrectes ({matched}/{total} correctes)."
        )
        self.matched = matched
        self.total = total


# ── Service ─────────────────────────────────────────────────────────


class SecurityQuestionsService:
    """Stateless. Construct per-request (cheap)."""

    @staticmethod
    def _normalise(answer: str) -> str:
        """Canonical normalisation applied on BOTH write + verify.
        Trim whitespace, drop case. Keeping this in one helper means
        a future tweak (e.g. accent-stripping) lands in exactly one
        place."""
        return (answer or "").strip().lower()

    # ── Reads ───────────────────────────────────────────────────────

    async def list_user_question_ids(
        self,
        *,
        sys_user_id: PydanticObjectId,
    ) -> list[PydanticObjectId]:
        """Return the `cfg_user_question_id`s the user has enrolled
        (no answers, no hashes — just the question ids so the front
        can hydrate them via the questions catalog)."""
        rows = await CfgUserQuestionResponseModel.find(
            CfgUserQuestionResponseModel.sys_user_id == sys_user_id
        ).to_list()
        return [r.cfg_user_question_id for r in rows]

    async def has_enrolled_questions(
        self,
        *,
        sys_user_id: PydanticObjectId,
    ) -> bool:
        count = await CfgUserQuestionResponseModel.find(
            CfgUserQuestionResponseModel.sys_user_id == sys_user_id
        ).count()
        return count > 0

    # ── Writes ──────────────────────────────────────────────────────

    async def replace_user_answers(
        self,
        *,
        sys_user_id: PydanticObjectId,
        answers: Iterable[tuple[str, str]],
    ) -> int:
        """Replace the user's question-answer set.

        `answers` is an iterable of (cfg_user_question_id_str, plain_answer)
        tuples. Returns the number of rows written.

        Implementation: wipe all existing rows for the user, then
        insert the new set. Not strictly atomic (no Mongo tx required
        for the deployment), but the wipe→write window is sub-second
        and protected by the controller-level lock on the user's own
        actions (only the authenticated user can hit `/set`).
        """
        await CfgUserQuestionResponseModel.find(
            CfgUserQuestionResponseModel.sys_user_id == sys_user_id
        ).delete()

        written = 0
        for qid_str, plain in answers:
            qid = PydanticObjectId(str(qid_str))
            row = CfgUserQuestionResponseModel(
                sys_user_id=sys_user_id,
                cfg_user_question_id=qid,
                response=None,  # legacy plaintext column stays empty
                response_hash=PasswordService.hash_password(
                    self._normalise(plain)
                ),
            )
            await row.insert()
            written += 1
        return written

    # ── Verify ──────────────────────────────────────────────────────

    async def verify_user_answers(
        self,
        *,
        sys_user_id: PydanticObjectId,
        answers: Iterable[tuple[str, str]],
    ) -> int:
        """Verify a batch of submitted answers against the stored hashes.

        `answers` is `(cfg_user_question_id_str, plain_answer)` tuples.
        Returns the number of correct matches on success. On any
        mismatch raises [SecurityQuestionsMismatchException].

        Behaviour:
          - The set of question_ids submitted MUST equal the set the
            user has enrolled (no skipping a question to bypass).
          - Comparison normalises (trim + lower) BEFORE Argon2 verify.
          - One miss = full failure: we don't tell the client which
            answer was wrong (forensic resistance — leaks make the
            channel useful as a credential probe).

        Raises [SecurityQuestionsNotSetException] if the user has no
        enrolled rows.
        """
        # Pull all rows for the user in one query, then bucket by qid.
        stored = await CfgUserQuestionResponseModel.find(
            CfgUserQuestionResponseModel.sys_user_id == sys_user_id
        ).to_list()
        if not stored:
            raise SecurityQuestionsNotSetException(
                "Aucune question de sécurité configurée pour ce compte."
            )

        stored_by_qid: dict[str, CfgUserQuestionResponseModel] = {
            str(r.cfg_user_question_id): r for r in stored
        }

        submitted: dict[str, str] = {}
        for qid_str, plain in answers:
            submitted[str(qid_str)] = plain

        # Set-equality check: same number AND same ids.
        if set(submitted.keys()) != set(stored_by_qid.keys()):
            raise SecurityQuestionsMismatchException(
                matched=0, total=len(stored_by_qid)
            )

        matched = 0
        total = len(stored_by_qid)
        for qid, plain in submitted.items():
            row = stored_by_qid[qid]
            if not row.response_hash:
                # Legacy row without a hash — cannot verify cryptographically.
                # Skip but count it as a miss so we don't silently let a
                # half-migrated row act as a backdoor.
                continue
            ok = PasswordService.verify_password(
                self._normalise(plain), row.response_hash
            )
            if ok:
                matched += 1

        if matched != total:
            raise SecurityQuestionsMismatchException(
                matched=matched, total=total
            )
        return matched

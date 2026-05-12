"""`VoteCryptoService` — secret-vote envelope encryption.

Locks the PPTX slide-15 invariant: *"Votes secrets : il est impossible
de remonter jusqu'au votant"*. Three layers tested:

  1. **DEK lifecycle** — `generate_dek` / `seal_dek` / `unseal_dek`.
     Round-trip; org-scoped sealing (one org's master key cannot
     unseal another's seal); tamper detection.

  2. **Voter id encryption** — `encrypt_voter_id` / `decrypt_voter_id`.
     Round-trip; per-resolution isolation (different DEK ⇒ ciphertext
     undecipherable); tamper detection.

  3. **Redaction + self-test** — `redacted_config_payload` masks the
     `sealed_dek_b64` field; `self_test` round-trips end-to-end.

Tests run on real `cryptography.fernet` — these aren't crypto-stubbed
like the BallotService suite. The crypto library is the one we trust;
this file proves we wired it correctly.
"""
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from cryptography.fernet import Fernet

from app.modules.vote.services.vote_crypto_service import VoteCryptoService


# Two distinct master keys representing two organisations. Real Fernet
# keys (32 url-safe base64 bytes) so seal/unseal goes through the
# library's actual KDF.
_ORG_A_MASTER = Fernet.generate_key()
_ORG_B_MASTER = Fernet.generate_key()


# ── DEK generation ─────────────────────────────────────────────────


def test_generate_dek_is_fernet_valid() -> None:
    """The generated DEK must construct a Fernet instance — that's
    the contract for `encrypt_voter_id`/`decrypt_voter_id`."""
    svc = VoteCryptoService(master_key_bytes=_ORG_A_MASTER)
    dek = svc.generate_dek()
    # Will raise if not a valid Fernet key (32 url-safe base64 bytes).
    Fernet(dek)


def test_generate_dek_is_unique_per_call() -> None:
    """Per-resolution isolation rests on each scrutin getting its own
    DEK. Two consecutive calls must produce different keys."""
    svc = VoteCryptoService(master_key_bytes=_ORG_A_MASTER)
    a = svc.generate_dek()
    b = svc.generate_dek()
    assert a != b


# ── DEK seal/unseal round-trip ─────────────────────────────────────


def test_seal_unseal_round_trip() -> None:
    svc = VoteCryptoService(master_key_bytes=_ORG_A_MASTER)
    dek = svc.generate_dek()
    sealed = svc.seal_dek(dek)
    assert isinstance(sealed, str)  # base64 string for MongoDB
    assert svc.unseal_dek(sealed) == dek


def test_sealed_payload_is_base64_ascii() -> None:
    """Stored on `VoteConfigModel.sealed_dek_b64` — must be ASCII so
    Mongo BSON keeps it as a plain string, no UTF-8 surprises."""
    svc = VoteCryptoService(master_key_bytes=_ORG_A_MASTER)
    sealed = svc.seal_dek(svc.generate_dek())
    sealed.encode("ascii")  # raises UnicodeEncodeError if not ASCII


def test_sealing_same_dek_twice_produces_different_output() -> None:
    """Fernet wraps each call with a fresh IV. Two seals of the same
    DEK ⇒ two distinct ciphertexts. Both must unseal to the same
    plaintext. This is what makes the seal IND-CPA secure (an
    attacker can't tell two scrutins were sealed with the same DEK
    just by comparing the stored sealed_dek_b64 strings)."""
    svc = VoteCryptoService(master_key_bytes=_ORG_A_MASTER)
    dek = svc.generate_dek()
    s1 = svc.seal_dek(dek)
    s2 = svc.seal_dek(dek)
    assert s1 != s2
    assert svc.unseal_dek(s1) == svc.unseal_dek(s2) == dek


# ── Cross-org seal isolation ───────────────────────────────────────


def test_cross_org_unseal_fails() -> None:
    """A DEK sealed with org A's master key cannot be unsealed by
    org B's. Defends against cross-tenant tally attempts: even with
    full Mongo read, org B can't decode org A's secret votes."""
    svc_a = VoteCryptoService(master_key_bytes=_ORG_A_MASTER)
    svc_b = VoteCryptoService(master_key_bytes=_ORG_B_MASTER)

    sealed_by_a = svc_a.seal_dek(svc_a.generate_dek())
    with pytest.raises(ValueError, match="invalide ou altéré"):
        svc_b.unseal_dek(sealed_by_a)


# ── Tampered seal detection ────────────────────────────────────────


def test_tampered_seal_raises() -> None:
    """One altered byte in the sealed_b64 string trips Fernet's HMAC."""
    svc = VoteCryptoService(master_key_bytes=_ORG_A_MASTER)
    sealed = svc.seal_dek(svc.generate_dek())
    # Flip a character mid-string.
    tampered = sealed[:10] + ("A" if sealed[10] != "A" else "B") + sealed[11:]
    with pytest.raises(ValueError, match="invalide ou altéré"):
        svc.unseal_dek(tampered)


def test_garbage_seal_raises() -> None:
    """A non-base64 input shouldn't crash the service — it should
    raise the typed error the BallotService catches."""
    svc = VoteCryptoService(master_key_bytes=_ORG_A_MASTER)
    with pytest.raises(ValueError, match="invalide ou altéré"):
        svc.unseal_dek("definitely-not-base64-???")


# ── Voter id encryption round-trip ─────────────────────────────────


def test_voter_id_round_trip() -> None:
    svc = VoteCryptoService(master_key_bytes=_ORG_A_MASTER)
    dek = svc.generate_dek()
    voter = "000000000000000000000099"  # ObjectId hex string

    ciphertext = svc.encrypt_voter_id(dek, voter)
    assert isinstance(ciphertext, str)
    assert ciphertext != voter  # must actually encrypt
    assert svc.decrypt_voter_id(dek, ciphertext) == voter


def test_voter_id_ciphertext_is_distinct_per_call() -> None:
    """Same voter, same DEK, two encrypt calls ⇒ two different
    ciphertexts (Fernet IV again). Both decrypt to the same voter.

    Critical property: if ciphertexts were deterministic, an attacker
    counting identical strings in `voter_user_id_enc` could infer
    "two ballots from the same voter" — collapsing the secret-vote
    guarantee for repeat patterns. IND-CPA prevents that."""
    svc = VoteCryptoService(master_key_bytes=_ORG_A_MASTER)
    dek = svc.generate_dek()
    voter = "000000000000000000000099"
    c1 = svc.encrypt_voter_id(dek, voter)
    c2 = svc.encrypt_voter_id(dek, voter)
    assert c1 != c2
    assert svc.decrypt_voter_id(dek, c1) == svc.decrypt_voter_id(dek, c2) == voter


def test_voter_id_per_resolution_isolation() -> None:
    """Two distinct DEKs (= two scrutins) ⇒ a ciphertext from one
    scrutin can't be decrypted with the other's DEK."""
    svc = VoteCryptoService(master_key_bytes=_ORG_A_MASTER)
    dek_a = svc.generate_dek()
    dek_b = svc.generate_dek()
    assert dek_a != dek_b

    ciphertext_under_a = svc.encrypt_voter_id(dek_a, "voter-x")
    with pytest.raises(ValueError, match="altéré ou DEK incorrect"):
        svc.decrypt_voter_id(dek_b, ciphertext_under_a)


def test_tampered_voter_ciphertext_raises() -> None:
    """A flipped byte in `voter_user_id_enc` trips Fernet's HMAC.
    The BallotService dup-detection catches this and skips the row,
    so honest voters aren't blocked by tampered evidence."""
    svc = VoteCryptoService(master_key_bytes=_ORG_A_MASTER)
    dek = svc.generate_dek()
    ciphertext = svc.encrypt_voter_id(dek, "voter-x")

    tampered = ciphertext[:10] + ("Z" if ciphertext[10] != "Z" else "Y") + ciphertext[11:]
    with pytest.raises(ValueError, match="altéré ou DEK incorrect"):
        svc.decrypt_voter_id(dek, tampered)


# ── Redaction ──────────────────────────────────────────────────────


def test_redacted_payload_masks_sealed_dek() -> None:
    """Defence-in-depth: even if a future endpoint accidentally
    returns the raw model dict, the redactor scrubs the sealed key."""
    svc = VoteCryptoService(master_key_bytes=_ORG_A_MASTER)
    payload = {
        "id": "abc",
        "title": "Test scrutin",
        "is_secret": True,
        "sealed_dek_b64": "very-secret-base64-blob",
    }
    out = svc.redacted_config_payload(payload)
    assert out["sealed_dek_b64"] == "<REDACTED:sealed_dek>"
    # Other fields untouched.
    assert out["id"] == "abc"
    assert out["title"] == "Test scrutin"
    assert out["is_secret"] is True


def test_redacted_payload_does_not_mutate_input() -> None:
    """The caller's dict shouldn't be modified in-place — the redactor
    returns a copy. A shared payload mutated by the redactor would
    leak through other code paths."""
    svc = VoteCryptoService(master_key_bytes=_ORG_A_MASTER)
    payload = {"sealed_dek_b64": "ORIGINAL"}
    svc.redacted_config_payload(payload)
    assert payload["sealed_dek_b64"] == "ORIGINAL"


def test_redacted_payload_no_op_when_field_absent() -> None:
    """A public-vote payload has no `sealed_dek_b64`. The redactor
    must not add the field as a side effect."""
    svc = VoteCryptoService(master_key_bytes=_ORG_A_MASTER)
    out = svc.redacted_config_payload({"id": "abc", "is_secret": False})
    assert "sealed_dek_b64" not in out


# ── self_test (health-check round-trip) ───────────────────────────


def test_self_test_passes_on_healthy_service() -> None:
    """The end-to-end happy path: generate → seal → unseal → encrypt
    voter → decrypt voter. Used by v1.1 health checks."""
    svc = VoteCryptoService(master_key_bytes=_ORG_A_MASTER)
    assert svc.self_test() is True


def test_self_test_returns_false_on_broken_master_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If `unseal_dek` somehow returns the wrong bytes (broken key
    derivation, bug in the library), self_test must return False
    rather than raise — health checks downgrade gracefully."""
    svc = VoteCryptoService(master_key_bytes=_ORG_A_MASTER)
    # Corrupt unseal so the round-trip assertion fails.
    monkeypatch.setattr(svc, "unseal_dek", lambda _s: b"wrong-bytes")
    assert svc.self_test() is False


# ── for_org → KmsResolverService integration ──────────────────────


@pytest.mark.asyncio
async def test_for_org_resolves_master_key_via_kms_resolver(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`for_org` is the single supported entry point for production
    paths that need crypto. It must call `KmsResolverService.resolve_for_org`
    with the org id and bind the resolved key to the returned instance.

    A regression where it silently falls back to the global key would
    break per-org isolation in multi-tenant deployments."""
    from beanie import PydanticObjectId

    org_id = PydanticObjectId()
    resolved_key = Fernet.generate_key()

    # Stub the KMS resolver. Late import — same pattern as the
    # production code path uses, so the monkeypatch covers it.
    import app.modules.security.services.kms.kms_resolver_service as kms
    resolve_mock = AsyncMock(return_value=resolved_key)
    monkeypatch.setattr(kms.KmsResolverService, "resolve_for_org", resolve_mock)

    svc = await VoteCryptoService.for_org(org_id, accept_language="fr")
    resolve_mock.assert_awaited_once_with(org_id)

    # Round-trip via the resolved key — proves the binding is correct.
    dek = svc.generate_dek()
    sealed = svc.seal_dek(dek)
    assert svc.unseal_dek(sealed) == dek
    # Sanity: a different master rejects the seal.
    other = VoteCryptoService(master_key_bytes=_ORG_B_MASTER)
    with pytest.raises(ValueError, match="invalide ou altéré"):
        other.unseal_dek(sealed)

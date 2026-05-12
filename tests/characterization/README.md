# Characterization tests — senat_digit_api

These tests are **not** functional tests. They pin the *current observable behavior* of the API so the §3.4 restructure pass can prove it changed nothing.

See `SN_APPS/_planning/05_characterization_harness.md` for the full workflow and rationale.

## Workflow

```bash
# 1. Capture baseline (run ONCE before any restructure work)
pytest tests/characterization --snapshot-update

# 2. Refactor freely.

# 3. Verify (zero diffs = behavior preserved)
pytest tests/characterization
```

## Prerequisites

- Local MongoDB at the URL in `CHAR_DB_URL` (default `mongodb://localhost:27017`).
- A `.env.local` populated from `.env.example`.
- All requirements installed (`pip install -r requirements.txt`).

## Volatile field redaction

Wall-clock timestamps, UUIDs, JWT bodies, signed-URL signatures are all redacted to `<REDACTED:type>` placeholders so snapshots stay deterministic. See `snapshot.py::REDACT`.

"""Capture/redact/diff helpers for the characterization harness.

Per the spec in `_planning/05_characterization_harness.md`. Volatile fields
(JWTs, UUIDs, timestamps, signed URLs) are redacted so snapshots stay
deterministic across runs. Add a redaction rule once in REDACT — never inline.
"""
import json
import re
from pathlib import Path
from typing import Any

SNAPSHOT_DIR = Path(__file__).parent / "snapshots"
SNAPSHOT_DIR.mkdir(exist_ok=True)

PINNED_HEADERS = (
    "content-type",
    "cache-control",
    "x-rate-limit-limit",
    "x-rate-limit-remaining",
)

REDACT = {
    "access_token":    "<REDACTED:jwt>",
    "refresh_token":   "<REDACTED:jwt>",
    "id":              "<REDACTED:uuid>",
    "_id":             "<REDACTED:uuid>",
    "uuid":            "<REDACTED:uuid>",
    "identifier":      "<REDACTED:uuid>",
    "created_at":      "<REDACTED:ts>",
    "updated_at":      "<REDACTED:ts>",
    "signed_at":       "<REDACTED:ts>",
    "expires_at":      "<REDACTED:ts>",
    "performed_at_utc":"<REDACTED:ts>",
    "signature":       "<REDACTED:sig>",
    "signed_url":      "<REDACTED:url>",
    "etag":            "<REDACTED:etag>",
    "audit_prev_hash": "<REDACTED:hash>",
    "audit_hash":      "<REDACTED:hash>",
    "consumer_hash":   "<REDACTED:hash>",
    "consumer_key":    "<REDACTED:key>",
}

REDACT_PATTERNS = [
    (re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b"),
     "<REDACTED:uuid>"),
    (re.compile(r"\b\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z?\b"),
     "<REDACTED:ts>"),
    (re.compile(r"\b[0-9a-f]{24}\b"), "<REDACTED:objectid>"),  # Mongo ObjectId
]


def _redact(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: (REDACT[k] if k in REDACT else _redact(v)) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_redact(v) for v in obj]
    if isinstance(obj, str):
        s = obj
        for pat, repl in REDACT_PATTERNS:
            s = pat.sub(repl, s)
        return s
    return obj


def _pin_headers(headers) -> dict:
    return {k: v for k, v in headers.items() if k.lower() in PINNED_HEADERS}


def capture(response) -> dict:
    try:
        body = response.json()
    except Exception:
        body = {"__non_json_body__": response.text}
    return {
        "status": response.status_code,
        "headers": _pin_headers(dict(response.headers)),
        "body": _redact(body),
    }


def path_for(scenario_name: str) -> Path:
    return SNAPSHOT_DIR / f"{scenario_name}.json"


def write(scenario_name: str, snapshot: dict) -> None:
    path_for(scenario_name).write_text(
        json.dumps(snapshot, indent=2, sort_keys=True, ensure_ascii=False)
    )


def read(scenario_name: str) -> dict | None:
    p = path_for(scenario_name)
    if not p.exists():
        return None
    return json.loads(p.read_text())


def diff(expected: dict, actual: dict) -> str | None:
    if expected == actual:
        return None
    import difflib
    e = json.dumps(expected, indent=2, sort_keys=True, ensure_ascii=False).splitlines()
    a = json.dumps(actual,   indent=2, sort_keys=True, ensure_ascii=False).splitlines()
    return "\n".join(difflib.unified_diff(e, a, fromfile="baseline", tofile="current", lineterm=""))

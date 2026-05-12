"""Snapshot-driven characterization tests.

This file is the contract that the §3.4 restructure pass must not break.
Run with `--snapshot-update` once after the clone-and-rename to capture
baseline; thereafter every run compares against the baseline and fails
on any drift.
"""
import pytest

from .scenarios import SCENARIOS
from . import snapshot as snap


@pytest.mark.parametrize("sc", SCENARIOS, ids=lambda s: s.name)
def test_scenario(sc, client, tokens, snapshot_update):
    headers = dict(sc.headers)
    if sc.role != "anon" and tokens.get(sc.role):
        headers["Authorization"] = f"Bearer {tokens[sc.role]}"

    r = client.request(sc.method, sc.path, json=sc.body, headers=headers)
    captured = snap.capture(r)

    if snapshot_update:
        snap.write(sc.name, captured)
        return

    expected = snap.read(sc.name)
    assert expected is not None, (
        f"No baseline snapshot for {sc.name}. "
        f"Run `pytest tests/characterization --snapshot-update` once before refactoring."
    )
    diff = snap.diff(expected, captured)
    assert diff is None, f"Behavior drift in {sc.name}:\n{diff}"

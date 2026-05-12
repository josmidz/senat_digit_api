"""Characterization scenarios.

Add a scenario when:
  - It exercises an endpoint or workflow that ANY downstream depends on
  - It hits a code path the §3.4 restructure is likely to touch
    (controllers, services, RLS, RBAC, seeds, get_formated_data)

Don't add a scenario for code paths under active feature development or
anything explicitly slated for behavior change in the restructure log.
"""
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Scenario:
    name: str
    method: str
    path: str
    role: str = "anon"
    body: Any = None
    headers: dict = field(default_factory=dict)
    side_effects: tuple = ()


# Paths use the `/api/v1` mount prefix as registered in `app.main`. After the
# restructure pass normalizes routes to `/verb/resource` we expect these to
# remain stable; any drift in path naming is an intentional rename and goes
# in `_planning/04_restructure_log.md`.
SCENARIOS: list[Scenario] = [
    # ---- ping / health ----
    Scenario("health.openapi", "GET", "/openapi.json"),

    # ---- seed-derived endpoints (initial coverage; expand after seed wiring) ----
    # Add scenarios once the §3.4 restructure pass renames endpoints to
    # /verb/resource. Until then only the openapi spec is pinned, which still
    # surfaces the full registered route table — any route addition/removal
    # during a "behavior-preserving" refactor will show up as a snapshot diff.
]

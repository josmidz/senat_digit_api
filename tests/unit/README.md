# `tests/unit/` — fast, deterministic service-level tests

Mock-only. No Mongo, no Motor, no `init_beanie`. Each file targets one
service module under `app/modules/`; the conftest provides shared
factories + autouse fixtures that defang the side-effect imports.

The whole suite runs in **<300 ms** — fast enough that you can pair
write-test + run on every save during development.

```
$ source .venv/bin/activate
$ set -a; source .env.local; set +a   # ENCRYPTION_KEY for crypto tests
$ python -m pytest tests/unit -W ignore
============================== 210 passed in 0.25s ==============================
```

The companion smoke harness (`bash/smoke/run_full_check.sh`) hits a
real running API for RBAC reachability assertions per role. Unit tests
cover service-level logic; smokes cover wiring + RBAC. They're
complementary — pick one based on what you're locking in.


## Harness conventions

### 1. Why mock-only

A unit test that needs a live Mongo + initialised Beanie collections
takes ~1 s of fixture setup before the first assertion. Multiplied
across 200 tests, that's 3+ minutes per run — too slow to live in the
inner loop.

Mock-only tests run in ~1 ms each, which means:

- Pre-commit hooks can run them on every commit without complaint.
- CI catches regressions in seconds.
- TDD-style `pytest --watch` is actually viable.

The trade-off: you stub the I/O boundary. The contract you're locking
in is "given these inputs, the service produces these mutations and
calls" — not "given a real DB, the round-trip works." Smokes cover the
latter.


### 2. Build models without Beanie init: `model_construct`

`Document.__init__` calls `get_motor_collection()`, which raises
`CollectionWasNotInitialized` unless `init_beanie()` was run. We don't
want to run it (slow, needs a real Mongo).

The factories in `conftest.py` use `Model.model_construct(...)` — a
Pydantic v2 escape hatch that bypasses both validation AND
`__init__`. Result: a fully-typed in-memory model instance ready to
hand to a service, no DB needed.

```python
def make_config(*, status=EVoteStatus.PROJET, ballots_cast_count=0, ...):
    return VoteConfigModel.model_construct(
        id=PydanticObjectId(),
        identifier="test-id",
        sys_organization_id=PydanticObjectId(),
        ...
        status=status,
        ballots_cast_count=ballots_cast_count,
    )
```

Defaults mirror the create endpoint's defaults so tests state
overrides explicitly. Add a new field on the model? Add it to the
factory with the matching default — tests will fail loudly if you
forget.


### 3. Patch class-level descriptors: `_ExprStub`

Beanie's query DSL evaluates expressions like
`Model.field == value` at runtime — that requires a class-level
`ExpressionField` descriptor that's only set up by `init_beanie`.
Without init, Pydantic v2's `__getattr__` falls through to
`AttributeError`.

The `_ExprStub` class supports every comparison + sort operator the
DSL needs (returning itself from each one), so the resulting
expression flows through the patched `find` / `find_one` /
`sort` cleanly:

```python
class _ExprStub:
    def __eq__(self, other): return self
    def __ne__(self, other): return self
    def __ge__(self, other): return self
    def __le__(self, other): return self
    def __gt__(self, other): return self
    def __lt__(self, other): return self
    def __pos__(self): return self  # +Field for ascending sort
    def __neg__(self): return self  # -Field for descending sort
    def __hash__(self): return 0


# In your fixture:
for field in ("sys_organization_id", "sequence_number"):
    monkeypatch.setattr(AuditEventModel, field, _ExprStub(), raising=False)
```

`_ExprStub` is duplicated across test files rather than centralised —
each file declares only the fields it needs, which makes the contract
visible inline. If you find yourself copying it for the third time
in a single file, factor it out into the fixture.


### 4. Patch `get_motor_collection` when the service constructs a model

If the service under test does `Model(...)` directly inside an async
method (rather than only reading via classmethods), the inner
`Document.__init__` still calls `get_motor_collection`. Patch it to a
MagicMock so the constructor proceeds without raising:

```python
monkeypatch.setattr(
    VoteBallotModel,
    "get_motor_collection",
    classmethod(lambda cls: MagicMock(name="motor_collection_stub")),
)
```

Beanie uses the returned object as a presence check during `__init__`;
nothing actually inserts via it (we patch `.insert` separately).


### 5. Mock the fluent query API

Beanie queries are `Model.find(...).find(...).sort(...).limit(...).to_list()`.
Each method returns a Query object so chaining works. Mock them with a
single MagicMock that returns itself from every chained method, plus
an async `to_list` returning your test rows:

```python
stub = MagicMock(name="QueryStub")
stub.find.return_value = stub
stub.sort.return_value = stub
stub.limit.return_value = stub

async def fake_to_list():
    return rows
stub.to_list = fake_to_list

monkeypatch.setattr(Model, "find", lambda *a, **kw: stub)
```

This pattern shows up in `test_audit_chain_verify.py`,
`test_ballot_service.py`, `test_proxy_service.py`, and
`test_notification_service.py`. If a service adds a new chained
method (`.skip(N)`, `.batch(N)`), extend the stub to return itself.


### 6. Bypass Pydantic v2's `__setattr__` guard

Pydantic v2 blocks regular attribute assignment on model instances —
`cfg.save = AsyncMock()` raises `ValueError("…object has no field 'save'")`.
`object.__setattr__` sidesteps it:

```python
save_mock = AsyncMock()
object.__setattr__(cfg, "save", save_mock)
```

Used to inject `.save` / `.insert` no-ops on the specific instances a
service hands to its persistence calls.


### 7. The capturing-insert pattern (notification tests)

When the service constructs a Beanie model inside the call (rather
than receiving one), test assertions need access to the actual
constructed instance. Replace `Model.insert` with a closure that
appends `self` to a list — every constructed row lands in the list,
fully-validated (so any field validators ran):

```python
inserted: List[NtfNotificationModel] = []

async def fake_insert(self):
    inserted.append(self)
    return self
monkeypatch.setattr(NtfNotificationModel, "insert", fake_insert)

# In tests:
await svc.emit_one(...)
assert inserted[0].title == "expected"
```

This is how `test_notification_service.py` validates that the
title-lowercase validator on `NtfNotificationModel` actually fires
during emit — without going through Mongo.


### 8. Defang side-effect imports: `freeze_audit_and_notify`

Several services have `try: ... except: pass` blocks that import +
emit audit-chain or notification events. Without mocks, those imports
trigger Mongo I/O and crash the test. The autouse fixture in
`conftest.py` replaces both classes with no-op stand-ins:

```python
@pytest.fixture(autouse=True)
def freeze_audit_and_notify(monkeypatch):
    class _NoopAudit:
        def __init__(self, *a, **kw): ...
        async def emit(self, *a, **kw): return None

    class _NoopNotif:
        def __init__(self, *a, **kw): ...
        async def emit_to_session_participants(self, *a, **kw): return None

    monkeypatch.setattr(ac, "AuditChainService", _NoopAudit)
    monkeypatch.setattr(ns, "NotificationService", _NoopNotif)
```

If your test file specifically wants to assert what audit/notif emits
look like, override these in a local fixture with a *capturing* class
(see `cast_harness` in `test_ballot_service.py`).


## Recipe — adding tests for a new service

1. Read the service file. List every Beanie classmethod it touches
   (`Model.get`, `Model.find`, `Model.find_one`, `Model.insert`, etc.)
   and every class-level field used in query expressions.

2. If the service constructs models directly (`Model(...)`), add the
   `get_motor_collection` patch in your fixture. Otherwise skip it.

3. Build a `harness` fixture in the test file that takes the
   per-test inputs (existing rows, configurable returns) and wires
   the relevant classmethods to AsyncMocks. Stub class-level fields
   with `_ExprStub`. Return a SimpleNamespace exposing the mocks for
   call-arity assertions.

4. Write a factory `_make_*` (or extend `make_config` / `make_ballot`
   in conftest if it's broadly useful) that returns a
   `model_construct`'d instance with the fields the test cares about.

5. Test invariants in this order: input gates (status checks, dup
   detection) → happy paths → side-effect emissions (audit / notif).
   Each test should assert *both* the return value AND the calls
   that should/shouldn't have fired.

6. Aim for one parametrize-table per invariant (e.g. status-gate ×
   every disallowed status). Keep individual tests small.

7. Run `pytest tests/unit/test_<service>.py -W ignore -v` while
   iterating; switch to the full suite (`pytest tests/unit -W ignore`)
   for the final pass.


## Coverage map

| File | Service | Tests |
|------|---------|-------|
| `test_vote_fsm_transitions.py` | VoteService FSM matrix | 38 |
| `test_vote_change_type_live.py` | VoteService change_type_live | 14 |
| `test_vote_transitions_integration.py` | VoteService FSM via public methods | 17 |
| `test_tally_required_count.py` | TallyService threshold formulas | 33 |
| `test_tally_decision.py` | TallyService rule semantics | 20 |
| `test_ballot_service.py` | BallotService cast (incl. real bug fix) | 23 |
| `test_vote_crypto_service.py` | VoteCryptoService (real Fernet) | 18 |
| `test_proxy_service.py` | ProxyService assign/revoke/active | 11 |
| `test_audit_chain_hash.py` | Audit hash construction | 17 |
| `test_audit_chain_verify.py` | Audit chain verification | 7 |
| `test_audit_chain_emit.py` | Audit chain emit (link + retry + lock) | 16 |
| `test_notification_service.py` | NotificationService emit + fan-out | 18 |
| `test_kms_resolver_service.py` | KmsResolverService per-org → global fallback | 18 |
| `test_session_service.py` | SessionService FSM + transitions + set_mode | 41 |
| `test_quorum_service.py` | QuorumService is_met arithmetic + shape | 12 |
| `test_agenda_service.py` | AgendaService activate/reorder/publish | 16 |
| `test_presence_service.py` | PresenceService sign + idempotent + status derivation | 18 |
| `test_parole_service.py` | ParoleService FSM + dispatch + queue | 49 |
| `test_document_service.py` | DocumentService version chain + amendment FSM + publish | 33 |
| `test_permission_check_middleware.py` | PermissionCheckMiddleware RBAC enforcement + audit | 18 |
| `test_token_service.py` | TokenService JWT create/verify (audience binding + expiry + tamper) | 21 |
| `test_auth_by_pass_middleware.py` | AuthByPassMiddleware best-effort populator + active-account gate | 17 |
| `test_rls_service.py` | RowLevelSecurityService grant priority + fail-closed | 22 |
| `test_rls_middleware.py` | RowLevelSecurityMiddleware skip-context setter | 5 |
| `test_sudo_check_middleware.py` | SudoActionCheckMiddleware sudo enforcement (pure helpers + ASGI branches) | 32 |
| `test_sudo_action_middleware.py` | sudo_action_middleware DI helper (defensive defaults + Redis validation + TOTP) | 13 |

Critical invariants locked: vote FSM transitions, mid-scrutin frozen-after-first-ballot rule, every PPTX-anchored majority rule, secret-vote anonymity (voter id null on row + audit `actor_user_id=None`), per-org sealed DEKs with IND-CPA non-determinism + cross-org isolation, audit chain tamper-evidence, proxy uniqueness rules, notification fan-out filters + dedup + mark-read defence-in-depth, KMS resolver's "per-org wins, fall back to global, hard-fail when neither" precedence.

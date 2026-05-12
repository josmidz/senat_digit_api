# Sudo Endpoint Implementation Guide

Last updated: 2026-02-22

## 1. Scope

This guide defines how to implement a new API endpoint that may require sudo validation.

It covers:
- What must be configured.
- How backend and frontend must interact.
- What must not be done.
- Current architecture constraints (including grouped and recursive validation requests).

This guide is aligned with:
- `app/modules/security/middleware/sudo_check_middleware.py`
- `app/modules/security/api/controller/sudo_action_controller.py`
- `app/modules/core/services/generic/generic_services.py`

Quick reference:
- `app/modules/security/VALIDATION_PARENT_ID_QUICK_GUIDE.md` for parent/child chaining (example: create organization + upload logo).

## 2. Current Sudo Architecture

### 2.1 Runtime flow
1. Frontend calls `GET /api/v1/sudo-actions/init-sudo-action` with `X-Sudo-Url`.
2. Backend decides if sudo is required for that endpoint and organization.
3. If required, backend creates sudo instruction in Redis.
4. Frontend calls protected endpoint with `X-Sudo-Instruction-Key` (+ `X-Sudo-Url`).
5. `SudoActionCheckMiddleware` validates Redis state and permissions.
6. For grouped flows, middleware sets `request.state.sudo_resolution`.
7. Generic service uses that context to queue grouped/cross validation requests.

### 2.2 Sudo type priority
Applied when an endpoint has multiple sudo flags enabled:
1. `is_sudo_group_inter_connected_organization_validation_action`
2. `is_sudo_group_cross_organization_validation_action`
3. `is_sudo_group_action`
4. `is_sudo_delegated_action`
5. `is_sudo_action`

### 2.3 Required org-level gates
Sudo is active only if all are true:
- Organization has `CFG_SUDO_ACTION_SETUP.is_enabled = true`.
- Endpoint has enabled row in `CFG_ORGANIZATION_SUDO_ACTION` for selected sudo type.

If not, flow is skipped for that organization.

## 3. Mandatory Checklist for New Endpoints

### 3.1 Route and middleware path
- Expose endpoint under API router that passes through `route_entry_point` middlewares.
- Do not put protected endpoint under excluded sudo prefixes:
  - `/api/v1/sudo-actions/`
  - `/api/v1/websocket/`
  - `/api/v1/ng-websocket/`
  - `/api/v1/websocket-service/`

### 3.2 RBAC endpoint metadata
- Add/seed RBAC endpoint row with correct URL and flags:
  - `is_sudo_action`
  - `is_sudo_delegated_action`
  - `is_sudo_group_action`
  - `is_sudo_group_cross_validation_action`
  - `is_sudo_group_inter_organization_validation_action`

Use only the flags required by business rules.

### 3.3 Organization configuration
- Enable sudo globally for organization in `CFG_SUDO_ACTION_SETUP`.
- Enable endpoint for organization in `CFG_ORGANIZATION_SUDO_ACTION` with the intended sudo type.

### 3.4 Access rules by sudo type
- `IS_SUDO_ACTION`
  - No validator list needed, standard sudo confirmation flow.

- `IS_SUDO_DELEGATED_ACTION`
  - Validators are from:
    - `GLOBAL_ACCESS` (user or group) OR
    - `DELEGATED_ACCESS` linked to `cfg_organization_sudo_action_id`.
  - If initiator is not eligible, backend returns delegated context and frontend must restrict UI to QR path.

- `IS_SUDO_GROUP_ACTION`
  - Must have at least one eligible validator from:
    - `GLOBAL_ACCESS` OR
    - `GROUPED_ACCESS` linked to `cfg_organization_sudo_action_id`.
  - If none exists, backend returns blocking error (`SUDO_GROUP_VALIDATORS_MISSING`).

- `IS_SUDO_GROUP_CROSS_ORGANIZATION_VALIDATION_ACTION`
  - Target orgs come from `SYS_CROSS_VALIDATION_ORGANIZATION`.
  - Validators come from `GLOBAL_ACCESS` of target orgs.
  - Missing mapping or validators must block operation.

- `IS_SUDO_GROUP_INTER_CONNECTED_ORGANIZATION_VALIDATION_ACTION`
  - Target orgs come from `CFG_SUDO_ACTION_ACCESS` with:
    - `GROUPED_INTER_CONNECTED_ORGANIZATION_VALIDATION_ACCESS`
    - targeted type = `INTER_CONNECTED_ORGANIZATION`
  - Validators come from target orgs `GLOBAL_ACCESS`.

### 3.5 Controller/service integration rules
- Prefer generic controller/service operations for CRUD.
- Always pass `request` to generic service methods on protected operations:
  - `add_data_to_collection(..., request=request)`
  - `upsert_data_to_collection(..., request=request)`
  - `update_data_in_collection(..., request=request)`
  - `soft_delete_data_from_collection(..., request=request)`
  - `hard_delete_data_from_collection(..., request=request)`

If `request` is omitted, grouped context is lost and operation may bypass intended queue logic.

### 3.6 Grouped recursive child operations
- New recursive linkage uses `OPS_VALIDATION_REQUEST.ops_validation_request_id`.
- For child operation creation, pass parent id via:
  - header `X-Validation-Parent-Id` (canonical), or
  - query `parent_validation_request_id` (alias), or
  - query `validation_request_parent_id` (legacy alias).
- Generic service will write parent linkage on child validation request.
- If a parent id is provided, backend must validate parent request before linking:
  - parent exists,
  - parent organization matches current user organization,
  - parent is still pending,
  - parent validation request type is grouped-style,
  - parent chain has no cycle and no broken ancestor,
  - parent chain stays in same organization.
- If parent validation fails, return `400/403/404` and do not create child request.

## 4. Frontend Contract

For sudo-protected calls:
1. Call `GET /api/v1/sudo-actions/init-sudo-action` with `X-Sudo-Url`.
2. If response indicates skip (sudo not enabled), submit operation directly.
3. Otherwise perform confirmation flow (totp/qr/local auth as returned).
4. Submit protected call with:
   - `X-Sudo-Instruction-Key`
   - `X-Sudo-Url`
   - Optional `X-Sudo-Totp-Key` when using TOTP shortcut.

Handle backend error codes explicitly in UI (do not collapse to generic error text).

### 4.1 Validation parent chaining (automatic)
- Frontend interceptor automatically:
  - reads `validation_context.current_validation_request_id` from mutation responses,
  - stores it as current parent validation request id,
  - sends it on next mutation request as `X-Validation-Parent-Id`.
- It also supports legacy fallback fields:
  - `validation_request_id`,
  - `data.validation_request_id`.
- Core files:
  - `senat_digit_app/src/app/core/interceptors/validation-context.interceptor.ts`
  - `senat_digit_app/src/app/core/common/sudo-header-state.service.ts`

### 4.2 Dev debug panel (frontend)
- A development-only floating panel is available in app root:
  - `senat_digit_app/src/app/app.component.html`
- It displays:
  - current parent validation request id,
  - whether a parent id is active,
  - last update timestamp.
- It uses helper methods on `SudoHeaderStateService`:
  - `setValidationParentRequestId(...)`
  - `clearValidationParentRequestId()`
  - `getValidationParentDebugSnapshot()`
- The panel is hidden in production (`environment.production == true`).

## 5. Grouped Request Data Behavior

For grouped/cross flows:
- Create can persist target record in pending status and queue validation request.
- Update/delete/upsert(existing) are queued and applied after validation.
- Validator rows are persisted in `OPS_VALIDATION_REQUEST_USER`.

Current recursive children exposure:
- `OPS_VALIDATION_REQUEST` response includes `child_validation_requests`.

### 5.1 Parent-child behavior for multi-step processes
- Use this for cases like:
  - Step 1: create organization (grouped).
  - Step 2: upload organization logo in another request.
- Step 2 sends parent id from step 1 response.
- Step 2 target record must also be created/updated as pending and child request must be linked with `ops_validation_request_id = parent`.

### 5.2 Unified mutation response contract
- For every mutation endpoint (`POST`, `PATCH`, `PUT`, `DELETE`, `UPSERT`), include `validation_context`:
  - `current_validation_request_id`,
  - `parent_validation_request_id`,
  - `root_validation_request_id`,
  - `resolved_sudo_action_type`,
  - `is_sudo_group_action`.
- For grouped queued responses, legacy fields (`validation_request_id`, `ops_validation_request_id`) may still be present for backward compatibility.
- If operation is not queued, `validation_context` is still returned with null ids and `is_sudo_group_action = false`.

## 6. What To Avoid

- Do not use legacy `OPS_VALIDATION_REQUEST_ASSOCIATED`.
- Do not implement new logic using `cascade_children` as linkage.
- Do not manually write `OPS_VALIDATION_REQUEST` from endpoint code when generic service can do it.
- Do not use DAO direct writes for sudo-protected business actions (bypasses queue/middleware context).
- Do not hardcode sudo type selection in controller; rely on middleware/controller resolution logic.
- Do not assume endpoint sudo flags alone are enough; org setup controls runtime behavior.
- Do not show only toast for critical blocked errors in frontend.
- Do not trust raw `parent_validation_request_id` without ownership and status checks.
- Do not allow cross-organization parent linkage.

## 7. Recommended Implementation Pattern (Custom Endpoint)

If you cannot use generic endpoint directly:
1. Keep endpoint under routed middleware chain.
2. Resolve user and validate request payload.
3. Call generic service CRUD method with `request=request`.
4. If service returns grouped queue payload, map it to proper API response.
5. Do not add extra legacy associated-request writes.

Minimal example:

```python
result = await self.generic_service.update_data_in_collection(
    collection_key=CollectionKey.SOME_COLLECTION,
    item_id=item_id,
    data=payload,
    accept_language=self.accept_language,
    request=request,
)

grouped_response = self._build_group_validation_response(result)
if grouped_response:
    return grouped_response
```

## 8. Validation Test Matrix (Minimum)

Before merge, test:
- Sudo disabled org: endpoint executes without sudo.
- Sudo enabled org + endpoint disabled in org config: executes without sudo.
- Simple sudo: requires instruction key and validates correctly.
- Delegated sudo:
  - eligible user can validate.
  - non-eligible user receives delegated access error.
- Grouped sudo:
  - missing validators -> blocked with explicit error code.
  - configured validators -> queues request and stores validator rows.
- Cross/inter grouped:
  - missing org mapping or global validators -> blocked.
  - valid config -> queues request with correct first validator.
- Recursive child operation:
  - child request saved with `ops_validation_request_id`.
  - parent returns child in `child_validation_requests`.

## 9. Migration Notes

Legacy associated-request collection usage has been removed from runtime flow.
Do not re-introduce:
- `CollectionKey.OPS_VALIDATION_REQUEST_ASSOCIATED`
- `OpsValidationRequestAssociatedModel`
- response field alias `associated_requests`

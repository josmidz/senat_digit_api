# Validation Parent ID Quick Guide

Last updated: 2026-02-22

Use this guide when one business flow is split across multiple HTTP requests and all child requests must be linked to the parent validation request.

Example:
- Request 1: create organization.
- Request 2: upload organization logo.

If request 1 is queued in grouped/cross sudo validation, request 2 must send the parent id so backend links both requests in the same validation chain.

## 1. Required response contract (parent request)

The parent mutation response must include:

```json
{
  "validation_context": {
    "current_validation_request_id": "vr_parent_123",
    "parent_validation_request_id": null,
    "root_validation_request_id": "vr_parent_123",
    "is_sudo_group_action": true
  }
}
```

Rules:
- Always return `validation_context` for mutation endpoints.
- If operation is not grouped/cross queued, ids can be null/empty and `is_sudo_group_action=false`.

## 2. Frontend behavior

1. Execute parent submission.
2. Read `validation_context.current_validation_request_id`.
3. If grouped/cross and current id exists, store it as parent id.
4. Execute child submission normally (interceptor adds header automatically):
   - `X-Validation-Parent-Id: <current_validation_request_id>`

In this repository, this is already handled by:
- `senat_digit_app/src/app/core/interceptors/validation-context.interceptor.ts`
- `senat_digit_app/src/app/core/common/sudo-header-state.service.ts`

Component-level note:
- If needed, you can explicitly set parent id before child call:
  - `sudoHeaderStateService.setValidationParentRequestId(currentValidationRequestId)`

## 3. Backend behavior for child request

Backend must:
- Read parent id from header (canonical): `X-Validation-Parent-Id`.
- Accept aliases for compatibility:
  - `parent_validation_request_id`
  - `validation_request_parent_id`
- Validate parent before linking:
  - parent exists,
  - same organization as current user,
  - parent still pending,
  - parent is grouped-style request,
  - no cycle in chain.
- Create child `OPS_VALIDATION_REQUEST` with:
  - `ops_validation_request_id = <parent_id>`

## 4. Minimal implementation checklist

- Endpoint uses middleware chain (do not bypass `route_entry_point` middleware).
- CRUD call passes `request=request` into generic service.
- Mutation response preserves `validation_context`.
- Do not manually create legacy associated request records.
- Do not pass parent id in request body for new implementations.

## 5. Common mistakes to avoid

- Forgetting to return `validation_context` on parent response.
- Uploading child resource without `X-Validation-Parent-Id`.
- Allowing parent linkage across organizations.
- Linking child to a non-pending or non-grouped parent request.
- Reintroducing legacy `OPS_VALIDATION_REQUEST_ASSOCIATED`.

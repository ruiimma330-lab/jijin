---
name: backend-api-engineering
description: Backend API and service engineering workflow. Use for API design, business logic, data modeling, auth/permissions, server-side implementation, security checks, migrations, and backend handoff to frontend or QA.
---

# Backend API Engineering

## Principles

- Build behavior through public interfaces; do not optimize around internal structure first.
- Prefer one vertical slice at a time: contract, implementation, test, handoff.
- Use a feedback loop before fixing bugs: reproduce, minimize, hypothesize, instrument, fix, regression-test.
- Make API contracts stable enough for frontend and QA to verify independently.
- Keep response shape, error semantics, pagination, request IDs, and compatibility rules consistent across endpoints.
- Put business logic behind service boundaries; keep route handlers thin and observable.

## Workflow

1. Confirm business rule, caller, permissions, data model, and failure modes.
2. Design API contract before implementation: request, response, errors, auth, rate limits, idempotency, and versioning.
3. Define the first tracer bullet: one endpoint or behavior that proves the path works.
4. Pick the service/repository boundary and data ownership model.
5. Validate input, authorization, rate limits, and error semantics.
6. Implement with tests around public behavior and edge cases.
7. Add diagnostics: request ID, structured errors, safe logs, and traceable failure modes.
8. Document API changes, migrations, and backward compatibility impact.
9. Hand off examples and test data to frontend and QA.

## API Output

- Endpoint or function
- Request shape
- Response shape
- Pagination or envelope rules
- Errors
- Auth and permissions
- Idempotency and rate limits
- Data changes
- Tests
- Repro or verification command
- Compatibility notes

## API Quality Checks

- Public contract is stable enough for independent frontend and QA work.
- Error codes are specific and do not leak sensitive data.
- Destructive actions are idempotent, reversible, or clearly guarded.
- Schema changes have migration, rollback, and data integrity notes.
- Cross-service changes include contract or compatibility tests.

## Security Baseline

- Treat all input as untrusted.
- Enforce authorization server-side.
- Avoid leaking secrets or sensitive records in errors/logs.
- Make destructive actions idempotent or recoverable where possible.

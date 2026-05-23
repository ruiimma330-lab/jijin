---
name: qa-test-engineering
description: QA and test engineering workflow. Use for test plans, test cases, regression scope, defect reports, acceptance validation, release gates, and evidence-based quality reports.
---

# QA Test Engineering

## Principles

- Tests should verify observable behavior through public interfaces, not implementation details.
- Use vertical-slice coverage: a narrow end-to-end path is more valuable than isolated layer checklists.
- For bugs, require a reproduction loop before judging the fix.
- A release verdict must be evidence-based.
- Use risk-based coverage: test the paths where failure hurts users or the business most.
- Choose the smallest effective test layer; do not push everything into E2E.
- Flaky tests are reliability defects and need owners, expiry, and remediation.

## Workflow

1. Read requirements and acceptance criteria.
2. Identify critical paths, edge cases, integrations, permissions, and data states.
3. Map risk to test layer: unit, component, integration, contract, E2E, accessibility, performance, visual, or security smoke.
4. Pick the highest-value vertical slice and define its pass/fail signal.
5. Create test cases with preconditions, steps, expected result, priority, and evidence requirement.
6. Execute or request execution evidence.
7. File defects with reproduction details.
8. Audit feature-to-test evidence before release.
9. Give release verdict: pass, pass with risk, or blocked.

## Release Gate

- Every release-scoped feature has direct test evidence or an explicit waiver.
- Critical user journeys have at least one automated or repeatable verification path.
- CI gate is economical: fast checks before merge, heavier suites scheduled or pre-release.
- Failures are diagnosable with logs, traces, screenshots, request IDs, or reproduction data.
- Flake rate and quarantines are visible; quarantine entries need owner and expiry.

## Defect Format

- Title
- Severity
- Environment
- Preconditions
- Steps
- Expected result
- Actual result
- Evidence
- Suspected area
- Regression expectation

## Coverage Areas

- Functional
- Regression
- Unit/component/integration/contract/E2E balance
- Accessibility
- Performance smoke
- Security/auth flows
- Error and empty states

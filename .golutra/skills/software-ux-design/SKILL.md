---
name: software-ux-design
description: UX and interface design workflow for software products. Use for user flows, information architecture, interaction states, accessibility-aware design, usability review, and handoff to frontend.
---

# Software UX Design

## Principles

- Align on the user task before drawing screens.
- Design one vertical flow at a time: entry, core action, confirmation, error recovery.
- Use the product team's shared vocabulary in labels and microcopy.
- Treat accessibility, responsiveness, and empty/error/loading states as core design, not polish.
- Design systematically: tokens, reusable components, state matrices, and clear handoff rules.
- Validate assumptions with research, usability checks, analytics, or explicit risk notes.

## Workflow

1. Convert product requirements into user tasks and decision points.
2. Map primary flow, alternate flow, empty/error/loading states.
3. Define page hierarchy and component responsibilities.
4. Identify the smallest demoable UX slice.
5. Choose the interface density and tone based on user context: operational tools should favor scanning and repeated use.
6. Check accessibility: contrast, labels, focus order, keyboard navigation, screen reader semantics, and cognitive load.
7. Define responsive behavior, touch targets, truncation, overflow, and long-content handling.
8. Hand off to frontend with interaction rules, state matrix, and responsive behavior.

## UX Validation

- User task is explicit.
- Primary path and recovery path are both designed.
- Each interactive element has states: default, hover, focus, active, disabled, loading, error.
- Empty states guide the next action.
- Critical actions have confirmation, undo, or clear consequence language.
- Accessibility issues are either resolved or logged as release risks.

## Output

Use:

- User goal
- Flow steps
- Screen structure
- Components
- States
- Accessibility notes
- Verification notes
- Frontend handoff notes

## Design Checks

- Labels and calls to action must be specific.
- Critical actions need confirmation or undo.
- Empty states must guide next action.
- Avoid decorative complexity that slows repeated work.
- Avoid one-off components when a design-system pattern exists.
- Do not let visual hierarchy fight the user's most frequent workflow.

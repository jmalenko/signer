# Project Rules

## Project Context

This repo contains a desktop app.

Key docs, keep them consistent with each other and with the code (incl. tests):
- [REQUIREMENTS.md](REQUIREMENTS.md) — features
- [DESIGN.md](DESIGN.md) — architecture and design decisions, includes instructions on how to run the app
- [TESTING.md](TESTING.md) — how to run and troubleshoot tests

## Process

- Keep REQUIREMENTS.md, DESIGN.md, and the code (including tests) consistent
  with each other.
  - Example: a requirement that only relevant toolbar buttons should be
    visible must also apply to the main menu — and that consistency
    expectation itself should be captured in REQUIREMENTS.md, not just
    implemented silently.

- When I tell you to do a final review: Just before committing, do a detailed, critical self-review of the diff.
  - Do a critical review all changes.
  - Ensure no tests are failing.
  - Clean up any temporary files you created. If unsure whether a file
    is temporary, ask the user rather than deleting it.
  - Propose the commit message: one summary sentence; add further detail
    lines only if needed, and don't use them to narrate the code changes
    (the diff already shows that). Do not mention test updates in the commit message; they are an expected part of implementation.
- You MUST NOT commit without explicit user approval.

## Implementation

- For every implementation task:
  - Confirm the requirement is clear and complete before starting.
    - If it isn't, add the missing detail to REQUIREMENTS.md yourself. This can be done before or after implementing.
  - Update DESIGN.md if the change affects architecture or behavior.
  - Unit tests are in scope for the task, not optional follow-up work.

- After every code change, run the test suite.
  - If a failure is caused directly by your change, fix the code immediately.
  - For any other failures, do a quick analysis and report them to the user
    instead of fixing them unprompted.
  - MUST NOT modify existing tests without explicit user approval.

- For every bug fix:
  - Before fixing the bug, write two test cases for it first:
    - First, with the expected behavior. This one should be failing.
    - Second, with the actual (buggy) behavior. This one should be passing.
  - When the fix lands:
    - Ensure the first test (previously failing) is passing now.
    - Ensure the second test (previously passing) is failing now. You may do only minor edits to this test.
  - After the review:
    - Delete the second (now failing) test — it only existed to document the bug; the first test remains as the regression test.

- When you need information from manual/user testing (e.g. runtime values),
  don't ask the user to copy values back to you. Log the needed information
  to a file instead, and truncate that file at the start of the app/tested
  action so it doesn't grow unbounded across runs.
- Put temporary files (logs, scratch scripts, etc.) in the repository root,
  and remove them before committing (see Process above).

# Running feedback notes
This file contains proposals for next implementation. These are not in scope yet.

-- UNRESOLVED

First observation:

Fix the rotation disk - the top part does not work - it does not show the cross cursor and when clicked, it deselect the annotation. It seems that the "rotation" area is shifted over the line connecting the disc to the boundary.

Also ensure that the top resize handle works properly. (It did not work in the testing because it started rotation instead of resize.)

Addition after some previous investigation: 

I noticed one more thing. It seems that the bottom resize handle (in the middle of the edge) also has the actual effective area shifted down by few pixels.
After more testing, that applieas to everything. E.g. Selecting the rectangle annotation - clicking the top edge does not select the rectangle (because the effective area starts below that and ends below the bottom edge.

To summarize: every annotation has the following issue: the mouse is not acting directly where the annotation is displayed, but few (10?) pixels below that. This happens only on MacOs (not windows).
(This probably does NOT apply to the toolbars or window resizing by borgers.)

First, confirm that you can detect this in an automated test.

-- DISMISSED (not native on Windows)

1. Open the signed document to another application (e.g. Outlook). Add to main menu and toolbar menu behond Save JPG". Do not show a save dialog.

Discuss desing: does the file need to be saved? I don't want it to be saved, but in the target application (like Outlook), it could be attached to an email and that would have a name. The name should match the default file name for saved documents.

-- REVIEW

Review this codebase for a specific class of logical error: code that LOOKS like it
handles/verifies/guards against a condition, but under certain circumstances silently
degrades, bypasses, or fabricates a result instead of failing loudly or surfacing the
problem to the caller/user. Do not fix anything yet — only report findings.

Search BOTH the application code (signer/) and the tests (tests/). Weight this toward
signer/ first: a logical error there affects real users, not just test coverage.

Concretely, search for and flag every instance of:

1. Broad or silent exception handling: `except Exception`, `except:`, or specific
   exceptions that are caught and then logged/ignored/passed/defaulted, where the
   caller has no way to know the operation didn't fully succeed. Distinguish between
   "expected, recoverable condition with a clear user-facing message" (fine) and
   "swallow and silently continue/return a default" (likely a bug).

2. Silent fallback to a default/placeholder value when an operation fails or input is
   missing/invalid, where the fallback could produce incorrect-but-plausible-looking
   results (e.g. wrong data silently substituted, a stale/cached value reused, a
   partial result treated as complete) instead of raising or informing the user.

3. Conditions that assume something "can't happen" (no assertion, no handling) where
   it actually can — e.g. an index/lookup assumed always present, an early-return that
   skips necessary follow-up steps under an edge case, off-by-one or inverted
   conditions that only manifest for specific inputs (empty collections, boundary
   values, first/last item, single-item vs. multi-item cases).

4. State/consistency bugs: a value updated in one place but a dependent/derived value
   not correspondingly updated or invalidated (stale cache, stale derived field,
   partial undo/redo state, orphaned reference).

5. Copy-paste or refactor artifacts: near-duplicate logic blocks where one was updated
   and a sibling wasn't, or a variable/condition that looks like it was meant to
   reference something else nearby.

6. (Same pattern, narrower scope) Test code where verification is bypassed rather than
   the assertion failing: skip/early-return guards on preconditions that should always
   hold (e.g. a checked-in fixture file assumed missing), auto-generating "expected"
   from "actual" when a baseline is absent, or platform/environment skips whose stated
   reason was never re-verified and may be stale.

For each finding, report:
- File and line reference.
- The exact code (condition, except clause, fallback, etc.).
- What has to be true for this to produce a wrong result or hide a real failure, in
  concrete terms (an example input/scenario if possible).
- Whether the guarded condition is something that should be *impossible in correct
  operation* (→ likely a real bug, should fail/raise instead) or *genuinely optional/
  environment-dependent* (→ legitimate, leave alone) — with your reasoning.
- A risk/confidence rating (high/medium/low): high = you can describe a concrete
  scenario where it produces a wrong result silently; low = theoretical/stylistic only.

Prioritize signer/ (production code) findings over tests/ findings in the final report.
Skip purely stylistic issues (naming, formatting, unused imports) — only logical
correctness/robustness issues in this category.

---


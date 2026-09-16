# Code Review — Implementation Plan

Date: 2026-09-16
Scope: `signer/canvas.py`, `signer/history/*`, `signer/objects.py`, `signer/compositor.py`,
`signer/document_loader.py`, `signer/pdf_utils.py`, `signer/main_window.py`, `signer/settings.py`,
`signer/notification.py`, `signer/export_quality_dialog.py`, `signer/cli.py`, `signer/app.py`,
docs (`REQUIREMENTS.md`, `DESIGN.md`, `TESTING.md`).

## Implementation status (updated 2026-09-16)

**Done** (code fixed, TDD regression tests added, full suite green — 774 passed / 19 skipped):
§0 (stable-id refactor), §1.1, §1.2, §1.3, §1.4, §1.5 (fixed opportunistically even though
`DuplicateAnnotationAction` is dead code — see note below), §1.6 (fallback logging), §2.2
(`ChangeColorAction.execute()` consistency), §2.3 (`objectChanged` emits), §2.4 (Save-As filename
auto-correct). New tests: `tests/unit/test_undo_redo_stable_id_bugs.py`,
`tests/unit/test_toolbar_property_crash_bug.py`, `tests/unit/test_save_as_format_switch_filename_bug.py`.

**New bug found and fixed while implementing §2.3** (not in the original review — see §2.3 note
below): `_on_width_changed()` and `_on_font_family_changed()` constructed
`ChangeLineWidthAction`/`ChangeFontFamilyAction` with keyword arguments that didn't match those
classes' actual constructors (`from_width`/`to_width` vs. `line_width_pt`/`from_line_width_pt`, and
`from_family`/`to_family` vs. `font_family`/`from_font_family`). This raised a `TypeError` on every
toolbar width or font-family change for any annotation currently on the page (PySide6 swallows the
exception at the Qt event-loop boundary, so it didn't crash the app outright, but the change was
silently **not recorded to history** — i.e. completely non-undoable — and spammed stderr). Fixed
alongside §2.3 since it's the same code path.

**Not yet done**: §2.1 (`CutAnnotationAction` — confirmed dead code, not constructed anywhere in
production; low priority). §3.1 (font_size_px/pt rename), §3.3 (compositor off-by-one clamp), §3.6
(LibreOffice timeout) — all still open, lowest priority per the plan.

**Done 2026-09-16 (continued)**: §3.2 (deduplicated the four `rotate_*` methods into a
`_rotate_pages()` helper, added `tests/unit/test_page_rotation.py` which previously had zero
coverage), §3.4 (added logging to the `fit_text_box()` Qt-metrics fallback, the per-annotation
print-render failure, and replaced `traceback.print_exc()` with `logging.exception()`), §3.5
(recent document/signature entries that no longer exist on disk are now pruned automatically
instead of erroring forever — see `tests/unit/test_recent_files_pruning.py`), §4.1, §4.2 (both
DESIGN.md fixes applied).

**New finding, FIXED 2026-09-16**: `SetTextAnnotationAction` and `SelectAnnotationAction` were dead
code — never constructed in `canvas.py` or `main_window.py` (only referenced by
`Action.deserialize()`'s dispatch table and the action-recorder/player test harness). The *real*
text-edit path, `MainWindow._on_edit_requested()` (double-click to edit text), set `obj.text =
new_text` directly and never recorded any history action — editing an existing text annotation's
content was not undoable, contradicting REQUIREMENTS.md's explicit "Supported Actions for
Undo/Redo" list ("Set text (change text annotation content)"). Fixed: `_on_edit_requested()` now
records a `SetTextAnnotationAction` (only when the text actually changed) using the stable id
helper; `SetTextAnnotationAction.execute()`/`undo()` now look up the object via `_object_map` first
(consistent with `ChangeColorAction`) and refit the text box after restoring. `SelectAnnotationAction`
remains dead code (selection state was intentionally excluded from undo history; no requirement
calls for it). Test: `tests/unit/test_text_edit_undo_bug.py`.

This document is a **plan**, not yet implemented. Findings are ordered by priority. Each item has
enough detail to implement directly. Per `AGENTS.md`, bug fixes will follow TDD (failing test for
expected behavior + a test that documents the current buggy behavior, delete the latter after the
fix lands and is reviewed).

---

## 0. Root cause shared by most history/undo bugs

The codebase has **three different, inconsistently-used object-identity schemes**:

1. Array index into `canvas.current_page_objects()` (position in the list) — used by
   `DeleteAnnotationAction`, `CutAnnotationAction`, `DuplicateAnnotationAction.execute()`,
   `SetTextAnnotationAction`, `SelectAnnotationAction`, and as the *fallback* almost everywhere else.
2. Stable id stored in `canvas._object_map: dict[int, CanvasObject]` — the intended design,
   assigned once in `add_object()` via `canvas._next_object_id`.
3. Python's `id(obj)` gated behind `hasattr(self, '_stable_id_map')`, e.g.
   [signer/canvas.py](signer/canvas.py#L1024): `_stable_id_map` **is never defined anywhere in the
   codebase** (confirmed via repo-wide search), so this branch is dead code and always falls through
   to (1).

Because array indices shift whenever objects are added/removed, any undo/redo action recorded with
an array-index `object_id` can silently operate on the wrong object once the list has changed shape
since the action was recorded (e.g. add A, add B, delete A, drag B, undo the drag → drags index 0,
which is now B... but a subsequent redo/undo interleaving with more deletes easily breaks this).

**Planned fix (do this first, it eliminates most of the individual bugs below in one pass):**

- Store the stable id directly on the object when it's created/registered, e.g.
  `obj._history_id = obj_id` in `add_object()` (and when objects are recreated via paste/duplicate/undo-restore).
  This avoids O(n) reverse-lookups in `_object_map` and removes the temptation to use array index
  "just this once".
- Add one helper on `DocumentCanvas`:
  ```python
  def _stable_id_for(self, obj: CanvasObject) -> int | None:
      """Return the object's stable history id, registering it if missing."""
  ```
  used everywhere an action needs an `object_id`, replacing all `objs.index(obj)` call sites:
  - [signer/canvas.py](signer/canvas.py#L1024-L1025) and [signer/canvas.py](signer/canvas.py#L1159-L1160) (move/resize drag recording — remove the dead `_stable_id_map` check entirely)
  - `remove_selected()` [signer/canvas.py](signer/canvas.py#L316-L322)
  - `delete_selected()` [signer/canvas.py](signer/canvas.py#L454-L481)
  - `_adjust_annotation_property()` [signer/canvas.py](signer/canvas.py#L432-L445)
  - `set_color_selected()` [signer/canvas.py](signer/canvas.py#L637)
  - `main_window.py`: `_on_width_changed`, `_on_font_size_changed`, `_on_font_family_changed`
    ([signer/main_window.py](signer/main_window.py#L964), [signer/main_window.py](signer/main_window.py#L988), [signer/main_window.py](signer/main_window.py#L1012)) — all currently do
    `obj_idx = objs.index(selected) if selected in objs else -1`.
- On the `action.py` side, make every action's `execute()`/`undo()` look up via `_object_map` **only**
  (no array-index fallback) once producers are fixed. The array-index fallback is not needed for
  the recorder/replay system's sake (see §5 — it uses its own independent, already-stable id
  scheme and never hits that fallback), so it can be removed outright rather than kept "just in
  case"; keep it only if some other non-recorder caller is found to depend on it during
  implementation.

This is a moderately large mechanical refactor; do it as its own PR/commit before the smaller
targeted fixes in §1–§3, since several of them touch the same call sites.

---

## 1. Critical bugs (undo/redo correctness)

### 1.1 Move/Resize during drag records array index, not stable id — FIXED
- **File:** [signer/canvas.py](signer/canvas.py#L1024-L1044) (move) and [signer/canvas.py](signer/canvas.py#L1159-L1178) (resize)
- **Confirmed:** `hasattr(self, '_stable_id_map')` is always `False` (attribute never set anywhere),
  so `obj_id` always comes from `objects.index(self._selected)`.
- **Impact:** Any workflow of add/delete followed by drag/resize + undo can mutate the wrong object.
- **Fix:** covered by the §0 refactor.
- **Test to add:** Add annotation A, add annotation B, delete A (B shifts to index 0), drag B, undo →
  assert B (not a phantom/wrong object) returns to its pre-drag position, and A stays deleted.

### 1.2 `delete_selected()` docstring says "Single undo unit" but records N separate actions — FIXED
- **File:** [signer/canvas.py](signer/canvas.py#L454-L481)
- **Confirmed:** loop calls `self.history.record_action(action)` once per selected object; there is
  no batching/grouping mechanism in `HistoryStack` (confirmed by reading
  [signer/history/history_stack.py](signer/history/history_stack.py) — `record_action` only ever
  merges consecutive `Move`/`Resize` actions of the *same* object id; every other action is pushed
  individually).
- **Impact:** Multi-select delete of 3 objects then a single Ctrl+Z only restores the last-deleted
  object; two more Ctrl+Z presses are needed. Contradicts REQUIREMENTS/DESIGN §5.14 ("single undo
  unit").
- **Fix:** Introduce a `CompositeAction(Action)` in `signer/history/action.py`:
  ```python
  class CompositeAction(Action):
      """Groups multiple sub-actions into a single undo/redo unit."""
      def __init__(self, actions: list[Action]) -> None:
          super().__init__("composite", {})
          self._actions = actions
      def execute(self, canvas): 
          for a in self._actions: a.execute(canvas)
      def undo(self, canvas):
          for a in reversed(self._actions): a.undo(canvas)
  ```
  Change `delete_selected()`, `duplicate_selected_multi()`, and the multi-object path of
  `paste_selected()`/`cut_selected()` (cut already reduces to copy + delete, so fixing delete fixes
  cut) to build a list of sub-actions and call `history.record_action(CompositeAction(sub_actions))`
  once, instead of calling `record_action()` per object. `CompositeAction` doesn't need
  `from_data()`/serialization support unless the action recorder replay tests need it (check §5).
- **Test to add:** select 3 annotations, delete, single Ctrl+Z restores all 3; single Ctrl+Y
  (redo) removes all 3 again.

### 1.3 `duplicate_selected_multi()` claims "Single undo unit" but records ZERO undo actions — FIXED
- **File:** [signer/canvas.py](signer/canvas.py#L487-L503)
- **Confirmed:** the method appends duplicates to `objs` directly and never calls
  `history.record_action(...)` at all (unlike single-object `duplicate_selected()`, which goes
  through `add_object()` → `AddAnnotationAction`). Multi-duplicate is currently **not undoable**.
- **Fix:** For each duplicate, build an `AddAnnotationAction`-equivalent (or reuse `add_object()` in
  a loop, but `add_object()` currently also emits `objectChanged` and sets single-selection each
  call — needs a "silent"/batched variant), wrap in the new `CompositeAction`, record once.
- **Test to add:** multi-select 2 objects, duplicate, Ctrl+Z removes both duplicates and restores
  original 2-item selection state.

### 1.4 `PasteAnnotationAction.undo()` removes objects via blind LIFO `pop()` — FIXED
- **File:** [signer/history/action.py](signer/history/action.py#L845-L851) (recorded from
  [signer/canvas.py](signer/canvas.py#L591-L594))
- **Confirmed:**
  ```python
  def undo(self, canvas: Any) -> None:
      if "pasted_objects_data" in self.data:
          objects = canvas.current_page_objects()
          for _ in self.data["pasted_objects_data"]:
              if objects:
                  objects.pop()
  ```
  This removes the *last N objects currently in the list*, regardless of whether they are the
  objects that were actually pasted. If the user pastes 2 objects then manually adds a 3rd (e.g. via
  toolbar), undo removes the manually-added object and one pasted object, leaving one pasted object
  behind — silent data corruption.
- **Fix:** `execute()` already creates the objects — keep references (like `AddAnnotationAction`
  keeps `self._added_object`) or assign+record stable ids for each pasted object at paste time, and
  have `undo()` remove those specific objects (by identity or by id via `_object_map`), not
  positional `pop()`.
- **Test to add:** paste 2 objects, add 1 more object manually, Ctrl+Z once → exactly the 2 pasted
  objects are removed, manually-added object remains.

### 1.5 `DuplicateAnnotationAction.undo()` also uses blind LIFO `pop()` — FIXED (dead code, fixed opportunistically)
- **File:** [signer/history/action.py](signer/history/action.py#L769-L773) — same pattern/fix as 1.4.
- **Test to add:** duplicate object, add another object, Ctrl+Z once → only the duplicate is
  removed.

### 1.6 `AddAnnotationAction.undo()` has a fragile 4-tier fallback (direct ref → object_map →
    property-matching → LIFO `pop()`) — FIXED (logging added)
- **File:** [signer/history/action.py](signer/history/action.py#L498-L561)
- Once every producer reliably assigns/propagates a stable id (§0), tiers 3 (property matching) and
  4 (LIFO) should no longer be reachable in normal operation. Keep them only as a last-resort with a
  logged warning (see §4.3) rather than silently mutating unrelated objects — this makes latent
  identity bugs visible in logs/tests instead of causing silent data loss.

---

## 2. Medium bugs

### 2.1 `CutAnnotationAction` restores at recorded array index — can reorder objects after undo
- **File:** [signer/history/action.py](signer/history/action.py#L785-L819)
- Same array-index-vs-stable-id issue as §0; `objects.insert(self.data["object_id"], obj)` uses a
  stale position if the list has changed shape since the cut. Fix alongside §0 (store id, use
  `_object_map`-based restore, e.g. append + rely on z-order not being semantically important, or
  keep a recorded neighbor id to reinsert near).

### 2.2 `ChangeColorAction`/`SetTextAnnotationAction` — `execute()` and `undo()` use different lookup
    strategies — PARTIALLY FIXED (`ChangeColorAction` only; `SetTextAnnotationAction` is dead code, see status note above)
- **File:** [signer/history/action.py](signer/history/action.py#L629-L664) (`ChangeColorAction`),
  [signer/history/action.py](signer/history/action.py#L672-L710) (`SetTextAnnotationAction`)
- **Confirmed:** `ChangeColorAction.execute()` only does array-index lookup; `undo()` tries
  `_object_map` first, falling back to array index. `SetTextAnnotationAction` doesn't use
  `_object_map` at all in either method (unlike `ChangeLineWidthAction`/`ChangeFontSizeAction`/
  `ChangeFontFamilyAction`, which already correctly try `_object_map` first in **both**
  `execute()` and `undo()` — use those three as the reference implementation).
- **Fix:** make `ChangeColorAction.execute()` and `SetTextAnnotationAction.execute()`/`undo()`
  consistent with the `_object_map`-first pattern already used by the font/line-width actions.

### 2.3 Toolbar property changes don't emit `objectChanged`, so canvas/toolbar visually lag — FIXED
    (also fixed a crash bug found in the same code path, see status note above)
- **Files:**
  - [signer/main_window.py](signer/main_window.py#L974) `_on_width_changed` — only calls `self.canvas.update()`
  - [signer/main_window.py](signer/main_window.py#L1010) `_on_font_size_changed` — same (already
    tracked as a known bug prior to this review)
  - [signer/main_window.py](signer/main_window.py#L1033) `_on_font_family_changed` — same
- **Fix:** add `self.canvas.objectChanged.emit()` alongside `self.canvas.update()` in all three
  handlers (mirrors what `add_object`/`move_selected`/etc. already do).
- **Test to add:** for each of width/font-size/font-family, changing the toolbar control emits
  `objectChanged` and the bounding box redraws immediately (existing tests already cover font-size
  partially per repo memory notes — extend the same pattern to width and font-family).

### 2.4 Save-As dialog: filename auto-correction on format switch never triggers — FIXED
- **File:** [signer/main_window.py](signer/main_window.py#L1537-L1568)
- **Confirmed:** the "ensure correct extension" step (~L1543-1544) mutates `output`'s suffix to the
  new format **before** the auto-correct check at L1556 compares `output.name == suggested_filename`.
  Since `suggested_filename` still has the *old* extension, this equality is always `False` once the
  suffix has already changed, so the intended auto-correction (`document-p#.jpg` →
  `document-signed.tiff` when switching to a single-file format) never runs; user ends up with a
  wrongly-shaped filename (e.g. `document-p#.tiff` instead of `document-signed.tiff`).
- **Fix:** capture `original_name = output.name` immediately after the user picks a file, before any
  suffix mutation, and compare against that in the auto-correct branch instead of the
  post-mutation `output.name`.
- **Test to add:** simulate choosing JPG format with multi-page placeholder name, then switching the
  filter to PDF/TIFF without editing the filename → resulting suggested filename should be the
  single-file form (`document-signed.pdf`), not `document-p#.pdf`.

---

## 3. Low-severity / code quality

### 3.1 `_font_size_px` actually stores **points**, not pixels
- **File:** [signer/objects.py](signer/objects.py#L295) (and throughout `VectorAnnotation`,
  `duplicate()` at [signer/objects.py](signer/objects.py#L590), and the several `_font_size_px`
  references in `main_window.py`/`canvas.py`/`action.py`)
- The constant `DEFAULT_TEXT_FONT_PT` and `FONT_SIZE_STEPS_PT` correctly use "PT" naming, but the
  runtime attribute is misleadingly named `_font_size_px` when it holds a point value that gets
  converted to pixels only inside `_make_font()` via `DPI_SCALE`.
- **Fix (naming-only, no behavior change):** rename `_font_size_px` → `_font_size_pt` everywhere
  (attribute, constructor param, serialization key `font_size_px` can stay for backward
  compatibility with saved data/clipboard JSON, or be migrated with a compat read in
  `from_dict()`). Use `vscode_renameSymbol`/careful search-replace; this touches
  `objects.py`, `canvas.py`, `action.py`, `main_window.py`. Low priority — do this only if there's
  spare time, since it's a large mechanical diff for a naming issue.

### 3.2 Duplicated rotation methods — FIXED
- **File:** [signer/canvas.py](signer/canvas.py#L206-L241) — `rotate_current_page_left/right`,
  `rotate_all_pages_left/right` are 4 near-identical bodies differing only in the angle delta and
  whether they loop over all pages.
- **Fix:** extract `_rotate(self, pages: list[int], delta: int) -> None` helper.

### 3.3 Compositor clamps annotation position into `[0, w-1]`/`[0, h-1]`, not `[0, w]`/`[0, h]`
- **File:** [signer/compositor.py](signer/compositor.py#L424-L426)
  ```python
  x = max(0, min(x, pw - 1))
  y = max(0, min(y, ph - 1))
  ```
- Objects placed with their top-left corner exactly at the page edge get shifted 1px inward. Very
  low impact in practice since `clamp_to_page()` already keeps objects within bounds during editing;
  only matters for edge-exact placements. Fix by relaxing to `pw`/`ph` if it's confirmed objects can
  legitimately be positioned there (verify against `clamp_to_page()` semantics in `objects.py`
  before changing, to avoid introducing an actual off-canvas placement bug).

### 3.4 Bare/broad `except Exception` clauses that swallow errors silently — FIXED (logging added; not narrowed to specific exception types, since the failure modes are broad by nature — e.g. any Qt/font issue, any per-annotation render issue)
- [signer/objects.py](signer/objects.py#L355) `fit_text_box()` fallback — silently falls back to a
  crude approximation if `QFontMetricsF` raises; add a debug log line so regressions are visible.
- [signer/main_window.py](signer/main_window.py#L1949-L1951) print rendering loop — silently skips
  an annotation that fails to render; add `logging.warning(...)`.
- [signer/main_window.py](signer/main_window.py#L2037-L2043) uses `traceback.print_exc()` (stderr
  only, invisible to GUI users) instead of `logging.exception(...)`.
- These are all "add a log line" fixes, not behavior changes — low risk, bundle together.

### 3.5 Recently-used document/signature entries that no longer exist on disk aren't pruned — FIXED
- **File:** [signer/main_window.py](signer/main_window.py#L1180-L1189) area — clicking a stale
  recent-file entry re-shows the same "not found" error every time instead of removing it from the
  list.
- **Fix:** on "file not found" for a recent-item open, remove that path from the relevant settings
  list and refresh the menu.

### 3.6 LibreOffice conversion timeout is a fixed 30s with no user feedback on timeout
- **File:** [signer/document_loader.py](signer/document_loader.py#L99)
- Large Word/ODT documents could exceed this. Low priority — consider raising the default and/or
  surfacing a clearer timeout-specific error message (already raises `ValueError` on
  `CalledProcessError`; confirm a `subprocess.TimeoutExpired` is handled with an equally clear
  message — verify during implementation).

---

## 4. Documentation fixes

### 4.1 DESIGN.md §5.6 vs §7.3.9 disagree on default text font size — FIXED
- [DESIGN.md](DESIGN.md) §5.6 says "default text size: 12pt"; §7.3.9 says "Default: 11 points".
  Code (`DEFAULT_TEXT_FONT_PT = 11` in [signer/objects.py](signer/objects.py#L25)) and
  `REQUIREMENTS.md` line 848 ("Default font size for text annotations: **11 points**") agree on 11.
  §5.6 is the stale one (it reflects the original ask in `REQUIREMENTS.md` line 63 before it was
  refined to 11pt in a later feedback round).
- **Fix:** update DESIGN.md §5.6 to say "default text size: 11pt" to match §7.3.9/code/the final
  requirement.

### 4.2 DESIGN.md §5.4 doesn't document the signature-specific default placement exception — FIXED
- §5.4 only documents the generic centered-placement formula. `default_signature_position_for()`
  ([signer/canvas.py](signer/canvas.py#L800-L806)) places signatures at 80% down the page instead,
  per `REQUIREMENTS.md` line 28 ("Default position for the signature is 80% from top, centered
  horizontally"). DESIGN.md should mention this exception explicitly so the two default-placement
  code paths are traceable to a documented rule.
- **Fix:** add a short note/sub-bullet to §5.4.

---

## 5. Action-recorder/replay system's assumptions — RESOLVED

Checked all 24 fixture files (`tests/fixtures/**/*.json`, top-level + all per-test subdirectories)
and read `tests/recording/action_player.py`, `tests/recording/action_recorder.py`, and
`tests/utils/test_helpers.py` (`ActionRecorder`) in full. Findings:

- **Fixture `object_id` is already a stable, sequential id — not an array index.** It's assigned by
  `ActionRecorder._get_object_id()` ([tests/utils/test_helpers.py](tests/utils/test_helpers.py#L129-L134)):
  `id(python_obj)` (Python object identity) is looked up in a private `_object_map: dict[int, int]`
  and mapped to a small monotonically-increasing counter (`_object_id_counter`) the first time each
  object is seen; the same small int is reused for every subsequent action on that object (move,
  resize, set_color, etc.) for the rest of the recording. Confirmed empirically in
  [tests/fixtures/undo_multiple.json](tests/fixtures/undo_multiple.json): `object_id` values are
  `0, 1, 2, 3`, each consistently reappearing across `add_annotation`/`move_annotation`/
  `resize_annotation`/`set_color` for that same logical object — this is exactly the "stable id"
  model §0 wants production code to use, not the fragile array-index scheme.
- **The player has its own, fully independent id-to-object bookkeeping.** `ActionPlayer` in
  [tests/recording/action_player.py](tests/recording/action_player.py#L28-L32) keeps a private
  `self._object_map: Dict[int, CanvasObject]` / `self._next_object_id`, populated via
  `_register_object()` ([tests/recording/action_player.py](tests/recording/action_player.py#L617-L623))
  as each fixture action creates/references an object. This is **entirely separate from
  `canvas._object_map`** — the player never reads or writes the canvas's real object map. Only as a
  defensive fallback (labeled "for backward compat") does it fall through to
  `canvas.current_page_objects()[obj_id]` (array index) if the id isn't in its own map — but since
  ids are always registered before use, this fallback path is never actually exercised by current
  fixtures.
  - **Conclusion: the §0 production-code refactor (fixing `canvas`'s internal identity scheme) has
    zero effect on the recording/replay system.** They don't share state or assumptions; no fixture
    migration needed.
- **No fixture (0 of 24, checked via full-text scan for the action-type strings) contains
  `delete_annotation`, `duplicate_annotation`, or `cut_annotation` actions.** Neither
  `action_recorder.py`'s `patch_main_window_for_recording()` nor `ActionPlayer._execute_action()`
  wrap/dispatch those operations at all — delete/duplicate/cut are simply never recorded or
  replayed through this system (they're only covered by direct unit/feature tests that call
  `canvas.delete_selected()` etc. directly, e.g. `tests/unit/test_*` and
  `tests/feature/test_copy_paste_workflows.py`).
  - **Conclusion: `CompositeAction` (§1.2/§1.3) needs no `from_data()`/serialization support for the
    recorder/player's sake** — it will never be constructed from a fixture. Serialization can be
    added later only if/when a real save/reload-of-history feature is introduced (none exists today;
    history is explicitly session-only per DESIGN.md §5.15).

No further verification needed before starting §0/§1 implementation.

---

## 6. Suggested implementation order

1. §0 root-cause refactor (stable id helper + remove dead `_stable_id_map` checks) — unblocks 1.1,
   half of 1.2/1.3, all of §2.1/2.2. §5 already confirms this is safe w.r.t. the recorder/replay
   system, so no separate verification step is needed first.
2. §1.2 + §1.3: add `CompositeAction`, wire into `delete_selected()`/`duplicate_selected_multi()`.
3. §1.4 + §1.5: fix Paste/Duplicate `undo()` to remove specific objects, not LIFO `pop()`.
4. §1.6: tighten `AddAnnotationAction.undo()` fallback logging (no behavior change to the primary
   path since §0 already makes stable ids reliable).
5. §2.3 (objectChanged emits) and §2.4 (Save-As filename bug) — independent, low-risk, quick wins;
   can be done in parallel with the above if convenient.
6. §3.x code-quality items — lowest priority, do opportunistically.
7. §4.x documentation fixes — no code dependency, can be done anytime, ideally alongside the
   corresponding code fix's commit for the text-size one (§4.1) since it's a "which one is correct"
   decision, and standalone for §4.2.

Each numbered bug fix above should get its own TDD test pair (expected-behavior test kept as
regression test; actual-buggy-behavior test deleted after fix + review) per `AGENTS.md`.

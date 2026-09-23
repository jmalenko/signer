# Functional Specification

This document is the authoritative description of Signer's **current** behavior. It is
organized by feature domain, not by release, and is kept in sync with the code. For the
business motivation behind a feature and its release history, see [REQUIREMENTS.md](REQUIREMENTS.md).
For architecture, rationale, and how to run/build/test the app, see [DESIGN.md](DESIGN.md) and
[TESTING.md](TESTING.md).

## Table of Contents

1. [Overview & Scope](#1-overview--scope)
2. [Toolbar & Menu](#2-toolbar--menu)
3. [Supported Document Formats](#3-supported-document-formats)
4. [Opening Documents & Projects](#4-opening-documents--projects)
5. [Export / Save As](#5-export--save-as)
6. [Page Navigation](#6-page-navigation)
7. [Annotations](#7-annotations)
8. [Selection & Multi-Selection](#8-selection--multi-selection)
9. [Editing Operations](#9-editing-operations)
10. [Document & Page Rotation](#10-document--page-rotation)
11. [Undo/Redo History](#11-undoredo-history)
12. [Printing](#12-printing)
13. [Keyboard Shortcuts Reference](#13-keyboard-shortcuts-reference)
14. [Notifications & Error Handling](#14-notifications--error-handling)
15. [Persistence & Settings](#15-persistence--settings)
16. [Project Files (.signer)](#16-project-files-signer)
17. [Prepare Signature Tool](#17-prepare-signature-tool)
18. [CLI Parameters](#18-cli-parameters)
19. [Platform Support](#19-platform-support)

---

## 1. Overview & Scope

Signer is a desktop app for placing a scanned signature (and other annotations) on top of a
document and exporting the result. Typical use: open a document, position a signature and any
supporting marks, and export or print the annotated result.

**Non-goals:**
- Digital certificate signing.
- OCR or general PDF editing beyond image export.
- Freehand drawing annotations.
- Advanced typography (multiple fonts per annotation, rich text) beyond a single font
  family/size per text annotation.

**Example assets** (`examples/`): `document.odt` (master document; other examples are derived
from it), `document.pdf`, `document.doc` / `document.docx`, `document1.pdf` (multi-page),
`document1.jpg`, `signature.png`, `signature.xcf` (GIMP source, not importable).

---

## 2. Toolbar & Menu

### 2.1 Toolbar layout (left to right)

| Control | Behavior |
|---|---|
| **Open** (with dropdown arrow) | Click opens the file picker directly; dropdown also offers Recent Documents |
| **Add** (annotation picker) | Clicking the button opens the same menu as its dropdown arrow (whole button is clickable) |
| **Save** | Opens the Save As dialog |
| Page navigation (◀ / label / ▶) | Only visible when the document has more than one page (see [§6](#6-page-navigation)) |
| **Duplicate** / **Delete** | Only visible when at least one annotation is selected |
| Color button | Annotation color; see context-sensitivity table below |
| Width spinner | Line width in points (vector types only) |
| Font Size spinner | Text annotations only |
| Font combo | Text annotations only |
| Angle spinner | Rotation in degrees; all annotation types |
| Hamburger menu (☰, far right) | See §2.2 |

The **Add** menu (and the hamburger **Annotations** menu) list: Checkmark, Crossmark, Line,
Arrow, Rectangle / Square, Ellipse / Circle, Text (submenu: Free text, Current date, Current
time, Current date & time, then recent texts), Signature / Image (submenu: From file…, then
recent images).

### 2.2 Hamburger menu structure

```
☰
├── File
│   ├── Open Document…
│   ├── Save As…
│   ├── ──────────────
│   ├── Save Project
│   ├── Save Project As…
│   ├── Change Document…
│   ├── Auto-save Project on Save      (checkable toggle)
│   ├── ──────────────
│   ├── Print
│   ├── ──────────────
│   ├── (Recent Documents, top-level)
│   ├── ──────────────
│   └── Exit
├── Edit
│   ├── Undo
│   ├── Redo
│   ├── Cut
│   ├── Copy
│   ├── Paste
│   ├── Duplicate
│   ├── Select All
│   ├── Delete
│   ├── Rotate Current Page Left
│   ├── Rotate Current Page Right
│   ├── Rotate All Pages Left
│   └── Rotate All Pages Right
├── Annotations
│   ├── Checkmark
│   ├── Crossmark
│   ├── Line
│   ├── Arrow
│   ├── Rectangle / Square
│   ├── Ellipse / Circle
│   ├── Text ▶ (Free text / Current date / time / date & time, then recent texts)
│   └── Signature / Image
├── Tools
│   └── Prepare Signature…
└── Help
    └── Homepage
```

The **Tools** group holds standalone utilities that don't operate on the currently open
document. See [§17](#17-prepare-signature-tool) for "Prepare Signature…".

Recent items (documents, texts, images/signatures) appear at the **top level** of their
respective menu, after the static items, separated by a horizontal rule. Each recent list holds
up to 10 entries, ordered most-recently-used first. See [§13](#13-keyboard-shortcuts-reference)
for the keyboard shortcut assigned to each action.

### 2.3 Context-sensitivity rules

Menu and toolbar state is re-evaluated whenever a menu is about to be shown (`aboutToShow`), so
it always reflects current document/selection/history state regardless of how that state
changed (menu, toolbar, or keyboard shortcut).

**Toolbar property controls**, shown per annotation type (or per selection, for multi-selection —
only controls relevant to at least one selected type are shown; a change applies only to the
selected annotations that support that property):

| Control | Checkmark | Crossmark | Line | Arrow | Rectangle | Ellipse | Text | Signature/Image |
|---|---|---|---|---|---|---|---|---|
| Color | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | hidden |
| Width spinner | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | hidden | hidden |
| Font size spinner | hidden | hidden | hidden | hidden | hidden | hidden | ✓ | hidden |
| Font family combo | hidden | hidden | hidden | hidden | hidden | hidden | ✓ | hidden |
| Angle spinner | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

When nothing is selected, all annotation-specific property controls are hidden. Duplicate and
Delete toolbar buttons are visible only when an annotation is selected. The page-navigation
block is hidden entirely (including the "Page 1/1" label) when the document has exactly one
page. Hidden control groups never leave two adjacent toolbar separators.

**Hamburger menu enablement:**

| Item(s) | Enabled when |
|---|---|
| Save As…, Print, Save Project, Save Project As…, Change Document…, rotation actions | A document is open |
| Undo | An action is available to undo |
| Redo | An action is available to redo |
| Cut, Copy, Duplicate, Delete | At least one annotation is selected |
| Paste | A document is open **and** annotation data is available to paste (prior copy/cut, in-app cache, or system clipboard) |
| Select All | The current page has at least one annotation |
| Add Annotation button (toolbar) | A document is open |

---

## 3. Supported Document Formats

| Format | Loader | Multi-page | Notes |
|---|---|---|---|
| PDF | PyMuPDF (fitz), direct | Yes | Supports encrypted PDFs (password prompt) |
| Word (`.docx`, `.doc`) | LibreOffice headless → temp PDF → PyMuPDF | Yes | Requires LibreOffice |
| ODT | LibreOffice headless → temp PDF → PyMuPDF | Yes | Requires LibreOffice |
| JPG, PNG, BMP, WEBP, GIF, ICO | Pillow, direct | No (1 page; GIF uses first frame) | |
| TIFF | Pillow, direct | Yes (multi-frame) | |

All pages, regardless of source format, are normalized to a list of `PIL.Image` objects
rendered internally at **300 DPI**.

**LibreOffice path resolution** (first match wins):
1. `libreoffice_path` in `config.json` (user-configured).
2. A well-known install location for the current OS (e.g. `Program Files\LibreOffice` on
   Windows, `/Applications/LibreOffice.app` or Homebrew paths on macOS, `/usr/bin/soffice` or
   `/snap/bin/libreoffice` on Linux).
3. LibreOffice found on system `PATH`.
4. Otherwise, show: *"LibreOffice is required to open Word and ODT documents. Please either
   install LibreOffice, configure the LibreOffice path in the settings file
   (`config.json`, field `libreoffice_path`), or use a PDF or image file instead."*

**Unsupported format**: *"File format not supported. Please choose a PDF, Word document, ODT,
or image file (JPG, PNG, BMP, WEBP, GIF, TIFF)."*

**Corrupt image/document**: validation error shown; app remains responsive.

The Open file dialog filters for all supported formats together, plus per-format filters
(PDF / Word / ODT / images) for clarity, and also recognizes `.signer` project files (§16).

---

## 4. Opening Documents & Projects

### 4.1 Generic Open action

A single Open action (toolbar button and File menu) accepts documents in any supported format
(§3) and `.signer` project files (§16). Opening a project restores its annotations onto the
referenced document (always showing page 1 first, regardless of any saved "current page").

### 4.2 Unsaved-changes prompt

Opening a new document or project (menu, toolbar, or drag-and-drop) when the current document
has unsaved annotation changes shows:

```
Title: "Save changes to '{filename}'?"
Buttons: [Save] [Don't Save] [Cancel]   (default: Cancel)
```

- **Save**: saves using the last-used format/path, then proceeds to load.
- **Don't Save**: discards the dirty flag, proceeds to load.
- **Cancel**: aborts; current document/state is kept.

This check runs once per open action; after the file dialog's event loop completes, keyboard
focus returns to the canvas so page navigation works immediately without a preliminary click.

### 4.3 Drag-and-drop

The canvas accepts dropped files (`text/uri-list`):

| Dropped item | With open document | Without open document |
|---|---|---|
| **Small image** (fits A6 at 300 DPI, ≤1748px on both dimensions; PNG/JPG/JPEG/BMP) | Creates a Signature/Image annotation at the drop position, scaled to fit ~A6 while preserving aspect ratio | Error: *"Cannot drop image: No document is currently open"* |
| **Big image** (exceeds A6 in any dimension) or **PDF** | Runs the unsaved-changes prompt (§4.2) if dirty, then loads the file as the document | Loads immediately as the document |

Other error cases: corrupted/unsupported dropped image → *"Cannot load image: Unsupported
format or corrupted file. Supported formats: PNG, JPG, JPEG, BMP."*; invalid/corrupted dropped
document → *"Cannot open file: Invalid or corrupted file."*; permission error → *"Cannot open
file: Access denied."*; a drop while a dialog is open is ignored.

### 4.4 Recent documents

Up to 10 recently opened documents/projects, most-recent-first, persisted across sessions (see
§15). Available via the toolbar Open dropdown and the hamburger File menu's top-level recent list.

### 4.5 Window & canvas sizing

- Before a document is loaded, the window sizes itself using portrait A4 geometry at the
  internal 300 DPI rendering resolution.
- Once a document is open, the window's aspect ratio adapts to the document's aspect ratio
  (scaled to fit available screen space, minimum canvas 520×640px, maximum 100% — no
  upscaling), while keeping the entire toolbar visible. The window is centered on screen when a
  document is opened.
- Canvas space outside the document is minimized: vertical window chrome is derived from the
  fixed toolbar height, so the canvas follows the document aspect ratio with no avoidable bars
  above/below an A4 page.
- Performance targets: open/render the current page in under 1 second for common office
  documents; drag/scale interaction has no visible lag; export quality suits typical print/email
  workflows.

---

## 5. Export / Save As

### 5.1 Supported export formats

| Format | Multi-page output | Compression |
|---|---|---|
| JPG | One file per page | Lossy, quality 1-100 (default 95) |
| PNG | One file per page | Lossless, always `compress_level=9` |
| BMP | One file per page | Uncompressed |
| PDF | Single file, all pages | Lossy raster embed, quality 1-100 (default 95) |
| TIFF | Single file, all pages (multi-frame) | Lossless, always LZW |

All formats render at 300 DPI.

### 5.2 Default file naming

- Single-page document: `{name}-signed.{ext}`.
- Multi-page, per-page formats (JPG/PNG/BMP): `{name}-signed-p#.{ext}`, where `#` is a
  placeholder that becomes the zero-padded page number on save (digit count = digits needed for
  the highest page number), e.g. `document-signed-p01.jpg` … `document-signed-p12.jpg`.
- Multi-page, single-file formats (PDF/TIFF): `{name}-signed.{ext}` (all pages inside).

### 5.3 Save As dialog behavior

- Remembers the last-used export format and pre-fills it.
- Uses a non-native (Qt-rendered) file dialog so the filename field can be monitored in real
  time; this trades the native OS dialog look for live auto-correction (see
  [DESIGN.md](DESIGN.md) for the rationale).
- **Real-time format switching**: changing the extension (or the file-type filter) updates the
  filename to match the new format's naming rules while preserving the user's custom filename
  stem:
  - Single-file → per-page format, multi-page doc: adds the `p#` placeholder.
  - Per-page → single-file format: removes the placeholder.
- **Validation**: single-file formats accept any filename. Per-page formats require the `#`
  placeholder when the document has more than one page; a filename missing it shows an info
  dialog and returns to the Save As dialog (not closed) for correction.
- **Options… button**: enabled only for lossy formats (JPG, PDF); opens a non-modal "Export
  Quality Options" panel with a 1-100 quality slider (labeled "small file" ↔ "large file",
  numeric value always visible) and OK/Cancel. Hidden for lossless formats (PNG/TIFF/BMP), which
  always use their best automatic setting.

### 5.4 Overwrite confirmation

Checked before export, per target file:

| Scenario | Dialog |
|---|---|
| Single target file exists | "The file '{name}' already exists. Do you want to replace it?" — [Replace] [Cancel] |
| A few (≤10) of several multi-page targets exist | Lists the specific files that will be overwritten — [Replace] [Cancel] |
| All multi-page targets exist | "All {N} pages of '{pattern}' will be overwritten." — [Replace] [Cancel] |
| More than 10 targets exist | Lists first 3 + "… (N more files)" — [Replace] [Cancel] |
| Fewer pages exported than a previous export with the same name pattern | Custom dialog listing files to overwrite **and** older out-of-range page files that can optionally be deleted, via an unchecked-by-default "Delete older page files" checkbox that relabels the primary button between "Replace" and "Replace and delete older page files" |

Filenames in these dialogs are shown relative to the export directory, sorted alphabetically,
with extensions. Clicking Cancel returns to the Save As dialog without closing it. If cleanup of
older files fails partway, a warning is shown but the current-range export still proceeds.

### 5.5 Post-export notification

See [§14](#14-notifications--error-handling) for the toast used after a successful export, and
the modal error dialog used on failure.

---

## 6. Page Navigation

- Toolbar: `◀` / page label / `▶`, visible only when the document has more than one page.
- Keyboard navigation is also available (see [§13](#13-keyboard-shortcuts-reference)).
- Independent per-page annotation lists (`page_index -> objects[]`); switching pages clears the
  current selection.

---

## 7. Annotations

### 7.1 Types and default geometry

All sizes are stored in PDF points (1/72 inch) and scaled for 300 DPI rendering via
`DPI_SCALE = 300/72 ≈ 4.167`.

| Type | Default size (pt) | Default size (px @300 DPI) |
|---|---|---|
| Checkmark | 20×20 | ≈83×83 |
| Crossmark | 20×20 | ≈83×83 |
| Line | 80×80 | ≈333×333 |
| Arrow (generic, points right/east by default) | 80×80 | ≈333×333 |
| Rectangle / Square | 80×80 | ≈333×333 |
| Ellipse / Circle | 80×80 | ≈333×333 |
| Text | fits content (see §7.2) | — |
| Signature / Image | native/fit size | — |

Default color: `#cc0000`. Default line width: 1.5pt (range 0.5-16pt). See [§2.3](#2-toolbar--menu)
for which types support color/width/font controls.

### 7.2 Text annotations

- Default font size 11pt, default font family Arial; no text wrapping.
- New text annotations render at the toolbar's current point size, with the boundary sized to
  fit the full text (via Qt font metrics) without cropping, zero margin.
- Ctrl+Enter inserts a newline in the text edit; Enter/closing the editor commits changes as
  per the current native editor behavior.
- Toolbar font-size changes refit the boundary immediately (no click needed to force a
  visual update).
- Resizing the boundary derives the largest whole-point font size that fits and pushes that
  value back to the toolbar spinner; during a live drag only the fitted boundary is shown (no
  transient mouse-sized flash), and the spinner remains operable immediately once the drag ends.
- `[` / `]` step the font size through `FONT_SIZE_STEPS_PT` = 6, 7, 8, 9, 10, 11, 12, 14, 16, 18,
  20, 24, 28, 32, 36, 40, 48, 54, 60, 66, 72 (clamped at the ends; snaps to the nearest step in
  the press direction if not already on the list).
- Toolbar property labels omit measurement units (tooltips describe units where relevant).

### 7.3 Image annotation

Signature and Image are unified as a single "Signature / Image" annotation type. Loading is via
a file dialog ("From file…") or a recent-images submenu (up to 10 entries, LRU). Any image
format supported by Pillow may be used; it is scaled to fit the bounding box while preserving
aspect ratio. Color and line-width controls are hidden for this type.

### 7.4 Shape auto-detection (Rectangle/Square, Ellipse/Circle)

- If height/width differ by ≤20%, the shape is created as a **square**/**circle**; otherwise a
  **rectangle**/**ellipse**. Holding any modifier key (Shift, Ctrl, or Alt) during creation
  disables snapping and forces the non-square/non-circle variant.
- On resize, the square/circle-vs-rectangle/ellipse classification is re-evaluated (visual only;
  the underlying annotation type in data is unchanged).

### 7.5 Line/Arrow angle snapping

While drawing or resizing a Line or the generic Arrow, if the angle is within 10° of one of the
8 cardinal/intercardinal directions (0°, 45°, 90°, …, 315°), it snaps exactly to that direction.
Holding any modifier key (Shift, Ctrl, Alt) disables snapping for precise control.

### 7.6 Free corner dragging

Applies to Line, Arrow, Rectangle, Ellipse, Checkmark, Crossmark (not Text or Signature/Image,
which move/scale as a unit). Dragging any corner/endpoint past the opposite corner swaps which
corner is which (e.g. dragging the bottom-right corner above the top-left turns it into the new
top-right corner); for Line/Arrow this can flip the line's effective direction.

### 7.7 Duplicate & default placement

- **Duplicate** preserves size and color, offsetting the copy by 20px (`DUPLICATE_OFFSET`).
- New annotations default to the **center of the current page**: `x = (page_width -
  object_width)/2`, `y = (page_height - object_height)/2`, clamped to page bounds.
- **Exception**: a Signature/Image annotation added via the `-signature` CLI argument or the
  Signature submenu defaults to 80% down the page instead: `y = 0.8 × page_height -
  object_height/2`, still centered horizontally. This mirrors typical bottom-of-page signature
  placement.

### 7.8 Color/width toolbar controls

The color and line-width toolbar controls are visible only when a compatible annotation is
selected (§2.3); there is no toolbar control for either when nothing is selected. Changing a
control updates the selected annotation(s) directly, and as a side effect also becomes the
default applied to the next newly-added annotation.

### 7.9 Rotation

- Every annotation has a `rotation` angle in whole degrees, clockwise from its natural
  orientation, normalized to `0`–`359`; new annotations start at `0`.
- A selected annotation has a rotation handle centered above its boundary and connected to it by
  a short stem. Dragging the handle around the annotation's center snaps to 15° increments by
  default. Holding Shift during the drag temporarily disables snapping for continuous rotation,
  consistent with the existing Line/Arrow snapping behavior in §7.5.
- The selection boundary and its resize handles rotate with the annotation. Hit-testing,
  moving, and resizing use the rotated geometry; resizing preserves the current angle.
- The toolbar Angle spinner is visible for every annotation type, accepts one-degree steps, and
  provides a reset-to-0 action. With a single selection it displays that annotation's angle.
- With a multi-selection, the primary annotation supplies the displayed reference angle.
  Changing that angle or dragging the shared rotation handle applies the same angular delta to
  every selected annotation and rotates every annotation center around the selection's shared
  center. Relative positions and relative angles are preserved.
- Line and Arrow endpoint dragging retains the 45° snapping rules in §7.5. Their `rotation`
  value describes the direction of the resulting endpoints; rotating either type moves both
  endpoints rigidly around its center.
- Rotation changes are undoable and redoable. Duplicate, cut, copy, and paste preserve the
  angle. Export and print render the same orientation shown on the canvas.

---

## 8. Selection & Multi-Selection

- Click an annotation to select it (single selection); click empty canvas to deselect all.
- `Shift+click` adds/removes the clicked annotation to/from the current selection.
- Selection is limited to the current page; navigating to another page clears it.
- A cursor inside the bounding box of one or more annotations selects the nearest one by
  distance to its nearest rendered (non-transparent) pixel; transparent pixels inside a bounding
  box still count as selectable space for that purpose. A cursor outside all bounding boxes
  selects nothing.
- A single selected annotation shows a blue boundary aligned with its rotated local axes, resize
  handles, and a rotation handle. A multi-selection shows each selected annotation's blue
  boundary plus one shared axis-aligned group boundary and rotation handle; resize handles are
  shown only on the primary selected object.

---

## 9. Editing Operations

All operations below apply to the full current selection (single or multi) as one undo/redo
unit unless noted otherwise. See [§13](#13-keyboard-shortcuts-reference) for keyboard shortcuts.

| Operation | Behavior |
|---|---|
| Move | 12pt per press; Shift+arrow = 1px |
| Resize | Drag boundary handles; non-text/non-signature types preserve aspect ratio unless the type supports free resize (Text, Line, Arrow, Rectangle, Ellipse). Dragging a handle past the opposite (anchor) handle flips the box across that anchor — the dragged handle becomes the opposite corner/edge and resizing continues. |
| Rotate | Drag the rotation handle around the object/group center (15° snapping by default; Shift disables snapping), or set a whole-degree angle in the toolbar |
| Duplicate | Copies preserving size, color, and rotation, offset 20px |
| Cut | Copies to clipboard (JSON), then deletes |
| Copy | Copies selection to clipboard as JSON, capturing coordinates at copy time (later moves of the source do not affect the paste) |
| Paste | Same page: applies the same 20px offset as Duplicate. Different page: no offset. |
| Delete | Removes selection |
| Select All | Selects all annotations on the current page |

The clipboard uses the same JSON annotation schema as project files and action recording (see
§16), and interoperates with the system clipboard across document instances/app launches.

---

## 10. Document & Page Rotation

- Actions (Edit menu, see [§13](#13-keyboard-shortcuts-reference) for shortcuts): Rotate Current
  Page Left/Right, Rotate All Pages Left/Right (90° increments; cumulative — 4× in one direction
  returns to 0°).
- **Per document**: rotation belongs to the document it was applied to. Opening another
  document resets every page back to 0°.
- Rotation is stored in project files (the `rotations` map, see [§16](#16-project-files-signer))
  and restored when the project is opened, with the rendered pages re-rotated to match.
- Page rotation applies the same rigid transform to the complete geometry of every annotation,
  including its center, local axes, boundary, and Line/Arrow endpoints. An annotation therefore
  remains attached to the same page content and rotates visually with that content.
- This page transform is composed with the annotation geometry for display, interaction, export,
  and print; it does not overwrite the annotation's stored coordinates or intrinsic `rotation`.
  Consequently, saving a project while a page is rotated does not bake that session-only page
  rotation into its annotations.
- For a point `(x, y)` on an original `W×H` page, the transforms into the rotated frame are:
  - 90° CCW: `(x, y) → (y, W - x)`
  - 180°: `(x, y) → (W - x, H - y)`
  - 270° CCW: `(x, y) → (H - y, x)`
- Annotation angles use the clockwise convention from §7.9. For display, a page rotation left
  subtracts 90° from each annotation's intrinsic angle; a page rotation right adds 90°,
  normalized to `0`–`359`.
- Mouse interaction coordinates are converted back through the inverse transform.
- The window auto-resizes to keep the correct aspect ratio across portrait/landscape rotation.
- Export renders each page with its own current rotation (mixed rotations per page are
  supported) across all export formats.
- Replacing the underlying document (Change Document) preserves every annotation's coordinates,
  size, and orientation as-is; it does not rotate their arrangement just because the new
  document has a different page orientation.
- If the replacement document has fewer pages than the original, annotations whose page index
  no longer exists become inaccessible (not shown, not exported, not included in a subsequent
  Save Project) — only annotations on pages that still exist in the new document remain in
  effect.

---

## 11. Undo/Redo History

- Unlimited history for the current session; **not persisted** — cleared when a new document is
  opened or the app closes.
- **Coalescing**: one continuous adjustment of the same annotation is a single undo entry — a
  drag from mouse press to release, or a run of consecutive arrow-key nudges. Only the state
  before and after the run is kept, not the intermediate positions it passed through. The
  gesture is the unit, not the number of moves: two separate drags are two undo entries, just
  like any other two edits. Nudging a multi-selection records one entry per key press, since
  the group move is a single compound entry that cannot absorb the next one.
- **Action model**: a partial format (used by action recording / test fixtures, e.g. `{type:
  "move_annotation", object_id: 0, x: 300, y: 400}`) is promoted to a full format at undo-stack
  finalization time (adds `from_x`/`from_y` etc.) — both formats use the same action classes and
  serialization, so no separate conversion step exists.
- **Undoable actions**: add, delete, move, resize, color change (annotation or default),
  set text, duplicate, cut/copy/paste (incl. multi-selection), select, rotate annotation or page
  (current or all), and multi-selection variants of delete/duplicate/color/width/rotation change
  as single units.
- Undoing a page rotation restores each affected page's own previous angle, so rotating one page
  and then all pages does not collapse them to a single shared orientation.
- Performing a new action while in an undone state clears the redo stack.
- Undo/redo always applies to the page the affected annotation belongs to, not to the page
  currently on screen; navigating between the action and the undo does not move the annotation
  to another page.

---

## 12. Printing

- Hamburger File menu → Print, opens the platform's native print dialog (printer selection,
  pages, copies, orientation, preview).
- Each page is rendered with its annotations composited (signatures, text, checkmarks, arrows,
  etc.) at 300 DPI before printing.
- Success and failure are both reported to the user; in automated tests, the print dialog
  interaction is bypassed (test mode).

---

## 13. Keyboard Shortcuts Reference

All shortcuts below are active only in the default document view, when no dialog is open and no
text input field currently has focus (this avoids accidental triggers while typing/confirming).

| Hotkey | No-Ctrl alternative | Action |
|---|---|---|
| ← / → (nothing selected) | — | Previous/next page |
| ↑ / ↓ (annotation selected) | — | Move selection up/down 12pt (Shift: 1px) |
| ← / → (annotation selected) | — | Move selection left/right 12pt (Shift: 1px) |
| Page Up / Page Down | — | Previous/next page |
| Home / End | — | First/last page |
| Ctrl+O | O | Open document |
| Ctrl+S | S | Save As… |
| Ctrl+P | P | Print |
| Ctrl+C | C | Copy selection |
| Ctrl+X | X | Cut selection |
| Ctrl+V | V | Paste |
| Ctrl+D | D | Duplicate selection |
| Ctrl+A | A | Select all on current page |
| Delete | — | Delete selection |
| Escape | — | Deselect all |
| Ctrl+Z | Z | Undo |
| Ctrl+Y / Ctrl+Shift+Z | Y | Redo |
| Ctrl+L | L | Rotate all pages left |
| Ctrl+R | R | Rotate all pages right |
| Shift+Ctrl+L | Shift+L | Rotate current page left |
| Shift+Ctrl+R | Shift+R | Rotate current page right |
| `[` / `]` | — | Decrease/increase line width or font size (context-dependent), stepping through the fixed lists in §7.2 (font) / below (line width) |
| `+` | — | Open the Add Annotation toolbar menu |

`[` / `]` for line width step through `LINE_WIDTH_STEPS_PT` = 0.5, 0.75, 1, 1.5, 2, 2.5, 3, 4, 5,
6, 8, 10, 12, 16 (clamped at the ends, snapping to the nearest step in the press direction).

There are no direct hotkeys for adding a specific annotation type; use the Annotations menu or
the toolbar Add button.

---

## 14. Notifications & Error Handling

Three distinct presentation styles, chosen by severity/urgency:

| Style | Used for | Dismissal |
|---|---|---|
| **Success toast** (green, bottom-right) | Post-export notification: "Exported {filename} to [directory link]" (link opens the platform file manager) | Auto-dismiss after 5s, or click the X button early |
| **Error toast** (red, bottom-right) | Brief/non-fatal errors that don't need a blocking dialog, e.g. "Unable to open directory" when the export-directory link target no longer exists | Manual only (X button); does **not** auto-dismiss |
| **Modal dialog** (`QMessageBox`) | Export/save failures (permission denied, disk full, corrupted output), validation errors, missing dependencies (e.g. LibreOffice) | Must be acknowledged; blocks the app window only, not other applications |

Neither toast steals focus from the main window.

**Specific error handling:**
- Missing/unreadable document: canvas interaction blocked, clear error message shown.
- Corrupt image/document: validation error shown, app stays responsive.
- Save failure: modal dialog with cause + recovery suggestion, Retry/Cancel.
- Invalid export path: validated before export, error shown with a corrected suggestion.
- Partial multi-page export failure: export stops, dialog lists failed pages and reason,
  Retry/Cancel; already-written pages remain on disk. The export is reported as failed, so the
  document still counts as having unsaved changes.
- Partially unreadable clipboard data on paste: the readable annotations are pasted and a dialog
  reports how many were skipped, rather than the paste appearing to have succeeded in full.
- Directory-link failure: red toast, "Unable to open directory", logged, does not crash.

---

## 15. Persistence & Settings

Stored as JSON in `config.json` (location depends on portable vs installed mode, §18):

| Field | Type | Default | Purpose |
|---|---|---|---|
| `recent_color` | hex string | `#cc0000` | Last-used annotation color |
| `recent_line_width_pt` | float | `1.5` | Last-used line width |
| `recent_font_family` | string | `Arial` | Last-used text font family |
| `recent_font_size_pt` | int | `11` | Last-used text font size |
| `libreoffice_path` | string \| null | `null` | Manual LibreOffice executable override |
| `last_save_directory` | string \| null | `null` | Last save location |
| `last_export_format` | string | `jpg` | Last-used export format |
| `last_export_folder` | string \| null | `null` | Last export destination folder |
| `last_jpeg_quality` | int | `95` | JPG export quality (1-100) |
| `last_pdf_image_quality` | int | `95` | PDF export image quality (1-100) |
| `recent_signature_paths` | list[string], ≤10 | `[]` | LRU signature/image files |
| `recent_text_strings` | list[string], ≤10 | `[]` | LRU free-text strings (excludes date/time presets) |
| `recent_document_paths` | list[string], ≤10 | `[]` | LRU opened documents/projects |
| `auto_save_project` | bool | `true` | Whether saving auto-writes the `.signer` project file |

Field names use snake_case (matching the Python settings model), since the file is user-facing
and may be hand-edited. Any change to a persisted value (including toggling "Auto-save Project
on Save", which also accepts Qt invocations that omit the checked argument by reading the
action's current check state) is written back immediately.

**Portable vs. installed config location** — checked in this order:
1. `config.json` next to the executable/`main.py` → **portable mode**.
2. Otherwise, the platform user-config directory (created on first use) → **installed mode**:
   - Windows: `%APPDATA%\Signer\config.json`
   - macOS: `~/Library/Application Support/Signer/config.json`
   - Linux: `~/.config/Signer/config.json`

If both locations have a file, the app-directory copy wins (portable mode takes precedence).
Migrating between modes is just moving/copying `config.json` between the two locations.

---

## 16. Project Files (`.signer`)

### 16.1 Purpose

A reusable workspace that stores a document reference plus its annotation layout, for recurring
signing workflows where the same annotations need to reapply to an updated document (e.g. a
monthly form where only the date changes).

### 16.2 Format

UTF-8 JSON. Root object contains exactly:

```json
{
  "version": 1,
  "document_path": "C:/path/to/document.pdf",
  "annotations": { "0": [ { "type": "add_annotation", "annotation_type": "text", "x": 100, "y": 200, "width": 150, "height": 40, "...": "..." } ] },
  "rotations": { "0": 90 }
}
```

- No `schema`, timestamps, `current_page`, or `settings` fields — intentionally minimal.
- Each annotation entry reuses the **same action entity shape** used by action recording and
  feature-test JSON fixtures: `type` is `add_annotation` or `open_signature`, with
  `annotation_type`, `x`, `y`, `width`, `height`, optional `page`, and only the type-specific
  fields needed to restore appearance (text/font properties, color, etc.). The optional
  `rotation` field stores the normalized clockwise annotation angle in degrees and defaults to
  `0` when absent, preserving compatibility with existing files. There is no separate
  project-only annotation schema.
- `width`/`height` are current rendered dimensions; when a `scale` field is present, base
  (unscaled) dimensions are derived by dividing by it, so scaling applies exactly once on load.
- Per-page rotations (§10) are stored in the optional `rotations` map (page index → angle),
  omitted keys meaning 0°. Annotation coordinates stay unrotated, so the page orientation is
  never baked into them.
- Page keys in `annotations` are normalized back to integer page indexes on load.

### 16.3 Naming & location

- Opening a plain document does **not** create a project file.
- A successful export establishes the project path: the exported basename with any multi-page
  `-p#` placeholder removed, plus `.signer` — e.g. `document-signed.jpg` →
  `document-signed.signer` (stored next to the exported file).
- Both auto-save and later explicit saves reuse that same established path.

### 16.4 Lifecycle

- **Auto-save Project on Save** (default enabled, toggle in File menu): writes the project only
  *after* a document export succeeds.
- **Save Project** / **Save Project As…**: reuse the established export-based path, or prompt
  for one if no export has occurred yet.
- Opening a project restores every annotation to its stored page, always displaying **page 1**
  first (the concept of a "saved current page" does not exist), and adds the project to Recent
  Documents.
- If the referenced document is missing or has changed, the app prompts with a **Change
  Document** action rather than failing silently; changing the document preserves every
  annotation's coordinates, size, orientation, and relative arrangement (see §10).
- Saving overwrites the existing `.signer` file in place.
- On open, the `version` field is validated; unsupported versions are rejected with a clear
  error. A missing `version`/no schema is acceptable for version 1 (schema is not part of the
  format).
- Export clips annotations at the page boundary while retaining any visible portion; fully
  off-page annotations remain invisible.

---

## 17. Prepare Signature Tool

A standalone utility (hamburger menu → Tools → "Prepare Signature…") that turns a plain scan or
photo of a signature into a transparent PNG, without requiring an external image editor. It does
not read or modify the currently open document/canvas; it only opens one image or PDF file and
saves a PNG.

The tool is a modal dialog with three stages (§17.1-§17.3); the tuning stage (Stage 3) also
covers live auto-trim/size guidance (§17.4) and concludes with the save action (§17.5) — those
are not separate dialog stages, just further behavior of the same screen.

### 17.1 Stage 1 — Open scan

- File picker accepts the same image formats the app can already open for documents/annotations
  (JPG, PNG, BMP, WEBP, GIF, ICO, TIFF), plus multi-page PDF, using the same rendering pipeline as
  document loading ([§3](#3-supported-document-formats)).
- For a PDF, page navigation controls (same style as the main document view, [§6](#6-page-navigation))
  let the user pick which page to work from; only shown when the opened file has more than one
  page.
- The chosen image/page is expected to be a plain scan/photo (e.g. of a full sheet of paper) and
  may contain more than just the signature.

### 17.2 Stage 2 — Crop

- The opened image is displayed with zoom (mouse wheel, `+`/`-`, fit-to-window default) and pan,
  so a small signature within a large scanned page can be selected precisely.
- The Stage 2 instructions explicitly tell the user to include the entire signature, including
  every stroke, because the selected area is processed in Stage 3.
- The user draws a rectangular selection over the signature, starting the drag from any corner
  (the opposite corner stays anchored regardless of drag direction); the selection can be
  redrawn or its edges/corners dragged to adjust, same interaction model as resizing an
  annotation. Only rectangular selection is supported (no freeform/lasso).
- "Next" advances to Stage 3 using the current selection; "Back"/re-opening lets the user pick a
  different file.

### 17.3 Stage 3.1 — Transparency preview & tuning

- The cropped region is background-removed and shown composited over a **checkerboard pattern**
  by default (the standard transparency indicator used by image editors), so the user can
  visually distinguish transparent pixels from white/light ones — this matters because a
  signature is typically placed over documents that aren't pure white.
- A preview background control lets the user switch the composited backdrop between
  **Checkerboard** and **White**, purely so they can visually confirm how the signature will
  look once applied to a page before saving. This choice affects only the on-screen preview, not
  the saved PNG (which always keeps its real alpha channel).
- The tool offers two sequential signature-extraction **methods**, each controlled by its own
  checkbox. Both methods may be selected at the same time and run in order:
  1. **Method 1: Luminance background removal** (selected by default): pixels are classified by
     how light they are, not by an exact color match, so it works on ordinary paper scans
     without color calibration.
  2. **Method 2: Keep ink color** (selected by default): pixels are classified by hue
     distance to a user-picked ink color, allowing black printed text or dots to be removed from
     around a colored signature.
- In **Method 1: Luminance background removal**, two sliders control the result, updating the
  preview live:
  - **Threshold** — luminance cutoff; pixels lighter than this become fully transparent, darker
    ink stays opaque.
  - **Softness** — width of the gradient band around the threshold, producing smooth
    (anti-aliased) edges instead of a hard cutout.
- In **Method 2: Keep ink color**, the user tunes the color filter applied to the output of
  Method 1 (or to the original crop when Method 1 is not selected):
  - The target ink-color swatch is **blue by default**, matching the common blue-ink signature
    case. The user may choose another color with the swatch color picker or use an eyedropper
    to sample a pixel directly from the crop.
  - Pixels are classified by **hue distance** to the target color (not luminance), so a colored
    signature is kept while black/gray/white content — regardless of how dark it is — is
    dropped, since it doesn't match the target hue and additionally fails a minimum-saturation
    check (near-black/white/gray pixels have no reliable hue and are always excluded). This is
    what removes black text/dots crossed by the ink: the overlapping black content is dropped,
    and the ink stroke crossing over it survives intact.
- **Color tolerance** (hue-distance cutoff) and **Softness** sliders control the ink-color
  filter. Method 2 has no luminance controls; those belong only to Method 1.
- The methods are displayed vertically, one below the other, rather than in a combobox. Each
  method has an independent checkbox and its controls directly below it. Checking or clearing
  either method immediately updates the preview. When both are checked, Method 1 runs first and
  Method 2 runs second; when only one is checked, only that method runs. Both methods are
  selected by default.
- The preview controls are displayed together in one row directly below the preview as
  **Preview**, a gap, **Background**, a gap, the background selector, and the **Show actual
  signature boundary** checkbox. The boundary checkbox is selected by default; both controls
  apply to either method. A vertical gap separates this row from Method 1.
- Directly below Method 2, the screen shows a selected-by-default checkbox labelled
  **"Scale signature to fit 12pt"**. The target regular-character height
  is fixed at 12pt; there is no target-height input. When selected, the UI shows the current
  estimated regular-character height and the calculated scaling information; numeric values are
  informational and are not required in the wireframe. When cleared, no automatic signature
  scaling is applied and the full extracted signature keeps its current dimensions.
- "Reset" restores the controls of each selected method to their default values.

#### Stage 3.1 wireframe

The Stage 3 tuning screen is arranged as follows. The two method selectors are shown together;
either or both can be active at the same time. The exact widget toolkit styling is implementation-defined,
but the grouping and order are part of the specification. The lower part of the screen has two
states depending on the Scale signature checkbox.

```text
+--------------------------------------------------------------------------+
| Transparency preview                                                     |
|                                                                          |
|                 [ full crop preview, fit to available area ]            |
|                 [ dashed actual-signature boundary by default ]         |
|                                                                          |
+--------------------------------------------------------------------------+
| Preview background: (o) Checkerboard  ( ) White   [x] Show actual       |
|                                                     signature boundary   |
|                                                                          |
| [x] Method 1: Luminance background removal                              |
|     Threshold:       [====================o=========]                    |
|     Edge softness:   [=============o================]                    |
|                                                                          |
| [x] Method 2: Keep ink color                                             |
|     Ink color:           [blue swatch] [Pick from image...]               |
|     Color tolerance:     [================o===========]                  |
|     Color softness:      [============o===============]                  |
|                                                                          |
| [x] Scale signature to fit 12pt                                         |
|                                                                          |
| [Back]                                                       [Save As...] |
+--------------------------------------------------------------------------+
```

The method selectors are independent checkboxes. The preview background selector and
actual-boundary checkbox apply to both methods. Method 1 has only the luminance controls, and
Method 2 has only the ink-color controls. If both methods are checked, the output alpha from
Method 1 is passed to Method 2 before auto-trimming and scaling. The scale checkbox is below
Method 2 because it applies to the final output of either method combination. There is no height
control in either scale state.
- "Back" returns to Stage 2 to reselect the crop region without re-opening the file.
- The preview always represents the entire user-drawn crop rectangle. If it is larger than the
  available preview area, the app scales the displayed preview down proportionally to fit the
  available width and height; it does not require scrolling. This display-only scaling never
  changes the crop selection or the saved signature dimensions. Resizing the selection requires
  going back to Stage 2.
- Re-entering Stage 3 (Back to Stage 2, then Next again) preserves every Stage 3 control exactly
  as the user left it (method checkboxes, ink color, sliders, scale checkbox, and preview state) -
  none of it resets to defaults just from navigating between stages. Likewise, returning to
  Stage 1 and continuing again preserves the Stage 2 crop selection, as long as the same page is
  still selected.

### 17.4 Stage 3.2 — Auto-trim & size guidance

- What the user drew in Stage 2 is a rough working area, not necessarily the exact signature
  bounds; after background removal there is usually a tighter "actual signature" rectangle
  (the bounding box of non-transparent content) inside it. To avoid confusing the two, the
  displayed preview (§17.3) always shows the full drawn crop, scaled to fit the available
  preview area when necessary, while a
  **"Show actual signature boundary"** checkbox (checked by default) overlays a dashed outline of
  the tighter bounding box on top of it, updating live as the threshold/softness (or
  color/tolerance) controls change.
- Regardless of whether the boundary overlay is shown, the bounding box described above is what
  actually gets saved: the saved PNG's bounds are auto-trimmed to it, so fully transparent
  border rows/columns left over from an imprecise Stage 2 selection are dropped and the saved
  file's bounds exactly match the visible signature. This auto-trim is not user-configurable.
- The tool calculates the full actual signature-boundary height using the same 300 DPI page-pixel
  convention as the rest of the app ([§7.1](#7-annotations)). The value is used for scaling
  information and is not an editable height control.
- To estimate regular-character height, calculate an alpha-weighted histogram of non-transparent
  pixels for each row within the actual signature bounds. Two independent constants control the
  estimate:
  - `CHARACTER_BAND_TOP_FRACTION` (constant `0.70`, found empirically) limits the search for the densest contiguous
    character band to the top 70% of the visible signature. This avoids letting long lower strokes
    dominate the normal-character estimate and can be tuned if the writing style requires it.
  - `CHARACTER_EXPANSION_BASELINE_PERCENT` (constant `60.0`, found empirically) identifies the first cumulative-alpha
    row used as the expansion baseline. That cumulative range defines the regular-character
    starting height for the expansion visualization; it is separate from the top-fraction search
    limit. The algorithm must be recalculated whenever extraction settings change.
- Starting from the expansion baseline, the expansion algorithm adds one row at a time from the
  top or bottom, choosing the candidate that adds more alpha-weighted pixels, until each requested
  expansion target is covered. Each later range contains the previous range.
- When scaling is selected, calculate the scaling factor before applying any resize:
  `scaling_factor = target_character_height / estimated_character_height`, with
  `target_character_height = 12pt`. Apply that factor to the complete extracted signature,
  including tall strokes, using aspect-ratio-locked high-quality resampling.
- When scaling is selected, the preview shows two horizontal guide lines surrounding the
  estimated regular-character band, updating live as extraction settings change. It also shows
  the estimated character height and calculated scaling factor; no other size input is shown.
- When `DEBUG=1` and scaling is selected, the preview also overlays a green, alpha-weighted row
  histogram inside the actual signature boundary. Each row's green bar extends from the
  boundary's left edge toward its right edge in proportion to that row's non-transparent pixel
  density. The 70% top-of-signature limit remains the character-estimation rule. Separately,
  debug mode shows expansion bars targeting 10%, 20%, through 90% of the full visible signature
  height, centered on the estimated regular-character band. Each later bar must be larger than
  or equal to the previous bar and contain it; labels show the expansion percentage. These
  overlays are display-only and do not affect preview centering or saved output.
- The recommended regular-character range is 10pt–24pt. The fixed 12pt target is within that
  range; the final full-signature height may exceed 24pt because tall strokes are intentionally
  preserved.

### 17.5 Stage 3.3 — Save

- "Save As…" writes the resulting image as a PNG (the only format the app treats as a signature
  source that supports an alpha channel), defaulting the filename to `signature.png` next to the
  source scan.
- After saving, the dialog remains on Stage 3 with the same preview and settings, so the user can
  continue reviewing or adjust the extraction before saving another version. The opened scan and
  Stage 2 crop remain available via Back without reopening the file.
- The saved file is a regular signature image: it can be used afterwards via Annotations →
  Signature/Image → From file…, via the recent-images list, or via the `-signature` CLI
  argument — no different from any other pre-made transparent signature.
- Closing the dialog (X button, Cancel/Escape) while a scan has been opened but not yet saved
  (or saved again after further changes) shows a confirmation: "You have not saved the prepared
  signature. Close anyway?" (Yes/No, default No). Closing after a successful save, or before any
  file has been opened, closes immediately without a prompt.

---

## 18. CLI Parameters

| Parameter | Meaning |
|---|---|
| `-document <path>` | Initial document to load (any format from §3, or a `.signer` project) |
| `-signature <path>` | Initial signature image to load (PNG preferred for transparency) |

- If `-signature` is given together with `-document`, the signature annotation is added
  immediately after load, at the default signature position (§7.7), and becomes fully selected
  (movable/deletable via keyboard right away).
- If `-signature` is omitted, no annotation is auto-added on open.
- If `-signature` is omitted, the previously-used signature file is remembered but **not**
  automatically re-added — it's only available for the Signature submenu's recent list.

Example: `signer -document examples/document.pdf -signature examples/signature.png`

---

## 19. Platform Support

- Supported OSes: Windows 7+, macOS 10.13+, and a maintained Linux distribution whose glibc is
  compatible with the release's PySide6/PyInstaller build.
- Native desktop actions (e.g. opening the export directory from a notification link) use
  platform-independent Qt APIs and open each platform's native file manager.
- LibreOffice remains an optional external dependency for Word/ODT input on every platform; it
  is never bundled with the executable.
- Distribution is a single-file executable per platform (see [DESIGN.md](DESIGN.md) for build
  commands and per-target packaging notes). A release build only proves that platform/CPU
  architecture; PyInstaller does not cross-compile, so Linux/macOS/Windows builds must each be
  produced (and smoke-tested) on their own target.

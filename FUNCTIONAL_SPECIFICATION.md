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

The toolbar consists of a **main row** plus a selection-properties area. The main row is always
visible and never changes size based on selection, so it always fits an A4-proportioned window:

| Control | Behavior |
|---|---|
| **Open** (with dropdown arrow) | Click opens the file picker directly; dropdown also offers Recent Documents |
| **Add** (annotation picker) | Clicking the button opens the same menu as its dropdown arrow (whole button is clickable) |
| **Save** | Opens the Save As dialog |
| **Separator** | Visual separator |
| Page navigation (◀ / current page / total pages / ▶) | Only visible when the document has more than one page; enter a page number in the current-page field and press Enter to navigate (see [§6](#6-page-navigation)) |
| **Separator** | Visual separator; visible when page navigation is visible |
| **Undo** / **Redo** | Reverses or reapplies the most recent undoable action; enabled only when available; shown after page navigation |
| **Separator** | Visual separator |
| **Zoom Out** (minus icon) | Decreases the current document zoom |
| **Fit to Window** (fit icon) | Restores the complete-page view |
| **Zoom In** (plus icon) | Increases the current document zoom |
| Hamburger menu (☰, far right) | See §2.2 |

The **selection-properties area** holds the controls that depend on the current selection,
built from real toolbar rows so it always looks consistent with the main row (including under
dark color schemes):

| Control | Behavior |
|---|---|
| **Duplicate** / **Delete** | Only visible when at least one annotation is selected |
| Color button | Annotation color; see context-sensitivity table below |
| Width spinner | Line width in points (vector types only) |
| Font Size spinner | Text annotations only |
| Font combo | Text annotations only |
| Spacing spinner | Character spacing in points; text annotations only |
| Angle spinner | Rotation in degrees; all annotation types |
| Hand-drawn toggle | Checkable "✎ Hand-drawn" button; sketch-like stroke style (all vector types except Text; see [§7.10](#710-hand-drawn-style)) |

Font Size, Font, and Spacing are independent toolbar items and overflow from right to left as
the available width decreases. Angle and its reset button remain grouped as one atomic item.

Whether the area's own height changes with selection, and how it handles controls that don't fit
the available width, depends on the "Overlay Selection Toolbar on Document" setting (Tools menu,
§2.2, default **off**):

- **Off (reserve space)**: the area is exactly one real toolbar row whose height is always
  reserved, whether or not anything is selected — its space is never given to/reclaimed from the
  canvas, so selecting or deselecting an annotation never resizes or rescales the document, and
  never adds a second row. A control that doesn't fit the row is instead placed behind a "…"
  button at the row's right edge (only shown when needed); clicking it shows the missing
  controls in a popup list anchored below the button.
- **On (overlay)**: the area floats over the top of the document canvas instead, and is visible
  if and only if an annotation is selected — the canvas keeps its size and the document is never
  rescaled, but the area covers its top strip while visible. It uses as many rows as needed: a
  control that doesn't fit the current row wraps onto the next one instead of an overflow button.

As the window narrows in reserve-space mode, a control moves into the "…" popup *before* it would
overlap that button, or before it would extend past the window edge when no button is shown yet.
The "…" button appears in the same resize step in which the first control moves into it. Every
control that leaves the row stays reachable — in the popup (reserve-space) or on a subsequent
row (overlay); controls are never clipped or silently dropped.

Switching the setting produces exactly the layout the app would show if it had been launched in
that mode: no reserved space or leftover strip remains from the previous mode.

Which individual controls are visible within the area still follows the selection/annotation-type
rules below.

The window's minimum width is driven only by the always-visible first row, including the zoom
controls and the hamburger menu, which are never pushed out of view; the selection-properties
area never affects it, in either mode — so
switching to an annotation type with more controls (e.g. Text) never changes the window's size.
We don't rely on Qt's own toolbar overflow ("»") button for this: it doesn't work for custom
widget controls like our labeled spinners/combos (its popup ends up empty), so it is suppressed
entirely and item placement (an overlay row vs. the reserve-space overflow menu) is decided by
our own logic.

The **Add** menu (and the hamburger **Annotations** menu) list: Checkmark, Crossmark, Line,
Arrow, Rectangle / Square, Ellipse / Circle, Text (submenu: Free text, Current date, Current
time, Current date & time, then recent texts), Signature / Image. In the **Add** menu,
Signature / Image is a submenu (From file…, then recent images); in the hamburger **Annotations**
menu it is a single item that opens the file picker, and recent images are available only from
the Add menu.

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
├── View
│   ├── Zoom In
│   ├── Zoom Out
│   └── Fit to Window
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
│   ├── Prepare Signature…
│   ├── ──────────────
│   └── Overlay Selection Toolbar on Document      (checkable toggle, default off)
└── Help
    └── Homepage
```

The **Tools** group holds standalone utilities that don't operate on the currently open
document. See [§17](#17-prepare-signature-tool) for "Prepare Signature…".

Recent items (documents, texts, images/signatures) appear at the **top level** of their
respective menu, after the static items, separated by a horizontal rule. Each recent list holds
up to 10 entries, ordered most-recently-used first. Recent documents and images are labeled with
their file name; see [§4.4](#44-recent-documents) for how same-named files are told apart. See [§13](#13-keyboard-shortcuts-reference)
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
| Character spacing spinner | hidden | hidden | hidden | hidden | hidden | hidden | ✓ | hidden |
| Angle spinner | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Hand-drawn toggle | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | hidden | hidden |

When nothing is selected, all annotation-specific property controls are hidden; in overlay mode
(§2.1) the whole selection-properties row also collapses, while in reserve-space mode its height
stays reserved regardless. Duplicate and Delete toolbar buttons are visible only when an
annotation is selected. The page-navigation block is hidden entirely (including the "Page 1/1"
label) when the document has exactly one page. Hidden control groups never leave two adjacent
toolbar separators.

**Hamburger menu enablement:**

| Item(s) | Enabled when |
|---|---|
| Save As…, Print, Save Project, Save Project As…, Change Document…, rotation actions | A document is open |
| Zoom In / Zoom Out / Fit to Window (toolbar and View menu) | A document is open; in addition, Zoom In is disabled at the maximum zoom, Zoom Out at the minimum zoom, and Fit to Window while the complete page is already shown |
| Undo (toolbar and Edit menu) | An action is available to undo |
| Redo (toolbar and Edit menu) | An action is available to redo |
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
| JPG, PNG, BMP, WEBP, GIF, ICO | Pillow, direct | No (1 page; of an animated GIF/WEBP/PNG or a multi-picture JPEG only the first frame is used) | |
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

**Unsupported format**: *"File format '.xyz' is not supported. Please choose a PDF, Word
document, ODT, or image file."* (shown in the "Could not open document" error dialog).

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

- **Save**: opens the Save As dialog (pre-filled with the last-used format and path); proceeds to
  load once the save succeeded, and stays on the current document if the dialog is cancelled.
- **Don't Save**: discards the dirty flag, proceeds to load.
- **Cancel**: aborts; current document/state is kept.

This check runs once per open action; after the file dialog's event loop completes, keyboard
focus returns to the canvas so page navigation works immediately without a preliminary click.

Only changes to the annotations (including undo/redo, and rotating a page) count as unsaved
changes. Zooming, panning, fitting to the window, navigating pages and selecting never do.

### 4.3 Drag-and-drop

The canvas accepts dropped files (`text/uri-list`):

| Dropped item | With open document | Without open document |
|---|---|---|
| **Small image** (fits A6 at 300 DPI, ≤1748px on both dimensions; any supported image format, §3) | Creates a Signature/Image annotation centered on the drop position (kept inside the page) at its pixel size, which is at most A6 by definition | Error: *"Cannot drop image: No document is currently open"* |
| **Big image** (exceeds A6 in any dimension), **PDF**, **Word/ODT document**, or **project** (`.signer`) | Runs the unsaved-changes prompt (§4.2) if dirty, then opens the file exactly as the Open action does | Opens immediately, exactly as the Open action does |

A dropped small image that becomes an annotation is also added, by absolute path, to the
recent images/signatures list (§7.3), as if it had been loaded with "From file…". Dropped
documents (big images, PDFs) are not.

Other error cases: a dropped file of an unsupported type, or an image that cannot be read →
*"Cannot open file: Unsupported format or corrupted file."*; a dropped document that cannot be
opened shows the same error as the Open action (§3); a dropped file that no longer exists →
*"File not found: …"*; a drop while a dialog is open is ignored.

### 4.4 Recent documents

Up to 10 recently opened documents/projects, most-recent-first, persisted across sessions (see
§15). Available via the toolbar Open dropdown and the hamburger File menu's top-level recent list.

Entries are stored by absolute path, however the file was opened (a relative command-line path is
made absolute against the working directory at that moment). Opening an already listed file moves
its entry to the front instead of adding another one. Opening a project adds the project and
the document it refers to.

**Entry labels** (recent documents and recent images/signatures alike): an entry is labeled with
its file name. When two or more entries in the same list share a file name, those entries are
labeled `name — folder`, where `folder` is the full path of the file's parent folder, shown
untruncated. Entries with a unique name keep the plain file name. Labels are recomputed whenever
the list is rebuilt.

### 4.5 Window & canvas sizing

- Before a document is loaded, the window sizes itself using portrait A4 geometry at the
  internal 300 DPI rendering resolution.
- Once a document is open, the window's aspect ratio adapts to the document's aspect ratio
  (scaled to fit available screen space, minimum canvas 520×640px, maximum 100% — no
  upscaling), while keeping the entire toolbar visible. The window is centered on screen when a
  document is opened.
- Canvas space outside the document is minimized: vertical window chrome is derived from the
  fixed toolbar height, so the canvas follows the document aspect ratio with no avoidable bars
  above/below an A4 page. In reserve-space mode (§2.1), the selection-properties row's height is
  also reserved up front, so selecting an annotation later never triggers a window resize.
- Performance targets: open/render the current page in under 1 second for common office
  documents; drag/scale interaction has no visible lag; export quality suits typical print/email
  workflows.

### 4.6 Document zoom

- The document view starts in **Fit to Window** mode, showing the complete current page within
  the available canvas while preserving its aspect ratio.
- The user can zoom in and out of the current page. Zooming is centered on the canvas unless the
  interaction provides a specific focal point; the view shall keep the focal document position
  under the pointer when zooming with a pointer-based interaction.
- Zoom steps shall be reversible within the available range: one Zoom In followed by one Zoom Out,
  or one Zoom Out followed by one Zoom In, shall restore the exact zoom level that was effective
  before the two actions when neither action is limited by a zoom boundary. At Fit to Window,
  Zoom Out is a no-op; the next Zoom In starts from the fit level.
- The user can restore **Fit to Window** at any time. Changing pages restores the complete-page
  view for the newly selected page.
- Zoom Out shall not reduce the document below its Fit to Window scale. The document must never
  become smaller than the canvas in both dimensions, which prevents gray space from appearing on
  all four sides at once.
- When zooming out leaves gray space on one side of an axis, the opposite document edge remains
  aligned with the corresponding window edge. The view must not recenter the document and move the
  gray space to the opposite side; the focal position is adjusted to preserve that edge alignment.
- When zoomed beyond the available canvas, the user can pan the page to reach any document area.
  Panning is available by dragging with the middle mouse button or by holding Space while
  dragging with the left mouse button.
  The page shall not be scaled up beyond the fit-to-window scale when fit mode is restored.
- Zoom changes only the display transform. Annotation coordinates, hit testing, selection,
  moving, and resizing are converted through the current view transform and remain in document
  coordinates.
- Export and print always render the document and annotations at the normal 300 DPI output
  resolution; the current on-screen zoom and pan position never affect exported or printed
  output.

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

All formats render at 300 DPI. Exported images and PDF pages carry that resolution (the PDF
page keeps the physical size of the source page, e.g. A4), not only the pixel dimensions.

When the document has no annotations, Save As explains that there is nothing to save and exports
nothing.
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
- **Format**: a recognized extension typed by the user decides the export format, even when the
  file-type filter shows another one; if the extension is missing or unknown, the selected filter
  decides. Switching the filter in the dialog re-writes the extension and updates the Options…
  button at once.- **Validation**: single-file formats accept any filename. Per-page formats require the `#`
  placeholder when the document has more than one page; a filename missing it shows an info
  dialog and returns to the Save As dialog (not closed) for correction.
- **Options… button**: enabled only for lossy formats (JPG, PDF); opens an "Export
  Quality Options" panel (modal, over the Save As dialog) with a 1-100 quality slider (labeled "small file" ↔ "large file",
  numeric value always visible) and OK/Cancel. Disabled (greyed out) for lossless formats
  (PNG/TIFF/BMP), which always use their best automatic setting.

### 5.4 Overwrite confirmation

Checked before export, per target file:

| Scenario | Dialog |
|---|---|
| Single target file exists (a single-file PDF/TIFF, or a single-page document exported to JPG/PNG/BMP) | "The file '{name}' already exists. Do you want to replace it?" — [Replace] [Cancel] |
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

- Toolbar: `◀` / current-page input field / total pages / `▶`, visible only when the document has
  more than one page.
- Keyboard navigation is also available (see [§13](#13-keyboard-shortcuts-reference)).
- Independent per-page annotation lists (`page_index -> objects[]`); switching pages clears the
  current selection.

---

## 7. Annotations

### 7.1 Types and default geometry

All sizes are defined in PDF points (1/72 inch). Internally, annotation coordinates and sizes are
document coordinates, i.e. pixels of the page rendered at 300 DPI, so a size in points is stored
multiplied by `DPI_SCALE = 300/72 ≈ 4.167`. Where a distance in this document is given in `px`,
it is such a 300-DPI document pixel.

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

The Arrow retains an 80×80pt storage square for sizing and endpoint calculations, but its
selection, hit-testing, and multi-selection boundary is the minimal local axis-aligned rectangle
containing the rendered shaft, arrowhead, and full stroke. Transparent space between that tight
rectangle and the storage square is not selectable. Checkmark and Crossmark use their storage
squares as their visual bounds: the Crossmark strokes end at the corners, and the Checkmark
reaches the left, bottom, top, and right edges.

### 7.2 Text annotations

- Default font size 11pt, default font family Arial; no text wrapping.
- Default character spacing is 0pt. The toolbar accepts positive and negative values in 1pt
  steps, with no application-imposed minimum or maximum, and refits the boundary immediately
  when the value changes.
- A selected text annotation has a diamond handle beyond the right-edge midpoint. Dragging it
  along the annotation's local horizontal axis changes character spacing without changing font
  size. The handle follows annotation rotation and spacing changes are undoable/redoable.
- New text annotations render at the toolbar's current point size, with the boundary sized to
  fit the full text (via Qt font metrics) without cropping, zero margin. The text is inside the
  boundary at any character spacing; the spacing after the last character of a line does not
  widen (or narrow) the boundary.
- Enter inserts a newline in the text edit; Ctrl+Enter (or the OK button) commits the changes.
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
a file dialog ("From file…") or a recent-images submenu (up to 10 entries, LRU). The image can be
any format of the supported-image list (§3) that the file dialog offers or that is dropped onto
the canvas; it is scaled to fit the bounding box while preserving
aspect ratio. Color and line-width controls are hidden for this type. An image dropped onto
the canvas (§4.3) is added to the recent-images list as well. Same-named entries are told apart
as described in §4.4.

### 7.4 Shape snapping (Rectangle/Square, Ellipse/Circle)

- While resizing a Rectangle or Ellipse, if width/height is within 0.8–1.2 the shape snaps to a
  **square**/**circle** (dragging a left/right edge makes the width equal to the height, a
  top/bottom edge makes the height equal to the width, a corner makes both the average of the
  two); beyond that range the shape is a free **rectangle**/**ellipse**.
  Holding any modifier key (Shift, Ctrl, or Alt) disables the snapping.
- The annotation type in the data is the same whether or not the shape is currently square.

### 7.5 Line/Arrow angle snapping

While drawing or resizing a Line or the generic Arrow, if the angle is within 10° of one of the
8 cardinal/intercardinal directions (0°, 45°, 90°, …, 315°), it snaps exactly to that direction.
Holding any modifier key (Shift, Ctrl, Alt) disables snapping for precise control.

A Line's local bounding box is the axis-aligned rectangle containing its complete stroked segment.
Each dimension is at least `N = stored side × 0.18 × sin(35°)`, matching how the perpendicular
spine-to-barb distance of a horizontal Arrow scales. Padding needed to reach `N` is split equally
on both sides so the Line remains centered. This rectangle is used for the visible blue boundary,
hit-testing, and group bounds; endpoint handles remain on the segment endpoints.

### 7.6 Free corner dragging

Applies to every annotation type. Dragging any corner/endpoint past the opposite corner swaps
which corner is which (e.g. dragging the bottom-right corner above the top-left turns it into
the new top-right corner); for Line/Arrow this can flip the line's effective direction.
Text, Line, Arrow, Rectangle and Ellipse resize freely; Signature/Image, Checkmark and Crossmark
keep their aspect ratio while resizing.

### 7.7 Duplicate & default placement

- **Duplicate** preserves size, color, and hand-drawn style (§7.10), offsetting the copy by 20px (`DUPLICATE_OFFSET`).
  The copies stay inside the page; several copies keep their relative positions and stacking
  order.
- New annotations default to the **center of the current page**: `x = (page_width -
  object_width)/2`, `y = (page_height - object_height)/2`, clamped to page bounds.

### 7.8 Color/width toolbar controls

The color and line-width toolbar controls are visible only when a compatible annotation is
selected (§2.3); there is no toolbar control for either when nothing is selected. Changing a
control updates every selected annotation that supports it (and is undoable). The change also
becomes the default applied to the next newly-added annotation, whichever way it was made: the
toolbar control, the `[` / `]` shortcuts, or resizing a text annotation (font size). The
Hand-drawn toggle (§7.10) follows the
same visibility rule; its default additionally looks at the annotations already in the document.

### 7.9 Rotation

- Every annotation has a `rotation` angle in whole degrees, clockwise from its natural
  orientation, normalized to `0`–`359`; new annotations start at `0`.
- A selected annotation has a rotation handle connected to its boundary by a short stem. For
  most types it is centered above the boundary; for Line and Arrow, whose boundary is the tight
  box around the stroke, it sits 24 viewport pixels from the center, perpendicular to the line,
  and so may lie inside that boundary. Dragging the handle around the annotation's center snaps
  to 15° increments by default. Holding Shift during the drag temporarily disables snapping for
  continuous rotation, consistent with the existing Line/Arrow snapping behavior in §7.5.
- The selection boundary and its resize handles rotate with the annotation. Hit-testing,
  moving, and resizing use the rotated geometry; resizing preserves the current angle.
- The toolbar Angle spinner is visible for every annotation type, accepts one-degree steps, and
  provides a reset-to-0 action. With a single selection it displays that annotation's angle.
- With a multi-selection, the primary annotation supplies the displayed reference angle.
  Changing that angle or dragging the shared rotation handle applies the same angular delta to
  every selected annotation and rotates every annotation center around the selection's shared
  center. Relative positions and relative angles are preserved.
- Line and Arrow endpoint dragging retains the 45° snapping rules in §7.5. Dragging an endpoint
  stores the direction of the line in the annotation's separate line `angle` (an Arrow without
  one points east, a Line without one runs from bottom-left to top-right), and does not change
  `rotation`. The Angle spinner always shows `rotation`, the turn of the whole annotation about
  its center, so it stays at its value after an endpoint drag; rotating either type with the
  spinner or the rotation handle moves both endpoints rigidly around its center.
- Rotation changes are undoable and redoable. Duplicate, cut, copy, and paste preserve the
  angle. Export and print render the same orientation shown on the canvas.

### 7.10 Hand-drawn style

Applies to Checkmark, Crossmark, Line, Arrow, Rectangle / Square, and Ellipse / Circle. Text and
Signature / Image have no such property.

- Each supported annotation has a boolean **hand-drawn** property, edited with the "Hand-drawn"
  toggle in the selection-properties area (§2.1, §2.3). The toggle is visible when at least one
  selected annotation supports it and shows the primary selected annotation's value; clicking it
  applies the new value to every selected supported annotation and ignores the others. There is
  no keyboard shortcut.
- When off, the annotation is drawn exactly as before. When on, an annotation that is composed
  of lines (Checkmark, Crossmark, Line, Arrow, Rectangle / Square) is composed of wobbly lines
  instead, drawn as slightly wobbly paths with the annotation's color, width, and round
  caps/joins.
- An Ellipse / Circle is one continuous closed curve with no start or end: its outline is
  divided into several segments joined by a smooth spline, and the wobble is applied around the
  whole outline, so no seam, gap, or overlap is visible where it would otherwise begin and end.
- The endpoints of each wobbly line are exactly those of the straight version; only the interior
  of each line deviates. The deviation grows with the stroke's length and line width, but is
  capped to a small fraction of the line's length (and, for Rectangle and Ellipse, of the shorter
  side) so the shape stays recognizable. A Rectangle's corners are exactly where the straight
  Rectangle has them, so switching the style on or off does not move them. The wobble may bulge
  slightly past the bounding box; print and export leave room for it, so it is never cut off.
- The wobble is fully determined by the annotation's **seed**, an integer chosen at random when
  the annotation is created, together with its local size. It is therefore identical across
  repaints, zoom levels, moves, rotation, selection, undo/redo, save/reload, copy/paste, and
  on-screen, printed, and exported rendering. Resizing changes the local size and so may change
  the wobble. Duplicate and copy/paste preserve the seed (the copy looks identical); separately
  created annotations get different seeds and so look different even when their geometry matches.
- Selection boundary, resize handles, hit-testing, snapping (§7.5), and bounding-box rules (§7.1)
  always use the ideal straight geometry, never the wobbly path; only the choice of the nearest
  of several overlapping annotations (§8) measures to the drawn pixels.
- Toggling the property is undoable; a toggle on a multi-selection is a single undo entry.
- A newly created annotation of a supported type (Add menu/toolbar; not Duplicate or Paste, which
  copy the source's value) gets its initial hand-drawn value from the first rule that applies. The
  document means all of its pages, and only annotations that support the property are considered:
  1. If any of them is not hand-drawn, the new annotation is **not** hand-drawn.
  2. Otherwise, if there are any (so all are hand-drawn), the new annotation **is** hand-drawn.
  3. Otherwise (the document has none) the last-used value applies: the most recently set value,
     like color and width (§7.8). It is initially **off**, so existing and new annotations look as
     before until the user turns it on, and is persisted as `recent_hand_drawn` (§15).

  The rules choose only the initial value; the user can still change it with the toggle, which
  also updates the last-used value. Text ignores the property.
- The property and seed are stored in project files, action recording, and the clipboard (§16),
  also for annotations that are not hand-drawn, so turning the style on later gives the look the
  annotation would have had before saving or copying; data without them loads as hand-drawn off
  with a new random seed.

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
  boundary plus one shared axis-aligned group boundary and rotation handle; a multi-selection
  has no resize handles (none are drawn and none can be grabbed).
- Moving a multi-selection with the mouse (dragging any selected annotation) moves every
  selected annotation by the same distance; so do the arrow keys.
- Resize handles are drawn entirely outside the boundary, just beyond the corner or edge they
  control, so they never cover the annotation and so their whole
  area resizes rather than competing with the move region inside the boundary.

---

## 9. Editing Operations

All operations below apply to the full current selection (single or multi) as one undo/redo
unit unless noted otherwise. See [§13](#13-keyboard-shortcuts-reference) for keyboard shortcuts.

| Operation | Behavior |
|---|---|
| Move | Arrow keys: 12pt (50px) per press; Shift+arrow = 1pt (about 4px). Every type is kept inside the page |
| Resize | Drag the handles just outside the boundary. Text, Line, Arrow, Rectangle and Ellipse resize freely; Signature/Image, Checkmark and Crossmark keep their aspect ratio. Dragging a handle past the opposite (anchor) handle flips the box across that anchor — the dragged handle becomes the opposite corner/edge and resizing continues. |
| Rotate | Drag the rotation handle around the object/group center (15° snapping by default; Shift disables snapping), or set a whole-degree angle in the toolbar |
| Duplicate | Copies preserving size, color, hand-drawn style and rotation, offset 20px; several copies keep their relative positions and stacking order, and the copies stay inside the page |
| Cut | Copies to clipboard (JSON), then deletes |
| Copy | Copies selection to clipboard as JSON, capturing coordinates at copy time (later moves of the source do not affect the paste) |
| Paste | Pastes the most recent copy, whether it was made in this window or in another instance. Same page: applies the same 20px offset as Duplicate. Different page: no offset. Pasted annotations keep their relative positions and stacking order and stay inside the page. |
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
- **Action model**: every undoable action records the complete state before and after it
  (e.g. a resize records the position and size, and for a Line/Arrow the direction as well), so
  undo restores exactly the previous state and redo exactly the resulting state, also when the
  result was limited by the page boundary.
- **Undoable actions**: add, delete, move, resize, color change of the selected annotation(s),
  set text, hand-drawn toggle (§7.10), duplicate, cut/copy/paste (incl. multi-selection),
  rotate annotation or page (current or all), and multi-selection variants of
  delete/duplicate/color/width/hand-drawn/rotation change as single units. Selecting and
  navigating are not undoable.
- Undo and redo never leave a selection that refers to an annotation that is not on the page
  anymore; the selection is cleared of such annotations.
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
  etc.) at 300 DPI before printing. The page size of the print job is the one chosen in the
  print dialog, the pages and number of copies chosen there are honored, and each rendered page
  is scaled to fit the paper while keeping its aspect ratio.
- Success and failure are both reported to the user; automated tests replace the print dialog
  with a stub that accepts it.

---

## 13. Keyboard Shortcuts Reference

All shortcuts below are active only in the default document view, when no dialog is open and no
text input field currently has focus (this avoids accidental triggers while typing/confirming).

| Hotkey | No-Ctrl alternative | Action |
|---|---|---|
| ← / → (nothing selected) | — | Previous/next page |
| ↑ / ↓ (annotation selected) | — | Move selection up/down 12pt (Shift: 1pt) |
| ← / → (annotation selected) | — | Move selection left/right 12pt (Shift: 1pt) |
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
| Delete / Backspace | — | Delete selection |
| Escape | — | Deselect all |
| Ctrl+Z | Z | Undo |
| Ctrl+Y / Ctrl+Shift+Z | Y | Redo |
| Ctrl+L | L | Rotate all pages left |
| Ctrl+R | R | Rotate all pages right |
| Shift+Ctrl+L | Shift+L | Rotate current page left |
| Shift+Ctrl+R | Shift+R | Rotate current page right |
| Ctrl++ / Ctrl+= | = | Zoom in |
| Ctrl+- | - | Zoom out |
| Ctrl+0 | 0 | Fit document to window |
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
- Partial multi-page export failure: export stops, dialog lists failed pages and reason,
  Retry/Cancel; already-written pages remain on disk. Retry writes the failed pages again. The
  export is reported as failed, so the document still counts as having unsaved changes.
- Partially unreadable clipboard data on paste: the readable annotations are pasted and a dialog
  reports how many were skipped, rather than the paste appearing to have succeeded in full.
- Directory-link failure: red toast, "Unable to open directory", logged, does not crash.

---

## 15. Persistence & Settings

Stored as JSON in `config.json` (location depends on portable vs installed mode, see below):

| Field | Type | Default | Purpose |
|---|---|---|---|
| `recent_color` | hex string | `#cc0000` | Last-used annotation color |
| `recent_line_width_pt` | float | `1.5` | Last-used line width |
| `recent_font_family` | string | `Arial` | Last-used text font family |
| `recent_font_size_pt` | int | `11` | Last-used text font size |
| `recent_character_spacing_pt` | float | `0.0` | Last-used text character spacing |
| `recent_hand_drawn` | bool | `false` | Last-used hand-drawn style (§7.10) |
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
| `overlay_selection_toolbar` | bool | `false` | Whether the selection-properties area floats over the document (§2.1) |

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
  "annotations": [ { "type": "add_annotation", "annotation_type": "text", "page": 0, "x": 100, "y": 200, "width": 150, "height": 40, "...": "..." } ],
  "rotations": { "0": 90 }
}
```

- No `schema`, timestamps, `current_page`, or `settings` fields — intentionally minimal.
- `document_path` is stored as an absolute path, whichever way the document was opened, so the
  project can be opened from any working directory.
- `annotations` is one flat list; every entry carries the index of its `page`.
- Each annotation entry reuses the **same action entity shape** used by action recording and
  feature-test JSON fixtures: `type` is `add_annotation` or `open_signature`, with
  `annotation_type`, `x`, `y`, `width`, `height`, optional `page`, and only the type-specific
  fields needed to restore appearance (text/font properties, color, etc.). The optional
  `rotation` field stores the normalized clockwise annotation angle in degrees and defaults to
  `0` when absent, preserving compatibility with existing files. Checkmark, Crossmark, Line,
  Arrow, Rectangle, and Ellipse entries additionally store `hand_drawn` (boolean) and `hand_drawn_seed` (integer, §7.10);
  absent means off (and a new random seed on load). There is no separate project-only annotation
  schema.
- `width`/`height` are current rendered dimensions; when a `scale` field is present, base
  (unscaled) dimensions are derived by dividing by it, so scaling applies exactly once on load.
- Per-page rotations (§10) are stored in the optional `rotations` map (page index → angle),
  omitted keys meaning 0°. Annotation coordinates stay unrotated, so the page orientation is
  never baked into them.
- A project that is not in this format (for instance an `annotations` value that is not a list)
  is rejected with an error message, without changing the document that is currently open.

### 16.3 Naming & location

- Opening a plain document does **not** create a project file.
- A successful export establishes the project path: the exported basename with any multi-page
  `-p#` placeholder removed, plus `.signer` — e.g. `document-signed.jpg` →
  `document-signed.signer` (stored next to the exported file). This happens whether or not
  Auto-save Project on Save is enabled.
- Both auto-save and later explicit saves reuse that same established path.
- Opening another document or project discards the established path, so a project is never
  saved under the name or in the folder of an earlier document.

### 16.4 Lifecycle

- **Auto-save Project on Save** (default enabled, toggle in File menu): writes the project only
  *after* a document export succeeds.
- **Save Project** / **Save Project As…**: reuse the established export-based path, or prompt
  for one if no export has occurred yet.
- Opening a project restores every annotation to its stored page, always displaying **page 1**
  first (the concept of a "saved current page" does not exist), and adds the project and its
  document to Recent Documents. If the project cannot be opened, the document that was open
  stays unchanged.
- If the referenced document is missing, the app prompts with a **Change
  Document** action rather than failing silently; changing the document preserves every
  annotation's coordinates, size, orientation, and relative arrangement (see §10). If the
  document is a password-protected PDF, the password is asked for exactly as when opening it
  directly. Changing the document also updates the window title and the recent lists.
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
  - **Threshold** — luminance at the middle of the transition: pixels at this luminance are half
    transparent, clearly lighter ones become fully transparent, clearly darker ink stays opaque.
  - **Softness** — total width of the transition band around the threshold (a softness of 40 at
    threshold 200 means fully opaque up to luminance 180 and fully transparent from 220), producing smooth
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
- "Reset" restores all four sliders (threshold, softness, color tolerance, color softness) to
  their default values, whichever methods are selected; the ink color and the method checkboxes
  are kept.

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
    character band to the top 70% of the visible signature; only row runs whose density is at
    least 20% of the peak density within that part count as part of a band. This avoids letting long lower strokes
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
  immediately after load at the center of the current page (§7.7), and becomes fully selected
  (movable/deletable via keyboard right away).
- If `-signature` is given without `-document`, no annotation can be added; the signature file
  is only added to the recent images list.
- If `-signature` is omitted, no annotation is auto-added on open.
- If `-signature` is omitted, the previously-used signature file is remembered but **not**
  automatically re-added — it's only available for the Add menu's Signature / Image recent list.

Example: `signer -document examples/document.pdf -signature examples/signature.png`

---

## 19. Platform Support

- Supported OSes: Windows 10 or later, macOS 13 or later (the minimum of the Qt 6.11 / PySide6
  6.11 builds the app ships with), and a maintained Linux distribution whose glibc is
  compatible with the release's PySide6/PyInstaller build. The macOS build is made on an
  Apple-silicon runner, so it targets Apple-silicon Macs.
- Native desktop actions (e.g. opening the export directory from a notification link) use
  platform-independent Qt APIs and open each platform's native file manager.
- LibreOffice remains an optional external dependency for Word/ODT input on every platform; it
  is never bundled with the executable.
- Distribution is a single-file executable per platform (see [DESIGN.md](DESIGN.md) for build
  commands and per-target packaging notes). A release build only proves that platform/CPU
  architecture; PyInstaller does not cross-compile, so Linux/macOS/Windows builds must each be
  produced (and smoke-tested) on their own target.

# Need
I need a simple tool that allows me to use two files: one with a PDF and one with my scanned signature. It should allow me to position the signature on the PDF and then save the combined image to a JPG file.

I'm now doing that in GIMP, but it has too many manual steps. Recommend how to make it faster.

## How to read this document

This is a high-level, business-facing change log: each entry explains *why* a capability was
added and *what* it gives the user, in roughly one paragraph plus a short bullet list. It is not
a specification — for the precise, current behavior (exact defaults, dialogs, schemas,
algorithms), see [FUNCTIONAL_SPECIFICATION.md](FUNCTIONAL_SPECIFICATION.md). For architecture and
how to run/test/build the app, see [DESIGN.md](DESIGN.md). New entries are appended at the end,
following the existing `## Version x.y.z - Title` convention.

# Requirement

1. A Windows app
2. Typical user workflow:
    1. User starts the app
    2. User opens the document
    3. App uses the previous signature file
    4. App shows the document and signature above it
    5. User can move and scale the signature above the document to position it correctly
    6. User saves the document
3. Parameters to the app: `-document` (file with document) and `-signature` (file with signature).
4. Menu options: Open document, Open signature, Save document with signature.
5. When started without specifying the signature file, automatically use the previous signature file.
6. The default file name of the "document with signature" is: _documentname_ + -signed.jpg
7. The document shall fit the application window. No zooming needed.
8. Default position for the signature is 80% from top, centered horizontally.
9. Document with signature has 300 DPI.

See [FUNCTIONAL_SPECIFICATION.md §18](FUNCTIONAL_SPECIFICATION.md#18-cli-parameters) (CLI) and
[§7.7](FUNCTIONAL_SPECIFICATION.md#7-annotations) (default placement).

# Version 1.1

Motivation: turn the single-signature tool into a general-purpose annotation tool that works
across multi-page documents, with a faster, toolbar-first UI and a distributable executable.

10. Support multi-page documents; signature can be placed on any page. Put paging controls in the Toolbar. Also support `Page Up`, `Page Down`, `Home`, and `End` keys.
11. The signature is displayed (in the app only) with a blue boundary.
12. Signature scaling is currently done with a slider. Remove slider and support scaling by dragging the boundary.
13. When the mouse is above the signature, change the mouse cursor to move arrows.
14. Replace primary actions from a standard hierarchical menu with big buttons in the Toolbar for faster navigation.
15. Annotations: other objects can be put on the document, similarly to signature. Each annotation
    supports color, moving/scaling, and duplicating. Supported types: Checkmark, Cross, 8 arrows
    (North, East, North-East, ...), Text (with a submenu for free text / current date / time /
    date & time), and Signature (with a submenu for opening from file and recent files). In the
    Toolbar, add a button that expands to a list from which the annotation type is selected and
    placed on the current page.
16. Make the resulting application a single-file executable (that can be distributed to other users).

See [FUNCTIONAL_SPECIFICATION.md §6](FUNCTIONAL_SPECIFICATION.md#6-page-navigation) (paging) and
[§7](FUNCTIONAL_SPECIFICATION.md#7-annotations) (annotation catalog).

Feedback after implementation:
- Remove the add signature button (signature can be added from the annotations).
- Move the annotation menu to 2nd position, just after Open document.
- Move the "Save JPG" item to the 3rd position. Put it into same group as the previous buttons (they belong to the same workflow).
- Make the annotation symbols one third of the current (so it can be used on a dicument with 12pt font immediately).
- Bug: I like that the resizing always respects aspect ratio. That should not be the case for free text. Make default text size 12pt; no wrapping. New line is created by pressing Ctrl+Enter. Resizing should be possible.
- Clarified terminology: signatury is a kind of annotation.
- Default position of the annotations is in the middle of the screen.
- Bug: Having annotaion buttons in the toolbar is ok, but enable those buttons only when an annotation is selected.
- Bug: Changing the color. When an annotation is selected, then change the color of the annotation. (Maintain current functionality: If none annotation is selected, set the color of the next new annoation.)
- Window size. Respect the size of the document (like change windows aspect ratio to match the document aspect ratio). But also ensure that the entire toolbar is visible.
- Clarification: If -signature parameter is used, then add the signature annotation immediately after opening the document. Otherwise, do not add anything (on open).
- Bug fix: The signature added via -signature must become fully selected (not just visually marked), so it can immediately be moved, deleted, etc. with the keyboard.

Feedback after implementation, round 2:
- The "Add annotation" button in toolbar does nothing. I must click the down arrow next to it. Make the entire button open the menu.
- I just noticed that text is edited in a new dialog window. I'm changing my mind, revert to standard behavior: Enter adds a new line, Ctrl+Enter closes the dialog.
- Annotation sizes are good. Do the following:
  - The arrows are too small. Make it twice bigger.
  - The text boundary is small, hiding most of the text. Workaround is to resize it properly. Do this boundry resizing (fit the content) automatically.
- In text annotations, make the margin zero. (Resizing by right-bottom corner moves the text.)
- Bug: When saving JPG, the text is unreadably small. Id does not match what the user sees in the application.
- Make the window width even smaller (there are still dark borders on the sides of an A4 document).

Feedback after implementation, round 3:
- When saving JPG, the default filename shall have no page number when the document has one page. If the document has more pages, it should have -p1 suffix when the user is on page 1; all the pages should be saved; the page number should be padded by zeroes.
- Resizing the text annotation just changes boundary and the text size remains the same. Make the font size adjust according to the bounding box. Keep aspect ratio of the text.
- New text annotations shall render at the point size shown in the toolbar, and their boundary shall fit the complete text without cropping.
- Text size changes shall be synchronized in both directions: changing the toolbar value refits the boundary, while resizing the boundary updates the toolbar value to the largest whole-point font size that fits.
- During text boundary resizing, only the fitted boundary shall be displayed; an intermediate mouse-sized boundary shall not flash. The toolbar size control shall remain immediately operable after the drag ends.
- Toolbar property labels shall not display measurement units.

See [FUNCTIONAL_SPECIFICATION.md §7.2](FUNCTIONAL_SPECIFICATION.md#7-annotations) (text sizing/fitting behavior).

## Version 1.2.0 - Hamburger menu

Motivation: move secondary/infrequent actions out of the toolbar into a standard hierarchical
menu, so the toolbar stays focused on primary actions.

1. The application shall provide a hamburger menu on the right end of the toolbar. The menu shall be vertical and hierarchical, containing typical main menu items.

2. The hamburger menu shall contain File, Edit, Annotations, and Help top-level groups.

See [FUNCTIONAL_SPECIFICATION.md §2.2](FUNCTIONAL_SPECIFICATION.md#2-toolbar--menu) for the current menu tree.

## Version 1.2.1 - Remove status bar

1. The status bar shall be removed. (Document name is shown in the window title; coordinates are unnecessary for this application.)

## Version 1.2.2 - Recent entries and documents

Motivation: reduce repetitive file/text picking for a small user's regular workflow (recurring documents, signatures, and text snippets).

1. Recent items shall appear at the top level of their respective menus, after the static items, separated by a horizontal rule from static items.

2. The application shall maintain LRU lists (maximum 10 items each) for recently used
   signature/image files, recently used text strings (except the predefined date/time strings),
   and recently opened documents.

3. Next to "Open Document", a small arrow shall open a list of recent documents.

4. Recent items shall persist across application sessions and appear in relevant menus with a separator preceding them.

See [FUNCTIONAL_SPECIFICATION.md §4.4](FUNCTIONAL_SPECIFICATION.md#4-opening-documents--projects).

## Version 1.2.3 - Settings persistence

1. The application shall store user preferences in a configuration file (shared with recent documents and texts): recent color, recent line width, recent font family and size, and the recent lists (documents, texts, and signature annotations).

2. Fields in `config.json` use snake_case names (e.g. `libreoffice_path`, `last_export_format`), matching the Python settings model, since the file is user-facing and may be hand-edited.

See [FUNCTIONAL_SPECIFICATION.md §15](FUNCTIONAL_SPECIFICATION.md#15-persistence--settings) for the full field reference.

## Version 1.2.4 - Window size and position

Motivation: avoid wasted screen space (dark borders) around the document and keep the toolbar reachable regardless of document shape.

1. The application shall automatically size the window to fit the document (matching aspect ratio, scaled to fit the screen, with a sensible minimum canvas size and no upscaling), keeping the entire toolbar visible.

2. The window shall be centered on the screen when a document is opened to ensure the entire window is visible.

See [FUNCTIONAL_SPECIFICATION.md §4.5](FUNCTIONAL_SPECIFICATION.md#4-opening-documents--projects) for exact sizing rules.

## Version 1.2.5 - Tests

Motivation: catch regressions automatically instead of relying on manual verification.

1. The application shall include automated unit tests and feature tests.
2. Feature tests replay a recorded workflow (open a document, add/move/resize annotations, save)
   and compare the exported output pixel-perfect to a reference image.
3. Unit tests shall cover coordinate transformations, bounding box calculations, and annotation serialization.
4. Feature tests shall cover each annotation type using representative example documents.

See [TESTING.md](TESTING.md) for how to run and extend the test suite.

## Version 1.2.6 - Application icon

1. The application icon shall depict a document with a pen writing a blue cursive signature. The pencil tip should touch the signature line to indicate active writing.

## Version 1.2.7 - Save dialog on document close

Motivation: avoid silently losing annotation work when switching documents or closing the app.

1. When a document has unsaved changes and it's closed (on application exit or when another document is opened), show a dialog informing the user about the changes and offering to discard or save.

See [FUNCTIONAL_SPECIFICATION.md §4.2](FUNCTIONAL_SPECIFICATION.md#4-opening-documents--projects).

## Version 1.2.8 - Open Encrypted PDF documents

1. When opening a PDF, if the document is encrypted, ask the user for the key.
2. Also create `examples/document-encrypted.pdf` with the same content as `document.pdf`, but encrypted with key "key123".

## Version 1.2.9 - Supported Document Formats

Motivation: the tool should work directly with the document formats users actually receive
(Word, ODT, scanned images), not just PDF, without a separate conversion step.

The application shall support opening documents in PDF, Word (`.docx`/`.doc`), ODT, and common
image formats (JPG, PNG, BMP, WEBP, GIF, ICO, and multi-frame TIFF). Word/ODT are converted via
headless LibreOffice; this is an optional dependency with clear error messages when missing.
Recent documents, the render pipeline, and CLI parameters continue to work unchanged across all
formats.

See [FUNCTIONAL_SPECIFICATION.md §3](FUNCTIONAL_SPECIFICATION.md#3-supported-document-formats) for the format table, LibreOffice resolution order, and error messages.

## Version 1.2.10 - Save Documents in Multiple Formats

Motivation: JPG isn't always the right output format (e.g. lossless PNG, or a single combined
PDF for a multi-page document); give users a real choice at export time.

The application shall support exporting to JPG (default), PNG, PDF, TIFF, and BMP via a unified
"Save As..." dialog, replacing the single "Save JPG" button. Default file naming differs for
single- vs multi-page documents and for single-file vs per-page formats.

See [FUNCTIONAL_SPECIFICATION.md §5](FUNCTIONAL_SPECIFICATION.md#5-export--save-as) for supported formats and naming rules.

## Version 1.2.11 - Auto-dismissing save notification

Motivation: a blocking "export succeeded" dialog interrupts a workflow that just needs a quick
confirmation; the user should be able to keep working immediately.

After a successful export, show a non-blocking, auto-dismissing notification (with a link to
open the export directory) instead of a modal dialog. Export failures still show a modal error
dialog, since those need explicit acknowledgment.

See [FUNCTIONAL_SPECIFICATION.md §14](FUNCTIONAL_SPECIFICATION.md#14-notifications--error-handling).

## Version 1.2.12 - Improve Export Dialog: Dynamic Page Number Placeholder

Motivation: users kept having to manually retype the page-number part of multi-page export
filenames whenever they switched export format; make the dialog handle that automatically.

The Save As dialog shall show a `#` placeholder for the page number in multi-page, per-page
export formats, and shall automatically add/remove that placeholder (while preserving the
user's custom filename) when the user switches between single-file and per-page export formats.

See [FUNCTIONAL_SPECIFICATION.md §5.3](FUNCTIONAL_SPECIFICATION.md#5-export--save-as) for the placeholder/validation rules and the non-native-dialog trade-off (also in [DESIGN.md](DESIGN.md)).

## Version 1.2.13 - Enhanced Overwrite Confirmation Notifications

Motivation: silently overwriting previously exported pages (or leaving stale ones behind from a
larger earlier export) is surprising; make both explicit and easy to control.

Before export, the application shall detect which target file(s) already exist and show an
appropriate confirmation (a single file, a short list, "all pages", or a summarized list for many
files). If a new export has fewer pages than a previous export with the same naming pattern, the
dialog shall also offer an opt-in checkbox to clean up the older, now out-of-range page files.

See [FUNCTIONAL_SPECIFICATION.md §5.4](FUNCTIONAL_SPECIFICATION.md#5-export--save-as) for the exact dialog scenarios.

## Version 1.2.14 - Export quality

Motivation: give advanced users control over the size/quality trade-off for lossy formats,
without adding a step to the common case.

The Save As dialog shall offer an "Options..." button for lossy formats (JPG, PDF) opening a
quality slider (1-100, default 95); lossless formats (PNG, TIFF, BMP) always use their best
automatic compression with no user control needed.

See [FUNCTIONAL_SPECIFICATION.md §5.3](FUNCTIONAL_SPECIFICATION.md#5-export--save-as) and [§15](FUNCTIONAL_SPECIFICATION.md#15-persistence--settings) for persisted quality settings.

## Version 1.2.15 - Print

1. The application provides a "Print" menu item in the main menu (hamburger menu → File), opening the platform's native print dialog with all pages rendered with their annotations.

See [FUNCTIONAL_SPECIFICATION.md §12](FUNCTIONAL_SPECIFICATION.md#12-printing).

## Version 1.2.16 - Document and page rotation

Motivation: documents (especially scans) sometimes come in with the wrong orientation; let the
user fix that for viewing/exporting without needing to edit the source file.

1. The application shall support rotating the whole document, or just the current page, 90° left/right (Edit menu).
2. Rotation shall be temporary (session-only) and not persisted.
3. Rotated pages shall export with their rotated orientation in all supported formats.
4. Annotations shall not rotate visually; their position shall be transformed so each annotation's center stays at the same visual location on the page.

See [FUNCTIONAL_SPECIFICATION.md §10](FUNCTIONAL_SPECIFICATION.md#10-document--page-rotation) for the coordinate transform formulas.

## Version 1.2.17 - Multi-Selection

Motivation: editing several annotations together (moving a whole group, deleting a batch) one at
a time was tedious; let users select and operate on multiple annotations at once.

1. Shift+click adds/removes an annotation to/from the current selection (limited to the current page; cleared on page navigation).
2. Move, delete, copy/cut/paste, duplicate, and color-change operations shall apply to the entire selection as a single undo/redo unit.
3. The clipboard shall use the same JSON annotation format as elsewhere in the app, so it can be pasted across pages and documents.

See [FUNCTIONAL_SPECIFICATION.md §8](FUNCTIONAL_SPECIFICATION.md#8-selection--multi-selection) and [§9](FUNCTIONAL_SPECIFICATION.md#9-editing-operations).

## Version 1.2.18 - Keyboard navigation and hotkeys

Motivation: frequent actions (move, undo, copy/paste, rotate, navigate) should be reachable
without leaving the keyboard, matching conventions from other desktop apps.

1. When an annotation is selected, arrow keys move it by 12pt (Shift: 1px).
2. The application shall support a documented set of hotkeys (with single-key alternatives to the Ctrl-based ones) for document/file operations, annotation operations, undo/redo, and document rotation, active only in the default document view (not while a dialog or text field has focus).
3. There are intentionally no direct hotkeys for adding a specific annotation type; use the Annotations menu or toolbar button.

See [FUNCTIONAL_SPECIFICATION.md §13](FUNCTIONAL_SPECIFICATION.md#13-keyboard-shortcuts-reference) for the full shortcut table.

## Version 1.2.19 - Annotation and text sizing

Motivation: the sizes should be appropriate for documents using text size 11 points.

1. Default font size for text annotations: 11 points.
2. Default sizes for vector annotations are defined so smaller marks (checkmark/crossmark) and larger shapes (line/rectangle/ellipse/arrow) both read clearly next to 11pt body text.
3. Default line width for annotations: 1.5 points.
4. All sizes are measured in PDF points (1/72 inch), converted to 300 DPI pixels for rendering.

See [FUNCTIONAL_SPECIFICATION.md §7.1](FUNCTIONAL_SPECIFICATION.md#7-annotations) for the exact default size table and DPI scaling.

## Version 1.2.20 - Terminology standardization

1. Rename the "Cross" annotation to "Crossmark" for consistency with "Checkmark".
2. All documentation, code, and user-facing text shall use "Crossmark" instead of "Cross".

## Version 1.2.21 - Undo/redo

Motivation: mistakes (wrong position, wrong color, accidental delete) should be cheap to fix
without manually reconstructing the previous state.

1. The application shall provide unlimited undo/redo history for the current document session (Ctrl+Z / Ctrl+Y), cleared when a new document is opened or the app closes.
2. Consecutive move/resize operations on the same annotation(s) shall be coalesced into a single history entry, so a single undo reverts an entire drag.
3. Undo/redo, action recording, and project-file persistence shall share one underlying action model, avoiding duplicate serialization logic.

Clarifications after implementation: several operations silently escaped the history or undid the
wrong thing, which is worse than an operation simply not being undoable — the user cannot tell
that the document no longer reflects what they did.

4. Undo and redo shall always act on the page the affected annotation belongs to, regardless of
   which page is currently displayed. Navigating between an edit and its undo shall never move an
   annotation to another page or discard it.
5. The coalescing in item 2 shall be bounded by the editing gesture: a drag from mouse press to
   release, or an uninterrupted run of arrow-key nudges. Repeating the gesture shall produce a
   separate undo step rather than extending the previous one.
6. Redo shall also be available through the conventional Ctrl+Shift+Z.
7. Where an operation cannot be completed in full, the application shall say so instead of
   reporting success: a paste that could not read every copied annotation, and an export that
   could not write every page, shall both be reported to the user, and a failed export shall
   leave the document marked as having unsaved changes.

See [FUNCTIONAL_SPECIFICATION.md §11](FUNCTIONAL_SPECIFICATION.md#11-undoredo-history).

## Version 1.2.22 - More annotation types and properties

Motivation: checkmark/crossmark/arrow/text/signature covered common cases, but users also
regularly need simple shapes (lines, rectangles, ellipses) and arbitrary images.

1. Add Line, Arrow (with the previous directional variants retained at this point), Rectangle/Square (auto-detected from aspect ratio, with a modifier-key override), Ellipse/Circle (same), and Image annotation types.
2. Add a "Width" (line width, in points) property for all types except Text and Signature/Image.
3. Text annotations gain Text Size and Font Family toolbar controls.
4. Line width and font size shall be adjustable via toolbar spinners and `[`/`]` keyboard shortcuts.
5. Signature and Image are unified as a single "Signature / Image" annotation type (no color/width controls).
6. Property controls (color, width, font) and the "Add Annotation"/"Save As..." buttons shall be context-sensitive to document/selection state.
7. All annotations shall support free corner dragging (dragging a corner past its opposite corner swaps which corner is which).

See [FUNCTIONAL_SPECIFICATION.md §7](FUNCTIONAL_SPECIFICATION.md#7-annotations) and [§2.3](FUNCTIONAL_SPECIFICATION.md#2-toolbar--menu) for the full type/property/visibility matrices.

## Version 1.2.23 - Smart line and arrow snapping

1. When drawing or resizing a line or generic arrow, the annotation shall snap to the nearest of the 8 cardinal/intercardinal directions when within 10° of it, unless a modifier key is held.

See [FUNCTIONAL_SPECIFICATION.md §7.5](FUNCTIONAL_SPECIFICATION.md#7-annotations).

## Version 1.2.24 - Simplify Arrow Annotation

Motivation: the 8 directional arrow variants added complexity without much practical benefit
over one arrow that can be rotated/positioned freely; consolidate to a single generic arrow.

1. Remove the 8 directional arrow types; retain only the generic `ARROW` type, pointing right (east) by default.
2. Simplify the Arrow menu entry to a single item (no submenu).

## Version 1.2.25 - Drag and drop and document open/save flow

Motivation: dragging a signature image or a document straight onto the app window is faster
than going through Open dialogs every time, as long as unsaved work is protected.

1. Dropping a small image (fits on A6 at 300 DPI) creates a Signature/Image annotation at the drop position.
2. Dropping a big image or a PDF loads it as the document, prompting to save first if the current document has unsaved changes.
3. Opening a new document (via menu or drag-drop) with unsaved changes shall prompt "Save changes to {filename}?" with Save / Don't Save / Cancel.

See [FUNCTIONAL_SPECIFICATION.md §4.3](FUNCTIONAL_SPECIFICATION.md#4-opening-documents--projects) for size thresholds and error cases.

## Version 1.2.26 - Portable

Motivation: some users want to run Signer from a USB drive or shared folder with its settings
travelling alongside it, without a separate "portable" build or installer.

1. The application shall support both a portable mode (settings next to the executable) and an installed mode (settings in the platform user-config directory), chosen automatically at startup based on whether `config.json` exists next to the executable.

See [FUNCTIONAL_SPECIFICATION.md §15](FUNCTIONAL_SPECIFICATION.md#15-persistence--settings) for the resolution order and migration between modes.

## Version 1.2.27 - Nearest annotation selection

1. When the cursor is inside the bounding box of one or more annotations, the nearest annotation (by distance to its nearest rendered visible pixel) shall be selected, even over transparent areas of its bounding box. A cursor outside all bounding boxes selects nothing.

See [FUNCTIONAL_SPECIFICATION.md §8](FUNCTIONAL_SPECIFICATION.md#8-selection--multi-selection).

## Version 1.2.28 - Context-sensitive toolbar visibility

Motivation: showing every control all the time regardless of whether it applies clutters the
toolbar and invites mistakes (e.g. changing "width" on a text annotation).

1. Toolbar property controls (color, width, font size, font family) shall be shown only for annotation types that support them, and hidden entirely when nothing is selected.
2. The page navigation block shall be hidden entirely for single-page documents.
3. Duplicate/Delete buttons shall be visible only when an annotation is selected.
4. Hidden control groups shall never leave duplicate adjacent separators.

See [FUNCTIONAL_SPECIFICATION.md §2.3](FUNCTIONAL_SPECIFICATION.md#2-toolbar--menu) for the full visibility matrix.

## Version 1.2.29 - Context-sensitive main menu items

1. Hamburger main menu items shall be disabled when their action isn't currently applicable (no document open, nothing selected, nothing to undo/redo, etc.), consistent with the toolbar's context-sensitive behavior, and re-evaluated every time a menu is about to be shown.

See [FUNCTIONAL_SPECIFICATION.md §2.3](FUNCTIONAL_SPECIFICATION.md#2-toolbar--menu).

## Version 1.2.30 - Add Annotation menu hotkey

1. In the default document view, pressing `+` shall open the Add Annotation toolbar menu.

## Version 1.2.31 - Error Notification are Manually Dismissed

Motivation: clarify that non-critical successes are safe to miss (so they auto-dismiss), while
errors of any kind must be positively acknowledged by the user.

1. Success toasts (e.g. post-export) remain green and auto-dismiss after 5 seconds.
2. Error toasts (e.g. "Unable to open directory") shall be red and require manual dismissal via the X button.
3. Export/save failures remain a separate, blocking modal-dialog category, distinct from both toast styles.

See [FUNCTIONAL_SPECIFICATION.md §14](FUNCTIONAL_SPECIFICATION.md#14-notifications--error-handling).

## Version 1.2.32 - Discrete step sizes for `[` / `]` shortcuts

Motivation: a small fixed increment per keypress made `[`/`]` too slow to reach commonly-used
sizes; step through a curated list of "usual" sizes instead.

1. The `[` / `]` keyboard shortcuts shall step through a fixed list of font-size and line-width values (rather than a small fixed increment), clamped at the ends (no wraparound).

See [FUNCTIONAL_SPECIFICATION.md §7.2](FUNCTIONAL_SPECIFICATION.md#7-annotations) and [§13](FUNCTIONAL_SPECIFICATION.md#13-keyboard-shortcuts-reference) for the exact step lists.

## Version 1.2.33 - A4 startup window size

1. When started without a document, the window shall use portrait A4 geometry, with canvas space outside the document minimized.

See [FUNCTIONAL_SPECIFICATION.md §4.5](FUNCTIONAL_SPECIFICATION.md#4-opening-documents--projects).

## Version 1.2.34 - Consistent copy/paste and duplicate positions

1. Pasting shall use the annotation coordinates captured at copy time, even if the source annotation is subsequently moved.
2. Pasting on the same page and duplicating shall apply the same offset; pasting on a different page shall apply no offset.

See [FUNCTIONAL_SPECIFICATION.md §9](FUNCTIONAL_SPECIFICATION.md#9-editing-operations).

## Version 1.2.35 - Linux and macOS support

Motivation: broaden the user base beyond Windows without maintaining a separate codebase or UI.

1. Signer shall support Windows, macOS, and Linux, using platform-independent Qt APIs for native desktop actions (e.g. opening the export directory).
2. A single-file executable shall be buildable for each supported platform; releases are built and tested separately per OS/architecture since PyInstaller does not cross-compile.
3. Linux releases shall be tested on the oldest supported distribution and on both X11 and Wayland sessions where applicable.

See [FUNCTIONAL_SPECIFICATION.md §19](FUNCTIONAL_SPECIFICATION.md#19-platform-support) and [DESIGN.md](DESIGN.md) for build details.

## Version 1.2.36 - Signer project file

Motivation: some documents need to be re-signed on a recurring basis (e.g. monthly) where only
one detail (like a date) changes but the rest of the annotation layout should be reused, instead
of recreating every annotation from scratch each time.

The application shall support reusable signer project files (`.signer`, JSON) for recurring
document-signing workflows: a successful export establishes the project's path and, when
auto-save is enabled, saves the project after each export. Opening a project restores every
annotation to its stored page. If the referenced document is missing or has changed, the app
offers a Change Document action that preserves every annotation's coordinates, size, and
orientation. Project persistence reuses the same annotation entity model as action recording and
test fixtures, avoiding a second serialization format.

See [FUNCTIONAL_SPECIFICATION.md §16](FUNCTIONAL_SPECIFICATION.md#16-project-files-signer) for the full format, naming, and lifecycle rules.

## Version 1.2.37 - Prepare Signature Tool

Motivation: the app assumed the signature image already had a transparent background, which
required users to prepare it manually (e.g. in GIMP) before use — a step most users cannot do
themselves. Provide a built-in tool that turns a plain scan/photo of a signature (possibly part
of a larger scanned page) into a ready-to-use transparent PNG.

1. Add a "Prepare Signature..." tool (hamburger menu → new "Tools" group), independent of the
   currently open document.
2. The tool lets the user open any supported image (a scan/photo, possibly containing more than
   just the signature), or a multi-page PDF (with page navigation to pick the right page), then
   zoom/pan it, and draw a rectangular selection around the signature.
3. After cropping, the tool shows a live preview of the selection with its background removed,
   composited over a checkerboard pattern (the standard transparency indicator), so the user can
   tell transparent pixels apart from white ones. A control lets the user switch the preview
   backdrop between checkerboard and white, purely for visual confidence in how the signature
   will look once applied — it has no effect on the saved file.
4. The app offers two sequential signature-extraction methods, each controlled by its own
    checkbox:
    - **Method 1: Luminance background removal** (selected by default): pixels are classified by
       how light they are (not by exact color), so it works on ordinary scans without color
       calibration. Its controls are threshold and edge softness.
    - **Method 2: Keep ink color** (selected by default): pixels are classified by hue distance to
       a user-picked ink color, primarily to remove black printed text or dots around a colored
       signature. Its controls are color tolerance and color softness; the default swatch is blue.
5. Both methods may be selected at the same time. When both are selected, Method 1 runs first
    and Method 2 runs second on Method 1's output. When only one is selected, only that method
    runs. The live preview updates immediately when either method checkbox or one of its controls
    changes.
6. A selected-by-default toggle shall scale the signature to fit the recommended 10pt–24pt
   range. While selected, the height input is hidden and replaced by a status such as
   "Will be scaled to 24pt from the current 50pt"; the status always reflects the current
   actual signature-boundary height.
7. When the scale toggle is cleared, an editable height input shall be shown. The user's entered
   height shall remain fixed when other method, crop-processing, or preview controls change and
   shall be used for the saved output. Editing the height automatically clears the scale toggle.
   The 10pt–24pt range remains the recommended target range.
8. Once satisfied with either method, the user saves the result as a PNG file (default filename
   `signature.png`) with a real alpha channel.
9. The saved PNG is a regular signature file: it can be opened afterwards via the normal
   Annotations → Signature/Image → From file... flow, or passed to `-signature`.
10. The saved PNG's bounds shall be auto-trimmed to the signature content — no fully transparent
    border rows/columns at the top, bottom, left, or right.
11. The user-drawn crop rectangle (step 2) and the actual bounding box of the signature content
    (after background removal) are two different rectangles, which was confusing. To clarify:
      - The Stage 3 preview shall always display the full crop rectangle; if necessary, it shall be
         proportionally downscaled to fit the available preview area. It shall not resize or
         reposition the crop selection as the removal sliders/methods/color change.
    - A "Show actual signature boundary" checkbox, **checked by default**, overlays the actual
      (auto-trimmed) signature bounding box on the preview, updating live as removal settings
      change.
      - The display is scaled down proportionally when the crop is larger than the available
         preview area, without requiring scrolling. This display-only scaling shall not change the
         crop selection or saved signature dimensions. Resizing the selection is out of scope here;
         the user must go back to step 2 for that.
12. Closing the tool (X button, Cancel/Escape) after opening a scan but before saving (or saving
    again after further changes) shall ask for confirmation before discarding the work.
13. Navigating back and forth between steps shall preserve prior settings: returning to step 2
   and continuing again keeps the previously drawn crop selection (for the same page), and
   returning to step 3 keeps all of its controls (method checkboxes, ink color, sliders,
   height/fit toggle, and manual height value) exactly as previously left, instead of resetting
   them.

See [FUNCTIONAL_SPECIFICATION.md §17](FUNCTIONAL_SPECIFICATION.md#17-prepare-signature-tool).

## Version 1.2.38 - Regular Character Signature Sizing

Motivation: a signature's overall bounds can be dominated by tall ascenders or descenders,
making overall-height scaling produce ordinary letters that are too small. Scale against the
regular character body instead, while preserving the complete signature including its tall
strokes.

1. When signature scaling is enabled, estimate the regular character height from the
   non-transparent-pixel row histogram using two independent constants:
   - `CHARACTER_BAND_TOP_FRACTION` (default `0.70`) limits the densest-band search to the top 70%
     of the actual signature bounds, avoiding domination by long lower strokes.
   - `CHARACTER_EXPANSION_BASELINE_PERCENT` (default `60.0`) selects the first cumulative-alpha
     row that defines the regular-character expansion baseline. This is separate from the search
     limit and both constants may be tuned independently.
2. Starting from that expansion baseline, add one row at a time from the top or bottom, choosing
   the candidate that adds more alpha-weighted pixels. Each requested expansion range contains
   the previous range.
3. Calculate a scaling factor, before applying any resize, that makes the estimated regular
   character height 12pt. Apply that factor to the complete signature; the final image may be
   taller than 12pt because tall strokes remain included.
4. Show two horizontal guide lines around the estimated regular-character band in the Stage 3
   preview, updating live as extraction settings change.
5. When the scale checkbox is selected, show the current regular-character height and calculated
   scaling information without a target-height input. The target is fixed at 12pt.
6. The existing 10pt–24pt recommendation applies to the regular character height; the overall
   signature height may exceed 24pt when tall strokes are present.
7. In debug mode (`DEBUG=1`) with scaling selected, the Stage 3 preview shall show an
   alpha-weighted green row histogram inside the actual signature boundary. The existing 70%
   top-of-signature limit remains the character-estimation rule. Debug-only expansion bars shall
   target 10%, 20%, through 90% of the full visible signature height, centered on the
   regular-character band; each bar shall be wider than and contain the previous bar, and shall
   be labelled with its expansion percentage. These overlays are display-only and shall not
   affect preview centering or saved output.

See [FUNCTIONAL_SPECIFICATION.md §17](FUNCTIONAL_SPECIFICATION.md#17-prepare-signature-tool).

## Version 1.2.39 - Annotation Rotation

Motivation: signatures benefit from quick, subtle variation between uses, and other annotations
sometimes need to follow content that is not horizontal. Rotation should remain geometrically correct when a page itself is rotated.

1. Every annotation type shall support free rotation around its center. Rotation shall be
   available directly from the selected annotation through a rotation handle outside its
   boundary and through a numeric angle control in the toolbar.
2. Dragging the rotation handle shall snap the angle to 15° increments by default. Holding Shift
   shall temporarily disable snapping for continuous rotation; the numeric control shall allow
   precise one-degree changes and resetting to 0°.
3. Rotating a multi-selection shall rotate the annotations and their positions as one group
   around the selection's shared center, while preserving each annotation's relative position.
4. Annotation rotation shall be undoable/redoable, copied when duplicating or copying/pasting,
   saved in project files, and reproduced in exported and printed output.
5. Rotating a page shall apply the same rigid 90° transformation to the complete geometry of
   every annotation on that page, superseding Version 1.2.16's center-only transformation. An
   annotation shall remain attached to the same page content: for example, both endpoints of an
   arrow shall still identify the same two points after page rotation.

The rotation is a visual variation only; it does not add cryptographic or legal protection to a
signature.

## Version 1.2.40 - Center Signature Placement

Signatures added through the `-signature` startup parameter or the Signature/Image annotation
menu shall be placed at the center of the page.

## Version 1.2.41 - Text Character Spacing

Motivation: forms often provide one box per character, requiring text to be spread evenly across
the available boxes.

1. Text annotations shall have character spacing in points, defaulting to 0pt. A toolbar control
   shall accept positive and negative values without an application-imposed limit.
2. A selected text annotation shall have a distinct handle beyond its right edge. Dragging the
   handle horizontally, or along the text line when rotated, shall change character spacing
   without changing the font size.
3. Spacing changes shall immediately refit the text boundary, support undo/redo, and be preserved
   by duplicate, copy/paste, project save/reload, export, and print.

## Version 1.2.42 - Resize handles outside the boundary

Motivation: on small annotations (e.g. a checkmark) the resize handles covered the annotation
itself, and on large ones the half of each handle that fell inside the boundary started a move
instead of a resize.

1. Corner and edge resize handles shall be drawn entirely outside the selection boundary, just
   beyond the corner or edge they control, for annotations of any size. Line and Arrow endpoint
   handles stay on their endpoints.
2. The whole visible area of a resize handle shall start a resize; no part of it shall start a
   move. Grabbing a handle shall not jump the annotation's size on the first pointer move.

# DESIGN

## 1. Goal
Build a small Windows desktop app to place a scanned signature (transparent image) on top of a PDF page and export the result as a JPG, with minimal manual steps.

## 1.1 Example Assets (Current Workspace)
- `examples/document.odt` (sample OpenDocument Text document; master file, other examples are derived from this)
- `examples/document.pdf` (sample one-page input document)
- `examples/document.doc` (sample Word document)
- `examples/document.docx` (sample Word document)
- `examples/document1.pdf` (sample multi-page input document, 1st page of master document)
- `examples/document1.jpg` (sample image document)
- `examples/signature.png` (sample signature image)
- `examples/signature.xcf` (GIMP source; not directly supported for import)

## 2. Scope (v1)
- Open a document in one of the supported formats: PDF, Word (.docx/.doc), ODT, or images (JPG, PNG, BMP, WEBP, GIF, TIFF).
- Multi-format support via format-agnostic document loader:
  - PDF: rendered directly via PyMuPDF
  - Word/ODT: converted to temporary PDF via LibreOffice, then rendered
  - Images: loaded directly via Pillow
- Open/select a signature image from annotation submenu (PNG preferred for transparency).
- Show document and signature overlay in one canvas.
- Drag signature to final position.
- Resize signature (scale up/down) before saving by dragging boundary handles.
- Save merged output as JPG.
- Support startup parameters:
  - `-document <path>` (any supported document format)
  - `-signature <path>` (image file, PNG preferred)
- If signature is not provided, reuse last signature file.
- Default output file name: `<documentname>-signed.jpg`.
- Document view fits window (no zoom controls in v1).
- Default position for new annotations: centered in the visible page.
- Support multi-page documents: place objects on any page.
- Add paging controls in toolbar and keyboard support (`PageUp`, `PageDown`, `Home`, `End`).
- Show blue boundary around selected signature/annotation while editing.
- Change mouse cursor to move arrows when hovering draggable objects.
- Use toolbar-first UI with large action buttons instead of hierarchical menu for primary actions.
- Support annotations (checkmark, crossmark, 8-direction arrows, text) with color + move + scale.
- Remove top-level "Open Signature" button from toolbar; signature insertion is done via annotation menu.

## 3. Non-Goals (v1)
- Digital certificate signing.
- OCR or PDF editing beyond image export.
- Rotation UI for signature.
- Freehand drawing annotations.
- Advanced typography controls (font families, rich text editing) for text annotations.

## 4. UX Design
### Main Window (Version 1.2.10 Update)
- Top toolbar (large buttons):
  - Open Document
  - Add Annotation (2nd position)
  - Save As... (3rd position, same workflow group, replaces "Save JPG")
  - Previous Page / Next Page
  - Annotation picker (dropdown):
    - Checkmark
    - Crossmark
    - Arrow N/NE/E/SE/S/SW/W/NW
    - Text ▶ Free text / Current date / Current time / Current date & time
    - Signature ▶ From file… / Recent (up to 10 LRU files)
- **Hamburger menu** (right end, three horizontal lines ☰):
  - **File:** Open Document, Recent Documents, Save As..., Exit
  - **Edit:** Undo, Redo, Cut, Copy, Paste, Duplicate, Select All, Delete
  - **Annotations:** List of all annotation types with submenus
  - **Help:** Homepage (on GitHub)
- Terminology: primary actions are provided as Toolbar buttons (faster navigation). They are also available in the hamburger menu for accessibility.
- Central canvas:
  - Background: rendered current PDF page (fit-to-window).
  - Foreground: draggable/scalable objects (signature + annotations).
  - Blue boundary for selected object.
- Status bar: (removed in version 1.2.1)

### Typical Flow
1. Start app.
2. Open document (or auto-load from `-document`).
3. If `-signature` is provided, add signature annotation immediately after document load.
4. If `-signature` is not provided, do not auto-add any annotation on open.
5. Navigate to page (toolbar or keyboard shortcuts).
6. Drag/scale signature to desired location.
7. Optionally add and adjust annotation objects.
8. Save document via "Save As..." dialog, selecting desired format (JPG, PNG, PDF, TIFF, BMP).

## 5. Functional Design
### 5.1 Input Handling
- Validate file existence and extensions.
- Supported document formats:
  - **PDF** input: support multi-page PDFs via PyMuPDF
  - **Word** (.docx, .doc): convert to PDF via LibreOffice, then render
  - **ODT**: convert to PDF via LibreOffice, then render
  - **Images** (JPG, PNG, BMP, WEBP, GIF, TIFF): load directly via Pillow
- Signature input: PNG (for transparency) or other image formats supported by Pillow.
- Unsupported format (e.g., `.xcf`, unsupported file types) should trigger a clear validation message.

### 5.2 Rendering Pipeline
1. For PDF documents: render active PDF page to bitmap at fixed internal DPI via PyMuPDF.
2. For Word/ODT documents: convert to temporary PDF via LibreOffice subprocess, then render via PyMuPDF.
3. For image documents: load directly via Pillow.
4. All document pages normalized to `List[PIL.Image]` at fixed internal DPI: **300 DPI**.
5. Scale page bitmap to fit viewport while preserving aspect ratio.
6. Render object layer for active page (signature + annotations) in viewport coordinates.
7. Support object move and scale (boundary-handle drag).
8. On save (active page):
   - Convert object viewport coordinates to source bitmap coordinates.
   - Composite signature and annotations in z-order over active page bitmap.
   - Export JPG.

### 5.3 Pagination Model
- Keep independent object lists per page (`page_index -> objects[]`).
- Page switch updates canvas to that page and its objects.
- Keyboard navigation:
  - `PageUp`: previous page
  - `PageDown`: next page
  - `Home`: first page
  - `End`: last page

### 5.4 Default Placement
- `x = (page_width - object_width) / 2`
- `y = (page_height - object_height) / 2`
- Clamp to page bounds.

### 5.5 Object Interaction
- Hover on draggable object: cursor changes to move arrows.
- Selected object shows blue boundary.
- Scale method: dragging object boundary handles.
- For non-text annotations, boundary scaling preserves aspect ratio.
- For free text annotations, boundary scaling supports non-proportional resize.

### 5.6 Annotations
- Supported types:
  - Checkmark
  - Crossmark
  - Arrow: N, NE, E, SE, S, SW, W, NW
  - Text (submenu):
    - Free text
    - Current date (inserts formatted date using system locale)
    - Current time (inserts formatted time using system locale)
    - Current date and time (inserts formatted datetime using system locale)
  - Signature (submenu):
    - From file… (opens file dialog, inserts PNG as signature overlay)
    - Up to 10 recently used signature files, ordered by LRU
- Each annotation supports:
  - Color
  - Move
  - Scale
  - Duplicate (creates a copy preserving size and color)
- Visual default size for symbol annotations is reduced to ~1/3 of previous prototype size.
- Free text behavior:
  - default text size: 12pt
  - no wrapping
  - newline entry via Ctrl+Enter in text editor dialog

### 5.7 Persistence
Use a lightweight local config file (JSON) in user profile (e.g., `%APPDATA%/Signer/config.json`) storing:
- `lastSignaturePath`
- `recentSignaturePaths` (up to 10, ordered by LRU)
- `recentTextStrings` (up to 10, ordered by LRU, excludes predefined date/time strings)
- `recentDocumentPaths` (up to 10, ordered by LRU)
- `lastOpenDocumentPath` (optional)
- `lastSaveDirectory` (optional)

Recent items appear in relevant menus:
- **File menu**: Recent documents at top level after static items, separated by horizontal rule
- **Annotations → Text submenu**: Recent texts at top level after static items, separated by horizontal rule
- **Signature submenu**: Recent signatures with separator (existing)
- **Toolbar "Open Document" dropdown**: Recent documents submenu

### 5.8 Export Formats (Save As)
Supported export formats for annotated documents:
- **JPG**: 300 DPI, lossy compression, default format
- **PNG**: 300 DPI, lossless compression, maintains transparency
- **PDF**: 300 DPI, raster images (embedded), all pages in single file
- **TIFF**: 300 DPI, compressed multi-frame, all pages in single file
- **BMP**: 300 DPI, uncompressed raster

File naming for multi-page export:
- Single-page: `{name}-signed.{ext}`
- Multi-page JPG/PNG/BMP: `{name}-signed-p01.{ext}`, `{name}-signed-p02.{ext}`, etc.
- PDF/TIFF: `{name}-signed.{ext}` (all pages in one file)

Save As Dialog Behavior:
- Preserves last used export format (extension) from previous save
- Format is auto-detected from file extension in the filename input
- User can change format by modifying the extension

### 5.9 Post-Export Notification (v1.2.11)
After successful export:
- Display an auto-dismissing notification toast (bottom-right corner)
- Duration: auto-dismiss after 5 seconds or manual close with X button
- Message format: "Exported {filename} to [directory link]"
- Directory link is clickable (underlined, colored) and opens Windows Explorer at that location
- Notification does not steal focus; user can continue working
- Notification text is readable with sufficient contrast against background

On export failure:
- Display a modal error dialog (blocks interaction) instead of notification
- Dialog shows specific error message, file path, and recovery suggestions
- Provide "Retry" and "Cancel" buttons
- Errors demand user acknowledgment; success notifications are non-intrusive

### 5.10 Export Quality Options (v1.2.14)

**Design Principle:**
- Standard user workflow: Select format → click Save → done (no extra steps)
- Advanced users: Click "Options" button to tune quality settings before saving
- Lossless formats automatically use best available quality (PNG: max compression, TIFF: LZW)

**Save As Dialog Changes:**
- Add "Options..." button (enabled and visible ONLY for lossy formats: JPG and PDF; hidden for lossless formats: PNG/TIFF/BMP)
- Button label: "Options..." or "Quality Options..."
- Button position: Near standard "Save" and "Cancel" buttons (similar to Word/Office)

**Quality Options Panel** (opened by "Options" button for lossy formats only):
- Non-modal dialog floating above Save As dialog
- Title: "Export Quality Options"
- Shows quality slider (1-100) with numeric value always visible
- Slider labels: "small file" on left ← → "large file" on right (indicates quality-to-filesize tradeoff)
- Buttons: "OK" (apply settings and close panel), "Cancel" (discard changes and close panel)
- After "OK": returns to Save As dialog so user can click "Save"
- After "Cancel": returns to Save As dialog; no quality settings changed

**Format-Specific Settings:**

**Lossy Formats (Options button enabled):**
| Format | Control | Range | Default | Slider Labels |
|--------|---------|-------|---------|----------------|
| **JPG** | Slider | 1-100 | 95 | "small file" ← → "large file" |
| **PDF** | Slider | 1-100 | 95 | "small file" ← → "large file" |

*For JPG and PDF, numeric value is always visible next to slider.*

**Lossless Formats (Options button hidden):**
| Format | Quality Control | Notes |
|--------|-----------------|-------|
| **PNG** | Automatic | Always uses compress_level=9 (maximum lossless compression) |
| **TIFF** | Automatic | Always uses LZW compression (industry standard) |
| **BMP** | Automatic | Always uncompressed (standard format) |

**User Workflows:**

*Standard (no quality adjustment):*
1. Click "Save As..." button
2. Select filename and format
3. Click "Save"
4. Export with default quality (JPG/PDF: 95; PNG: max compression; TIFF: LZW)
5. Success notification appears

*Advanced (with quality adjustment):*
1. Click "Save As..." button
2. Select filename and format
3. Click "Options..." button (if enabled for that format)
4. Adjust quality slider and click "OK"
5. Click "Save"
6. Export with selected quality settings
7. Success notification appears

**Settings Persistence:**
- Configuration fields in `config.json`:
  - `lastJpegQuality` (int, 1-100, default: 95)
  - `lastPdfImageQuality` (int, 1-100, default: 95)
- PNG and TIFF settings NOT persisted (always use best quality automatically)
- Options panel pre-populates with last-used values for JPG and PDF
- Settings updated when user clicks "OK" in options panel (not during export)

**Export Behavior:**
- JPG: Pass `quality=value` to `PIL.Image.save()` (user-selected or default 95)
- PNG: Always pass `compress_level=9` to `PIL.Image.save()` (no user choice, automatic best quality)
- PDF: Pass `quality=value` when compositing raster images (user-selected or default 95)
- TIFF: Always use `compression='tiff_deflate'` (LZW, no user choice, automatic best quality)
- BMP: No additional parameters (always uncompressed)

**Error Handling:**
- Invalid quality values: clamp to valid range
- Corrupted config file: use format defaults
- Export failure: show error dialog with cause

**Benefits of This Approach:**
- Simpler standard workflow (one less dialog)
- Power users can still access quality controls
- Lossless formats always get best quality without overhead
- Consistent with Office/Word "Options" button pattern

### 5.11 CLI Parameters
- `-document <path>`: initial document to load (any supported format: PDF, Word, ODT, or image).
- `-signature <path>`: initial signature to load (image file, PNG preferred).
- If `-signature` is provided with `-document`, add signature annotation immediately after load.
- If `-signature` is omitted, do not auto-add annotations on document open.

Example startup:
- `Signer.exe -document examples/document.pdf -signature examples/signature.png`
- `Signer.exe -document examples/document.docx -signature examples/signature.png`

### 5.12 File Naming (All Formats)
Default save name (applies to all export formats):
- Input `document.pdf` => `document-p<page>-signed.{ext}` for multi-page clarity (example: `document-p3-signed.jpg`)
- If conflict exists, append numeric suffix (`-signed-1.jpg`, etc.)
- Version 1.2.10 unifies this across all formats via "Save As" dialog

### 5.13 Document and Page Rotation (v1.2.16)

**Design Principle**: Rotation is temporary (session-only) for viewing and exporting; no persistence to disk.

**Menu Items**: Four rotation actions in Edit menu:
- Rotate Current Page Left (90° counter-clockwise)
- Rotate Current Page Right (90° clockwise)
- Rotate All Pages Left (all pages 90° counter-clockwise)
- Rotate All Pages Right (all pages 90° clockwise)

**Rotation Behavior**:
- Per-page rotation state tracked via `_page_rotations: dict[int, int]` (maps page index to angle in 0/90/180/270)
- Rotation is cumulative: clicking "left" 4 times on same page returns to 0°
- Annotations do not rotate visually, but their position coordinates are transformed so the center remains at the same visual location
- Coordinate transformation accounts for the changed coordinate system after page rotation
- Window auto-resizes to maintain aspect ratio for portrait↔landscape transitions (via `_recompute_fit()`)

**Annotation Coordinate Transformation**:
- Original annotation coordinates stored relative to unrotated page
- **Center-based transformation**: Calculate annotation center from top-left corner (x, y), transform center coordinates, convert back to top-left corner
- **Display**: Annotation center is transformed via `_transform_doc_coords_by_rotation()` so centers remain at the same visual location on the page after rotation
- **Export**: Annotation center is transformed via `page_objects_with_rotation_at()` so centers appear at the correct visual position on the rotated page
- **Mouse interaction**: Mouse coordinates are converted via `_transform_doc_coords_inverse()` to convert back from rotated to original coordinates
- **Key property**: Annotations themselves are NOT rotated—only their position changes. Signatures keep their aspect ratio, text stays upright, etc.
- **Transformation formulas** (mapping W×H original page to H×W rotated page):
  - 90° CCW: (x, y) → (y, W - x)
  - 180°: (x, y) → (W - x, H - y)
  - 270° CCW: (x, y) → (H - y, x)

**Export Behavior**:
- All export formats (JPG, PNG, PDF, TIFF, BMP) export rotated pages as-is
- Multi-page documents can have mixed rotations (different angles per page); each exports with its own rotation
- Annotations are exported at their transformed coordinates on rotated pages
- `page_objects_with_rotation_at()` returns objects with coordinates pre-transformed for export
- Rotation does not modify stored image files, only the displayed/exported view

**Implementation Details**:
- Rendering: PIL `Image.rotate(degrees, expand=True)` applies rotation with dimension swapping
- Dimension swapping: 90°/270° rotations swap width↔height for proper fit calculation
- Pixmap caching: `_update_rotated_pixmap()` regenerates QPixmap after rotation
- Canvas coordinate mapping: 
  - Display: `_object_view_rect()` transforms annotation coords
  - Interaction: `_view_to_doc()` applies inverse transformation
  - Export: `page_objects_with_rotation_at()` returns shallow copies with transformed coordinates
- Export integration: `get_page_image_with_rotation()` returns rotated PIL image; export functions use transformed object coordinates

### 5.14 Multi-Selection Feature (v1.2.17)

**Selection Mechanics**:
- **Single-selection**: Click on an annotation to select it (existing behavior, unchanged)
- **Multi-selection**: Hold Shift and click on an annotation to add it to or remove it from current selection
- **Selection scope**: Limited to annotations on the current page only; selection is cleared when navigating to a different page
- **Clear selection**: Click on empty canvas to deselect all (existing behavior when no Shift held)

**Multi-Selection Operations**:
When multiple annotations are selected, the following operations apply to all selected annotations:

| Operation | Behavior |
|-----------|----------|
| **Move** (arrow keys) | All selected annotations move together; Arrow keys: ~10px; Shift+Arrow: ~50px |
| **Delete** (Delete key) | Delete all selected annotations in single undo/redo unit |
| **Copy** (Ctrl+C) | Copy all selected annotations to clipboard as JSON |
| **Cut** (Ctrl+X) | Copy all selected to clipboard, then delete in single undo unit |
| **Paste** (Ctrl+V) | Paste copied annotations onto current page; applies ~10px offset on same page, no offset on different page |
| **Duplicate** (Ctrl+D) | Create copies of all selected, offset by ~15px; single undo unit |
| **Color change** | Apply color to all selected annotation types that support it |

**Visual Feedback**:
- Single selection: Blue boundary around selected annotation (existing)
- Multi-selection: Blue boundary around all selected annotations; resize handles shown only on primary selected object

**Clipboard Format (JSON)**:
Annotations are serialized as a JSON array when copied/cut. Format preserves all object properties:
```json
[
  {
    "type": "signature|checkmark|cross|arrow_*|text",
    "x": 100.0,
    "y": 200.0,
    "scaled_width": 300.0,
    "scaled_height": 150.0,
    "page": 0,
    "color": "#cc0000",
    ...
  }
]
```

When pasted:
- **Same page**: Offset applied (~10 pixels) to avoid exact overlap with originals
- **Different page**: No offset applied (already distinct location)

**Implementation Details**:
- Data structures: `_selected` (primary) + `_selected_multiple` (set of all selected)
- Methods: `select_annotation(obj, multi)`, `clear_selection()`, `get_selected_annotations()`, `is_multi_selected()`
- Multi-operation methods: `move_selected()`, `delete_selected()`, `duplicate_selected_multi()`, `copy_selected()`, `cut_selected()`, `paste_selected()`
- Rendering: All selected annotations display blue boundary; resize handles only on primary
- Page navigation: Selection cleared when switching pages via `set_current_page()`
- Keyboard handling: Shift+click for multi-select; arrow keys for move; Delete/Ctrl+C/X/V for delete/copy/cut/paste

**Menu Items** (Edit menu):
- Cut (Ctrl+X): Works on single or multi-selection
- Copy (Ctrl+C): Works on single or multi-selection
- Paste (Ctrl+V): Pastes to current page with offset behavior as described
- Duplicate (Ctrl+D): Works on single or multi-selection
- Delete (Delete): Works on single or multi-selection

**Edge Cases & Constraints**:
- Multi-selection limited to current page; switching pages clears selection
- Copy/paste works across document instances via system clipboard
- Cache is set on first paste and persists for subsequent pastes, preventing intermediate copy operations from corrupting cached positions
- Each multi-operation (move all, delete all) is a single undo/redo unit
- Invalid operations on mixed types are gracefully ignored (e.g., line width only applies to vector types)

**Backward Compatibility**:
- Existing single-selection behavior unchanged (click selects one, click-empty deselects)
- All existing operations (Delete, Duplicate, Color change) now work with multi-selection
- Undo/redo: each multi-operation is single unit, maintaining existing behavior for single operations
- Paste position preservation: Cache strategy ensures copy→move→paste sequences work correctly even with external Ctrl+C interference

## 6. Error Handling
- Missing/unreadable document: block canvas interaction, show clear error message.
- Missing signature annotation: allow document load, prompt user to add a signature annotation before save.
- Corrupt image/document: show validation error and keep app responsive.
- Save failure (permissions/locked file/disk full): show modal error dialog with specific cause and recovery suggestions; offer retry or cancel.
- Invalid export path (bad characters, too long): validate before export and show error with corrected suggestion.
- Directory link failure (path no longer exists): show brief toast notification "Unable to open directory"; do not crash.
- Partial export failure (multi-page): stop process, show error listing failed pages and reason, offer retry or cancel.

### Error Dialog vs Notification Toast
- **Modal error dialogs** (block interaction): export failures, validation errors, missing dependencies
- **Auto-dismissing toasts** (non-intrusive): success notifications, secondary warnings that don't block workflow

## 6.1 Selection-Dependent Toolbar Actions
- Duplicate/Delete actions are enabled only when an annotation is selected.
- Color action behavior:
  - when annotation selected: change selected annotation color
  - when none selected: set default color for next new annotation

## 7. Architecture
### Modules
- `ui/` window, toolbar, canvas, drag/scale behavior.
- `core/pdf_renderer` PDF -> bitmap.
- `core/compositor` object overlay + JPG export.
- `core/pagination` page navigation and page-scoped state.
- `core/annotations` annotation factories, geometry, styling.
- `core/settings` load/save user config.
- `core/cli` parse startup arguments.

### Data Model
- `DocumentState`: file path, page count, current page index, rendered bitmap size.
- `SignatureState`: path, image size, page index, position, scale.
- `AnnotationState`: type, color, page index, position, scale, text (for text/date annotations), source_path (for signature annotations).
- `SessionState`: output path defaults, selected object, dirty flag.

## 8. Tool Analysis

### Multi-Format Document Support (v1.2.9)
For Word and ODT support, the app integrates with LibreOffice:
- **LibreOffice** (headless): Converts Word and ODT to temporary PDF for rendering
- **PyMuPDF (fitz)**: Renders PDF pages (including converted docs) to images
- **Pillow**: Handles direct image loading and JPG export

Path resolution for LibreOffice:
1. Check settings file (`libreOfficePath` field in config.json)
2. Search system PATH
3. Show error if not found

## Option A (Recommended): Python + PySide6 + PyMuPDF + Pillow + LibreOffice
- **PySide6**: native-feeling desktop UI on Windows, quick iteration.
- **PyMuPDF (fitz)**: reliable PDF page rendering to image.
- **Pillow**: robust compositing and JPG export.
- **argparse**: CLI parameter parsing.
- **PyInstaller**: package to a single Windows executable.

### Pros
- Fastest delivery for this feature set.
- Good image/PDF tooling ecosystem.
- Easy maintenance for a small utility.

### Cons
- Larger packaged binary than pure .NET.
- Python runtime included in distribution.

## Option B: .NET 8 WPF + Pdfium + ImageSharp/SkiaSharp
### Pros
- Very native Windows stack.
- Strong deployment options (MSIX, single-file publish).

### Cons
- More setup complexity for PDF/image pipeline.
- Slower iteration if team is less familiar with C# desktop UI.

## Option C: Electron + pdf.js + canvas
### Pros
- Strong UI flexibility.

### Cons
- Heavier memory footprint.
- Unnecessary complexity for a simple local utility.

## 9. Decision
### Chosen Option
**Option A (Python + PySide6 + PyMuPDF + Pillow) is the decided implementation path for v1.**

### Decision Rationale
- Shortest implementation path.
- Lowest delivery risk for required features.
- Supports single-file Windows distribution via PyInstaller `--onefile`.

### Confirmed Implementation Decisions
- PDF render quality is fixed to **300 DPI**.
- Signature scaling is included in v1 via boundary-handle drag.
- Initial product name is **Signer** (can be renamed before release).
- Code signing is out of scope for v1 packaging.
- Multi-page PDFs are supported with toolbar + keyboard navigation.
- Save behavior exports the active page to JPG.

### Dialog Implementation Trade-off (Version 1.2.12)
- **Native Windows file dialog** (default Qt behavior) does NOT expose underlying text input widget (QLineEdit)
- **Smart filename handling** requires real-time monitoring of user input as they type to:
  - Preserve custom filename stem across format changes
  - Auto-update filename when user changes file extension
  - Capture user intent without dialog blocking
- **Trade-off decision**: Use **non-native Qt dialog** (DontUseNativeDialog flag) to access QLineEdit
  - Pros: Enables powerful auto-correction, filename preservation, real-time format detection
  - Cons: Older UI appearance (Windows 95-style classic Qt theme instead of modern Windows Aero)
- **Rationale**: Functional capability takes priority over native UI appearance for this utility
- **Test coverage**: 41+ tests cover all format switching, placeholder, and validation scenarios

### Version 1.2.12 Implementation Details
- **Real-time capture**: `QLineEdit.textChanged.connect(self._on_filename_text_changed)`
- **Non-native dialog**: `QFileDialog.setOption(DontUseNativeDialog, True)` set before `exec()`
- **Placeholder calculation**: `len(str(total_pages))` gives required digit count
- **Custom stem extraction**: `Path(filename).stem` gets name without extension
- **Format detection**: Both `ExportFormat.from_extension()` and `ExportFormat.from_filter_string()`
- **Smart validation**: Separate paths for single-file vs multi-file formats
- **User interaction flow**: User types → validation → if invalid, show info dialog → user retries (dialog stays open)

## Tool Decision
Use **Option A** for v1 due to shortest implementation path and low risk for required features.

## 10. Performance and Quality Targets
- Open and render current PDF page in < 1 second for common office documents.
- Drag/scale objects with smooth interaction (no visible lag).
- Export quality suitable for typical print/email workflows.
- Window aspect ratio should adapt to document aspect ratio while keeping the full toolbar visible.

## 11. Test Strategy (Design-Level)
- Unit tests:
  - default filename generation,
  - position math and bounds clamping,
  - settings persistence behavior.
- Manual functional tests:
  - startup with/without CLI args,
  - startup using sample assets (`examples/document.pdf` + `examples/signature.png`),
  - **verify Word document (.docx) opens and renders correctly,**
  - **verify ODT document opens and renders correctly,**
  - **verify image document (.jpg) opens and renders correctly,**
  - **verify unsupported format shows error dialog,**
  - verify page navigation via toolbar and keys (`PageUp`, `PageDown`, `Home`, `End`),
  - verify per-page object persistence when switching pages,
  - verify cursor change on hover and blue boundary on selection,
  - verify boundary-handle scaling behavior,
  - verify text annotation allows non-proportional resize,
  - verify text default is 12pt, no wrapping, and Ctrl+Enter creates newline,
  - verify toolbar order: Open Document, Add Annotation, Save As...,
  - verify no top-level Open Signature toolbar button,
  - verify duplicate/delete enabled only when selection exists,
  - verify color behavior for selected vs non-selected state,
  - verify annotation insertion and color/move/scale for all supported types,
  - verify annotation duplication (size and color preserved),
  - verify text annotation date/time/datetime insertion uses system locale,
  - verify signature annotation "From file…" inserts correctly,
  - verify signature annotation LRU list updates and respects 10-item limit,
  - load invalid files,
  - drag and save accuracy,
  - transparency preserved in composition before JPG flattening,
  - **verify export success shows auto-dismissing notification toast with directory link,**
  - **verify clicking directory link opens Windows Explorer at export location,**
  - **verify notification auto-dismisses after 5 seconds,**
  - **verify manual close button (X) on notification works,**
  - **verify export failure shows modal error dialog with specific error message,**
  - **verify error dialog includes retry and cancel buttons,**
  - **verify partial export failure (multi-page) shows error with list of failed pages.**

## 12. Recommended Workflow Improvements vs GIMP
- One-step startup with saved signature.
- Fit-to-window preview with direct drag positioning.
- One-click export to predictable filename.

This removes repetitive manual steps (open layers, align, export settings) and makes signing routine documents significantly faster.

## 12.1 Open Clarification (Captured)
- Because output format is JPG (single image), save action exports the **active page** only.
- Future extension (not in current scope): batch export all pages as `document-p1-signed.jpg`, `document-p2-signed.jpg`, etc.

## 13. Packaging & Distribution (Option A)
### Objective
Distribute the app as a single Windows executable for non-technical users.

### Recommended Build Tool
- **PyInstaller** in `--onefile` mode.

### Important Clarification
- `--onefile` creates a **single distributable `.exe`**.
- It is not a fully static native binary; at launch, the bundle extracts runtime files to a temporary directory and starts the app.

### Build/Release Strategy
1. Build on the same target OS family (Windows) used by end users.
2. Pin dependency versions for reproducible outputs.
3. Produce one release artifact: `signer.exe`.
4. Include a checksum file (e.g., SHA-256) for integrity verification.

### Distribution Notes
- End users do **not** need a separate Python installation.
- Expect larger binary size due to embedded interpreter and libraries.
- For v1, distribute as unsigned executable (no code signing).
- Some antivirus tools may flag unsigned executables; communicate checksum and distribution source clearly.

### Acceptance Criteria for Packaging
- App runs on a clean Windows machine with no Python installed.
- CLI args `-document` and `-signature` work in packaged form.
- PDF render, drag placement, and JPG export behavior match development mode.

## 14. Test Architecture and Strategy (v1.2.5+)

### 14.1 Overview
The test suite includes:
1. Unit tests for core functionality (coordinate transforms, bounding boxes, serialization)
2. Feature tests with action recording capability for end-to-end workflows
3. Image comparison for pixel-perfect verification against reference images

### 14.2 Test Structure
```
tests/
├── __init__.py
├── conftest.py                  # Pytest fixtures and configuration
├── unit/
│   ├── __init__.py
│   ├── test_coordinate_transforms.py
│   ├── test_bounding_box.py
│   ├── test_annotation_serialization.py
│   └── test_settings.py
├── feature/
│   ├── __init__.py
│   ├── test_document1_annotations.py     # Signature + annotation type tests
│   ├── test_multipage_annotations.py
│   └── test_undo_redo.py                 # Future
├── fixtures/
│   ├── document1.pdf
│   ├── document1-signed-expected.jpg
│   ├── document.pdf
│   └── signature.png
├── recording/
│   ├── __init__.py
│   ├── action_recorder.py       # Records user actions for test creation
│   └── action_player.py         # Plays back recorded actions
└── utils/
    ├── __init__.py
    ├── image_comparison.py      # Pixel-perfect image comparison
    └── test_helpers.py          # Common test utilities
```

### 14.3 Action Recording System

The action recording system enables developers to:
1. Enable recording mode via environment variable `SIGNER_RECORD_ACTIONS=1`
2. Perform actions in the application (add annotations, move, resize, etc.)
3. Persist recorded actions to a JSON file
4. Use that output to create automated feature tests

#### Supported Action Types
- `open_document`: Load a PDF document
- `open_signature`: Load a signature image
- `add_annotation`: Add an annotation (type, position, page)
- `move_annotation`: Move annotation to new position
- `resize_annotation`: Resize annotation (width, height, handle)
- `select_annotation`: Select an annotation
- `change_color`: Change annotation or default color
- `change_page`: Navigate to page
- `save_document`: Save active page to JPG

#### Recording Output Format (JSON)
```json
{
  "actions": [
    {"type": "open_document", "path": "examples/document1.pdf"},
    {"type": "open_signature", "path": "examples/signature.png"},
    {"type": "add_annotation", "annotation_type": "checkmark", "page": 0, "x": 100, "y": 200},
    {"type": "move_annotation", "object_id": 1, "x": 150, "y": 250},
    {"type": "resize_annotation", "object_id": 1, "width": 200, "height": 200, "handle": 7},
    {"type": "save_document", "path": "output/test.jpg"}
  ]
}
```

**Note:** Version and timestamp fields are omitted. Test version management is handled via test code, not action records. Actions execute sequentially when replayed.

### 14.4 Unit Tests

#### Coordinate Transformations
- Viewport to document coordinate conversion
- Document to viewport coordinate conversion
- Fit scale calculation
- Page offset calculation
- Handle position calculations

#### Bounding Box Calculations
- Object bounding box in document space
- Object bounding box in viewport space
- Handle rect calculations
- Clamp to page bounds
- Text box fitting

#### Annotation Serialization
- SignatureObject serialization/deserialization
- VectorAnnotation serialization/deserialization
- Settings persistence
- Recent lists LRU behavior

#### Settings Tests
- Settings load/save
- Default values
- Path resolution (Windows/Linux)
- Recent lists management

### 14.5 Feature Tests

#### Test Coverage
Each feature test shall:
1. Operate non-interactively (automatically handle dialogs)
2. Use recorded action sequences
3. Verify expected output against reference images (pixel-perfect comparison)
4. Cover all annotation types (signature, checkmark, cross, arrows, text)

#### Main Feature Tests
1. **document1.pdf with Signature and Annotations**
   - Open document1.pdf
   - Add signature from examples/signature.png
   - Add one annotation of each supported type
   - Move and resize each item
   - Save to JPG
   - Compare pixel-perfect to reference image

2. **Multi-page Document Annotations**
   - Open document.pdf (multi-page)
   - Add different annotations on different pages
   - Navigate between pages
   - Verify annotations persist per page
   - Export all pages with individual verification

#### Image Comparison
- Use PIL/Pillow for pixel-by-pixel comparison
- Enforce pixel-perfect matching (exact images required)
- Generate diff image on failure
- Report pixel-level differences visually

### 14.6 Test Dependencies
- `pytest>=7.0.0`: Test framework
- `pytest-qt>=4.2.0`: Qt widget testing
- `pytest-cov>=4.0.0`: Coverage reporting
- `Pillow>=9.0.0`: Image comparison and manipulation

### 14.7 Test Fixtures
- `qapp`: QApplication instance
- `main_window`: MainWindow instance
- `canvas`: DocumentCanvas instance
- `sample_pdf`: Path to test PDF
- `sample_signature`: Path to test signature
- `temp_dir`: Temporary directory for outputs

### 14.8 Running Tests
```bash
# Run all tests
pytest

# Run unit tests only
pytest tests/unit/

# Run feature tests only
pytest tests/feature/

# Run with coverage
pytest --cov=signer --cov-report=html

# Run specific test
pytest tests/feature/test_document1_annotations.py -v
```

### 14.9 Recording Feature Tests

The action recording system allows developers to record manual interactions in the application and convert them into automated test scenarios.

#### Enabling Recording

Set the environment variable `SIGNER_RECORD_ACTIONS=1` before running the application:

```bash
# Linux/macOS
export SIGNER_RECORD_ACTIONS=1
python -m signer

# Windows PowerShell
$env:SIGNER_RECORD_ACTIONS=1
python -m signer

# Windows CMD
set SIGNER_RECORD_ACTIONS=1
python -m signer
```

#### What Gets Recorded

The following actions are automatically captured when recording is enabled:

| Action | Recorded Data |
|--------|---------------|
| Open document | File path |
| Open signature | File path |
| Add annotation (vector) | Type, position (x,y), page |
| Add text annotation | Text content, position, page |
| Move annotation | Object ID, new position (x,y) |
| Resize annotation | Object ID, new size (width,height), handle used |
| Change color | Object ID, color hex value |
| Change page | Page index |
| Save document | Output file path |

#### Recording Workflow

1. **Start the application with recording enabled**
   ```bash
   SIGNER_RECORD_ACTIONS=1 python -m signer
   ```

2. **Perform your test scenario**
   - Open a document
   - Add signatures, checkmarks, text, arrows
   - Move and resize annotations
   - Change colors
   - Navigate between pages
   - Save the document

3. **Close the application**
   - The recorded actions will be printed to stdout
   - A JSON file will be saved to `tests/recorded_actions/recorded_actions_<timestamp>.json`

4. **Create the reference image**
   - The saved output from step 2 becomes your reference image
   - Copy it to `tests/fixtures/{testname}_actions-expected/{testname}-output.png`

5. **Create the feature test**
   - Use the recorded actions JSON as a guide
   - Write or update a test in `tests/feature/` that reproduces the steps
   - Use `assert_images_equal_with_results()` to compare output with reference

#### Recorded Actions Format (JSON)

```json
{
  "version": "1.0",
  "actions": [
    {
      "type": "open_document",
      "path": "/path/to/document.pdf",
      "timestamp": 1234567890.123
    },
    {
      "type": "open_signature",
      "path": "/path/to/signature.png",
      "timestamp": 1234567891.456
    },
    {
      "type": "add_annotation",
      "annotation_type": "checkmark",
      "x": 400.0,
      "y": 300.0,
      "page": 0,
      "object_id": 0,
      "timestamp": 1234567892.789
    },
    {
      "type": "move_annotation",
      "object_id": 0,
      "x": 300.0,
      "y": 400.0,
      "timestamp": 1234567893.012
    },
    {
      "type": "resize_annotation",
      "object_id": 0,
      "width": 250.0,
      "height": 250.0,
      "handle": 7,
      "timestamp": 1234567894.345
    },
    {
      "type": "change_color",
      "object_id": 0,
      "color": "#ff0000",
      "timestamp": 1234567895.678
    },
    {
      "type": "change_page",
      "page": 1,
      "timestamp": 1234567896.901
    },
    {
      "type": "save_document",
      "path": "/path/to/output.jpg",
      "timestamp": 1234567897.234
    }
  ]
}
```

#### Best Practices for Recording

1. **Use descriptive test names**: `test_document1_signature_checkmark_pixel_perfect`
2. **Keep tests focused**: One test per feature scenario
3. **Use fixtures**: Leverage `conftest.py` fixtures for common setup
4. **Test pixel-perfect**: All comparisons require exact pixel matching
5. **Document the scenario**: Add docstrings explaining what the test verifies
6. **Verify recording is enabled**: Check console output for "ACTION RECORDING ENABLED" message
7. **Use relative paths**: Recorded paths are often absolute; normalize to relative in test fixtures

#### Troubleshooting Recording

| Problem | Solution |
|---------|----------|
| Recording not working | Ensure `SIGNER_RECORD_ACTIONS=1` is set BEFORE starting application |
| Actions not captured | Check console for "ACTION RECORDING ENABLED" message; verify patched methods are being called |
| File not found in JSON | Paths may be absolute; convert to relative for portability (e.g., `examples/document1.pdf`) |
| Output not saved | Ensure you called save_document action before closing app |

#### Disabling Recording

Simply don't set the environment variable, or set it to 0:

```bash
# Normal run without recording
python -m signer

# Explicitly disable
SIGNER_RECORD_ACTIONS=0 python -m signer
```

#### Extending the Recorder

To record additional actions:

1. Add a new `record_*` method to `ActionRecorder` in `tests/recording/action_recorder.py`
2. Add the corresponding patch in the recording initialization
3. Update the action type documentation above

### 14.10 Step-by-Step: Adding a New Feature Test

This section guides developers through the complete process of adding a new feature test. We'll use the example of creating a test for the "checkmark annotation" (this test already exists, but the process applies to any new test).

#### Step 1: Plan Your Test
Define what workflow you want to test:
- Document to use (PDF path)
- Annotations/signature to add
- Actions to perform (move, resize, etc.)
- Expected outcome

**Example: Cross Annotation Test**
- Document: `examples/document.pdf`
- Action: Add a cross annotation, move it, resize it, save
- Expected output: JPG with cross at specific position/size

#### Step 2: Create Fixture Directory Structure

Create a directory for your test fixture images:
```
tests/fixtures/
├── {testname}_actions-expected/
│   ├── {testname}-output.png           # Reference image
│   └── ...other pages if multi-page
```

**Example for cross annotation:**
```
tests/fixtures/
├── cross_actions-expected/
│   └── cross-output.png
```

If using the example PDF documents, they're already in `tests/fixtures/`.

#### Step 3: Generate a Reference Image

You have two options:

**Option A: Use the App to Generate Output (Recommended)**
1. Open the application manually
2. Open your test document
3. Add annotations and position them as your test will
4. Save the JPG
5. Copy to `tests/fixtures/{testname}_actions-expected/`
6. Rename to `{testname}-output.png` (use underscore format)

**Option B: Manual Composition (for pixel-perfect control)**
Use `signer.objects.py` and `signer.compositor.py` to create reference images programmatically.

**Example path:**
```
tests/fixtures/cross_actions-expected/cross-output.png
```

#### Step 4: Create Actions JSON File

Create a JSON fixture file with the action sequence:

**Location:** `tests/fixtures/{testname}_actions.json`

**Format:**
```json
{
  "actions": [
    {"type": "open_document", "path": "examples/document.pdf"},
    {"type": "add_annotation", "annotation_type": "cross", "page": 0, "x": 300, "y": 400},
    {"type": "move_annotation", "object_id": 0, "x": 350, "y": 450},
    {"type": "resize_annotation", "object_id": 0, "width": 120, "height": 120, "handle": 7},
    {"type": "save_document", "path": "output.jpg"}
  ]
}
```

**Annotation Types:**
- `signature`: Load from file
- `checkmark`: ✓ symbol
- `cross`: ✗ symbol
- `arrow`: One of N, NE, E, SE, S, SW, W, NW
- `text`: Free text string

**Handle Positions (for resizing):**
```
0 1 2
3   4
5 6 7
```

**Example for cross annotation:**
```json
{
  "actions": [
    {"type": "open_document", "path": "examples/document.pdf"},
    {"type": "add_annotation", "annotation_type": "cross", "page": 0, "x": 300, "y": 400},
    {"type": "save_document"}
  ]
}
```

**Naming Convention:**
- File: `tests/fixtures/crossmark_actions.json`
- This name becomes the `test_name` used in results organization
- Results appear in: `test-results/actual/cross_actions/`

#### Step 5: Create the Feature Test Class

Create a new test file or add to existing: `tests/feature/test_{feature_name}.py`

**Template Structure:**
```python
import unittest
from pathlib import Path

from signer.app import MainWindow
from signer.settings import SettingsStore
from tests.recording.action_player import ActionPlayer
from tests.utils.image_comparison import assert_images_equal_with_results

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


class TestCrossAnnotation(unittest.TestCase):
    """Test crossmark annotation workflow."""
    
    @classmethod
    def setUpClass(cls):
        """Set up fixtures once for the class."""
        cls.actions_file = FIXTURES_DIR / "crossmark_actions.json"
        cls.expected_image = FIXTURES_DIR / "crossmark_actions-expected" / "crossmark-output.png"
    
    def setUp(self):
        """Create a fresh MainWindow for each test."""
        from tempfile import TemporaryDirectory
        self.temp_dir = TemporaryDirectory()
        
        # Isolated settings for this test
        settings_store = SettingsStore(Path(self.temp_dir.name))
        self.main_window = MainWindow(settings_store=settings_store)
        self.main_window.show()
    
    def tearDown(self):
        """Clean up after each test."""
        if self.main_window:
            self.main_window.close()
        self.temp_dir.cleanup()
    
    def test_cross_annotation_pixel_perfect(self):
        """Test that cross annotation renders correctly."""
        # Play recorded actions
        player = ActionPlayer(self.main_window)
        output_image = player.play_from_file(self.actions_file)
        
        # Verify against reference
        assert_images_equal_with_results(
            output_image,
            self.expected_image,
            test_name="cross_actions",
            save_results=True
        )
```

**Key Points:**
- Class name: `Test{FeatureName}` (e.g., `TestCrossAnnotation`)
- Test method name: `test_{feature}_pixel_perfect`
- Use `test_name="cross_actions"` (matches JSON filename without .json)
- Import fixtures from: `FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"`
- Use `ActionPlayer` to execute recorded actions
- Use `assert_images_equal_with_results()` for image verification

#### Step 6: Run Your Test

```bash
# Run just your new test
pytest tests/feature/test_cross_annotation.py -v

# Run all feature tests
pytest tests/feature/ -v

# Check results in the browser
python tests/utils/review_results.py open
```

#### Step 7: Inspect Results

After running the test:
1. **HTML Report** opens automatically at: `tests/test-results/report.html`
2. **Test Summary List** shows your test with status badge
3. **Comparison View** shows Expected vs Actual side-by-side
4. **Global Diff** visualization shows pixel differences in red/white

**Directory Structure After Test:**
```
tests/test-results/
├── actual/
│   └── cross_actions/
│       ├── cross_actions.png          # Generated output
│       ├── cross_actions_expected.png # Reference
│       └── info.json                  # Metadata with PASS/FAIL status
├── diff.png                           # Pixel-level diff (global)
└── report.html                        # Interactive report
```

#### Step 8: Fix Mismatches (If Any)

**If test FAILS:**

Option A: Update reference image (if output is correct):
```bash
python tests/utils/review_results.py copy-to-expected cross_actions
```
This copies the actual output to the reference and re-runs tests.

Option B: Debug the implementation (if output is wrong):
1. Open `tests/test-results/actual/cross_actions/` to inspect images
2. Check `diff.png` for pixel-level differences
3. Fix the app code
4. Re-run test

#### Step 9: Add Additional Validation Tests (Optional)

You can add more test methods to the same class for different aspects:

```python
class TestCrossAnnotation(unittest.TestCase):
    # ... previous code ...
    
    def test_cross_actions_file_structure(self):
        """Verify actions JSON has required fields."""
        import json
        with open(self.actions_file) as f:
            data = json.load(f)
        
        assert "actions" in data
        assert isinstance(data["actions"], list)
        assert len(data["actions"]) > 0
    
    def test_cross_actions_include_required_types(self):
        """Verify all actions have type field."""
        import json
        with open(self.actions_file) as f:
            data = json.load(f)
        
        for action in data["actions"]:
            assert "type" in action, "Action missing 'type' field"
```

#### Example: Complete Cross Annotation Test

Here's a complete working example:

**File: `tests/fixtures/crossmark_actions.json`**
```json
{
  "actions": [
    {"type": "open_document", "path": "examples/document.pdf"},
    {"type": "add_annotation", "annotation_type": "cross", "page": 0, "x": 300, "y": 400},
    {"type": "move_annotation", "object_id": 0, "x": 350, "y": 450},
    {"type": "save_document"}
  ]
}
```

**File: `tests/feature/test_cross_annotation.py`**
```python
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from signer.app import MainWindow
from signer.settings import SettingsStore
from tests.recording.action_player import ActionPlayer
from tests.utils.image_comparison import assert_images_equal_with_results

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


class TestCrossmarkAnnotation(unittest.TestCase):
    """Test crossmark annotation workflow."""
    
    @classmethod
    def setUpClass(cls):
        cls.actions_file = FIXTURES_DIR / "crossmark_actions.json"
        cls.expected_image = FIXTURES_DIR / "crossmark_actions-expected" / "crossmark-output.png"
    
    def setUp(self):
        self.temp_dir = TemporaryDirectory()
        settings_store = SettingsStore(Path(self.temp_dir.name))
        self.main_window = MainWindow(settings_store=settings_store)
        self.main_window.show()
    
    def tearDown(self):
        if self.main_window:
            self.main_window.close()
        self.temp_dir.cleanup()
    
    def test_cross_annotation_pixel_perfect(self):
        """Test that cross annotation renders correctly."""
        player = ActionPlayer(self.main_window)
        output_image = player.play_from_file(self.actions_file)
        
        assert_images_equal_with_results(
            output_image,
            self.expected_image,
            test_name="cross_actions",
            save_results=True
        )
```

**File: `tests/fixtures/cross_actions-expected/cross-output.png`**
- Generate via running the app manually, or
- Use reference image generator utility

#### Step 10: Commit to Repository

```bash
git add tests/fixtures/crossmark_actions.json
git add tests/fixtures/cross_actions-expected/
git add tests/feature/test_cross_annotation.py
git commit -m "Add feature test for cross annotation"
```

#### Checklist for New Feature Test

- [ ] Test fixture directory created: `tests/fixtures/{name}_actions-expected/`
- [ ] Reference image saved: `tests/fixtures/{name}_actions-expected/{name}-output.png`
- [ ] Actions JSON created: `tests/fixtures/{name}_actions.json`
- [ ] Test class created: `tests/feature/test_{name}.py`
- [ ] Test runs and passes: `pytest tests/feature/test_{name}.py -v`
- [ ] HTML report shows PASS status with green badge
- [ ] Optional: Additional validation tests added
- [ ] Committed to repository

#### Common Pitfalls

1. **Naming mismatch**: JSON file name must match `test_name` parameter
   - File: `crossmark_actions.json` ✓
   - Parameter: `test_name="cross_actions"` ✓

2. **Missing expected image**: File must exist before test runs
   - Path: `tests/fixtures/cross_actions-expected/cross-output.png` ✓

3. **Wrong object IDs**: Action player uses 0-based indexing for objects
   - First object: `object_id: 0` ✓

4. **Absolute vs relative paths**: Use relative paths in JSON
   - `"path": "examples/document.pdf"` ✓
   - NOT `"path": "C:\\full\\path\\document.pdf"` ✗

5. **Forgetting to call `assert_images_equal_with_results()`**: Without this, test will pass but not verify output
   - Call this function in every pixel-perfect test ✓

### 14.11 Coordinate System Best Practices (Important)

**Problem:** Coordinates can be placed in wrong positions if the PDF coordinate system (bottom-left origin, y increases upward) is confused with the screen coordinate system (top-left origin, y increases downward).

**Root Cause:** PDF stores annotation positions in "PDF points" at 72 DPI with origin at page bottom-left. Screen rendering uses "viewport coordinates" at screen DPI with origin at top-left. Forgetting the coordinate transformation causes annotations to render at the wrong location.

#### Coordinate Systems Reference

**PDF Coordinate System (Storage in `objects.py`)**
- Origin: Bottom-left corner (0, 0)
- Y-axis: Increases upward ↑
- Storage: Points at 72 DPI
- Page height: Standard PDF = 792 points (11 inches)
- Transformation: `screen_y = (page_height_points - pdf_y) × DPI_scale`

**Screen Coordinate System (Rendering)**
- Origin: Top-left corner (0, 0)
- Y-axis: Increases downward ↓
- Rendering: Pixels at 300 DPI (or screen DPI)
- Canvas height: Varies with window/zoom
- Applied automatically by canvas rendering

#### Common Mistakes That Cause Coordinate Swaps

1. **Forgetting coordinate transformation** — Using PDF y-coordinate directly as screen y
2. **X/Y transposition** — Assigning x value to y parameter or vice versa
3. **Page height miscalculation** — Not subtracting from page height when converting
4. **DPI scale confusion** — Mixing 72 DPI (PDF) with 300 DPI (screen) without proper scaling
5. **Hard-coding screen coordinates** — Testing with rendered positions instead of PDF storage values

#### Best Practice: Never Calculate Test Coordinates Manually

**❌ DON'T** – Guessing coordinates from visual inspection:
```python
# WRONG: Looking at rendered image and trying to place crossmark at "Two"
# "Two looks like it's at pixel 100, 300" → Wrong absolute coordinates
"x": 100,
"y": 300,
```

**✅ DO** – Generate reference images from actual rendering:
```python
# 1. Use action_player to execute actions and render
from tests.recording.action_player import play_actions_from_file
play_actions_from_file(main_window, fixture_json, output_path=reference_image)

# 2. The output becomes the expected image
# 3. Test fixture contains PDF coordinates that produce that rendering
```

#### Why This Works

1. **ActionPlayer directly sets annotation coordinates** → `obj.x = x; obj.y = y` (PDF points)
2. **Canvas rendering applies transformation** → Internal coordinate conversion handles PDF→screen
3. **Reference image captures correct rendering** → Visual position is guaranteed by rendering engine
4. **Test fixture coordinates match rendering** → No manual calculation needed

#### Example: Document1 Crossmark Test

**File: `tests/fixtures/document1_crossmark.json`**
```json
{
  "actions": [
    {"type": "open_document", "path": "examples/document1.pdf"},
    {"type": "add_annotation", "annotation_type": "crossmark", "page": 0, "x": 65, "y": 606},
    {"type": "save_document"}
  ]
}
```

**Why these coordinates?**
- `x: 65, y: 606` are PDF points that produce the crossmark next to "Two" checkbox
- Not screen pixels or guesses from visual inspection
- Generated by rendering through ActionPlayer and capturing output
- Guaranteed to work because coordinates come from actual rendering

#### Workflow to Prevent Coordinate Mistakes

1. **Plan your test scenario** (e.g., "Add crossmark next to 'Two' checkbox")
2. **Run the app with RECORDING enabled** and manually place annotation where you want it
3. **Capture the recorded coordinates** from action_recorder output (printed to stdout)
4. **Use those recorded coordinates** in your fixture JSON
5. **Regenerate reference image** using ActionPlayer with those exact coordinates
6. **Test passes** because both fixture and reference come from the same rendering

#### Troubleshooting Coordinate Mismatches

| Symptom | Root Cause | Fix |
|---------|-----------|-----|
| Annotation appears at top-left | Y-coordinate treating PDF as screen | Check page height subtraction logic |
| Annotation too far down/up | DPI scale miscalculation (72 vs 300) | Verify scaling factor in coordinate transform |
| X position correct, Y inverted | Screen vs. PDF coordinate system swap | Use action_player to regenerate fixture |
| Test fails with visual mismatch | Coordinates guessed, not recorded | Re-run app with RECORDING, capture real coordinates |
| Different position on different PDFs | Page height not accounted for | Ensure `page_height_points` is PDF-specific, not hard-coded |

#### Prevention Checklist

- [ ] Never manually calculate coordinates from visual inspection
- [ ] Always use ActionPlayer to generate reference images from fixture coordinates
- [ ] Test fixture coordinates come from recording actual user placement
- [ ] Reference image is output from ActionPlayer with those exact coordinates
- [ ] If visual mismatch occurs, regenerate both fixture and reference from scratch
- [ ] Ensure test environment has consistent rendering (fonts, anti-aliasing, DPI)

### 14.12 Quick Workflow: Creating a Feature Test (Practical)

This is the **fast, practical workflow** for creating a new feature test. Use this when you want to quickly add a test by performing actions in the app.

#### The 4-Step Process

**Step 1: Tell the AI the test name**
```
I want to create a feature test called "document1-checkmark".
Follow the section "14.12 Quick Workflow: Creating a Feature Test (Practical)" of DESIGN.md to do that.
```

**Step 2: Get the command**
I will respond with a command to run that captures your actions:
```bash
SIGNER_RECORD_ACTIONS=1 python main.py -document examples/document1.pdf
```

**Step 3: Run the command and perform actions**
```bash
# Copy and run the command above
# Then in the app:
# 1. Open the document (already done via -document flag)
# 2. Perform your actions (add annotations, move, resize, etc.)
# 3. Save the file
# 4. Close the app
```

The saved files and recorded actions go to a temp location.

**Step 4: I create the test**
I will:
1. Extract the recorded actions → `tests/fixtures/{testname}_actions.json`
2. Take your saved output → `tests/fixtures/{testname}_actions-expected/{testname}-output.png`
3. Generate the complete test class → `tests/feature/test_{testname}.py`
4. Run all tests to verify they pass

**Result:** New feature test is ready with 5+ test methods, all passing ✅

#### Example

**You:** "Create feature test called 'arrow-north'"

**Me:** "Run this command:"
```bash
SIGNER_RECORD_ACTIONS=1 python main.py -document examples/document1.pdf -signature examples/signature.png
```

**You:** "Running... [performs actions in the app, saves as arrow-north-output.png, closes app]"

**Me:** [Creates everything automatically]
- ✅ `tests/fixtures/arrow_actions.json` (from recorded actions)
- ✅ `tests/fixtures/arrow_actions-expected/arrow-output.png` (your saved file)
- ✅ `tests/feature/test_arrow_annotation.py` (complete test class)
- ✅ All tests passing
- ✅ HTML report shows new test in summary

#### What Gets Created Automatically

All of these are generated from your one saved output file:

```
tests/
├── fixtures/
│   ├── arrow_actions.json                    # Recorded actions
│   └── arrow_actions-expected/
│       └── arrow-output.png                  # Your saved file (reference)
└── feature/
    └── test_arrow_annotation.py              # Complete test class with:
                                              # - test_generate_reference_image
                                              # - test_arrow_annotation_pixel_perfect
                                              # - test_arrow_actions_file_structure
                                              # - test_arrow_actions_include_required_types
                                              # - test_annotation_positions_are_valid
```

#### Key Points

- **One-time setup**: Just perform the workflow once
- **Minimal naming**: Tell me the test name, I handle the rest
- **Automatic validation**: Test is created ready to pass
- **HTML report ready**: New test appears in the report with status badge immediately
- **Extensible**: Easy to add more test methods later if needed

#### Next Feature Tests to Create Using This Method

1. Arrow annotation (N, NE, E, SE, S, SW, W, NW)
2. Text annotation (free text)
3. Date annotation
4. Time annotation
5. Color changes
6. Multi-page workflows
7. Duplicate annotations
8. Undo/redo functionality

### 14.12 Test Results Inspection and Diff Workflow

After running tests, results are automatically organized and a visual report is generated for inspection.

#### Directory Structure

```
tests/
├── test-results/
│   ├── document1_checkmark/
│   │   ├── document1-signed_actual.png         # Generated test output (named after expected file)
│   │   ├── document1-signed_expected.png       # Reference image
│   │   ├── document1-signed_diff.png           # Pixel-level diff visualization (all use expected base)
│   │   └── info.json                           # Test metadata: {"match": true/false}
│   ├── document1_crossmark/
│   │   ├── document1-signed_actual.png         # Actual output uses expected file's base name
│   │   ├── document1-signed_expected.png       # Reference baseline
│   │   ├── document1-signed_diff.png           # Diff also uses expected base name
│   │   └── info.json
│   └── report.html                             # Interactive HTML report
```

#### Pixel-Level Diff Visualization

The diff image provides visual comparison:
- **White pixels**: Identical between actual and expected images
- **Red pixels**: Different pixels detected

This enables quick visual inspection of exactly which pixels differ.

#### HTML Report Features

The auto-generated interactive HTML report includes:

- **Test Summary List** at the top with color-coded status badges:
  - **✓ PASS** (green) = Images match perfectly
  - **✗ FAIL** (red) = Images have differences (with mismatch %)
- **Clickable test names** - Click any test in the summary to jump directly to that test's detailed view
- **Test cards** showing:
  - Test name and status badge
  - Side-by-side comparison: Expected | Actual | Diff
  - Mismatch percentage for failed tests
- **Responsive layout** that adapts as more tests are added

#### Viewing Results

**Recommended: Open HTML report in browser**

After running tests, view results:
```bash
cd tests/test-results
# On Windows:
start report.html
# On macOS:
open report.html
# On Linux:
xdg-open report.html
```

**Alternative: Direct file browser**

Browse `tests/test-results/` to manually inspect:
- `{test_name}/{expected_base}_actual.png` - Generated output (named after expected image)
- `{test_name}/{expected_base}_expected.png` - Reference baseline
- `{test_name}/{expected_base}_diff.png` - Red/white pixel diff
- `{test_name}/info.json` - Pass/fail status
- `report.html` - Interactive comparison viewer

#### Accepting Changes

If you intentionally modified expected behavior and verified the output is correct:

1. Visually confirm the new output in the HTML report looks correct
2. Copy the actual output to become the new reference:
   ```bash
   # Copy actual to expected in tests/fixtures/
   cp tests/test-results/{test_name}/{test_name}_actual.png tests/fixtures/{test_name}_actions-expected/{test_name}-output.png
   ```
3. Re-run tests - they should now pass:
   ```bash
   pytest tests/feature/ -v
   ```

#### Implementation Details

Key functions in test infrastructure:

**image_comparison.py**:
- `compare_images()` - Compares two images pixel-by-pixel (exact match required); always generates diff for visualization
- `_create_diff_image()` - Creates white background with red pixels marking differences
- `assert_images_equal_with_results()` - Assertion with auto-save to test-results directory; enforces pixel-perfect matching

**test_results.py**:
- `get_test_results_dir()` - Returns/creates `tests/test-results/` directory
- `organize_test_output()` - Saves actual/expected/diff images named after expected filename base; stores match status in info.json
- `create_comparison_report()` - Generates HTML report from test-results directory
- `_generate_html_report()` - Renders HTML with summary list, test cards, and side-by-side viewer

**conftest.py**:
- Auto-generates HTML report after test session completes

#### Workflow Example

1. Run tests:
   ```bash
   pytest tests/feature/ -v
   ```
2. Open HTML report:
   ```bash
   start tests/test-results/report.html
   ```
3. Inspect results visually - color-coded badges show pass/fail instantly
4. Click test name to view detailed comparison (Expected | Actual | Diff)
5. If differences are intentional and verified as correct, copy actual to expected:
   ```bash
   cp tests/test-results/{test_name}/{test_name}_actual.png tests/fixtures/{test_name}_actions-expected/{test_name}-output.png
   ```
6. Re-run tests to confirm they pass

#### Tips

- **Status badges at a glance**: Green ✓ PASS / Red ✗ FAIL makes it easy to see test health instantly
- **Mismatch percentage**: Failed tests show exact percentage of pixels that differ
- **Diff is visual**: White/red visualization works on any image type and is immediately clear
- **Check diff.png**: Fastest way to spot pixel differences; white background with red marks
- **Selectable test names**: Test names in the report are selectable/copyable for easy reference
- **Vertical test list**: Tests display one per row for easy scanning
- **Persistent results**: Results persist across runs, useful for comparing history
- **Results not committed**: Add `tests/test-results/` to `.gitignore` (already present)

### 14.13 Naming Conventions and Common Pitfalls

#### Naming Convention Table

Follow these patterns when creating tests:

| Item | Pattern | Example |
|------|---------|---------|
| JSON file | `{name}_actions.json` | `crossmark_actions.json` |
| Test class | `Test{Name}` | `TestCrossAnnotation` |
| Test method | `test_{feature}_{type}` | `test_cross_annotation_pixel_perfect` |
| test_name param | `{name}_actions` | `test_name="cross_actions"` |
| Expected dir | `{name}_actions-expected/` | `cross_actions-expected/` |
| Output image | `{name}-output.png` | `cross-output.png` |
| Results appear in | `test-results/{name}_actions/` | `test-results/cross_actions/` |

#### Object IDs in Actions

Objects are tracked by creation order (0-based indexing):

- First added object: `object_id: 0`
- Second added object: `object_id: 1`
- Third added object: `object_id: 2`
- etc.

Example workflow:
```json
[
  {"type": "open_signature", "path": "examples/signature.png"},           // → object_id: 0 (signature)
  {"type": "add_annotation", "annotation_type": "cross", "page": 0},     // → object_id: 1 (cross)
  {"type": "move_annotation", "object_id": 1, "x": 200, "y": 300},       // Refers to cross (id 1)
  {"type": "add_annotation", "annotation_type": "checkmark", "page": 0}, // → object_id: 2 (checkmark)
  {"type": "resize_annotation", "object_id": 2, "width": 100, "height": 100}  // Refers to checkmark
]
```

#### Common Pitfalls and Solutions

| Problem | Solution |
|---------|----------|
| Reference image not created | Ensure `test_generate_reference_image()` test method runs first. This creates the expected baseline in fixtures/ |
| Image path errors in JSON | Use relative paths: `"examples/document.pdf"` ✓ <br> NOT absolute paths: `"C:\\Users\\...\\document.pdf"` ✗ |
| save_document action has no path | Specify absolute path in actions: `"path": "C:\\Users\\...\\output.png"` (agent automatically sets this) |
| Objects not found in move/resize | Check object_id matches creation order. Count which object was created (0-indexed) |
| GUI not updating after actions | Add `QApplication.processEvents()` after `play_actions_from_file()` to flush pending events |
| Test skipped with "Actions file not found" | Ensure `{name}_actions.json` exists in `tests/fixtures/` |
| Test skipped with "Reference image not found" | Run `test_generate_reference_image()` first to create baseline in `tests/fixtures/{name}_actions-expected/` |
| Mismatch percentage high | Check that your expected image is correct. If yes, and changes are intentional, copy actual to expected. If no, debug app rendering |

#### Best Practices

✓ Always add both `test_generate_reference_image()` and pixel-perfect test methods  
✓ Use `document1.pdf` for consistency with existing tests  
✓ Include signature first (object_id: 0) before adding annotations  
✓ Use absolute paths when saving test outputs (agent handles this)  
✓ Run full test suite after adding new tests: `pytest tests/ -q`  
✓ Check HTML report for visual verification before committing  
✓ Keep fixture directory structure organized by test name  
✓ Commit fixture JSON files and images to repository  
✓ Do NOT commit test-results/ directory (transient, regenerated each run)  

#### Debugging Test Failures

If a pixel-perfect test fails:

1. Open `tests/test-results/report.html` in browser
2. Find your test in the summary list (red ✗ FAIL badge)
3. Click test name to jump to detailed view
4. Compare Expected vs Actual images side-by-side
5. Check Diff image (red pixels show differences)
6. Determine if:
   - **App code is wrong**: Fix implementation, re-run
   - **Changes are intentional**: Copy actual to expected, re-run
   - **Rendering mismatch**: Investigate DPI settings, font rendering, or timing; may need to regenerate reference

#### Next Feature Tests to Add

Based on REQUIREMENTS.md and DESIGN.md scope:

1. **Arrow annotations**: Create one test for arrow direction (e.g., N). Use as template for remaining 7 directions (NE, E, SE, S, SW, W, NW)
2. **Text annotations**: Create separate tests for free text, current date, current time, date+time
3. **Color changes**: Test changing annotation colors before save
4. **Multi-page workflows**: Test placing annotations on different pages, verifying independence
5. **Advanced workflows**: Duplicate, delete, undo/redo, mixed annotations

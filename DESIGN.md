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
- Support annotations (checkmark, cross, 8-direction arrows, text) with color + move + scale.
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
    - Cross
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
  - Cross
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

### 5.9 CLI Parameters
- `-document <path>`: initial document to load (any supported format: PDF, Word, ODT, or image).
- `-signature <path>`: initial signature to load (image file, PNG preferred).
- If `-signature` is provided with `-document`, add signature annotation immediately after load.
- If `-signature` is omitted, do not auto-add annotations on document open.

Example startup:
- `Signer.exe -document examples/document.pdf -signature examples/signature.png`
- `Signer.exe -document examples/document.docx -signature examples/signature.png`

### 5.10 File Naming (All Formats)
Default save name (applies to all export formats):
- Input `document.pdf` => `document-p<page>-signed.{ext}` for multi-page clarity (example: `document-p3-signed.jpg`)
- If conflict exists, append numeric suffix (`-signed-1.jpg`, etc.)
- Version 1.2.10 unifies this across all formats via "Save As" dialog

## 6. Error Handling
- Missing/unreadable PDF: block canvas interaction, show clear message.
- Missing signature annotation: allow document load, prompt user to add a signature annotation before save.
- Corrupt image/PDF: show validation error and keep app responsive.
- Save failure (permissions/locked file): show retryable error.

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
  - verify toolbar order: Open Document, Add Annotation, Save JPG,
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
  - transparency preserved in composition before JPG flattening.

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

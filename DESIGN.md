# DESIGN

## 1. Goal
Build a small Windows desktop app to place a scanned signature (transparent image) on top of a PDF page and export the result as a JPG, with minimal manual steps.

## 1.1 Example Assets (Current Workspace)
- `examples/document.pdf` (sample one-page input document)
- `examples/signature.png` (sample signature image)
- `examples/signature.xcf` (GIMP source; not directly supported for import)
- `examples/document.odt` (non-PDF sample; expected validation failure)

## 2. Scope (v1)
- Open a PDF document.
- Open/select a signature image (PNG preferred for transparency).
- Show document and signature overlay in one canvas.
- Drag signature to final position.
- Resize signature (scale up/down) before saving by dragging boundary handles.
- Save merged output as JPG.
- Support startup parameters:
  - `-document <path>`
  - `-signature <path>`
- If signature is not provided, reuse last signature file.
- Default output file name: `<documentname>-signed.jpg`.
- Document view fits window (no zoom controls in v1).
- Default signature position: 80% from top, horizontally centered.
- Support multi-page PDFs: place objects on any page.
- Add paging controls in toolbar and keyboard support (`PageUp`, `PageDown`, `Home`, `End`).
- Show blue boundary around selected signature/annotation while editing.
- Change mouse cursor to move arrows when hovering draggable objects.
- Use toolbar-first UI with large action buttons instead of hierarchical menu for primary actions.
- Support annotations (checkmark, cross, 8-direction arrows, text) with color + move + scale.

## 3. Non-Goals (v1)
- Digital certificate signing.
- OCR or PDF editing beyond image export.
- Rotation UI for signature.
- Freehand drawing annotations.
- Advanced typography controls (font families, rich text editing) for text annotations.

## 4. UX Design
### Main Window
- Top toolbar (large buttons):
  - Open Document
  - Open Signature
  - Save JPG
  - Previous Page / Next Page
  - Annotation picker (dropdown):
    - Checkmark
    - Cross
    - Arrow N/NE/E/SE/S/SW/W/NW
    - Text ▶ Free text / Current date / Current time / Current date & time
    - Signature ▶ From file… / Recent (up to 10 LRU files)
- Terminology: primary actions are provided as Toolbar buttons (faster navigation). They may be mirrored in the menu for compatibility.
- Central canvas:
  - Background: rendered current PDF page (fit-to-window).
  - Foreground: draggable/scalable objects (signature + annotations).
  - Blue boundary for selected object.
- Status bar:
  - Current document path.
  - Current signature path.
  - Current page number / total pages.
  - Selected object coordinates/size.

### Typical Flow
1. Start app.
2. Open document (or auto-load from `-document`).
3. Auto-load signature from `-signature` or last used signature.
4. Navigate to page (toolbar or keyboard shortcuts).
5. Drag/scale signature to desired location.
6. Optionally add and adjust annotation objects.
7. Save active page to JPG.

## 5. Functional Design
### 5.1 Input Handling
- Validate file existence and extensions.
- PDF input: support multi-page PDFs.
- Signature input: PNG (for transparency).
- Unsupported signature formats (e.g., `.xcf`) should trigger a clear validation message.

### 5.2 Rendering Pipeline
1. Render active PDF page to bitmap at fixed internal DPI: **300 DPI**.
2. Scale page bitmap to fit viewport while preserving aspect ratio.
3. Render object layer for active page (signature + annotations) in viewport coordinates.
4. Support object move and scale (boundary-handle drag).
5. On save (active page):
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
- `x = (page_width - signature_width) / 2`
- `y = 0.8 * page_height - signature_height / 2`
- Clamp to page bounds.

### 5.5 Object Interaction
- Hover on draggable object: cursor changes to move arrows.
- Selected object shows blue boundary.
- Scale method: dragging object boundary handles.

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

### 5.7 Persistence
Use a lightweight local config file (JSON) in user profile (e.g., `%APPDATA%/Signer/config.json`) storing:
- `lastSignaturePath`
- `recentSignaturePaths` (up to 10, ordered by LRU)
- `lastOpenDocumentPath` (optional)
- `lastSaveDirectory` (optional)

### 5.8 CLI Parameters
- `-document <path>`: initial document to load.
- `-signature <path>`: initial signature to load.
- If only `-document` is provided, use `lastSignaturePath`.

Example startup:
- `Signer.exe -document examples/document.pdf -signature examples/signature.png`

### 5.9 File Naming
Default save name:
- Input `document.pdf` => `document-p<page>-signed.jpg` for multi-page clarity (example: `document-p3-signed.jpg`)
- If conflict exists, append numeric suffix (`-signed-1.jpg`, etc.)

## 6. Error Handling
- Missing/unreadable PDF: block canvas interaction, show clear message.
- Missing signature: allow document load, prompt to open signature before save.
- Corrupt image/PDF: show validation error and keep app responsive.
- Save failure (permissions/locked file): show retryable error.

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

## Option A (Recommended): Python + PySide6 + PyMuPDF + Pillow
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

## 11. Test Strategy (Design-Level)
- Unit tests:
  - default filename generation,
  - position math and bounds clamping,
  - settings persistence behavior.
- Manual functional tests:
  - startup with/without CLI args,
  - startup using sample assets (`examples/document.pdf` + `examples/signature.png`),
  - verify unsupported format handling using `examples/signature.xcf`,
  - verify invalid document handling using `examples/document.odt`,
  - verify page navigation via toolbar and keys (`PageUp`, `PageDown`, `Home`, `End`),
  - verify per-page object persistence when switching pages,
  - verify cursor change on hover and blue boundary on selection,
  - verify boundary-handle scaling behavior,
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

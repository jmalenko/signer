# DESIGN

## 1. Goal
Build a small Windows desktop app to place a scanned signature (transparent image) on top of a PDF page and export the result as a JPG, with minimal manual steps.

## 1.1 Example Assets (Current Workspace)
- `examples/document.pdf` (sample one-page input document)
- `examples/signature.png` (sample signature image)

## 2. Scope (v1)
- Open a PDF document.
- Open/select a signature image (PNG preferred for transparency).
- Show document and signature overlay in one canvas.
- Drag signature to final position.
- Resize signature (scale up/down) before saving.
- Save merged output as JPG.
- Support startup parameters:
  - `-document <path>`
  - `-signature <path>`
- If signature is not provided, reuse last signature file.
- Default output file name: `<documentname>-signed.jpg`.
- Document view fits window (no zoom controls in v1).
- Default signature position: 80% from top, horizontally centered.

## 3. Non-Goals (v1)
- Multi-page signing UX.
- Digital certificate signing.
- OCR or PDF editing beyond image export.
- Rotation UI for signature.

## 4. UX Design
### Main Window
- Top menu:
  - File > Open Document
  - File > Open Signature
  - File > Save Document with Signature
  - File > Exit
- Central canvas:
  - Background: rendered first page of PDF (fit-to-window).
  - Foreground: draggable signature image.
- Status bar:
  - Current document path.
  - Current signature path.
  - Cursor/signature coordinates (optional, useful for support).

### Typical Flow
1. Start app.
2. Open document (or auto-load from `-document`).
3. Auto-load signature from `-signature` or last used signature.
4. Drag signature to desired location.
5. Save merged JPG.

## 5. Functional Design
### 5.1 Input Handling
- Validate file existence and extensions.
- PDF input: assume one-page PDFs in v1.
- Signature input: PNG (for transparency).
- Unsupported signature formats (e.g., `.xcf`) should trigger a clear validation message.

### 5.2 Rendering Pipeline
1. Render PDF page to bitmap at fixed internal DPI: **300 DPI**.
2. Scale bitmap to fit viewport while preserving aspect ratio.
3. Place signature overlay in viewport coordinates.
4. Allow signature scale adjustment (while preserving signature aspect ratio).
5. On save:
   - Convert signature viewport coordinates back to source bitmap coordinates.
   - Composite signature alpha over page bitmap.
   - Export JPG.

### 5.3 Default Placement
- `x = (page_width - signature_width) / 2`
- `y = 0.8 * page_height - signature_height / 2`
- Clamp to page bounds.

### 5.4 Persistence
Use a lightweight local config file (JSON) in user profile (e.g., `%APPDATA%/Signer/config.json`) storing:
- `lastSignaturePath`
- `lastOpenDocumentPath` (optional)
- `lastSaveDirectory` (optional)

### 5.5 CLI Parameters
- `-document <path>`: initial document to load.
- `-signature <path>`: initial signature to load.
- If only `-document` is provided, use `lastSignaturePath`.

Example startup:
- `Signer.exe -document examples/document.pdf -signature examples/signature.png`

### 5.6 File Naming
Default save name:
- Input `document.pdf` => `document-signed.jpg`
- If conflict exists, append numeric suffix (`-signed-1.jpg`, etc.)

## 6. Error Handling
- Missing/unreadable PDF: block canvas interaction, show clear message.
- Missing signature: allow document load, prompt to open signature before save.
- Corrupt image/PDF: show validation error and keep app responsive.
- Save failure (permissions/locked file): show retryable error.

## 7. Architecture
### Modules
- `ui/` window, menu, canvas, drag behavior.
- `core/pdf_renderer` PDF -> bitmap.
- `core/compositor` signature overlay + JPG export.
- `core/settings` load/save user config.
- `core/cli` parse startup arguments.

### Data Model
- `DocumentState`: file path, rendered bitmap size.
- `SignatureState`: path, image size, position.
- `SessionState`: output path defaults, dirty flag.

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
- Input documents are assumed to be one-page PDFs.
- PDF render quality is fixed to **300 DPI**.
- Signature scaling is included in v1.
- Initial product name is **Signer** (can be renamed before release).
- Code signing is out of scope for v1 packaging.

## Tool Decision
Use **Option A** for v1 due to shortest implementation path and low risk for required features.

## 10. Performance and Quality Targets
- Open and render first PDF page in < 1 second for common office documents.
- Drag signature with smooth interaction (no visible lag).
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
  - load invalid files,
  - drag and save accuracy,
  - transparency preserved in composition before JPG flattening.

## 12. Recommended Workflow Improvements vs GIMP
- One-step startup with saved signature.
- Fit-to-window preview with direct drag positioning.
- One-click export to predictable filename.

This removes repetitive manual steps (open layers, align, export settings) and makes signing routine documents significantly faster.

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

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
  - font point sizes are converted to pixels at the document rendering DPI
  - the initial boundary is calculated from Qt font metrics to fit every line without cropping
  - toolbar size changes recalculate the text boundary from font metrics
  - boundary resizing derives the largest whole-point font size that fits and refreshes the toolbar; non-proportional bounds may contain extra space but do not crop text
  - live canvas resizing refits the text boundary before each repaint, avoiding transient mouse-sized bounds; resize history uses the same path
  - no wrapping
  - newline entry via Ctrl+Enter in text editor dialog
- Toolbar property labels omit measurement units; tooltips describe units where relevant.

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
- Color: green
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

On brief/non-fatal errors that don't warrant a modal dialog (e.g. directory link no longer
exists), use the same toast widget styled red instead of green, and do **not** start the
auto-dismiss timer — the user must close it manually via the X button. This signals "needs
acknowledgment" without blocking the window like a modal dialog would.

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
| **Paste** (Ctrl+V) | Paste copied annotations at their copy-time coordinates; applies the 20px duplicate offset on the same page and no offset on a different page |
| **Duplicate** (Ctrl+D) | Create copies of all selected, offset by 20px; single undo unit |
| **Color change** | Apply color to all selected annotation types that support it |

**Visual Feedback**:
- Single selection: Blue boundary around selected annotation (existing)
- Multi-selection: Blue boundary around all selected annotations; resize handles shown only on primary selected object

**Clipboard Format (JSON)**:
Annotations are serialized as a JSON array when copied/cut, preserving all object properties including type, position, size, color, and content.
Serialization happens at copy time, so moving the source annotations afterward does not change the pasted coordinates.

When pasted:
- **Same page**: The same 20-pixel offset used by Duplicate is applied to avoid exact overlap with originals
- **Different page**: No offset applied (already distinct location)

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

### 5.15 Undo/Redo History (v1.2.21)

The application maintains unlimited undo/redo history during a document session. History is not persisted to disk; it is cleared when a new document is opened or the application closes. Consecutive move/resize operations on the same annotation are coalesced into a single history entry.

### 5.16 Extended Annotation Types & Properties (v1.2.22)

#### New Annotation Types

**Line Annotation**:
- Simple straight line drawn from start to end point
- Properties: color, line width (width property)
- Free corner dragging: drag either endpoint past the opposite endpoint to change line direction

**Arrow Annotation**:
- Line with an arrowhead at the end
- Subtypes: Generic (direction auto-calculated) + 8 Directional (E, SE, S, SW, W, NW, N, NE)
- Arrow order in menu: East, South-East, South, South-West, West, North-West, North, North-East
- Generic arrow: arrowhead direction determined by line angle (start→end)
- Directional arrows: arrowhead fixed to specified direction; line can extend any direction
- Properties: color, line width (width property)
- Free corner dragging: drag either endpoint past the opposite endpoint to change line direction; generic arrow updates direction accordingly

**Rectangle & Square Annotation**:
- Filled outline rectangle (no fill, stroke only)
- Shape detection: automatic during creation based on aspect ratio
  - If height-width difference ≤ ±10%: created as **square**
  - Otherwise: created as **rectangle**
- Shape override: holding **Ctrl key during creation** forces creation as **rectangle** regardless of aspect ratio
- Properties: color, line width (width property)
- Free corner dragging: corners swap when dragged past opposite corner; shape type (square/rectangle) is re-evaluated on resize

**Ellipse & Circle Annotation**:
- Filled outline ellipse/circle (no fill, stroke only)
- Shape detection: automatic during creation based on aspect ratio
  - If height-width difference ≤ ±10%: created as **circle**
  - Otherwise: created as **ellipse**
- Shape override: holding **Ctrl key during creation** forces creation as **ellipse** regardless of aspect ratio
- Properties: color, line width (width property)
- Free corner dragging: corners swap when dragged past opposite corner; shape type (circle/ellipse) is re-evaluated on resize

**Image Annotation**:
- User-provided image file (all formats supported; scaled to fit bounding box while preserving aspect ratio)
- Loading: File dialog to select image; recent 10 images tracked in submenu for quick access
- Properties: No color or width controls (hidden/disabled for this type)
- Free corner dragging: supported; aspect ratio preserved during resize

#### Extended Properties for All Types

**Line Width Property** (applies to: Line, Arrow, Rectangle, Ellipse, Checkmark, Crossmark):
- Unit: points (1 point = 1/72 inch)
- Range: 0.5 to 16 points
- Default: 1.5 points
- UI Control: Toolbar spinner showing value in points (free-form, 0.5 point step)
- Keyboard control: `[` to decrease, `]` to increase — steps through the fixed list
  `LINE_WIDTH_STEPS_PT` = (0.5, 0.75, 1, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10, 12, 16); clamped at the
  ends (no wraparound), matching the 0.5-16 point range above. Current value snaps to the
  nearest step in the press direction if it isn't already on the list.
- Context-sensitive: visible and enabled only for vector annotation types
- Excluded from: Text, Signature/Image annotations

**Font Size Property** (applies to: Text annotations only):
- Unit: points (1 point = 1/72 inch)
- Range: 6 to 72 points
- Default: 11 points
- UI Control: Toolbar spinner showing value in points (free-form, 1 point step)
- Keyboard control: `[` to decrease, `]` to increase — steps through the fixed list
  `FONT_SIZE_STEPS_PT` = (6, 7, 8, 9, 10, 11, 12, 14, 16, 18, 20, 24, 28, 32, 36, 40, 48, 54, 60,
  66, 72); clamped at the ends (no wraparound). Current value snaps to the nearest step in the
  press direction if it isn't already on the list.
- Resize behavior: When text bounding box is resized, font size scales proportionally
  - Calculation: `new_font_size = old_font_size × (new_height / old_height)`
- Context-sensitive: visible and enabled only for Text annotations

**Font Family Property** (applies to: Text annotations only):
- Source: System fonts via Qt QFontComboBox
- Default: System default font (usually Arial or Liberation Sans)
- UI Control: Toolbar combo box with all available system fonts
- Context-sensitive: visible and enabled only for Text annotations

#### Updated Annotation Menu Structure

```
Annotations Menu
├── Checkmark
├── Crossmark
├── Line
├── Arrow
│   ├── Arrow (generic)
│   ├── ────────────── (separator)
│   ├── Arrow East
│   ├── Arrow South-East
│   ├── Arrow South
│   ├── Arrow South-West
│   ├── Arrow West
│   ├── Arrow North-West
│   ├── Arrow North
│   └── Arrow North-East
├── Rectangle / Square
├── Ellipse / Circle
├── Text
└── Signature / Image
    ├── Signature
    ├── ────────────── (separator)
    └── Load Image...
    └── ────────────── (separator)
    └── Recent Images
        ├── image1.png
        ├── image2.jpg
        └── ... (up to 10 recent entries)
```

#### UI Context-Sensitivity

Control visibility and enable/disable state based on:
1. Whether document is open
2. Whether annotation is selected
3. Type of selected annotation

**Toolbar Control Visibility Map**:

| Control | Checkmark | Crossmark | Line | Arrow | Rectangle | Ellipse | Text | Sig/Image |
|---------|-----------|-----------|------|-------|-----------|---------|------|-----------|
| Color | ✓ enabled | ✓ enabled | ✓ enabled | ✓ enabled | ✓ enabled | ✓ enabled | ✓ enabled | ✗ hidden |
| Width spinner | ✓ enabled | ✓ enabled | ✓ enabled | ✓ enabled | ✓ enabled | ✓ enabled | ✗ hidden | ✗ hidden |
| Font size spinner | ✗ hidden | ✗ hidden | ✗ hidden | ✗ hidden | ✗ hidden | ✗ hidden | ✓ enabled | ✗ hidden |
| Font family combo | ✗ hidden | ✗ hidden | ✗ hidden | ✗ hidden | ✗ hidden | ✗ hidden | ✓ enabled | ✗ hidden |

**Button State**:
- "Add Annotation" button: **disabled** when no document open; **enabled** when document is open
- "Save JPG" button: **disabled** when no document open; **enabled** when document is open

#### Free Corner Dragging Behavior

**Applies to**: Line, Arrow, Rectangle, Ellipse (and existing Checkmark, Crossmark)

**Not applies to**: Text, Signature/Image annotations (only support move/scale as single unit)

**Behavior**:
- User drags any corner/endpoint past the opposite corner → coordinates swap
- Example 1 (Line): Line from (100, 100) to (200, 200), drag end point to (50, 50) → line is now from (200, 200) to (50, 50)
- Example 2 (Arrow generic): Arrow pointing SE (from TL to BR), drag BR corner above/left of TL → arrow now points NE (corners swapped)
- Example 3 (Rectangle): Rectangle with corners at (100, 100) and (200, 200), drag BR corner to (50, 50) → corners are now (200, 200) and (50, 50), effectively swapping
- Shape type re-evaluation: After resize, Rectangle/Ellipse types are re-checked:
  - Rectangle: if height-width difference now ≤ ±10%, it becomes square (visual only, remains "rectangle" type in data)
  - Ellipse: if height-width difference now ≤ ±10%, it becomes circle (visual only, remains "ellipse" type in data)

#### Recent Images Tracking

**Configuration**:
- Store in `config.json` as `recentImagePaths: List[str]`
- Maximum entries: 10
- Persistence: Across application sessions
- No explicit clear option in UI (user can edit settings file if needed)

**Behavior**:
- When image is loaded via "Load Image...", its path is prepended to recent list
- If path already in list, move to front (LRU ordering)
- List limited to most recent 10 entries
- Recent images submenu populated from this list
- Clicking recent image immediately loads it without dialog

#### Serialization Format (v1.2.22)

All annotations include JSON format version identifier:
```json
{
  "version": "1.2.22",
  "annotations": [
    {
      "id": 0,
      "type": "line|arrow|rectangle|ellipse|image|text|checkmark|crossmark|signature",
      "x": 100,
      "y": 100,
      "width": 50,
      "height": 50,
      "color": "#FF0000",
      "line_width": 1.5,
      "arrow_subtype": "generic|east|southeast|south|southwest|west|northwest|north|northeast",
      "font_size": 11.0,
      "font_family": "Arial",
      "text": "...",
      "image_path": "...",
      "image_data": "..."
    }
  ]
}
```

**Backward Compatibility**:
- Old format (without `version` field or with `version < "1.2.22"`) loads successfully
- Missing properties use defaults (line_width: 1.5, font_size: 11, font_family: system default)
- Export respects old annotations (width property preserved if present, calculated on load if absent)

### 5.17 Drag-and-Drop and Document Open/Save Flow (v1.2.25)

#### Drag-and-Drop Implementation

**Drop Target Registration**:
- Main canvas widget has drop acceptance enabled via `setAcceptDrops(True)`
- Accepted MIME types: `text/uri-list` (file paths via OS drag-and-drop)

**File Type Detection**:
- Extract file extension from dropped file path
- Check against supported formats:
  - **Small images**: PNG, JPG, JPEG, BMP (if dimensions fit A6 at 300 DPI)
  - **Documents**: PDF, JPG, JPEG, PNG, BMP (if exceeds A6 size or is PDF)

**Size Threshold Calculation**:
- A6 paper: 105mm × 148mm (4.1" × 5.8")
- At 300 DPI: 1240 pixels × 1748 pixels
- A6-equivalent dimension: `max(width, height) ≤ 1748`
  - Interpretation: Image fits on A6 in any orientation (portrait or landscape)
- **Small image**: Both dimensions ≤ 1748 (fits A6 in any rotation)
- **Big image**: Either dimension > 1748 (exceeds A6 in at least one orientation)

**Drop Handlers**:

*Case 1: Small Image + Active Document*
- Load image file via PIL
- Validate: file not corrupted, format supported
- Create Signature/Image annotation at drop position:
  - `x, y` = drop coordinates in document space (convert from viewport coordinates)
  - Size: scale image to fit ~A6 size (~1240×1748px) while preserving aspect ratio
  - Color: not applicable (hidden for Signature/Image type)
  - Line width: not applicable (hidden for Signature/Image type)
- Add annotation to current page's object list
- Refresh canvas rendering
- Action: Record as `add_annotation` for undo/redo (not for action recording)

*Case 2: Small Image + No Active Document*
- Show error dialog: "Cannot drop image: No document is currently open. Please open or create a document first."
- Do not create annotation
- Focus window

*Case 3: Small Image + Corrupted/Unsupported*
- Catch PIL.Image.open() exception
- Show error dialog: "Cannot load image: Unsupported format or corrupted file. Supported formats: PNG, JPG, JPEG, BMP."
- Do not create annotation

*Case 4: Big Image or PDF + Active Document with Unsaved Changes*
- Detect unsaved changes via `DocumentState.dirty` flag
- Show save prompt dialog (modal, blocks interaction):
  ```
  Title: "Save changes to 'document-name.pdf'?"
  Message: "Save changes before opening the dropped file?"
  Buttons: [Save] [Don't Save] [Cancel]
  Default button: Cancel
  ```
- **Save button**: Call `save_document()` with last-used format/path, then load dropped file
- **Don't Save button**: Discard `DocumentState.dirty` flag, load dropped file immediately
- **Cancel button**: Abort drop operation; keep current document in current state
- If save fails: show error and return to document without loading dropped file

*Case 5: Big Image or PDF + Active Document without Unsaved Changes*
- Load dropped file immediately via `load_document()` (same path as File → Open)
- Clear page-scoped annotations on load (or preserve if document is extension of previous)
- Render first page
- Clear undo/redo stack (new document session)
- Update window title with new filename

*Case 6: Big Image or PDF + No Active Document*
- Load dropped file immediately without save prompt
- Same behavior as Case 5

*Case 7: Invalid/Corrupted File*
- Catch exception during `load_document()` 
- Show error dialog: "Cannot open file: Invalid or corrupted file."
- Keep current document open (or remain in no-document state)

*Case 8: File Permissions Error (access denied)*
- Catch `PermissionError` or OS-level access exception
- Show error dialog: "Cannot open file: Access denied. Please ensure the file is not in use."

#### Menu-Triggered Open (File → Open)

**Behavior**:
- Same save prompt flow as drag-and-drop (Cases 4-5)
- File picker (native Windows dialog):
  - Filter: "All Supported Files (*.pdf, *.jpg, *.jpeg, *.png, *.bmp)"
  - Allows user to select any file in the filter
- After selection, follow drag-and-drop logic for that file type (Cases 1-7)

**Note**: Unlike drag-and-drop, menu-triggered open can handle small images as documents (they open as single-page documents via the big image path).

#### Save Prompt Dialog

**Reusable Component** (used for both drag-drop and menu-open):
```python
class SavePromptDialog:
    def __init__(self, filename: str):
        # Dialog with title, message, three buttons
        # Default button: Cancel
        # Return value: "save" | "dont_save" | "cancel"
    
    def exec_() -> str:
        # Modal execution, blocks interaction
        pass
```

**Dialog Content**:
- Title: `f"Save changes to '{filename}'?"`
- Message: "Save changes before opening a new document?"
- Buttons: `[Save]` `[Don't Save]` `[Cancel]`
- Default: Cancel button has keyboard focus

**Integration Points**:
- `app.open_document_with_prompt()` - reusable method calling save prompt + load
- Used by: File menu → Open, drag-and-drop handlers

#### New Document State Management

**Dirty Flag**:
- Set to `True` when annotation is added/modified/deleted
- Set to `False` after successful save or new document load
- Reset to `False` when opening new document (via File → Open or drag-drop)

**Undo/Redo Stacks**:
- Cleared when new document is opened
- Cleared when application closes
- Not persisted to disk

## 6. Error Handling
- Missing/unreadable document: block canvas interaction, show clear error message.
- Missing signature annotation: allow document load, prompt user to add a signature annotation before save.
- Corrupt image/document: show validation error and keep app responsive.
- Save failure (permissions/locked file/disk full): show modal error dialog with specific cause and recovery suggestions; offer retry or cancel.
- Invalid export path (bad characters, too long): validate before export and show error with corrected suggestion.
- Directory link failure (path no longer exists): show a red, manually-dismissed toast notification "Unable to open directory"; do not crash.
- Partial export failure (multi-page): stop process, show error listing failed pages and reason, offer retry or cancel.

### Error Dialog vs Notification Toast
- **Modal error dialogs** (block interaction): export failures, validation errors, missing dependencies
- **Auto-dismissing toasts** (non-intrusive, green): success notifications
- **Manually-dismissed toasts** (non-intrusive but red): brief/non-fatal errors that don't need a blocking dialog (e.g. directory link failure); user must click the X button to close them

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

## 8. Multi-Format Document Support Integration
For Word and ODT support, the app integrates with LibreOffice:
- **LibreOffice** (headless): Converts Word and ODT to temporary PDF for rendering
- **PDF Rendering**: PDF pages (including converted docs) are rendered to images at 300 DPI
- **Image Handling**: Direct image loading and export for JPG, PNG, BMP, and other formats

LibreOffice path resolution:
1. Check settings file for user-configured path
2. Search system PATH
3. Show error if not found with guidance on manual configuration

## 9. Performance and Quality Targets
- Open and render current PDF page in < 1 second for common office documents.
- Drag/scale objects with smooth interaction (no visible lag).
- Export quality suitable for typical print/email workflows.
- Window aspect ratio should adapt to document aspect ratio while keeping the full toolbar visible.
- Before a document is loaded, size the window using portrait A4 dimensions at the
  internal 300 DPI rendering resolution.
- Derive vertical window chrome from the fixed toolbar height. The remaining canvas
  follows the document aspect ratio so an A4 page has no avoidable bars above or below.

---

## Testing

See [TESTING.md](TESTING.md) for comprehensive testing documentation including:
- How to run unit and feature tests
- LibreOffice configuration for multi-format tests  
- Test infrastructure overview
- Action recording system for creating new tests

## 9. Distribution Builds

### Building the Executable with PyInstaller

To create `signer.exe` from the Python source code:

```bash
# Build a single-file executable (recommended for portable distribution)
.venv\Scripts\python -m PyInstaller --noconfirm --log-level INFO --onefile --windowed --name signer --icon signer/resources/signer.ico --add-data "signer/resources:signer/resources" main.py
```

This creates:
- `dist/signer.exe` — Single executable file containing all dependencies, resources, and icon
- `build/` — Temporary build files (can be deleted)
- `signer.spec` — PyInstaller spec file (for rebuilding)

**Output location**: `dist/signer.exe`

**For development/testing**: Run directly from source without building
```bash
python main.py
# or with arguments:
python main.py -document examples/document.pdf -signature examples/signature.png
```

**VS Code tasks**:
- `Run Signer` — Runs the app from source code
- `Run Signer (examples)` — Runs with example files
- `Build signer.exe (onefile)` — Creates the PyInstaller executable in `dist/signer.exe` with icon and resources

### PyInstaller Configuration

Key flags used:
- `--onefile` — Creates single executable (not directory with dependencies)
- `--windowed` — GUI app (no console window)
- `--name signer` — Output filename (`signer.exe`)
- `--icon signer/resources/signer.ico` — Embeds the application icon in the executable (displays in taskbar, window title, and file icon)
- `--add-data "signer/resources:signer/resources"` — Bundles the resources directory (icons, images) into the executable for runtime access via `sys._MEIPASS`
- `--noconfirm` — Don't ask before overwriting
- `--log-level INFO` — Show build progress
- `main.py` — Entry point file

### Portable Build

After building the executable (see "Building the Executable with PyInstaller" above):

1. Copy `dist\signer.exe` to any directory on a portable medium (USB drive, external disk, etc.)
2. Optionally, copy or create an empty `config.json` file in the same directory to customize settings

When the user runs `signer.exe` on any machine:
- If `config.json` exists in the app directory, it will be used (portable mode)
- If not, `config.json` will be auto-created in `%APPDATA%/Signer/` on first save (installed mode)


### Edge Cases

- **Both locations exist**: Portable mode takes precedence (app directory checked first)
- **No write permissions to app directory**: AppData fallback ensures portability on read-only installations (e.g., network share)
- **AppData unavailable**: Should not occur on Windows; error handling defers to existing config error handling
- **Corrupted config**: Handled by existing error handling; mode detection unaffected

---

## 10. User Installation & Configuration

### System Requirements

- **Windows**: 7 or later
- **macOS**: 10.13 or later
- **Linux**: Ubuntu 18.04+, Fedora 28+, or equivalent

For Word (.docx/.doc) and ODT file support, LibreOffice is optional.

### Running Signer

Double-click to launch the app:
- Use menu: File → Open Document to load a PDF, image, or Word/ODT file
- Menu: Annotations to add signatures and marks
- Menu: File → Save As... to export as JPG, PNG, PDF, TIFF, or BMP

### Optional: LibreOffice for Word/ODT Support

To open Word (.docx/.doc) and OpenDocument (.odt) files, install LibreOffice:

```bash
brew install libreoffice                # macOS
sudo apt install libreoffice            # Ubuntu/Debian
choco install libreoffice               # Windows (via Chocolatey)
# Or download from https://www.libreoffice.org/download/
```

The app auto-detects LibreOffice. If installed in a custom location, manually set in config.json:
```json
{
  "libreoffice_path": "/path/to/soffice"
}
```

### Settings & Configuration

Configuration is stored in:
- **macOS**: `~/Library/Application Support/Signer/config.json`
- **Linux**: `~/.config/Signer/config.json`
- **Windows**: `%APPDATA%\Signer\config.json`
- **Portable mode**: `./config.json` in app directory (takes precedence if exists)

Settings persist: recent documents, signatures, colors, export quality, LibreOffice path.

---

## 10.1 For Developers

### Setup

**Prerequisites**: Python 3.10+, pip, git

```bash
git clone <repository-url>
cd signer

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate              # macOS/Linux
# .venv\Scripts\activate               # Windows

# Install dependencies
pip install -r requirements.txt
```

### Running Tests

```bash
pytest                                  # Run all tests
pytest -v                              # Verbose output
pytest --cov=signer --cov-report=html  # With coverage
```

See [TESTING.md](TESTING.md) for detailed testing documentation.

### Building Executables

**Windows:**
```bash
pyinstaller --onefile --windowed --name signer --icon signer/resources/signer.ico --add-data "signer/resources:signer/resources" main.py
```

**macOS/Linux:**
```bash
pyinstaller --onefile --windowed --name signer --icon signer/resources/signer.ico --add-data "signer/resources:signer/resources" main.py
```

Output: `dist/signer.exe` (Windows), `dist/signer.app` (macOS), or `dist/signer` (Linux)

### Architecture

Cross-platform support via:
- `sys.platform` for platform detection (`"win32"`, `"darwin"`, `"linux"`)
- `pathlib.Path` for cross-platform paths (no hardcoded separators)
- `get_config_dir()` in `settings.py` for platform-specific config locations
- PySide6 for native GUI on all platforms


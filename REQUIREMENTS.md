# Need
I need a simple tool that allows me to use two files: one with a PDF and one with my scanned signature. It should allow me to position the signature on the PDF and then save the combined image to a JPG file.

I'm now doing that in GIMP, but it has too many manual steps. Recommend how to make it faster.

# Requirement

1. A Windows app
2. Typical user workflow:
    1. User starts the app
    2. User opens the document
    3. App uses the previous signature file
    4. App shows the document and signature above it
    5. User can move and scale the signature above the document to position it correctly
    6. User saves the document
3. Parameters to the app:
    1. -document file
        - File with document
    2. -signature file
        File with signature
4. Menu options:
    1. Open document
    2. Open signature
    3. Save document with signature
5. When started without specifying the signature file, automatically use the previous signature file.
6. The default file name of the "document with signature" is: _documentname_ + -signed.jpg
7. The document shall fit the application window. No zooming needed.
8. Default position for the signature is 80% from top, centered horizontally.
9. Document with signature has 300 DPI.

# Version 1.1

10. Support multi-page documents; signature can be placed on any page. Put paging controls in the Toolbar. Also support `Page Up`, `Page Down`, `Home`, and `End` keys.
11. The signature is displayed (in the app only) with a blue boundary.
12. Signature scaling is currently done with a slider. Remove slider and support scaling by dragging the boundary.
13. When the mouse is above the signature, change the mouse cursor to move arrows.
14. Replace primary actions from a standard hierarchical menu with big buttons in the Toolbar for faster navigation.
15. Annotations: other objects can be put on the document, similarly to signature.
    1. Each annotation should support:
        1. Color
        2. Moving and scaling
        3. Duplicating (maintains size and color)
    2. Supported annotations:
        1. Checkmark
        2. Cross
        3. 8 arrows (North, East, North-East, ...)
        4. Text - has a submenu with items
            - Free text
            - Current date - this and following items just create a free text with some value. Use system locale.
            - Current time
            - Current date and time
        5. Signature - has a submenu with items:
            - From file... - opens a "Open file" dialog and puts the signature from the selected file.
            - List of 10 recent signature files used, order by LRU.
    3. In the Toolbar, add a button that expands to a list from which the annotation type is selected and then placed on the current page.
16. Make the resulting application a single-file executable (that can be distributed to other users).

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
- When saving JPG, the default filename shall have no page number when the document+as one page. If the document has more pages, it should have -p1 suffix when the4ser is on page 1; all the pages shoulde saved; the page-umber should be padded by zeroes.
- Resizing the text annotation just changes boundary and the text size remains the same. Make the font size adjust according to|he bounding box. Keep aspect ratio of the text.

## Version 1.2.0 - Hamburger menu

1. The application shall provide a hamburger menu on the right end of the toolbar. The menu shall be vertical and hierarchical, containing typical main menu items.

2. The hamburger menu shall contain the following structure:
    - File: Open Document, Recent Documents, Save JPG, Exit
    - Edit: Undo, Redo, Cut, Copy, Paste, Duplicate, Select All, Delete
    - Annotations: List of all annotation types
    - Help: Homepage (on GitHub, http://www.github.com/jmalenko/signer)

## Version 1.2.1 - Remove status bar

1. The status bar shall be removed. (Document name is shown in the window title; coordinates are unnecessary for this application.)

## Version 1.2.2 - Recent entries and documents

1. Recent items shall appear at the top level of their respective menus, after the static items, separated by a horizontal rule from static items.

2. The application shall maintain LRU lists (maximum 10 items each) for:
    - Recently used signature/image files
    - Recently used text strings (except the predefined strings with date and time)
    - Recently opened documents

3. Next to "Open Document", a small arrow shall open a list of recent documents.

4. Recent items shall persist across application sessions and appear in relevant menus with a separator preceding them.

## Version 1.2.3 - Settings persistence

1. The application shall store user preferences in a configuration file (shared with recent documents and texts). The following preferences shall be persisted:
    - Recent color
    - Recent line width
    - Recent font family and size
    - Recent lists (documents, texts and signature annotations)

### Details added by AI

2. The configuration file shall be stored at:
    - Windows: `%APPDATA%\Signer\config.json`
    - Unix/Linux: `~/.signer/config.json`

3. Color persistence behavior:
    - When no annotation is selected, the color picker sets the default color for new annotations
    - When an annotation is selected, the color picker changes the selected annotation's color AND updates the default color for future annotations
    - The toolbar color indicator always reflects the current default color (or selected annotation's color when one is selected)
    - Color changes are persisted immediately to the configuration file

4. Font and line width persistence:
    - Font family and size are used when creating new text annotations
    - Line width factor is used when creating new vector annotations (checkmark, cross, arrows)
    - These settings are applied immediately when creating new annotations

## Version 1.2.4 - Window size and position

1. The application shall automatically size the window to fit the document:
    - Window aspect ratio matches the document aspect ratio
    - Document is scaled to fit within available screen space while maintaining aspect ratio
    - Minimum canvas size of 520x640 pixels
    - Maximum scale of 100% (no upscaling beyond original document size)
    - Entire toolbar must remain visible

2. The window shall be centered on the screen when a document is opened to ensure the entire window is visible.

## Version 1.2.5 - Tests

1. The application shall include automated unit tests and feature tests.

2. Automated feature test: Open document1.pdf, add signature, add checkmark, move and resize each item, save JPG, compare pixel-perfect to a reference image (document1-signed-expected.jpg).

3. Automated feature test: document.pdf - add annotations on different pages, export all pages, verify each page.

4. Automated feature test: Undo/redo - add annotation, move it, undo, verify position; redo, verify position. (To be implemented later.)

5. Automated feature test: Copy/paste between pages and documents. (To be implemented later.)

6. Unit tests shall cover: coordinate transformations, bounding box calculations, annotation serialization.

7. How the automated feature tests shall be created: I as a developer want to record the actions (move, scale, add text, add checkmark) by using the application. Update the code that captures these actions. You will then use the record output to write the test case. Then the code may be disabled; it will be used only in development later to create feature tests.

8. Feature tests shall cover each annotation type (checkmark, crossmark, arrows, text, signature) using document1.pdf.

### Details added by AI

The following details clarify the test implementation requirements:

1. **Non-Interactive Testing**: Tests must run without user interaction. Any file save dialogs or other blocking UI elements must be automatically dismissed or handled programmatically. The test process must not require manual intervention.

2. **Action Recording and Persistence**: The action recording system shall:
   - Be triggered via environment variable `SIGNER_RECORD_ACTIONS=1`
   - Persist recorded actions to a JSON file in the current working directory or a specified output path
   - Record action details without version or timestamp fields (version management is handled via test code, not action records)
   - Execute recorded actions sequentially when replayed

3. **Recorded Action Format**: Each action shall include:
   - `type`: Action type (open_document, add_annotation, move_annotation, resize_annotation, select_annotation, change_color, change_page, save_document)
   - `annotation_type` (for add_annotation): checkmark, cross, arrow_n/ne/e/se/s/sw/w/nw, text, signature
   - Page index (for page-specific actions)
   - Position coordinates, dimensions, colors, or other relevant parameters
   - NO `version` or `timestamp` fields

4. **Annotation Placement**: New annotations shall be placed in the middle of the visible screen:
   - X = (canvas_width - annotation_width) / 2
   - Y = (canvas_height - annotation_height) / 2
   - Within page bounds

5. **Test Framework**: Use pytest with pytest-qt for Qt widget testing. Fixtures shall provide:
   - QApplication instance
   - MainWindow instance
   - DocumentCanvas instance
   - Temporary directories for test outputs
   - Sample PDF and signature files

## Version 1.2.6 - Application icon

1. The application icon shall depict a document with a pen writing a blue cursive signature. The pencil tip should touch the signature line to indicate active writing.

## Version 1.2.7 - Save dialog on document close

1. When a documnet has some changes (any annotations changed since the last save) and it's closed (on application exit or when another document is opened), show a dialog informing user about the changes. Offer to forget changes or save the document. 

## Version 1.2.8 - Open Encrypted PDF documnets

1. When opening a PDF, if the document is enrypted, ask user for key.

2. Also create examples\document-encrypted.pdf with same content AS document.pdf, but encrypted with key "key123".

## Version 1.2.9 - Supported Document Formats

### Supported Document Formats
The application shall support opening and editing documents in the following formats:

1. **PDF** (existing) — via PyMuPDF (fitz)
   - Multi-page support with page navigation
   - Encrypted PDF support with password prompt

2. **Word** — via headless LibreOffice conversion
   - Formats: `.docx` (Microsoft Word 2007+), `.doc` (Microsoft Word 97-2003)
   - Converted to temporary PDF, then rendered
   - Page-per-page support with navigation
   - Requires LibreOffice installed on system (or portable version bundled)

3. **ODT** (OpenDocument Text) — via headless LibreOffice conversion
   - Converted to temporary PDF, then rendered
   - Page-per-page support with navigation
   - Requires LibreOffice installed on system (or portable version bundled)

4. **Image Formats** — via Pillow
   - Single-page image formats: JPG, PNG, BMP, WEBP, GIF (first frame), ICO
   - Multi-page image format: TIFF (multi-frame)
   - Loaded directly as single or multi-page document
   - No scaling; image is displayed at native resolution (or zoomed to fit window)

### User Interface Changes

1. **Open Document Button/Menu**
   - Clicking the "Open Document" button in toolbar opens a file dialog with all supported formats
   - File dialog filter: "All Supported Files (*.pdf; *.docx; *.doc; *.odt; *.jpg; *.jpeg; *.png; *.bmp; *.webp; *.gif; *.ico; *.tiff; *.tif)"
   - Also show individual format filters for clarity (e.g., "PDF Files (*.pdf)", "Word Documents (*.docx; *.doc)", "ODT Files (*.odt)", etc.)

### Implementation Details

1. **Format Detection**
   - Use file extension (case-insensitive) to determine handler
   - Display error if file type not supported

2. **Page Handling**
   - All formats normalize to a list of PIL Image objects
   - PDF/ODT/TIFF support multiple pages with toolbar/keyboard navigation
   - Single-image formats (JPG, PNG, etc.) are treated as 1-page documents

3. **LibreOffice Integration for Word and ODT**
   - LibreOffice path resolution (priority order):
     1. Try LibreOffice path from settings file (new field: `libreOfficePath`, manually edited by user)
     2. Try LibreOffice from system PATH
     3. If neither found, show error dialog
   - Convert Word (.docx, .doc) and ODT to temporary PDF using: `<libreoffice_path> --headless --convert-to pdf <file>`
   - Clean up temporary PDF after loading
   - Show error if LibreOffice not found or conversion fails

### Test Coverage

1. Add test assets:
   - `examples/document.docx` — sample Word document with multiple pages and formatting
   - `examples/document.odt` — sample ODT with multiple pages and formatting
   - `examples/document1.jpg` — sample JPG image document

2. Automated tests shall verify:
   - Open Word document (.docx) with multiple pages; navigate all pages
   - Open ODT document with multiple pages; navigate all pages
   - Open JPG image; verify rendering at correct aspect ratio
   - Open multi-frame TIFF; verify all frames accessible via page navigation
   - Unsupported format shows error dialog
   - File dialog correctly filters all supported formats
   - Save exported JPG from each format type

### Error Handling

- **Missing LibreOffice** (required for Word and ODT): Show clear message: "LibreOffice is required to open Word and ODT documents. Please either install LibreOffice, configure the LibreOffice path in the settings file (`%APPDATA%\Signer\config.json`, field `libreOfficePath`), or use a PDF or image file instead."
- **Unsupported format**: Show error: "File format not supported. Please choose a PDF, Word document, ODT, or image file (JPG, PNG, BMP, WEBP, GIF, TIFF)."
- **Corrupt image/document**: Show validation error and keep app responsive

### Backward Compatibility (What Remains Unchanged)

1. **Recent Documents**
   - Recent documents dropdown (via small arrow) remains available, showing all recently opened formats

2. **Rendering Pipeline**
   - All pages are rendered to 300 DPI internally (same as PDF)
   - Image-only formats scaled to fit window while preserving aspect ratio

3. **CLI Parameters**
   - `-document <path>` now accepts any supported format (not just PDF)
   - `-signature <path>` remains image-only (PNG preferred) 

## Version 1.2.10 - Save Documents in Multiple Formats

### Overview
Extend document export functionality beyond JPG. Users can save annotated documents in multiple file formats via a unified "Save As..." dialog. The "Save JPG" button is removed in favor of this flexible export interface.

### Supported Export Formats

1. **JPG** — default format, 300 DPI, lossy compression
2. **PNG** — lossless compression, 300 DPI, maintains transparency of annotations
3. **PDF** — raster images, all pages in single PDF file, 300 DPI
4. **TIFF** — compressed multi-page TIFF, all pages in single file, 300 DPI
5. **BMP** — uncompressed raster, 300 DPI

### User Interface Changes

1. **"Save As..." button in Toolbar** (replaces "Save JPG")
   - Opens the "Save As..." dialog
   - Remembers last used export format and applies it as default

2. **"Save As..." in Hamburger Menu**
   - File menu → Save As...
   - Same dialog as toolbar button

3. **"Save As..." Dialog**
   - File name input field (pre-populated with smart default using last export format)
   - File browser to select destination folder
   - File extension automatically selected from filename
   - Format detection: extension determines export format
   - "Save" and "Cancel" buttons
   - Confirmation if file already exists (overwrite/rename/cancel)

### Default File Naming

1. **For single-page documents**: `{original_name}-signed.{extension}`
   - Example: `invoice.pdf` → `invoice-signed.jpg`

2. **For multi-page documents**: 
   - JPG/PNG/BMP: Separate file per page with page number: `{original_name}-signed-p01.jpg`, `{original_name}-signed-p02.jpg`, etc.
   - PDF: Single file: `{original_name}-signed.pdf` (contains all pages)
   - TIFF: Single file: `{original_name}-signed.tif` (contains all pages as frames)

### Export Behavior

1. **JPG/PNG/BMP**: Raster format, one file per page (or single file for single-page documents)
2. **PDF**: Raster format (embedded as images), all pages in one file
3. **TIFF**: Compressed multi-frame TIFF, all pages in one file

### Backward Compatibility

1. **CLI behavior**: `-document` parameter unchanged; saved files use format-specific naming convention
2. **Save behavior**: Exports all pages (for PDF/TIFF) or per-page (for JPG/PNG/BMP)

### Persistence

1. **Recent export format**: Store last-used export format in config.json (field: `lastExportFormat`), default to JPG
2. **Recent export folder**: Store last used export folder in config.json (field: `lastExportFolder`)

### Error Handling

1. **Unsupported format on save**: Show error dialog (should not occur via UI selection)
2. **Write permission denied**: Show error dialog with path suggestion
3. **Disk full**: Show error with available space info
4. **Invalid filename**: Sanitize and warn user of auto-correction

### Test Coverage

1. Unit tests:
   - Filename generation for single vs multi-page documents
   - Format-specific DPI and compression handling

2. Feature tests:
   - Export single-page document to each format
   - Export multi-page document to each format; verify all pages saved
   - Verify exported file quality (DPI, color accuracy)
   - Overwrite confirmation dialog
   - Invalid filename handling

### Implementation Notes

- PDF export may require PyMuPDF or reportlab (evaluate existing dependencies)
- TIFF multi-frame support via Pillow (already in requirements)
- Maintain 300 DPI for all export formats

## Version 1.2.11 - Auto-dismissing save notification

### Overview
Replace the blocking post-export dialog with a non-intrusive notification that auto-dismisses. The notification includes a clickable link to open the export directory.

### Behavior

1. **Notification Display**
   - After successful export, show a notification toast (not a modal dialog)
   - Position: Bottom-right corner of the main window
   - Duration: Auto-dismiss after 5 seconds (user can manually close it with an X button)
   - Message format: "Exported {filename} to [directory link]"
   - Example: "Exported document-signed-p01.jpg to C:\Users\...\Documents"

2. **Directory Link**
   - The directory path in the notification is displayed as a clickable hyperlink (underlined, colored differently)
   - Clicking the link opens the export directory in Windows Explorer
   - Hovering over the link shows a pointer cursor

3. **Multiple Files**
   - For multi-page exports (JPG/PNG/BMP), message lists the pattern: "Exported document-signed-pXX.{ext} to [directory link]"
   - For single-file exports (PDF/TIFF), message shows the filename: "Exported document-signed.{ext} to [directory link]"

### User Experience

- User is not blocked after export; they can immediately continue working
- Notification appears and fades out automatically
- User can manually close the notification by clicking the X button if desired
- Notification does not steal focus from the main window

### Error Handling on Failure

1. **Export Failure (permission denied, disk full, corrupted output, etc.)**
   - Display an error dialog (modal) instead of a notification
   - Dialog title: "Export Failed"
   - Message explains the specific error (e.g., "Permission denied" or "Insufficient disk space")
   - Show the file path that failed to save
   - Include suggestions (e.g., "Check folder permissions" or "Free up disk space")
   - Provide a "Retry" and "Cancel" button
   - Do not proceed to the notification; remain on error state until resolved or cancelled

2. **Directory Open Failure (if user clicks the link)**
   - If clicking the export directory link fails (e.g., path no longer exists, network disconnected)
   - Show a brief error notification: "Unable to open directory"
   - Log the error for debugging
   - Do not crash the application

3. **Partial Export Failure (multi-page export)**
   - If exporting multiple pages and some pages fail:
   - Stop the export process
   - Show error dialog listing which pages failed and the reason
   - Offer option to retry or cancel
   - Previously exported pages remain on disk

4. **Invalid Export Path**
   - If the export path contains invalid characters or is too long:
   - Show error dialog before attempting export
   - Suggest a corrected path
   - Allow user to modify the filename/path and retry

### Implementation Notes

- Use a lightweight toast/notification widget (not a QDialog)
- May reuse existing notification system if available, or implement a custom notification panel
- Ensure notification text is readable against background (sufficient contrast)
- Errors should be modal dialogs to ensure user sees and acknowledges them
- Success notifications should be non-intrusive (toast) to allow continued workflow

## Version 1.2.12 - Improve Export Dialog: Dynamic Page Number Placeholder

### Overview
Enhance user experience for multi-page document exports by showing dynamic page number placeholders in the save dialog. When users change file extensions, the dialog automatically updates filenames to match format requirements while preserving the custom filename stem they've typed.

### Behavior

1. **Placeholder Format**
   - For multi-page documents (JPG/PNG/BMP formats), display a single hash symbol (`#`) as a page number placeholder in the filename
   - When exporting, replace `#` with the actual page number, zero-padded to match the document's page count
   - Number of digits = number of digits required to represent the highest page number

2. **Real-Time Format Switching**
   - As user types filename in save dialog, dialog monitors input in real-time
   - When user changes file extension (e.g., `.pdf` → `.jpg`), format change is detected automatically
   - Dialog automatically updates filename to match new format requirements:
     - **PDF/TIFF → JPG/PNG/BMP**: Adds placeholder if multi-page (preserves custom stem)
       - User types: `my-report.pdf` → changes to JPG for 50-page doc → becomes `my-report-p#.jpg`
     - **JPG/PNG/BMP → PDF/TIFF**: Removes placeholder (preserves custom stem)
       - User types: `my-report-p#.jpg` → changes to PDF → becomes `my-report.pdf`
   - User's custom filename stem is always preserved through format changes
   - No dialog interruption; changes appear in real-time in filename field

3. **Smart Filename Validation**
   - **For single-file formats (PDF/TIFF)**: Accept any filename with correct extension
     - `report.pdf`, `my-document.pdf`, `final-contract.pdf` all valid ✅
     - No special naming pattern required
   - **For multi-file formats (JPG/PNG/BMP)**: 
     - Single-page documents: Any name OK (e.g., `report.jpg`)
     - Multi-page documents: Filename must include `#` placeholder
       - `document-p#.jpg` valid ✅ (generates `document-p01.jpg`, `document-p02.jpg`, etc.)
       - `document.jpg` invalid ❌ for multi-page (requires placeholder for proper page numbering)
   - If validation fails, show info dialog with expected format, allow user to retry

### Implementation Details

1. **Non-Native Dialog for Real-Time Monitoring**
   - Uses Qt-rendered file dialog instead of Windows native dialog (via `DontUseNativeDialog`)
   - Enables access to underlying QLineEdit widget for real-time filename capture
   - Trades Windows native dialog appearance for powerful auto-correction and filename preservation
   - Result: Qt styling appears as Windows 95-style dialog (classic look)
   - **Trade-off rationale**: Modern Windows native dialog doesn't expose text input field, preventing real-time monitoring

2. **Dialog Filename Suggestion Logic**
   - When opening Save As dialog, suggest filename based on document and format:
     - If single-page document: `{name}-signed.{ext}` (no placeholder)
     - If single-file format (PDF/TIFF): `{name}-signed.{ext}` (no placeholder)
     - If multi-page + multi-file format (JPG/PNG/BMP): `{name}-signed-p#.{ext}` (single # as placeholder)
   - User can edit the filename; custom stem is captured as they type
   - File extension change triggers format detection and updates filename automatically
   - File type filter selection in dropdown also triggers format detection
   - If user has edited filename (custom stem detected), stem is preserved in new format
   - If user hasn't edited (using system suggestion), new system suggestion is applied

### Edge Cases

1. **User removes or changes placeholder**
   - If user removes `#` from multi-page JPG/PNG/BMP filename:
   - On save, validation catches mismatch and shows info dialog
   - User can edit filename and retry saving
   - Returns to save dialog (not closed) so user can fix

2. **Multiple format switches**
   - User custom stem preserved across all switches:
     - Types `report.pdf` (single-file)
     - Switches to JPG 50-page → `report-p#.jpg` (custom stem `report` preserved)
     - Switches to PNG → `report-p#.png` (custom stem preserved)
     - Switches back to PDF → `report.pdf` (custom stem preserved)

3. **Very long filenames with placeholder**
   - Dialog display and validation still works correctly
   - Placeholder properly replaced even in long filenames
   - Test coverage: 41 passing tests (see TESTING.md for details)
   - Implementation notes: see DESIGN.md section 9.4 for trade-off rationale

## Version 1.2.13 - Enhanced Overwrite Confirmation Notifications

### Overview
Provide detailed overwrite confirmations that list affected files when users export, with smart detection of older page files and optional cleanup via checkbox.

### File Existence and Cleanup Detection

1. **Pre-save Validation**
   - Before export, check if any target file(s) will overwrite existing files
   - For multi-page exports: check all generated filenames
   - For single-file exports: check the single target filename
   - **Detect older files**: If the generated filename pattern matches previous exports, detect "older" page files that extend beyond the new export range
     - Example: Exporting a 20-page document when 50 older pages exist → detect `document-signed-p21.jpg` through `document-signed-p50.jpg` as candidates for cleanup

2. **Overwrite Notification Dialog** (replaces or augments existing confirmation)
   - Triggered when target file(s) already exist
   - Display format depends on number of files affected
   - **If older files detected**: Show separate lists with checkbox to include them in cleanup

#### Notification Format

##### Scenario A: Single File (Single-page document or PDF/TIFF format)
```
Title: "File Already Exists"
Message: "The file 'document-signed.jpg' already exists.

Do you want to replace it?"

Buttons: [Replace] [Cancel]
```

##### Scenario B: Multiple Files (Multi-page JPG/PNG/BMP with few overwrites)
```
Title: "Some Files Already Exist"
Message: "The following files will be overwritten:

• document-signed-p01.jpg
• document-signed-p02.jpg
• document-signed-p03.jpg

Do you want to replace them?"

Buttons: [Replace] [Cancel]
```

##### Scenario C: All Files Will Be Overwritten (Multi-page, all files exist)
- **Optimized message** for common case where user is re-exporting same document:
```
Title: "All Files Will Be Overwritten"
Message: "All 25 pages of 'document-signed-p#.jpg' will be overwritten.

Do you want to replace them?"

Buttons: [Replace] [Cancel]
```

##### Scenario D: Large Number of Files (More than 10 files affected)
- **Summarized message** to avoid overwhelming the user:
```
Title: "Files Already Exist"
Message: "25 file(s) will be overwritten:

• document-signed-p01.jpg
• document-signed-p02.jpg
• document-signed-p03.jpg
• ... (22 more files)

Do you want to replace them?"

Buttons: [Replace] [Cancel]
```

##### Scenario E: Older Page Files Detected (Multi-page export, fewer pages than before)
- **When**: New export has fewer pages than previous export AND file pattern exactly matches (same prefix/format)
- **Example**: Exporting 20 pages when 50 previous pages exist
- **Dialog Type**: Custom QDialog with checkbox and dynamic button text
```
Title: "Replace Files and Clean Up Old Pages?"

Message: "These files will be overwritten:

• document-signed-p01.jpg
• document-signed-p02.jpg
• ... (18 more files)

And these older page files can be deleted:

• document-signed-p21.jpg
• document-signed-p22.jpg
• ... (30 more files)"

Checkbox: [☐] Delete older page files  (default: unchecked)

Buttons: [Replace] [Cancel]
         (Button text changes based on checkbox state)
         - If unchecked: "Replace"
         - If checked: "Replace and delete older page files"
```

### Dialog Decision Logic

```python
IF single_file_export AND file_exists:
    Show Scenario A
ELSE IF multi_file_export:
    existing_files = [f for f in generated_filenames if f exists]
    older_files = detect_older_page_files(filename_pattern, total_pages)
    
    IF len(existing_files) == 0 AND len(older_files) == 0:
        // No confirmation needed, proceed with export
    ELSE IF len(older_files) > 0 AND pattern_matches_exactly:
        Show Scenario E (with cleanup checkbox and dynamic button text)
    ELSE IF len(existing_files) == total_files AND placeholder_unchanged:
        Show Scenario C (optimized "all files" message)
    ELSE IF len(existing_files) <= 10:
        Show Scenario B (list all files)
    ELSE:
        Show Scenario D (list first 3, show "... (N more files)" summary)
```
   ```

2. **Detect Older Files Logic**
   - Pattern detection: Extract prefix and suffix from the generated filename (e.g., `document-signed-p#` pattern)
   - Search directory for files matching pattern
   - Identify files with page numbers > total_pages (these are "older" files from previous exports)
   - Only show cleanup option if:
     - File pattern exactly matches current export pattern (same prefix/suffix)
     - At least one older file exists beyond the new page range
     - Pattern is unambiguous (e.g., no other similarly named exports with different prefixes)

3. **Cleanup Execution**
   - If user checks the cleanup checkbox and clicks Replace: delete older files along with overwriting current-range files
   - If user unchecks the checkbox: only overwrite files in the current export range
   - If older files fail to delete: show warning but proceed with export of current files
   - Log deleted files for debuggings: [Replace] [Cancel]
```
- Checkbox is **unchecked by default** (user must explicitly opt-in to delete)
- Only shown if pattern exactly matches current naming scheme and older files are outside the new rangeyou want to replace them?"

Buttons: [Replace] [Cancel]
```

### Dialog Decision Logic

1. **Detect overwrite scenario**
   ```
   IF single_file_export AND file_exists:
       Show Scenario A
   ELSE IF multi_file_export:
       existing_files = [f for f in generated_filenames if f exists]
       IF len(existing_files) == 0:
           // No confirmation needed, proceed with export
       ELSE IF len(existing_files) == total_files AND placeholder_unchanged:
     older files are detected, user has control via checkbox: opt-in to delete, or proceed with export only
- If user clicks Cancel: return to Save As dialog without closing it
- If user clicks Replace: proceed with export (and cleanup if checkbox was checked)
- After successful export: show notification as per Version 1.2.11 (non-intrusive toast)
- **Safety first**: Cleanup is never automatic; user must explicitly check the checkbox and confirm Replace
       ELSE:
           Show Scenario D (list first 3, show "... (N more files)" summary)
   ```

2. **File List Formatting**
   - List filenames relative to export directory (not full paths) for readability
   - Sort alphabetically by filename
   - Show file extension to clarify format (e.g., `.jpg`, `.png`)

3. **Placeholder Preservation in Message**
   - When listing existing files, use the actual filenames (not placeholder format)
   - Example: Show `document-signed-p01.jpg` (not `document-signed-p#.jpg`)

#### User Experience

- Confirmation dialog blocks export until user decides
- If user clicks Cancel: return to Save As dialog without closing it
   - Older page files detected → show Scenario E with cleanup checkbox

4. **Older File Detection and Cleanup**
   - Test pattern matching: detect when new export has fewer pages than previous
   - Test checkbox state: verify cleanup only happens if explicitly checked
   - Test filename patterns across different document names and page counts
   - Verify cleanup doesn't affect unrelated files with similar names
   - Test error handling: if cleanup fails on some files, export still succeeds
- If user clicks Replace: proceed with export (overwrite files)
- After successful export: show notification as per Version 1.2.11 (non-intrusive toast)

### Test Coverage

1. **File Existence Detection**
   - Single file exists → show Scenario A dialog
   - Multiple files exist → appropriate scenario based on count

2. **Overwrite Scenarios**
   - No existing files → proceed without confirmation
   - All multi-page files exist → show Scenario C optimized message
   - Subset of files exist → show Scenario B with file list
   - Large number (>10) of files exist → show Scenario D with summary

3. **Older File Detection and Cleanup**
   - Test pattern matching: detect when new export has fewer pages than previous
   - Test checkbox state: verify cleanup only happens if explicitly checked
   - Test filename patterns across different document names and page counts
   - Verify cleanup doesn't affect unrelated files with similar names
   - Test error handling: if cleanup fails on some files, export still succeeds

### Implementation Notes

- File existence checks should happen before showing confirmation
- Pattern detection: Extract prefix and suffix from generated filename
- Only show cleanup checkbox when pattern exactly matches and older files exist beyond new range
- If cleanup fails on some files: show warning but proceed with export of current files
- Log deleted files for debugging

## Version 1.2.14 - Export quality

### Overview

Provide users with optional quality/compression control in the Save As dialog. Standard workflow has no extra steps; users can click "Options" to adjust quality settings if desired. Lossless formats automatically use best-available compression without user interaction.

### Format Categories

**Lossy Formats** (user can adjust quality for file size/quality trade-off):
- **JPG/JPEG**: Lossy compression; quality is adjustable (1-100, default: 95)
- **PDF**: Lossy when embedded with rasterized images; quality is adjustable (1-100, default: 95)

**Lossless Formats** (data preserved perfectly; compression is automatic and optimal):
- **PNG**: Lossless; always uses maximum compression (compress_level=9)
- **TIFF**: Lossless; always uses LZW compression (industry standard, lossless)
- **BMP**: Lossless; typically uncompressed in standard BMP format (RLE compression available but not exposed)

### User Interface Changes

1. **"Options" Button in Save As Dialog**
   - Location: In the Save As dialog (similar to Word/Office "Options" pattern)
   - Label: "Options..." or "Quality Options..."
   - **Enabled for**: Lossy formats only (JPG, PDF)
   - **Disabled/Hidden for**: Lossless formats (PNG, TIFF, BMP) — these use optimal compression automatically
   - Clicking opens non-modal quality options panel (format-specific)
   - User can adjust settings before clicking "Save"

2. **Export Quality Options Panel** (opened by "Options" button)
   - Dialog title: "Export Quality Options"
   - Subtitle: "Choose quality/compression settings for [format name]:"
   - Format-specific controls (see Format Details section below)
   - Buttons: "OK" (apply and close), "Cancel" (discard and close)
   - If "Cancel": panel closes, returns to Save As dialog; no changes applied
   - If "OK": saves settings and closes panel; Save As dialog remains open for "Save" click

### Format Details

#### JPG/JPEG (Lossy Format)
- **Control**: Quality slider (1-100) with numeric value always visible; labels "small file" ← → "large file"
- **Behavior**: Users can adjust quality to trade file size for image quality

#### PDF (Lossy When Rasterized)
- **Control**: Quality slider (1-100) with numeric value always visible; labels "small file" ← → "large file"
- **Behavior**: Quality affects embedded raster image quality and file size

#### PNG, TIFF, BMP (Lossless Formats)
- **Compression**: Always automatic and optimal (no user control needed)
  - PNG: compress_level=9 (maximum compression)
  - TIFF: LZW compression (industry standard)
  - BMP: Uncompressed (standard format)

### Settings Persistence

1. **Configuration Fields** (stored in `config.json`)
   - `lastJpegQuality` (integer, 1-100, default: 95)
   - `lastPdfImageQuality` (integer, 1-100, default: 95)
   - Note: PNG, TIFF, BMP have no settings (always use optimal automatic values)

2. **Behavior**
   - Quality options panel pre-populates with last-used values for JPG and PDF only
   - Settings updated when user clicks "OK" in options panel
   - Settings persist across application sessions
   - JPG and PDF maintain independent settings

## Version 1.2.15 - Print

1. The application provides a "Print" menu item in the main menu (hamburger menu → File).

### Implementation Details

1. **Menu Item**: Added "Print" action to File menu in hamburger menu (after "Save As...")
2. **Print Dialog**: Opens native Windows print dialog allowing user to:
   - Select printer
   - Configure print settings (pages, copies, orientation)
   - Preview before printing
3. **Page Rendering**: 
   - All document pages rendered with annotations
   - Each page composited with its annotations (signatures, text, checkmarks, arrows)
   - Pages printed at high resolution (300 DPI)
4. **User Feedback**:
   - Success message shown after printing
   - Error messages displayed if printing fails
   - Test mode support (no dialog interaction during tests)

## Version 1.2.16 - Document and page rotation

1. The application shall support document rotation (90° to the left and 90° to the right). Add these items into Edit main menu.

1. The application shall support rotation of the current page from the document (90° to the left and 90° to the right). Add these items into Edit main menu.

1. Rotation shall be temporary (session-only) and not persisted.

1. When exporting documents, rotated pages shall be saved with their rotated orientation in all supported formats (JPG, PNG, PDF, TIFF, BMP).

1. When a page is rotated, annotations shall not rotate visually, but their position coordinates shall be transformed so that the center of each annotation remains at the same visual location on the page. This accounts for the changed coordinate system after rotation.

## Version 1.2.17 - Multi-Selection

### Selection Mechanics
1. Click on an annotation to select it (existing behavior, unchanged).
2. Shift+click shall add (or remove if already in selection) the annotation under the mouse to the selection.
3. Click on empty canvas to deselect all.
4. Selection shall be limited to annotations on the current page only. Selection across pages is not supported.
5. When navigating to a different page, the current selection shall be cleared.

### Multi-Selection Operations
When multiple annotations are selected, the following operations shall apply to all selected annotations:

6. **Move** (arrow keys): All selected annotations move together with small increments (arrow key: ~10 pixels, Shift+arrow: ~50 pixels).
7. **Delete**: Delete all selected annotations at once (single undo/redo unit).
8. **Copy/Cut**: Copy or cut all selected annotations to clipboard (JSON format, can be pasted on different pages or in different document instances).
9. **Paste**: Paste copied/cut annotations onto the current page (pasted annotations are offset slightly to avoid exact overlap).
10. **Duplicate**: Duplicate all selected annotations on the same page (single undo/redo unit).
11. **Color**: Change color of all selected annotations at once (single undo/redo unit).
12. **Line width** (vector annotations only): Change line width of selected vector annotations (Checkmark, Cross, Arrows) — applies only to compatible types when multi-selected with text/signature.

### Visual Feedback
13. All selected annotations shall display a blue boundary (same as single-selection).

### Clipboard Format
15. Clipboard shall use JSON format for serialized annotations, compatible with existing annotation serialization.
16. Pasted annotations shall have adjusted coordinates (offset by ~10 pixels) to avoid exact overlap with originals if pasted on the same page. No aadjusted coordinated if the paste is to another page.

## Version 1.2.18 - Keyboard navigation and hotkeys

1. When an annotation is selected, arrow keys (left, right, up, down) shall move it by 12pt. With Shift held, movement shall be 1px.

2. **Supported hotkeys and keyboard shortcuts:**

| Hotkey | Alternative (no Ctrl) | Action |
|--------|----------------------|--------|
| **Navigation & Movement** |
| ← / → (no selection) | — | Navigate to previous/next page |
| ↑ / ↓ (selected) | — | Move selected annotation up/down by 12pt (Shift: 1px) |
| ← / → (selected) | — | Move selected annotation left/right by 12pt (Shift: 1px) |
| Page Up | — | Go to previous page |
| Page Down | — | Go to next page |
| Home | — | Go to first page |
| End | — | Go to last page |
| **Document & File Operations** |
| Ctrl+O | O | Open document |
| Ctrl+S | S | Show Save As dialog |
| Ctrl+P | P | Print |
| **Annotation Operations** |
| Ctrl+C | C | Copy selected annotation(s) |
| Ctrl+X | X | Cut selected annotation(s) |
| Ctrl+V | V | Paste annotation(s) |
| Ctrl+D | D | Duplicate selected annotation(s) |
| Ctrl+A | A | Select all annotations on current page |
| Delete | — | Delete selected annotation(s) |
| Escape | — | Deselect all annotations |
| **Undo/Redo** |
| Ctrl+Z | Z | Undo |
| Ctrl+Y | Y | Redo |
| **Document Rotation** |
| Ctrl+L | L | Rotate all document pages left (90°) |
| Ctrl+R | R | Rotate all document pages right (90°) |
| Shift+Ctrl+L | Shift+L | Rotate current page left (90°) |
| Shift+Ctrl+R | Shift+R | Rotate current page right (90°) |

**Context:** All hotkeys (both Ctrl-based and single-key variants) are active only in the default document view when no dialog or text input field is active. They are intentionally unavailable when:
- A dialog is open (Open, Save As, Overwrite confirmation, etc.)
- A text input field is active (in a text annotation being edited, in the Save dialog filename field, etc.)

This prevents accidental triggering of hotkeys while the user is typing or confirming actions.

3. **Note on annotation addition hotkeys**: Hotkeys for directly adding specific annotation types (Checkmark, Cross, Arrows, Text, Signature) are not provided; these are accessed via the Annotations menu or toolbar button.

## Version 1.2.19 - Annotation and text sizing

Motivation: The sizes should be a appropriate for documents using text size 11 points. 

1. Default font size for text annotations: **11 points**

2. Default annotation size (width/height) for vector annotations: **20 points**
   - Checkmark: 20×20 points
   - Cross: 20×20 points  
   - Arrows: 40×40 points (2× base size)

3. Default line width for annotations: **1.5 points**
   - Proportional to the annotation size for visual consistency

4. All sizes are measured in PDF points (1/72 inch)
   - When placed on the document, 20 points = ~0.22 inches
   - These are absolute measurements in document-space, not relative to screen zoom

5. **Coordinate System and DPI Scaling**
   - Document uses PDF points (72 DPI) for coordinate storage
   - Internal rendering at 300 DPI requires scaling: `DPI_SCALE = 300 / 72 ≈ 4.167`
   - All sizes converted to 300 DPI pixels during rendering:
     - Checkmark/Cross: 20pt × 4.167 ≈ 83 pixels
     - Arrows: 40pt × 4.167 ≈ 167 pixels
     - Font: 11pt × 4.167 ≈ 46 pixels
   - Settings store sizes in PDF points; rendering applies DPI scaling automatically
   - Serialization preserves PDF points for compatibility

## Version 1.2.20 - Terminology standardization

1. Rename the "Cross" annotation to "Crossmark" for consistency with "Checkmark".
2. All documentation, code, and user-facing text shall use "Crossmark" instead of "Cross". 

## Version 1.2.21 - Undo/redo

### Overview
Provide unlimited undo/redo history for the current document session with automatic coalescing of consecutive move/resize operations to reduce memory usage and simplify undo semantics.

### Core Requirements

1. **Unlimited History for Current Session**
   - Undo/redo stack maintains unlimited history for the current document
   - History is **not persisted** to disk; it is cleared when:
     - A new document is opened (via "Open Document" or startup parameter)
     - The application is closed
   - Keyboard shortcuts: **Ctrl+Z** (undo), **Ctrl+Y** (redo)
   - Menu items: Edit menu → Undo, Edit menu → Redo (available via hamburger menu)

2. **Consecutive Move/Resize Coalescing**
   - Consecutive move/resize operations on the same annotation(s) are coalesced into a single history entry
   - Definition of "consecutive": Move or resize actions on the same object(s) with no other user actions (add, delete, color change, page navigation) in between
   - Only initial and final states are stored (intermediate states discarded)
   - Example: Dragging an annotation from (100, 100) to (200, 200) and then from (200, 200) to (300, 300) via mouse drag → single undo entry that reverts to (100, 100)
   - Actions on different objects create separate entries

3. **Unified Action Format**
   - Undo/redo history and action recording use the same underlying action mechanism
   - Action format supports two representations:
     - **Partial format** (recording): Contains only target state and essential parameters
       - Example: `{type: "move_annotation", object_id: 0, x: 300, y: 400}`
       - Lightweight and suitable for test fixture files
       - Used by action recording system for test creation
     - **Full format** (undo/redo): Contains both initial and final states
       - Example: `{type: "move_annotation", object_id: 0, from_x: 100, from_y: 100, to_x: 300, to_y: 400}`
       - Enables precise state restoration for undo
       - Generated at finalization time by capturing current object state
   - The system seamlessly handles both formats:
     - Recording produces partial-format JSON files (unchanged from current system)
     - Undo/redo automatically promotes partial format to full format when needed
     - Both use the same Action classes and serialization logic
     - No special conversion required; both formats are interoperable

### Supported Actions for Undo/Redo
- Add annotation
- Delete annotation
- Move annotation
- Resize annotation
- Change color (annotation or default)
- Set text (change text annotation content)
- Duplicate annotation
- Cut/Copy/Paste annotations (including multi-selection)
- Select annotation
- Rotate page (current page or all pages)
- Multi-selection operations (delete, copy, cut, paste, duplicate as single undo units)

### Test Coverage

1. **Feature Test**: Record and replay a workflow that exercises undo/redo with coalescing
   - Open document
   - Add annotation
   - Drag annotation twice (verify coalescing into single history entry)
   - Undo (verify annotation reverts)
   - Redo (verify annotation restored)
   - Perform additional operations and verify undo/redo stack management

2. **Unit Tests**:
   - Action serialization and deserialization
   - Coalescing logic (same object merges, different objects separate)
   - Undo/redo stack state transitions
   - Stack clearing on document open

### User Experience

- User performs action (add/move/delete) → action recorded and pushed to undo stack
- User presses Ctrl+Z → last action undone, redo stack updated
- User presses Ctrl+Y → last undone action redone
- User performs new action while in undo state → redo stack cleared
- User opens new document → undo/redo stacks cleared
- Multiple consecutive drags on same object merge into single entry, so single Ctrl+Z reverts the entire drag sequence

### Overview

1. Signature has a transparent background.

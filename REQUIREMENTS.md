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

7. Feature tests shall cover each annotation type (checkmark, crossmark, arrows, text, signature) using document1.pdf.

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

2. Default annotation size (width/height) for vector annotations:
   - Checkmark: 20×20 points
   - Cross: 20×20 points
   - Line: 80×80 points
   - Rectangle: 80×80 points
   - Ellipse: 80×80 points
   - Arrows: 160×160 points

3. Default line width for annotations: **1.5 points**
   - Proportional to the annotation size for visual consistency

4. All sizes are measured in PDF points (1/72 inch)
   - When placed on the document, 20 points = ~0.28 inches
   - These are absolute measurements in document-space, not relative to screen zoom

5. **Coordinate System and DPI Scaling**
   - Document uses PDF points (72 DPI) for coordinate storage
   - Internal rendering at 300 DPI requires scaling: `DPI_SCALE = 300 / 72 ≈ 4.167`
   - All sizes converted to 300 DPI pixels during rendering:
   - Checkmark/Cross: 20pt × 4.167 ≈ 83 pixels
   - Line/Rectangle/Ellipse: 80pt × 4.167 ≈ 333 pixels
   - Arrows: 160pt × 4.167 ≈ 667 pixels
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

### User Experience

- User performs action (add/move/delete) → action recorded and pushed to undo stack
- User presses Ctrl+Z → last action undone, redo stack updated
- User presses Ctrl+Y → last undone action redone
- User performs new action while in undo state → redo stack cleared
- User opens new document → undo/redo stacks cleared
- Multiple consecutive drags on same object merge into single entry, so single Ctrl+Z reverts the entire drag sequence

## Version 1.2.22 - More annotation types and properties

1. The following additional annotation types shall be supported:
    - Line
    - Arrow (line with tip) - with a submenu. The first item shall be "Arrow (generic)". The previous default directional arrows shall be retained.
   - Rectangle / Square: If the height-width difference is within ±20%, the shape shall be a square; otherwise a rectangle. Holding any modifier key (Shift, Ctrl, or Alt) shall disable this snapping and keep the shape as a rectangle.
   - Circle / Ellipse: If the height-width difference is within ±20%, the shape shall be a circle; otherwise an ellipse. Holding any modifier key (Shift, Ctrl, or Alt) shall disable this snapping and keep the shape as an ellipse.
    - Image: User selects a file via an Open file dialog. Recent entries shall be added to the submenu.

2. A new annotation property "Width" (in points) shall be added for all annotation types except Text and Signature / Image.

3. Text annotations shall have the following properties:
    - Text size
    - Font family
    The controls shall be in the toolbar.

4. Annotation line width shall be adjustable via:
    - A toolbar spinner/input showing the value in points
    - Keyboard shortcuts: `[` / `]` to decrease/increase

5. Text font size shall be adjustable via:
    - A toolbar spinner/input showing the value in points
    - Keyboard shortcuts: `[` / `]`
    - Resizing the text bounding box shall also scale the font size proportionally

6. Annotation menu order shall be:
    - Checkmark
    - Cross
    - Line
    - Arrow
        - Arrow (generic)
        - 8 Directional Arrows - Start with East, then south-east, south etc.
    - Rectangle / Square
    - Ellipse / Circle
    - Text
   - Signature / Image

7. Signature and Image shall be unified as a single "Signature / Image" annotation type. Color and width controls shall be hidden/disabled for this type.

8. Property controls (color, width, font) shall be context-sensitive: only shown/enabled for compatible annotation types.

9. The "Add Annotation" button and "Save As..." shall be disabled when no document is open.

10. All annotations shall support free corner dragging: dragging any corner past its opposite corner shall change how we refer to the corners (e.g., bottom-right dragged above top-left becomes top-right). This applies to all annotation types including lines and arrows. For lines and arrows, the main line is still drawn from the same corner (so the line can switch from south-east direction to north-east direction).

## Version 1.2.23 - Smart line and arrow snapping

1. When drawing or resizing a line or generic arrow: if the angle is within 10° of a cardinal direction (horizontal, vertical, or diagonal), the annotation shall snap to exactly that direction unless a modifier key is held.

2. Snap targets are the 8 cardinal/intercardinal directions:
   - 0° (horizontal right)
   - 45° (diagonal up-right)
   - 90° (vertical up)
   - 135° (diagonal up-left)
   - 180° (horizontal left)
   - 225° (diagonal down-left)
   - 270° (vertical down)
   - 315° (diagonal down-right)

3. Snapping is disabled when any modifier key (Shift, Ctrl, Alt) is held, allowing precise angle control.

## Version 1.2.24 - Simplify Arrow Annotation

### Overview
Simplify the arrow annotation system by removing directional variants. The application currently supports one generic arrow plus eight compass-direction variants (North, North-East, East, etc.). This version consolidates to a single generic arrow type pointing right (east).

### Requirements

1. **Remove directional arrow types**: Delete `ARROW_N`, `ARROW_NE`, `ARROW_E`, `ARROW_SE`, `ARROW_S`, `ARROW_SW`, `ARROW_W`, and `ARROW_NW` from the `AnnotationType` enum. Retain only the generic `ARROW` type.

2. **Simplify menu structure**: Remove the Arrow submenu from the Annotations menu in both the toolbar and hamburger menu. The Arrow option shall be a single menu item (not expandable).

3. **Arrow orientation**: When an arrow annotation is added to the document, it shall point right (east) by default. *(This documents existing behavior.)*

## Version 1.2.25 - Drag and drop and document open/save flow

### Overview
Enable drag-and-drop functionality for small images (as Signature/Image annotations) and PDF files (document loading), with smart handling of unsaved changes via save-first prompts.

### Requirements

1. Drag-and-drop of a small image file onto the application shall create a Signature/Image annotation at the drop position on the current page. Small image is defined as an image that fits on A6 paper at 300 DPI (in any orientation).

2. Drag-and-drop of a big image or PDF file onto the application shall: if the current document has unsaved annotations, prompt to save first; then load the dropped file as a document (big images open as single-page documents).

3. When opening a new document (via menu or drag-drop) with unsaved changes in the current document, the application shall prompt "Save changes to {filename}?" with Save / Don't Save / Cancel options.

### Implementation Details

**Size Thresholds**
- Small image: A6 at 300 DPI = 1240 × 1748 pixels (fits on A6 in any orientation)
- Big image: Exceeds A6 size in any dimension; opens as single-page document
- Supported image formats: PNG, JPG, JPEG, BMP (with transparency for PNG)
- Supported document formats: PDF, and big images (PNG, JPG, JPEG, BMP)

**Drop Behavior - Small Images**
- With active document: Create annotation at drop position
- With no active document: Show error "Cannot drop image: No document is currently open"
- Corrupted/unsupported format: Show error "Cannot load image: Unsupported format or corrupted file"

**Drop Behavior - Big Images/PDFs**
- With unsaved changes: Show save prompt with [Save] [Don't Save] [Cancel] buttons (default: Cancel)
  - Save: Save document, then load dropped file
  - Don't Save: Discard changes, load dropped file
  - Cancel: Keep current document, abort drop
- Without unsaved changes: Load dropped file immediately
- With no active document: Load dropped file without prompting
- Invalid/corrupted file: Show error "Cannot open file: Invalid or corrupted file"

**Menu-Triggered Open**
- Same save prompt flow as drag-drop (requirement 3)
- File picker filters for: PDF, JPG, PNG, BMP
- Default button: Cancel

**Edge Cases**
- Drop while dialog is open: Ignore drop event
- File permissions error: Show error "Cannot open file: Access denied"

## Version 1.2.26 - Portable

### Overview
Support both portable and installed deployment models via runtime detection of configuration file location. A single codebase automatically adapts to the deployment environment without requiring separate builds or installers.

### Deployment Modes

| Mode | Config Location | Typical Use Case | Activation |
|------|-----------------|------------------|------------|
| **Portable** | `./config.json` (app directory) | USB drives, shared folders, portable installs, no AppData changes | Copy `config.json` to app directory |
| **Installed** | `%APPDATA%/Signer/config.json` | Standard Windows installation, per-user configuration | Default when `config.json` not in app directory |

### Configuration Search Order

1. Check if `config.json` exists in application directory → Use portable mode
2. Otherwise, use `%APPDATA%/Signer/config.json` → Use installed mode
   - Directory created automatically on first use
   - Each Windows user gets separate config


### Migration Scenarios

#### Scenario A: Install → Portable
1. User has config at `%APPDATA%/Signer/config.json`
2. Copy file to application directory
3. Next run: Portable mode activated

#### Scenario B: Portable → Install
1. User has config at `./config.json` in app directory
2. Move file to `%APPDATA%/Signer/config.json`
3. Next run: Installed mode activated

### How Users Create a Portable Application

A portable application runs from any directory (USB drive, shared folder, local disk) without requiring AppData. For Signer, the executable itself is already portable by nature—it's a single `signer.exe` file. Making it fully portable is just a matter of where the config file lives.

#### Default Behavior (Installed Mode)
1. User downloads/copies `signer.exe` to any directory
2. Runs `signer.exe`
3. App checks for `config.json` in the same directory as the executable
4. If not found, app creates config in `%APPDATA%/Signer/config.json`
5. Settings persist in AppData (tied to that Windows user account)

#### Enable Portable Mode
To make the application fully portable (settings travel with the executable):

**Scenario: Migrate from Installed to Portable**

*Initial State (Installed Mode):*
- Location of `signer.exe`: Any directory (e.g., `C:\Program Files\Signer\`, `Downloads\`, etc.)
- Location of config: `%APPDATA%\Signer\config.json` (expands to `C:\Users\username\AppData\Roaming\Signer\config.json`)

*Steps to Enable Portable Mode:*
1. User has been running `signer.exe` normally (config in AppData)
2. Run `signer.exe` and use the app normally (any adjustments get saved to AppData)
3. Close the application
4. Copy `%APPDATA%\Signer\config.json` to the **same directory** as `signer.exe`
   - Example: If `signer.exe` is at `C:\Program Files\Signer\signer.exe`, copy config to `C:\Program Files\Signer\config.json`
   - Or copy both files to a USB drive: `D:\signer.exe` and `D:\config.json`
5. Next run: Portable mode activated; app checks the app directory first and finds `config.json` there

*Result: Fully Portable*
- `config.json` now lives next to `signer.exe` in the **same directory**
- Entire folder can be:
  - Moved to USB drive (e.g., `D:\` or `E:\portable-signer\`)
  - Copied to different computer
  - Shared on network drive
  - Synced to cloud (OneDrive, Dropbox, Google Drive)
- Settings travel with the executable
- Each directory containing `signer.exe` + `config.json` is independent
- Uninstall = delete the folder (no AppData cleanup needed)

#### Edge Cases
- **Both locations exist** (`config.json` in app dir + AppData): App directory version takes precedence (portable mode)
- **AppData unavailable** (e.g., network share with restrictions): App still works via portable mode
- **No config file anywhere**: App creates it in AppData on first run (default installed mode)

## Version 1.2.27 - Nearest annotation selection

1. When the cursor is inside the bounding box of one or more annotations, transparent pixels within those bounding boxes shall count as selectable space.
2. When multiple annotation bounding boxes contain the cursor, the nearest annotation shall be selected based on the distance to its nearest rendered visible pixel.
3. A cursor outside all annotation bounding boxes shall select nothing.

## Version 1.2.28 - Context-sensitive toolbar visibility

1. Toolbar property controls shall be shown only for the currently selected annotation type.
2. When no annotation is selected, annotation-specific toolbar controls shall be hidden.
3. The page navigation block shall be shown only for documents with more than one page.
4. When the document has exactly one page, the entire page navigation section shall be hidden, including any page label such as "Page 1/1".
5. The toolbar property section shall be defined per annotation type as follows:
   - No selection: hide all annotation property controls (color, width, font size, font family).
   - Text: show color, font size, and font family controls
   - Signature / Image: show no controls
   - Other: show color and width controls
6. The Duplicate and Delete toolbar buttons shall be visible only when an annotation is selected.
7. Toolbar group separators shall not be duplicated: when a group of controls (e.g. page navigation, or the color/width/font property group) is hidden, only a single dividing separator shall remain, never two adjacent separators.
8. When multiple annotations are selected, the toolbar shall show only the controls that are relevant to at least one selected annotation.
9. When a property is changed while multiple annotations are selected, the change shall be applied only to the selected annotations that support that property.

## Version 1.2.29 - Context-sensitive main menu items

1. Main menu (hamburger) items shall be disabled when the corresponding action is not applicable, consistent with the toolbar's context-sensitive behavior.
2. File menu:
   - "Save As…" and "Print" shall be enabled only when a document is open.
3. Edit menu:
   - "Undo" shall be enabled only when there is an action available to undo.
   - "Redo" shall be enabled only when there is an action available to redo.
   - "Cut", "Copy", "Duplicate", and "Delete" shall be enabled only when at least one annotation is selected.
   - "Paste" shall be enabled only when a document is open and there is annotation data available to paste (from a prior copy/cut, in-app cache, or the system clipboard).
   - "Select All" shall be enabled only when the current page has at least one annotation.
   - "Rotate Current Page Left/Right" and "Rotate All Pages Left/Right" shall be enabled only when a document is open.
4. Menu item state shall be re-evaluated whenever the menu is about to be shown, so it always reflects the latest document, selection, and history state regardless of how that state changed (menu action, toolbar action, or keyboard shortcut).

## Version 1.2.30 - Add Annotation menu hotkey

1. In the default document view, pressing `+` shall open the Add Annotation menu in the toolbar.

### Assumption

1. Signature has a transparent background.

## Version 1.2.31 - Error Notification are Manually Dismissed

### Overview
Clarify and enforce the distinction between success and error notification toasts introduced
in Version 1.2.11, so error toasts are visually distinct and require explicit acknowledgment.

1. **Success toasts** (e.g. post-export notification): green, auto-dismiss after 5 seconds,
   can also be closed early via the X button.
2. **Error toasts** (e.g. "Unable to open directory" when the export directory link fails):
   red, do **not** auto-dismiss — the user must manually close them via the X button.
3. This distinguishes non-critical successes (safe to miss) from errors (must be acknowledged)
   while still avoiding blocking modal dialogs for brief/non-fatal errors.
4. Export/save failures (e.g. insufficient disk space, permission denied) remain a separate
   category from toasts: they are shown using the native system dialog style (`QMessageBox`),
   modal to the application window (blocks further interaction with the app until dismissed,
   but does not block other applications on the system).

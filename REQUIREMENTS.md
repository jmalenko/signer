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

--

Feedback after implementation:

1. I noticed that the tests run the application. That's ok, but the application remains open and I (user) have to close it manually so the tests continues. Thus happens when a dialog (saved 3 pages) was open. Make the test such that tey do not require user interaction.

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

# Assumptions
1. Signature has a transparent background.

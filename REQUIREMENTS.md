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

(Version 1.1)

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

# Assumptions
1. Signature has a transparent background.
1. Signature is a PNG file.

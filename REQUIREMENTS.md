
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

# Assumptions
1. Signature has a transparent background.
1. Signature is a PNG file.


# Need
I need a simple tool that allows me to use two files, one with a PDF and oher with my scanned signature, allows me to position the signature in the pdf and then saves the combinad image to a jpg file.

I'm now doing that in gimp, but it seems as too many manual steps. Recommend how to make it faster. 

# Requirement

1. A Windows app
2. Typicall user workflow:
    1. User starts the app
    2. User opens the document
    3. App uses the previous file with signature
    4. App shows the document and signature above it
    4. User can move and scale the signature above the document to position it to the correct place.
    6. User savesdocument
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
5. The default file name of the "document with signature" is: _documentname_ + -signed.jpg
7. The document shall fit the application window. No zooming needed.
8. Default position for the signature is 80% from top, centered horizontally.
9. Document with signature has 300 DPI.

# Assumptions
1. Signature has a transparent backgroud.
2. One page document.

# Out of scope (potential future enhancements)
- multi-page documents
- ANNoATIONS - Other symbols like checkmarc, crossess, date etc.

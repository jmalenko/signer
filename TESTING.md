# Testing Guide for Signer v1.2.9

## Overview

The Signer test suite includes comprehensive tests for multi-format document support (PDF, Word, ODT, Images). Tests can be run with or without LibreOffice support.

## Basic Test Execution

### Run all tests
```bash
pytest tests/
```

### Run specific test class
```bash
pytest tests/unit/test_multiformat_documents.py::TestPDFDocumentLoading
```

### Run specific test
```bash
pytest tests/unit/test_multiformat_documents.py::TestPDFDocumentLoading::test_load_pdf_document
```

## Testing Multi-Format Documents (Word, ODT)

Multi-format document tests require LibreOffice to be installed. There are two ways to enable these tests:

### Option 1: Configure in Settings (Persistent)

Add LibreOffice path to your config file:
- **File location**: `%APPDATA%\Signer\config.json` (Windows)
- **Field**: `libreOffice_path`

Example:
```json
{
  "libreOffice_path": "C:\\PortableApps\\LibreOfficePortable\\App\\libreoffice\\program\\soffice.exe"
}
```

Then run tests normally:
```bash
pytest tests/
```

### Option 2: Command-Line Parameter (One-Time)

Pass the LibreOffice path via `--libreoffice-path`:

```bash
pytest tests/ --libreoffice-path "C:\Program Files\LibreOffice\program\soffice.exe"
```

Or for portable LibreOffice:
```bash
pytest tests/ --libreoffice-path "C:\PortableApps\LibreOfficePortable\App\libreoffice\program\soffice.exe"
```

## Test Organization

### Multi-Format Document Tests (`test_multiformat_documents.py`)

- **TestDocumentLoaderRegistry**: Registry format detection
- **TestPDFDocumentLoading**: PDF rendering (always works, no LibreOffice needed)
- **TestWordDocumentLoading**: DOCX and DOC format support (requires LibreOffice)
- **TestODTDocumentLoading**: OpenDocument Text support (requires LibreOffice)
- **TestImageDocumentLoading**: JPG, PNG, TIFF format support (always works)
- **TestUnsupportedFormats**: Error handling for unsupported formats
- **TestLibreOfficePath**: LibreOffice path configuration

### Test Results

**Without LibreOffice configured:**
- PDF, image, and format detection tests: ✅ PASS
- Word/ODT tests: ⊘ SKIP (with informative message)
- Total: ~131 passed, 6 skipped

**With LibreOffice configured:**
- All tests: ✅ PASS
- Total: 136 passed, 1 skipped (unrelated)

## Finding LibreOffice Executable

### Windows - Installed Version
```
C:\Program Files\LibreOffice\program\soffice.exe
C:\Program Files (x86)\LibreOffice\program\soffice.exe
```

### Windows - Portable Version
Look in your PortableApps directory:
```
C:\PortableApps\LibreOfficePortable\App\libreoffice\program\soffice.exe
```

### Linux
```
/usr/bin/soffice
/opt/libreoffice/program/soffice
```

### macOS
```
/Applications/LibreOffice.app/Contents/MacOS/soffice
```

## Fixture: libreoffice_path

The `libreoffice_path` pytest fixture automatically:
1. Checks command-line parameter (`--libreoffice-path`)
2. Falls back to settings file (`config.json`)
3. Returns `None` if neither is configured

Tests handle `None` gracefully by skipping with an informative message.

## Configuration Precedence

1. **Command-line parameter** (`--libreoffice-path`) - highest priority
2. **Settings file** (`config.json`)
3. **Not configured** - tests skip with message

## Troubleshooting

### Tests are skipping when LibreOffice is available

**Cause**: LibreOffice path not configured and not passed via command-line

**Solution**: 
- Update `config.json` with correct path, OR
- Pass `--libreoffice-path` when running tests

### "LibreOffice executable not found" error

**Cause**: Path is incorrect or LibreOffice is not installed

**Solution**:
- Verify the path exists on your system
- Use correct path separator (backslash on Windows, forward slash on Unix)
- Ensure you're pointing to `soffice` executable, not a directory

### DOCX/ODT conversion fails

**Cause**: Headless LibreOffice conversion error

**Solution**:
- Verify LibreOffice installation is functional
- Try running LibreOffice UI to ensure it initializes properly
- Check permissions on temporary directory

## CI/CD Integration

For continuous integration, use the `--libreoffice-path` parameter:

### GitHub Actions Example
```yaml
- name: Run tests with LibreOffice
  run: |
    pytest tests/ --libreoffice-path "C:\Program Files\LibreOffice\program\soffice.exe"
```

### GitLab CI Example
```yaml
test:
  script:
    - pytest tests/ --libreoffice-path "/usr/bin/soffice"
```

## Version 1.2.12 - Export Dialog Placeholder Tests

### Test Coverage (41 passing tests for Version 1.2.12 features)

#### Placeholder Calculation Tests
- Correct digit padding: 1-9 pages (1 digit), 10-99 (2 digits), 100-999 (3 digits), 1000+ (4 digits)
- Single-page documents show no placeholder
- Placeholder replacement with correct zero-padding

#### Format Switching Detection Tests
- Detection of format change via file extension
- Detection of format change via filter dropdown
- Auto-correction when user hasn't edited filename
- Preservation when user has custom stem

#### Filename Preservation Tests
- Custom stem extracted and preserved across format switches
- Multiple format switches maintain same stem
- Placeholder added/removed correctly for each format

#### Validation Tests
- Single-file format (PDF/TIFF): Custom names accepted with correct extension
- Multi-file single-page: No placeholder required
- Multi-file multi-page: Placeholder validation enforced
- Extension validation for all formats

#### Edge Case Tests
- User removes placeholder → validation catches and shows info dialog
- User changes format after filename was set → filename updates correctly
- Very long filenames with placeholder → dialog remains readable
- Multiple format switches preserve custom stem across all transitions

### Test Files
- **test_format_switching.py**: Format change detection and filename auto-correction (17 tests)
- **test_placeholder_dialog.py**: Placeholder validation and calculation (24 tests)

## Version 1.2.14 - Export Quality Tests

### Overview

Tests for optional quality/compression control accessible via "Options" button in Save As dialog. Lossless formats (PNG, TIFF, BMP) automatically use optimal compression; lossy formats (JPG, PDF) allow user quality adjustment.

### Test Coverage

#### Unit Tests

**Settings Persistence** (test_export_quality.py)
- `lastJpegQuality` persisted to config file (default: 95)
- `lastPdfImageQuality` persisted to config file (default: 95)
- PNG/TIFF/BMP have no settings (always use automatic optimal values)
- Load settings on startup; use defaults if corrupted config
- Update settings only when user clicks "OK" in options panel

**Value Validation**
- JPG quality: Valid range 1-100 with clamping
- PDF image quality: Valid range 1-100 with clamping
- Invalid values fallback to defaults
- Type checking for numeric values

**Format Category Tests**
- Lossy formats (JPG, PDF): Have user-configurable quality via "Options" button; "Options" button enabled for these formats
- Lossless formats (PNG, TIFF, BMP): Use automatic optimal values; "Options" button hidden for these formats
- PNG always uses compress_level=9 (maximum lossless compression)
- TIFF always uses LZW compression (industry standard)
- BMP always uncompressed (standard format)

**Slider Appearance Tests** (Lossy Formats)
- Numeric value always visible on quality slider (not hidden/collapsed)
- Slider has left label "small file" and right label "large file"
- Labels accurately indicate quality-to-filesize tradeoff

#### Feature Tests

**Options Button Visibility/State** (test_export_quality_dialog.py)
- "Options" button visible and enabled in Save As dialog ONLY for lossy formats (JPG, PDF)
- "Options" button hidden for lossless formats (PNG, TIFF, BMP)
- Clicking "Options" opens non-modal quality options panel (lossy formats only)

**Quality Options Panel** (Lossy Formats: JPG, PDF)
- Panel title: "Export Quality Options"
- Shows quality slider (1-100) with numeric value always visible next to slider
- Slider labels: "small file" on left ← → "large file" on right
- Pre-populates with last-used value for that format
- "OK" button saves settings and closes panel
- "Cancel" button discards changes and closes panel
- Save As dialog remains open after "OK" or "Cancel"

**Quality Options Panel** (Lossless Formats: PNG, TIFF, BMP)
- "Options" button is hidden for these formats (no panel to show)
- Lossless formats always use automatic optimal compression without user adjustment

**Export Behavior**
- JPG export uses quality value from last-used setting (or default 95)
- PDF export uses image quality value from last-used setting (or default 95)
- PNG export always uses compress_level=9 (maximum lossless compression)
- TIFF export always uses LZW compression
- BMP export uses no compression (standard format)

**Settings Persistence**
- Quality settings persist across application restart
- JPG quality set to 50, close app, reopen → shows 50 in options panel
- PDF image quality set to 80, close app, reopen → shows 80 in options panel
- PNG/TIFF/BMP: No persistence needed (always use optimal values)

**Standard Workflow** (No Options Click)
- User selects JPG format
- Clicks "Save" directly (without clicking "Options")
- Export uses default quality 95
- File size/quality appropriate for default

**Advanced Workflow** (With Options)
- User selects JPG format
- Clicks "Options" button
- Adjusts quality slider to 50
- Clicks "OK" in options panel
- Clicks "Save" in Save As dialog
- Export uses quality 50
- File size smaller, quality lower than default 95

**Dialog Closure Behavior**
- Options panel closes on "OK" → returns control to Save As dialog
- Options panel closes on "Cancel" → returns control to Save As dialog
- Save As dialog does NOT close; user can click "Save" or change filename

#### Edge Cases

**Invalid Config File**
- Corrupted `config.json`: Use format defaults (95 for JPG/PDF)
- Missing fields: Use format defaults
- Type mismatch (string instead of int): Use format defaults

**Unsupported Quality Values**
- Value < 1: Clamp to 1
- Value > 100: Clamp to 100
- Non-numeric input in options panel: Show validation error or reset to last-valid value

**Format Changes with Settings**
- Set JPG quality to 50
- Change format to PDF
- Options panel shows PDF quality (may be different from JPG)
- Change back to JPG
- JPG quality still remembered as 50

**Concurrent Exports**
- Export JPG with quality 50
- While exporting, change options to quality 80
- Running export uses 50 (settings lock or read-only during export)
- Next export uses 80

#### Manual Testing

**JPG Quality Verification**
- Export same document with quality 95: Compare file size and visual quality
- Export same document with quality 50: Verify file size is smaller
- Export with quality 100: Verify maximum file size and quality

**PNG Compression Verification**
- Export PNG multiple times: File size should be consistent (always maximum compression)
- Compare PNG file size with JPG: PNG should be similar or larger (lossless vs lossy)

**TIFF Compression Verification**
- Export TIFF: Check file format metadata for LZW compression method
- Compare TIFF with BMP: TIFF should be smaller (compressed vs uncompressed)

**BMP Format Verification**
- Export BMP: File size largest compared to PNG/TIFF/JPG (no compression)
- Click "Options" for BMP: Should show informational panel (no adjustments available)

**Settings Persistence Manual Check**
- Set JPG quality to 30
- Restart application
- Open Save As dialog
- Click "Options" for JPG
- Verify slider shows 30 (not default 95)

### Test Files

- **test_export_quality.py**: Unit tests for settings persistence, validation, format categories
- **test_export_quality_dialog.py**: Feature tests for Options button, quality panel, export behavior

## Related Files

- **conftest.py**: Pytest configuration and fixtures
- **test_multiformat_documents.py**: Multi-format document tests
- **pytest.ini**: Pytest settings and documentation

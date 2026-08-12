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

## Related Files

- **conftest.py**: Pytest configuration and fixtures
- **test_multiformat_documents.py**: Multi-format document tests
- **pytest.ini**: Pytest settings and documentation

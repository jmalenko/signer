# Testing Guide

## Running Tests

### All tests
```bash
pytest tests/
```

### Unit tests only
```bash
pytest tests/unit/
```

### Feature tests only
```bash
pytest tests/feature/
```

### With coverage report
```bash
pytest --cov=signer --cov-report=html
```

### Specific test file
```bash
pytest tests/feature/test_document1_annotations.py -v
```

## Multi-Format Document Testing (Word, ODT)

Multi-format tests require LibreOffice to convert Word and ODT documents to PDF before rendering.

### Option 1: Configure in Settings (Persistent)

Add LibreOffice path to `%APPDATA%\Signer\config.json`:

```json
{
  "libreoffice_path": "C:\\Program Files\\LibreOffice\\program\\soffice.exe"
}
```

Then run tests normally:
```bash
pytest tests/
```

### Option 2: Command-Line Parameter (One-Time)

```bash
pytest tests/ --libreoffice-path "C:\Program Files\LibreOffice\program\soffice.exe"
```

For portable LibreOffice:
```bash
pytest tests/ --libreoffice-path "C:\PortableApps\LibreOfficePortable\App\libreoffice\program\soffice.exe"
```

## Finding LibreOffice Executable

### Windows - Installed
```
C:\Program Files\LibreOffice\program\soffice.exe
```

### Windows - Portable
```
C:\PortableApps\LibreOfficePortable\App\libreoffice\program\soffice.exe
```

### Linux
```
/usr/bin/soffice
```

### macOS
```
/Applications/LibreOffice.app/Contents/MacOS/soffice
```

## Test Results

After running feature tests, view the HTML report:

```bash
# Windows
start tests/test-results/report.html

# macOS
open tests/test-results/report.html

# Linux
xdg-open tests/test-results/report.html
```

**Report features:**
- Color-coded status badges (✓ PASS / ✗ FAIL)
- Side-by-side Expected vs Actual image comparison
- Pixel-level diff visualization with color-coded classification:
  - **Red**: Pixel is white in expected and non-white in actual (unexpected/added pixels)
  - **Violet**: Pixel is non-white in expected and white in actual (missing pixels)
  - **Orange**: Pixel is non-white in both expected and actual (modified/different pixels)
  - **White**: Matching pixels
- Test summary at top with clickable test names
- Full-size image modal view on click, with mouse wheel zoom and pan support

## Test Results Directory Structure

```
tests/test-results/
├── {test_name}/
│   ├── {name}_actual.png          # Generated output
│   ├── {name}_expected.png        # Reference baseline
│   ├── {name}_diff.png            # Color-coded pixel difference visualization
│   └── info.json                  # Pass/fail status
└── report.html                     # Interactive HTML report
```

## Accepting Changes

If output changes are intentional and verified as correct:

1. Verify in HTML report (Expected vs Actual look correct)
2. Copy actual to expected:
   ```bash
   cp tests/test-results/{test_name}/{name}_actual.png tests/fixtures/{name}_actions-expected/{name}-output.png
   ```
3. Re-run tests to confirm they pass:
   ```bash
   pytest tests/feature/ -v
   ```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Tests skip when LibreOffice is available | Update `config.json` with correct path OR pass `--libreoffice-path` when running tests |
| "LibreOffice executable not found" error | Verify path exists on your system; use backslash on Windows, forward slash on Unix |
| Word/ODT conversion fails | Verify LibreOffice installation is functional; try running LibreOffice UI first |
| Tests report high mismatch percentage | Verify expected image is correct; if changes are intentional, copy actual to expected |

## Test Structure

Test files organize unit, feature, and recording tests:

```
tests/
├── unit/                          # Core functionality tests
├── feature/                       # End-to-end workflow tests
├── fixtures/                      # Test data and reference images
├── recording/                     # Action recording utilities
├── test-results/                  # Generated test reports (not committed)
└── conftest.py                    # Pytest configuration
```

See [DESIGN.md](DESIGN.md) for architecture and testing concepts.

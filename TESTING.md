# Testing Guide

## Overview

Tests are split into two kinds, both under `pytest`:

- **Unit tests** (`tests/unit/`): coordinate transformations, bounding-box calculations,
  annotation serialization, and other logic-level checks.
- **Feature tests** (`tests/feature/`): end-to-end workflows driven by replaying a recorded
  action sequence (JSON) against a real `MainWindow`/`Canvas`, then pixel-comparing the exported
  image against a reference image.

```
tests/
├── unit/                          # Core functionality tests
├── feature/                       # End-to-end workflow tests
├── fixtures/                      # Recorded action JSON + reference images
├── recording/                     # Action recording/playback utilities
├── test-results/                  # Generated test reports (not committed)
└── conftest.py                    # Pytest configuration, fixtures
```

See [DESIGN.md](DESIGN.md) for architecture, and
[FUNCTIONAL_SPECIFICATION.md](FUNCTIONAL_SPECIFICATION.md) for the behavior these tests verify.

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
pytest tests/feature/test_recorded_workflows.py -v
```

## Multi-Format Document Testing (Word, ODT)

Multi-format tests require LibreOffice to convert Word and ODT documents to PDF before rendering.

### Option 1: Configure in Settings (Persistent)

Add `libreoffice_path` to the platform configuration file:

- Windows: `%APPDATA%\Signer\config.json`
- macOS: `~/Library/Application Support/Signer/config.json`
- Linux: `~/.config/Signer/config.json`

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

## Recording New Feature Tests

Feature tests replay a recorded JSON action sequence and compare the rendered output to a
reference image. To create a new one:

1. Run the app from source with recording enabled:
   ```bash
   SIGNER_RECORD_ACTIONS=1 python main.py -document examples/document.pdf
   ```
2. Perform the workflow you want to capture (add annotations, move/resize them, etc.), then
   close the application.
3. The recorder writes the captured actions to
   `tests/recorded_actions/recorded_actions_<timestamp>.json` (printed to the console on exit).
4. Move/rename that file into `tests/fixtures/{name}.json`, matching the naming convention of
   existing fixtures (e.g. `line.json`, `text_props.json`).
5. Add a case to `WORKFLOW_TEST_CASES` in
   [tests/feature/test_recorded_workflows.py](tests/feature/test_recorded_workflows.py),
   pointing at the new fixture name and an expected-output annotation prefix.
6. Run the new test once; it will fail with no reference image yet. Inspect the generated
   `*_actual.png` in the HTML report (see below), and once it looks correct, promote it to the
   expected baseline using the same **Accepting Changes** steps above.

Playback is driven by `tests/recording/action_player.py`; the recorder itself lives in
`tests/recording/action_recorder.py` and is only active when `SIGNER_RECORD_ACTIONS=1` is set
(see `signer/app.py`).

## Release Validation

A successful build/test run on one platform does not establish that another platform works —
each target OS must be built and validated separately before publishing, including a manual
smoke test of document open, annotation rendering/fonts, export, the clickable export-directory
link, and Word/ODT conversion (if LibreOffice is installed). See [DESIGN.md](DESIGN.md) for the
full build/smoke-test matrix and Linux-specific commands.

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Tests skip when LibreOffice is available | Update `config.json` with correct path OR pass `--libreoffice-path` when running tests |
| "LibreOffice executable not found" error | Verify path exists on your system; use backslash on Windows, forward slash on Unix |
| Word/ODT conversion fails | Verify LibreOffice installation is functional; try running LibreOffice UI first |
| Tests report high mismatch percentage | Verify expected image is correct; if changes are intentional, copy actual to expected |

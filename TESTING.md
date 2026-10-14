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

### Matching the GitHub test run

The platform-stable unit-test step explicitly uses `QT_QPA_PLATFORM=offscreen` on every OS.
To reproduce it locally on macOS/Linux:

```bash
QT_QPA_PLATFORM=offscreen python -m pytest tests/unit --ignore=tests/unit/test_toolbar_onscreen.py --ignore=tests/unit/test_window_sizing.py --capture=no --no-qt-log
```

On PowerShell, first configure the backend and font directory, then run the same
`python -m pytest` command:

```powershell
$env:QT_QPA_PLATFORM = "offscreen"
$env:QT_QPA_FONTDIR = Join-Path $env:WINDIR "Fonts"
```

Windows offscreen Qt uses FreeType instead of the native Windows font database. Without
`QT_QPA_FONTDIR`, Qt may discover no fonts, producing blank text and invalid text bounds.
CI points it at `C:/Windows/Fonts` and checks font availability and text metrics before tests.
The test step disables Python and pytest-qt output capture so native fatal messages and crash
traces remain visible even when the process aborts before pytest can report a failure.

An empty `QT_QPA_PLATFORM` is not equivalent to offscreen:
it lets Qt select the native backend, whose window constraints and widget metrics differ.
Matching the backend does not guarantee identical results across dependency versions or hosts.

Install from `requirements.txt` before comparing results. PySide6 is pinned to `6.11.2`,
the locally validated version. A Linux CI run with `6.12.0` aborted with
`none_dealloc: deallocating None` during checkerboard painting; the pin is a conservative
rollback while that native reference-count failure is investigated. It is not proof that all
cross-platform failures are resolved.

The three-row overlay regression deliberately widens controls relative to the actual canvas
width, then verifies that all controls remain visible in order. It does not assume that the
window manager honours a requested 400px window width.

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
pytest tests/feature/test_document_all_annotations.py -q
```

Qt runs with the `offscreen` platform during tests. Native font discovery is platform-dependent:
macOS still exposes its CoreText fonts, whereas a headless Windows runner may report none. Tests
that exercise font controls must use the application's guaranteed common-font choices rather than
assuming any particular font is installed by the host.

### On-screen toolbar tests

Some selection-toolbar bugs cannot reproduce offscreen. Offscreen, a control's `sizeHint()`
happens to equal the width Qt later allocates inside the styled toolbar row, and Qt honours a
shrink below a stale minimum — on a real window server neither holds. That is why toolbar issues
were repeatedly marked fixed while still reproducing for users.

`tests/unit/test_toolbar_onscreen.py` runs as part of the normal `pytest` suite. Each test starts
a subprocess with the host's native platform plugin so it can coexist with the main suite's
offscreen `QApplication`. It skips only when no window server is available (for example, a
headless Linux runner without `DISPLAY` or `WAYLAND_DISPLAY`). It can also be run directly:

```bash
QT_QPA_PLATFORM=cocoa pytest tests/unit/test_toolbar_onscreen.py   # macOS
QT_QPA_PLATFORM=xcb   pytest tests/unit/test_toolbar_onscreen.py   # X11
```

It drives the window programmatically and needs no interaction. The resize scenario validates
every dynamically created overlay row, including widths that require three or more rows. The
offscreen suite alone is not sufficient evidence for toolbar layout work.

CI runs this file in a separate step on Windows and macOS. The parent pytest process remains
offscreen, while each scenario subprocess explicitly selects `windows` or `cocoa`. Reproduce
that step locally with:

```bash
QT_QPA_PLATFORM=offscreen python -m pytest tests/unit/test_toolbar_onscreen.py
```

On PowerShell, set `$env:QT_QPA_PLATFORM = "offscreen"` before the same pytest command.
The headless Linux CI runner has no native desktop session, so native toolbar checks remain
local X11/Wayland checks there.

The mode-switch comparison places both windows at the same position and a size that fits the
available desktop, then waits for stable geometry. It checks that the actual outer window
geometry matches the request and remains unchanged by the mode switch, before comparing
canvas geometry and pixels exactly. This prevents native screen clamping of a fixed 700px
height from silently comparing differently sized windows on smaller CI desktops.

When the mode-switch image comparison fails, it saves expected and actual screenshots as
`native-toolbar-*.png` in the repository root. CI uploads them as the
`native-toolbar-windows` or `native-toolbar-macos` artifact even when the job fails.
The pixel-equality assertion remains unchanged. Compare the images before attributing a
mismatch to a stale toolbar strip: native focus or hover states can also change pixels.
Remove locally generated snapshots after investigation and before committing.

## Static Analysis with Ruff

Install Ruff in the active virtual environment if needed:

```bash
python -m pip install ruff
```

Check application and test code:

```bash
python -m ruff check signer tests
```

Save the findings to a report:

```bash
python -m ruff check signer tests --output-format concise > ruff-report.txt
```

Ruff returns exit code `1` when it finds violations. Some findings can be fixed automatically:

```bash
python -m ruff check signer tests --fix
```

Review the resulting diff and run the full test suite after using `--fix`. Ruff's automatic
cleanup may remove imports that are used indirectly by tests or runtime callbacks. Project-level
exceptions are defined in `pyproject.toml`; currently `F841` and `RUF059` are ignored.

## Testing the Prepare Signature Tool

The tool's image processing (luminance removal, hue filtering, sequential alpha composition,
content auto-trim, resize) lives in
`signer/signature_background.py` as pure functions and is covered by `tests/unit/` cases that
assert on pixel/alpha values of small synthetic images (no Qt event loop needed). The dialog
itself (`signer/prepare_signature_dialog.py`) is a standalone workflow that doesn't touch the
open document/canvas, so it is exercised with targeted widget-level unit tests rather than the
canvas action-recording/playback system in `tests/recording/` (which is scoped to document
annotation workflows).

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

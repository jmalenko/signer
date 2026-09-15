"""Pytest configuration and fixtures for Signer tests."""

import os
import sys
import tempfile
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication

# Add the project root to the path so we can import signer modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from signer.canvas import DocumentCanvas
from signer.main_window import MainWindow
from signer.objects import AnnotationType, SignatureObject, VectorAnnotation
from signer.settings import AppSettings, SettingsStore


# Run Qt in offscreen mode so tests don't pop up visible application windows.
# Respect an existing QT_QPA_PLATFORM (e.g. set by the user) if already defined.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="session")
def qapp():
    """Create a QApplication instance for the test session."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app


class QtBot:
    """Simple Qt bot for testing without pytest-qt dependency."""
    
    def __init__(self):
        self.widgets = []
    
    def addWidget(self, widget):
        """Register a widget for cleanup."""
        self.widgets.append(widget)
    
    def cleanup(self):
        """Clean up all registered widgets."""
        for widget in self.widgets:
            try:
                widget.deleteLater()
            except Exception:
                pass


@pytest.fixture
def qtbot(qapp):
    """Create a QtBot instance for test cleanup."""
    bot = QtBot()
    yield bot
    bot.cleanup()


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test outputs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_pdf():
    """Path to the sample single-page PDF."""
    return Path(__file__).parent.parent / "examples" / "document1.pdf"


@pytest.fixture
def sample_multipage_pdf():
    """Path to the sample multi-page PDF."""
    return Path(__file__).parent.parent / "examples" / "document.pdf"


@pytest.fixture
def sample_signature():
    """Path to the sample signature image."""
    return Path(__file__).parent.parent / "examples" / "signature.png"


@pytest.fixture
def settings_store(temp_dir):
    """Create a SettingsStore that ONLY uses default settings (no user config).
    
    This ensures tests are reproducible and don't depend on the user's installed settings.
    """
    # Use a config path in temp_dir that will never exist, forcing defaults
    config_path = temp_dir / "config_never_exists.json"
    store = SettingsStore(app_name="SignerTest")
    store._settings_path = config_path
    # Verify the path doesn't exist (so load() returns defaults)
    assert not store._settings_path.exists(), "Settings file should not exist for clean test environment"
    return store


@pytest.fixture
def app_settings():
    """Create default AppSettings for testing (no user config loaded).
    
    This ensures tests are reproducible and consistent.
    """
    return AppSettings()


@pytest.fixture
def libreoffice_path(request):
    """Get LibreOffice path from command line or settings.
    
    Can be provided via:
    - Command line: pytest --libreoffice-path <path>
    - Settings: config.json libreoffice_path field
    
    If a path is specified (either via CLI or settings), it must exist.
    If the path does not exist, the test fails.
    """
    # First, check command line parameter
    cli_path = request.config.getoption("--libreoffice-path")
    if cli_path:
        if not Path(cli_path).exists():
            pytest.fail(f"LibreOffice executable not found at: {cli_path}")
        return cli_path
    
    # Fall back to settings
    store = SettingsStore()
    settings = store.load()
    if settings.libreoffice_path:
        if not Path(settings.libreoffice_path).exists():
            pytest.fail(f"LibreOffice executable not found at: {settings.libreoffice_path}")
        return settings.libreoffice_path
    
    return None


@pytest.fixture
def canvas(qapp):
    """Create a DocumentCanvas instance."""
    canvas = DocumentCanvas()
    yield canvas
    canvas.deleteLater()


@pytest.fixture
def main_window(qapp, settings_store, app_settings):
    """Create a MainWindow instance."""
    window = MainWindow(settings_store=settings_store, settings=app_settings)
    window.show()
    yield window
    window.close()


@pytest.fixture
def signature_object(sample_signature):
    """Create a SignatureObject from the sample signature."""
    from PIL import Image
    img = Image.open(sample_signature).convert("RGBA")
    return SignatureObject(img, str(sample_signature), 100, 100, 0)


@pytest.fixture
def checkmark_annotation():
    """Create a checkmark VectorAnnotation."""
    return VectorAnnotation(AnnotationType.CHECKMARK, 100, 100, 0)


@pytest.fixture
def text_annotation():
    """Create a text VectorAnnotation."""
    return VectorAnnotation(AnnotationType.TEXT, 100, 100, 0, text="Test text")


@pytest.fixture
def arrow_annotation():
    """Create an arrow VectorAnnotation."""
    return VectorAnnotation(AnnotationType.ARROW, 100, 100, 0)


# Test data paths
TEST_DATA_DIR = Path(__file__).parent / "fixtures"
FIXTURES_DIR = Path(__file__).parent / "fixtures"
EXAMPLES_DIR = Path(__file__).parent.parent / "examples"


def pytest_configure(config):
    """Configure pytest with custom markers and options."""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "feature: Feature tests")


def pytest_sessionstart(session):
    """Clear test-results directory at start of each test session.
    
    This ensures each test run starts fresh without accumulated stale results
    from previous runs, keeping the report clean and current.
    """
    import shutil
    test_results_dir = Path(__file__).parent / "test-results"
    if test_results_dir.exists():
        try:
            shutil.rmtree(test_results_dir, ignore_errors=True)
            print(">> Cleared test-results directory for fresh results")
        except Exception as e:
            # If cleanup fails, continue anyway - don't block tests
            print(f"WARNING: Could not clear test-results directory: {e}")


def pytest_sessionfinish(session, exitstatus):
    """Auto-generate test results report after test session."""
    try:
        from tests.utils.test_results import create_comparison_report
        report_path = create_comparison_report()
        if (Path(__file__).parent / "test-results").exists():
            print(f"\n📊 Test comparison report: {report_path}")
    except Exception:
        pass  # Silently skip if report generation fails


def pytest_addoption(parser):
    """Add custom command-line options for pytest."""
    parser.addoption(
        "--libreoffice-path",
        action="store",
        default=None,
        help="Path to LibreOffice soffice executable for testing Word/ODT formats",
    )


def pytest_collection_modifyitems(config, items):
    """Automatically mark tests based on their location."""
    for item in items:
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        elif "feature" in str(item.fspath):
            item.add_marker(pytest.mark.feature)
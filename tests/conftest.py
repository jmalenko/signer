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


@pytest.fixture(scope="session")
def qapp():
    """Create a QApplication instance for the test session."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app


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
    """Create a SettingsStore with a temporary config file."""
    config_path = temp_dir / "config.json"
    store = SettingsStore(app_name="SignerTest")
    store._settings_path = config_path
    return store


@pytest.fixture
def app_settings():
    """Create default AppSettings for testing."""
    return AppSettings()


@pytest.fixture
def libreoffice_path(request):
    """Get LibreOffice path from command line or settings.
    
    Can be provided via:
    - Command line: pytest --libreoffice-path <path>
    - Settings: config.json libreOffice_path field
    
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
    return VectorAnnotation(AnnotationType.ARROW_N, 100, 100, 0)


# Test data paths
TEST_DATA_DIR = Path(__file__).parent / "fixtures"
EXAMPLES_DIR = Path(__file__).parent.parent / "examples"


def pytest_configure(config):
    """Configure pytest with custom markers and options."""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "feature: Feature tests")
    config.addinivalue_line("markers", "slow: Slow tests")
    config.addinivalue_line("markers", "gui: Tests requiring GUI")


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
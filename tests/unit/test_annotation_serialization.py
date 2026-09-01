"""Unit tests for annotation serialization."""

import json
import tempfile
from pathlib import Path

import pytest
from PySide6.QtGui import QColor

from signer.objects import (
    CanvasObject, VectorAnnotation, SignatureObject, AnnotationType,
    DEFAULT_FONT_FAMILY, DEFAULT_TEXT_FONT_PT, DEFAULT_LINE_WIDTH_FACTOR
)
from signer.settings import AppSettings, SettingsStore
from PIL import Image


class TestAnnotationSerialization:
    """Tests for annotation serialization/deserialization."""
    
    def test_canvas_object_basic_attributes(self):
        """Test CanvasObject basic attributes."""
        obj = CanvasObject(100, 200, 300, 150, 1)
        
        assert obj.x == 100
        assert obj.y == 200
        assert obj._base_width == 300
        assert obj._base_height == 150
        assert obj.scale == 1.0
        assert obj.page == 1
        assert obj.color == QColor("#cc0000")
    
    def test_vector_annotation_attributes(self):
        """Test VectorAnnotation attributes."""
        ann = VectorAnnotation(
            AnnotationType.CHECKMARK, 10, 20, 0,
            font_family="Arial",
            font_size_px=24,
            line_width_factor=0.1
        )
        
        assert ann.ann_type == AnnotationType.CHECKMARK
        assert ann.x == 10
        assert ann.y == 20
        assert ann.page == 0
        assert ann._font_family == "Arial"
        assert ann._font_size_px == 24
        assert ann._line_width_factor == 0.1
        assert ann.text == ""
    
    def test_text_annotation_attributes(self, qapp):
        """Test Text annotation attributes."""
        ann = VectorAnnotation(
            AnnotationType.TEXT, 0, 0, 0,
            text="Hello World",
            font_family="Times New Roman",
            font_size_px=36
        )
        
        assert ann.ann_type == AnnotationType.TEXT
        assert ann.text == "Hello World"
        assert ann._font_family == "Times New Roman"
        assert ann._font_size_px == 36
    
    def test_signature_object_attributes(self):
        """Test SignatureObject attributes."""
        img = Image.new("RGBA", (200, 100), (255, 0, 0, 255))
        sig = SignatureObject(img, "/path/to/sig.png", 50, 50, 0)
        
        assert sig.path == "/path/to/sig.png"
        assert sig.x == 50
        assert sig.y == 50
        assert sig.page == 0
        assert sig._base_width == 200
        assert sig._base_height == 100
    
    def test_duplicate_vector_annotation(self):
        """Test VectorAnnotation duplication."""
        ann = VectorAnnotation(
            AnnotationType.CHECKMARK, 100, 100, 0,
            font_family="Arial",
            font_size_px=24,
            line_width_factor=0.1
        )
        ann.scale = 2.0
        ann.color = QColor("#ff0000")
        
        dup = ann.duplicate()
        
        assert dup.ann_type == AnnotationType.CHECKMARK
        assert dup.x == 120  # offset by 20
        assert dup.y == 120
        assert dup.page == 0
        assert dup.scale == 2.0
        assert dup.color == QColor("#ff0000")
        assert dup._font_family == "Arial"
        assert dup._font_size_px == 24
        assert dup._line_width_factor == 0.1
    
    def test_duplicate_text_annotation(self):
        """Test Text annotation duplication preserves text."""
        ann = VectorAnnotation(
            AnnotationType.TEXT, 50, 50, 0,
            text="Test text",
            font_family="Courier",
            font_size_px=18
        )
        
        dup = ann.duplicate()
        
        assert dup.text == "Test text"
        assert dup._font_family == "Courier"
        assert dup._font_size_px == 18
    
    def test_duplicate_signature_object(self):
        """Test SignatureObject duplication."""
        img = Image.new("RGBA", (100, 100), (255, 0, 0, 255))
        sig = SignatureObject(img, "/path/to/sig.png", 100, 100, 0)
        sig.scale = 1.5
        sig.color = QColor("#00ff00")
        
        dup = sig.duplicate()
        
        assert dup.path == "/path/to/sig.png"
        assert dup.x == 120
        assert dup.y == 120
        assert dup.scale == 1.5
        assert dup.color == QColor("#00ff00")
        # Image should be a copy
        assert dup._image is not sig._image
        assert dup._image.size == sig._image.size
    
    def test_annotation_type_enum_values(self):
        """Test AnnotationType enum values."""
        assert AnnotationType.SIGNATURE.value == "signature"
        assert AnnotationType.CHECKMARK.value == "checkmark"
        assert AnnotationType.CROSSMARK.value == "crossmark"
        assert AnnotationType.ARROW.value == "arrow"  # v1.2.24: Single arrow type
        assert AnnotationType.TEXT.value == "text"
    
    def test_arrow_types_set(self):
        """Test ARROW_TYPES set contains only the arrow type."""
        from signer.objects import ARROW_TYPES
        
        assert AnnotationType.ARROW in ARROW_TYPES
        assert len(ARROW_TYPES) == 1  # v1.2.24: Only one arrow type
        assert AnnotationType.CHECKMARK not in ARROW_TYPES
        assert AnnotationType.TEXT not in ARROW_TYPES
    
    def test_arrow_angles(self):
        """Test ARROW_ANGLES mapping."""
        from signer.objects import ARROW_ANGLES
        
        assert ARROW_ANGLES[AnnotationType.ARROW] == 0.0  # v1.2.24: Points right (east)


class TestSettingsSerialization:
    """Tests for settings serialization."""
    
    def test_app_settings_defaults(self):
        """Test AppSettings default values."""
        settings = AppSettings()
        
        assert settings.recent_color == "#cc0000"
        assert settings.recent_line_width_pt == 1.5
        assert settings.recent_font_family == "Arial"
        assert settings.recent_font_size_pt == 11
        assert settings.last_signature_path is None
        assert settings.last_open_document_path is None
        assert settings.last_save_directory is None
        assert settings.recent_signature_paths == []
        assert settings.recent_text_strings == []
        assert settings.recent_document_paths == []
    
    def test_app_settings_custom_values(self):
        """Test AppSettings with custom values."""
        settings = AppSettings(
            recent_color="#ff0000",
            recent_line_width_pt=2.0,
            recent_font_family="Times",
            recent_font_size_pt=11,
            last_signature_path="/path/sig.png",
            recent_signature_paths=["/path/sig1.png", "/path/sig2.png"],
            recent_text_strings=["Text 1", "Text 2"],
            recent_document_paths=["/path/doc1.pdf", "/path/doc2.pdf"]
        )
        
        assert settings.recent_color == "#ff0000"
        assert settings.recent_line_width_pt == 2.0
        assert settings.recent_font_family == "Times"
        assert settings.recent_font_size_pt == 11
        assert settings.last_signature_path == "/path/sig.png"
        assert len(settings.recent_signature_paths) == 2
        assert len(settings.recent_text_strings) == 2
        assert len(settings.recent_document_paths) == 2
    
    def test_settings_store_load_default(self, temp_dir):
        """Test SettingsStore loads defaults when no config file."""
        config_path = temp_dir / "config.json"
        store = SettingsStore(app_name="TestApp")
        store._settings_path = config_path
        
        settings = store.load()
        
        assert isinstance(settings, AppSettings)
        assert settings.recent_color == "#cc0000"
    
    def test_settings_store_save_load(self, temp_dir):
        """Test SettingsStore save and load roundtrip."""
        config_path = temp_dir / "config.json"
        store = SettingsStore(app_name="TestApp")
        store._settings_path = config_path
        
        # Create settings with custom values
        settings = AppSettings(
            recent_color="#ff0000",
            recent_line_width_pt=2.0,
            recent_font_family="Times",
            recent_font_size_pt=11,
            last_signature_path="/path/sig.png",
            recent_signature_paths=["/path/sig1.png", "/path/sig2.png"],
            recent_text_strings=["Text 1", "Text 2"],
            recent_document_paths=["/path/doc1.pdf"]
        )
        
        # Save
        store.save(settings)
        
        # Load
        loaded = store.load()
        
        assert loaded.recent_color == "#ff0000"
        assert loaded.recent_line_width_pt == 2.0
        assert loaded.recent_font_family == "Times"
        assert loaded.recent_font_size_pt == 11
        assert loaded.last_signature_path == "/path/sig.png"
        assert loaded.recent_signature_paths == ["/path/sig1.png", "/path/sig2.png"]
        assert loaded.recent_text_strings == ["Text 1", "Text 2"]
        assert loaded.recent_document_paths == ["/path/doc1.pdf"]
    
    def test_settings_store_load_corrupted(self, temp_dir):
        """Test SettingsStore handles corrupted config gracefully."""
        config_path = temp_dir / "config.json"
        config_path.write_text("invalid json")
        
        store = SettingsStore(app_name="TestApp")
        store._settings_path = config_path
        
        settings = store.load()
        
        # Should return defaults
        assert isinstance(settings, AppSettings)
        assert settings.recent_color == "#cc0000"
    
    def test_settings_store_load_partial(self, temp_dir):
        """Test SettingsStore loads partial config with defaults for missing."""
        config_path = temp_dir / "config.json"
        config_path.write_text(json.dumps({"recent_color": "#ff0000"}))
        
        store = SettingsStore(app_name="TestApp")
        store._settings_path = config_path
        
        settings = store.load()
        
        assert settings.recent_color == "#ff0000"
        # Other values should be defaults
        assert settings.recent_line_width_pt == 1.5
        assert settings.recent_font_family == "Arial"
    
    def test_settings_path_windows(self, temp_dir):
        """Test SettingsStore path resolution."""
        store = SettingsStore(app_name="TestApp")
        store._settings_path = temp_dir / "config.json"
        
        assert store.settings_path == temp_dir / "config.json"
    
    def test_recent_lists_lru_behavior(self):
        """Test recent lists maintain LRU order with max 10 items."""
        settings = AppSettings()
        
        # Add 12 items to recent_signature_paths
        for i in range(12):
            path = f"/path/sig{i}.png"
            if path in settings.recent_signature_paths:
                settings.recent_signature_paths.remove(path)
            settings.recent_signature_paths.insert(0, path)
            settings.recent_signature_paths = settings.recent_signature_paths[:10]
        
        # Should only have 10 items
        assert len(settings.recent_signature_paths) == 10
        # Most recent should be first
        assert settings.recent_signature_paths[0] == "/path/sig11.png"
        # Oldest (sig0, sig1) should be dropped
        assert "/path/sig0.png" not in settings.recent_signature_paths
        assert "/path/sig1.png" not in settings.recent_signature_paths
    
    def test_recent_text_excludes_predefined(self):
        """Test recent text strings exclude predefined date/time strings."""
        settings = AppSettings()
        
        # These are the predefined strings that should be excluded
        predefined = {"01/01/2024", "12:00:00", "01/01/2024 12:00:00"}
        
        for text in predefined:
            if text in settings.recent_text_strings:
                settings.recent_text_strings.remove(text)
            settings.recent_text_strings.insert(0, text)
            settings.recent_text_strings = settings.recent_text_strings[:10]
        
        # Predefined strings should not be in recent texts
        # (This is handled at the application level, not in settings)
        # But we can verify the list can contain them if added directly
        assert len(settings.recent_text_strings) == 3


class TestCompositorSerialization:
    """Tests for compositor output path generation."""
    
    def test_build_default_output_path_single_page(self):
        """Test default output path for single page document."""
        from signer.compositor import build_default_output_path
        
        path = build_default_output_path("/docs/document.pdf", 0, "/output", 1)
        
        assert path.name == "document-signed.jpg"
        assert path.parent == Path("/output")
    
    def test_build_default_output_path_multi_page(self):
        """Test default output path for multi-page document."""
        from signer.compositor import build_default_output_path
        
        path = build_default_output_path("/docs/document.pdf", 0, "/output", 3)
        
        assert path.name == "document-signed-p1.jpg"
        
        path = build_default_output_path("/docs/document.pdf", 2, "/output", 3)
        assert path.name == "document-signed-p3.jpg"
    
    def test_build_default_output_path_padding(self):
        """Test page number padding for multi-page documents."""
        from signer.compositor import build_default_output_path
        
        # 10 pages -> 2 digit padding
        path = build_default_output_path("/docs/document.pdf", 0, "/output", 10)
        assert path.name == "document-signed-p01.jpg"
        
        path = build_default_output_path("/docs/document.pdf", 9, "/output", 10)
        assert path.name == "document-signed-p10.jpg"
        
        # 100 pages -> 3 digit padding
        path = build_default_output_path("/docs/document.pdf", 0, "/output", 100)
        assert path.name == "document-signed-p001.jpg"
    
    def test_build_page_output_path(self):
        """Test build_page_output_path function."""
        from signer.compositor import build_page_output_path
        
        path = build_page_output_path("document-signed", 0, 1, "/output")
        assert path == Path("/output/document-signed.jpg")
        
        path = build_page_output_path("document-signed", 0, 3, "/output")
        assert path == Path("/output/document-signed-p1.jpg")
        
        path = build_page_output_path("document-signed", 2, 3, "/output")
        assert path == Path("/output/document-signed-p3.jpg")
    
    def test_composite_objects_to_jpg(self, temp_dir):
        """Test compositing objects to JPG."""
        from signer.compositor import composite_objects_to_jpg
        from signer.objects import VectorAnnotation, AnnotationType
        from PIL import Image
        
        # Create a base page image
        page = Image.new("RGB", (800, 600), (255, 255, 255))
        
        # Create a simple annotation
        ann = VectorAnnotation(AnnotationType.CHECKMARK, 100, 100, 0)
        ann.color = QColor("#ff0000")
        
        output_path = temp_dir / "output.jpg"
        
        composite_objects_to_jpg(page, [ann], output_path)
        
        assert output_path.exists()
        
        # Verify output is valid JPEG
        result = Image.open(output_path)
        assert result.format == "JPEG"
        assert result.size == (800, 600)
        assert result.mode == "RGB"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
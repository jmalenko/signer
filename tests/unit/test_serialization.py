"""Unit tests for annotation serialization."""

import base64
from io import BytesIO

import pytest
from PIL import Image
from PySide6.QtGui import QColor

from signer.objects import (
    AnnotationType,
    CanvasObject,
    ProjectFile,
    SignatureObject,
    VectorAnnotation,
)


class TestCanvasObjectSerialization:
    """Tests for CanvasObject base serialization."""
    
    def test_canvas_object_to_dict(self):
        """Test basic CanvasObject serialization."""
        obj = CanvasObject(100, 200, 300, 150, 0)
        obj.scale = 2.0
        obj.color = obj.color  # Keep default
        
        data = obj.to_dict()
        
        assert data["type"] == "CanvasObject"
        assert data["x"] == 100
        assert data["y"] == 200
        assert data["base_width"] == 300
        assert data["base_height"] == 150
        assert data["scale"] == 2.0
        assert data["page"] == 0
        assert data["color"] == "#cc0000"
    
    def test_canvas_object_from_dict_not_implemented(self):
        """Test that base class from_dict raises NotImplementedError."""
        with pytest.raises(NotImplementedError):
            CanvasObject.from_dict({})


class TestSignatureObjectSerialization:
    """Tests for SignatureObject serialization."""
    
    def test_signature_object_to_dict(self):
        """Test SignatureObject serialization."""
        img = Image.new("RGBA", (200, 100), (255, 0, 0, 255))
        sig = SignatureObject(img, "test.png", 50, 50, 0)
        sig.scale = 1.5
        
        data = sig.to_dict()
        
        assert data["type"] == "SignatureObject"
        assert data["x"] == 50
        assert data["y"] == 50
        assert data["base_width"] == 200
        assert data["base_height"] == 100
        assert data["scale"] == 1.5
        assert data["page"] == 0
        assert data["color"] == "#cc0000"
        assert data["path"] == "test.png"
        assert "image_data" in data
        
        # Verify image data is valid base64
        img_data = base64.b64decode(data["image_data"])
        restored_img = Image.open(BytesIO(img_data))
        assert restored_img.size == (200, 100)
    
    def test_signature_object_from_dict(self):
        """Test SignatureObject deserialization."""
        img = Image.new("RGBA", (200, 100), (255, 0, 0, 255))
        sig = SignatureObject(img, "test.png", 50, 50, 0)
        sig.scale = 1.5
        
        data = sig.to_dict()
        restored = SignatureObject.from_dict(data)
        
        assert restored.x == 50
        assert restored.y == 50
        assert restored._base_width == 200
        assert restored._base_height == 100
        assert restored.scale == 1.5
        assert restored.page == 0
        assert restored.color.name() == "#cc0000"
        assert restored.path == "test.png"
        assert restored.image.size == (200, 100)
    
    def test_signature_object_roundtrip(self):
        """Test full roundtrip serialization/deserialization."""
        img = Image.new("RGBA", (150, 75), (0, 255, 0, 255))
        sig = SignatureObject(img, "sig.png", 100, 200, 1)
        sig.scale = 0.5
        sig.color = sig.color  # Keep default
        
        data = sig.to_dict()
        restored = SignatureObject.from_dict(data)
        
        # Check all properties match
        assert restored.x == sig.x
        assert restored.y == sig.y
        assert restored._base_width == sig._base_width
        assert restored._base_height == sig._base_height
        assert restored.scale == sig.scale
        assert restored.page == sig.page
        assert restored.color.name() == sig.color.name()
        assert restored.path == sig.path
        assert restored.image.size == sig.image.size


class TestVectorAnnotationSerialization:
    """Tests for VectorAnnotation serialization."""
    
    def test_checkmark_to_dict(self):
        """Test checkmark annotation serialization."""
        ann = VectorAnnotation(AnnotationType.CHECKMARK, 100, 100, 0)
        ann.scale = 2.0
        
        data = ann.to_dict()
        
        assert data["type"] == "VectorAnnotation"
        assert data["x"] == 100
        assert data["y"] == 100
        # 20 * 300/72 = 83.3333...
        assert abs(data["base_width"] - 83.33) < 0.01
        assert abs(data["base_height"] - 83.33) < 0.01
        assert data["scale"] == 2.0
        assert data["page"] == 0
        assert data["color"] == "#cc0000"
        assert data["ann_type"] == "checkmark"
        assert data["text"] == ""
        # Font properties are only saved for TEXT annotations
        assert "font_family" not in data
        assert "font_size_pt" not in data
        assert data["line_width_pt"] == 1.5
        # Natural width/height also scaled
        assert abs(data["natural_width"] - 83.33) < 0.01
        assert abs(data["natural_height"] - 83.33) < 0.01
    
    def test_checkmark_from_dict(self):
        """Test checkmark annotation deserialization."""
        ann = VectorAnnotation(AnnotationType.CHECKMARK, 100, 100, 0)
        ann.scale = 2.0
        
        data = ann.to_dict()
        restored = VectorAnnotation.from_dict(data)
        
        assert restored.x == 100
        assert restored.y == 100
        # 20 * 300/72 = 83.3333...
        assert abs(restored._base_width - 83.33) < 0.01
        assert abs(restored._base_height - 83.33) < 0.01
        assert restored.scale == 2.0
        assert restored.page == 0
        assert restored.color.name() == "#cc0000"
        assert restored.ann_type == AnnotationType.CHECKMARK
        assert restored.text == ""
    
    def test_crossmark_to_dict(self):
        """Test crossmark annotation serialization."""
        ann = VectorAnnotation(AnnotationType.CROSSMARK, 50, 50, 0)
        
        data = ann.to_dict()
        
        assert data["ann_type"] == "crossmark"
        # 20 * 300/72 = 83.3333...
        assert abs(data["base_width"] - 83.33) < 0.01
        assert abs(data["base_height"] - 83.33) < 0.01
    
    def test_arrow_to_dict(self):
        """Test arrow annotation serialization."""
        ann = VectorAnnotation(AnnotationType.ARROW, 0, 0, 0)
        
        data = ann.to_dict()
        
        assert data["ann_type"] == "arrow"
        # 80 * 300/72 = 333.3333...
        assert abs(data["base_width"] - 333.33) < 0.01
        assert abs(data["base_height"] - 333.33) < 0.01
    
    def test_text_annotation_to_dict(self, qapp):
        """Test text annotation serialization."""
        ann = VectorAnnotation(AnnotationType.TEXT, 100, 100, 0, text="Hello World")
        ann.scale = 1.5
        
        data = ann.to_dict()
        
        assert data["ann_type"] == "text"
        assert data["text"] == "Hello World"
        assert data["font_family"] == "Arial"
        assert data["font_size_pt"] == 11
        assert "natural_width" in data
        assert "natural_height" in data
    
    def test_text_annotation_from_dict(self):
        """Test text annotation deserialization."""
        ann = VectorAnnotation(AnnotationType.TEXT, 100, 100, 0, text="Hello World")
        ann.scale = 1.5
        
        data = ann.to_dict()
        restored = VectorAnnotation.from_dict(data)
        
        assert restored.x == 100
        assert restored.y == 100
        assert restored._base_width == ann._base_width
        assert restored._base_height == ann._base_height
        assert restored.scale == 1.5
        assert restored.page == 0
        assert restored.color.name() == "#cc0000"
        assert restored.ann_type == AnnotationType.TEXT
        assert restored.text == "Hello World"
        assert restored._font_family == "Arial"
        assert restored._font_size_pt == 11
    
    def test_text_annotation_custom_font(self):
        """Test text annotation with custom font settings."""
        ann = VectorAnnotation(
            AnnotationType.TEXT, 0, 0, 0, text="Custom",
            font_family="Times New Roman",
            font_size_pt=24,
            line_width_pt=2.5
        )

        data = ann.to_dict()

        assert data["font_family"] == "Times New Roman"
        assert data["font_size_pt"] == 24
        assert data["line_width_pt"] == 2.5

        restored = VectorAnnotation.from_dict(data)
        assert restored._font_family == "Times New Roman"
        assert restored._font_size_pt == 24
        assert restored._line_width_pt == 2.5
    
    def test_multiline_text_annotation(self):
        """Test multiline text annotation serialization."""
        ann = VectorAnnotation(AnnotationType.TEXT, 0, 0, 0, text="Line 1\nLine 2\nLine 3")
        
        data = ann.to_dict()
        restored = VectorAnnotation.from_dict(data)
        
        assert restored.text == "Line 1\nLine 2\nLine 3"
        assert restored._base_height > restored._font_size_pt * 2
    
    def test_vector_annotation_roundtrip(self):
        """Test full roundtrip for all annotation types."""
        for ann_type in [
            AnnotationType.CHECKMARK,
            AnnotationType.CROSSMARK,
            AnnotationType.ARROW,
            AnnotationType.TEXT,
        ]:
            if ann_type == AnnotationType.TEXT:
                ann = VectorAnnotation(ann_type, 10, 20, 0, text="Test")
            else:
                ann = VectorAnnotation(ann_type, 10, 20, 0)
            
            ann.scale = 1.5
            ann.color = ann.color
            
            data = ann.to_dict()
            restored = VectorAnnotation.from_dict(data)
            
            assert restored.x == ann.x
            assert restored.y == ann.y
            assert restored._base_width == ann._base_width
            assert restored._base_height == ann._base_height
            assert restored.scale == ann.scale
            assert restored.page == ann.page
            assert restored.color.name() == ann.color.name()
            assert restored.ann_type == ann.ann_type
            if ann_type == AnnotationType.TEXT:
                assert restored.text == ann.text


class TestSerializationEdgeCases:
    """Tests for edge cases in serialization."""
    
    def test_color_serialization(self):
        """Test that custom colors are serialized correctly."""
        from PySide6.QtGui import QColor
        ann = VectorAnnotation(AnnotationType.CHECKMARK, 0, 0, 0)
        ann.color = QColor("#ff00ff")
        
        data = ann.to_dict()
        assert data["color"] == "#ff00ff"
        
        restored = VectorAnnotation.from_dict(data)
        assert restored.color.name() == "#ff00ff"
    
    def test_page_serialization(self):
        """Test that page number is serialized."""
        ann = VectorAnnotation(AnnotationType.CHECKMARK, 0, 0, 5)
        
        data = ann.to_dict()
        assert data["page"] == 5
        
        restored = VectorAnnotation.from_dict(data)
        assert restored.page == 5
    
    def test_scale_serialization(self):
        """Test that scale is serialized correctly."""
        ann = VectorAnnotation(AnnotationType.CHECKMARK, 0, 0, 0)
        ann.scale = 3.5
        
        data = ann.to_dict()
        assert data["scale"] == 3.5
        
        restored = VectorAnnotation.from_dict(data)
        assert restored.scale == 3.5
    
    def test_signature_with_transparency(self):
        """Test signature with transparent pixels."""
        img = Image.new("RGBA", (100, 100), (255, 0, 0, 128))  # Semi-transparent
        sig = SignatureObject(img, "trans.png", 0, 0, 0)
        
        data = sig.to_dict()
        restored = SignatureObject.from_dict(data)
        
        # Check alpha channel preserved
        assert restored.image.mode == "RGBA"
        pixel = restored.image.getpixel((50, 50))
        assert pixel[3] == 128  # Alpha value

    def test_project_file_uses_same_annotation_schema(self):
        """Project persistence should reuse the same object serialization contract."""
        check = VectorAnnotation(AnnotationType.CHECKMARK, 42, 24, 1)
        sig = SignatureObject(Image.new("RGBA", (20, 10), (0, 0, 0, 255)), "sig.png", 60, 80, 1)

        project = ProjectFile.from_annotations(
            document_path="/tmp/form.pdf",
            export_path="/tmp/form-signed.jpg",
            annotations=[check, sig],
            current_page=1,
            page_count=2,
        )

        assert set(project) == {"version", "document_path", "annotations"}
        assert project["version"] == 1
        assert len(project["annotations"]) == 2
        assert project["annotations"][0]["type"] == "add_annotation"
        assert project["annotations"][1]["type"] == "open_signature"

        restored = ProjectFile.load_annotations(project)
        assert len(restored) == 2
        assert [type(obj).__name__ for obj in restored] == ["VectorAnnotation", "SignatureObject"]
        assert restored[0].page == 1
        assert restored[1].path == "sig.png"

    def test_from_annotations_explicitly_serializes_page_zero(self):
        """Regression test (silent-failure review finding #8): page 0 must be written
        explicitly rather than relying on `if obj.page:` (falsy for 0) plus a matching
        default on the read side - two independently-written defaults silently
        agreeing is fragile, not an explicit contract.
        """
        check = VectorAnnotation(AnnotationType.CHECKMARK, 42, 24, 0)

        project = ProjectFile.from_annotations(
            document_path="/tmp/form.pdf",
            export_path="/tmp/form-signed.jpg",
            annotations=[check],
            current_page=0,
            page_count=1,
        )

        assert project["annotations"][0]["page"] == 0

    def test_project_file_roundtrip_preserves_object_state(self):
        """Round-tripping through the project file should keep the stored object data intact."""
        text = VectorAnnotation(AnnotationType.TEXT, 12, 18, 0, text="Hello")
        text.color = QColor("#123456")
        text.scale = 2.0

        project = ProjectFile.from_annotations(
            document_path="/tmp/example.pdf",
            export_path="/tmp/example-signed.jpg",
            annotations=[text],
            current_page=0,
            page_count=1,
        )

        restored = ProjectFile.load_annotations(project)
        assert len(restored) == 1
        assert restored[0].ann_type == AnnotationType.TEXT
        assert restored[0].text == "Hello"
        assert restored[0].color.name() == "#123456"
        assert restored[0].scale == 2.0

    def test_project_file_roundtrip_preserves_rotation_and_angle(self):
        """Regression test (silent-failure review finding #1): rotating an annotation,
        then saving/reopening the project, must keep the rotation - not silently reset it.
        """
        checkmark = VectorAnnotation(AnnotationType.CHECKMARK, 10, 20, 0)
        checkmark.rotation = 45.0

        line = VectorAnnotation(AnnotationType.LINE, 30, 40, 0)
        line._angle = 30.0

        sig = SignatureObject(Image.new("RGBA", (20, 10), (0, 0, 0, 255)), "sig.png", 5, 5, 0)
        sig.rotation = 90.0

        project = ProjectFile.from_annotations(
            document_path="/tmp/example.pdf",
            export_path="/tmp/example-signed.jpg",
            annotations=[checkmark, line, sig],
            current_page=0,
            page_count=1,
        )

        restored = ProjectFile.load_annotations(project)
        assert restored[0].rotation == 45.0
        assert restored[1]._angle == 30.0
        assert restored[2].rotation == 90.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
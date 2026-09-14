"""Unit tests for bounding box calculations."""

import pytest
from PySide6.QtCore import QRectF, QPointF

from signer.objects import (
    CanvasObject, VectorAnnotation, SignatureObject, AnnotationType,
    HANDLE_FX, HANDLE_FY, ANCHOR_HANDLE
)
from PIL import Image


class TestBoundingBox:
    """Tests for bounding box calculations."""
    
    def test_canvas_object_bounding_box(self):
        """Test basic bounding box of CanvasObject."""
        obj = CanvasObject(100, 200, 300, 150, 0)
        
        # Bounding box in document space
        assert obj.x == 100
        assert obj.y == 200
        assert obj.scaled_width == 300
        assert obj.scaled_height == 150
        
        # Right and bottom edges
        assert obj.x + obj.scaled_width == 400
        assert obj.y + obj.scaled_height == 350
    
    def test_scaled_width_height_properties(self):
        """Test scaled_width and scaled_height properties."""
        obj = CanvasObject(0, 0, 100, 100, 0)
        
        assert obj.scaled_width == 100
        assert obj.scaled_height == 100
        
        obj.scale = 2.0
        assert obj.scaled_width == 200
        assert obj.scaled_height == 200
        
        obj.scale = 0.5
        assert obj.scaled_width == 50
        assert obj.scaled_height == 50
    
    def test_clamp_to_page(self):
        """Test clamping object to page bounds."""
        obj = CanvasObject(100, 100, 200, 200, 0)
        
        # Page is 500x500, object at (100,100) with size 200x200 fits fine
        obj.clamp_to_page(500, 500)
        assert obj.x == 100
        assert obj.y == 100
        
        # Move object partially off page
        obj.x = 450
        obj.y = 450
        obj.clamp_to_page(500, 500)
        # Should be clamped to max(0, 500-200) = 300
        assert obj.x == 300
        assert obj.y == 300
        
        # Move object completely off page
        obj.x = -100
        obj.y = -100
        obj.clamp_to_page(500, 500)
        assert obj.x == 0
        assert obj.y == 0
    
    def test_clamp_to_page_larger_than_page(self):
        """Test clamping when object is larger than page."""
        obj = CanvasObject(0, 0, 1000, 1000, 0)
        
        # Page is 500x500, object is 1000x1000
        obj.clamp_to_page(500, 500)
        # max(0, 500-1000) = max(0, -500) = 0
        assert obj.x == 0
        assert obj.y == 0
    
    def test_vector_annotation_bounding_box(self):
        """Test VectorAnnotation bounding box."""
        # Checkmark has default base size 20 points, scaled to 300 DPI (20 * 300/72 ≈ 83.33 px)
        ann = VectorAnnotation(AnnotationType.CHECKMARK, 50, 50, 0)
        
        assert ann.x == 50
        assert ann.y == 50
        # 20 * 300/72 = 83.3333...
        assert abs(ann._base_width - 83.33) < 0.01
        assert abs(ann._base_height - 83.33) < 0.01
        assert abs(ann.scaled_width - 83.33) < 0.01
        assert abs(ann.scaled_height - 83.33) < 0.01
    
    def test_arrow_annotation_bounding_box(self):
        """Test Arrow annotation bounding box (larger default)."""
        ann = VectorAnnotation(AnnotationType.ARROW, 0, 0, 0)
        
        # Arrows have base size 80 points, scaled to 300 DPI (80 * 300/72 ≈ 333.33 px)
        # 80 * 300/72 = 333.3333...
        assert abs(ann._base_width - 333.33) < 0.01
        assert abs(ann._base_height - 333.33) < 0.01
    
    def test_text_annotation_bounding_box(self, qapp):
        """Test Text annotation bounding box."""
        ann = VectorAnnotation(AnnotationType.TEXT, 0, 0, 0, text="Test")
        
        # Text has default size based on font metrics
        assert ann._base_width > 0
        assert ann._base_height > 0
        assert ann.scale == 1.0
    
    def test_text_fit_text_box(self):
        """Test text box fitting to content."""
        ann = VectorAnnotation(AnnotationType.TEXT, 0, 0, 0, text="Hello World")
        
        # fit_text_box is called in constructor, so box should already fit text
        # Width should be based on text width, height on line height
        assert ann._base_width > 0
        assert ann._base_height > 0
        assert ann.scale == 1.0
        
        # Calling fit_text_box again should not change size
        old_width = ann._base_width
        old_height = ann._base_height
        ann.fit_text_box()
        assert ann._base_width == old_width
        assert ann._base_height == old_height
    
    def test_text_fit_text_box_multiline(self):
        """Test text box fitting with multiple lines."""
        ann = VectorAnnotation(AnnotationType.TEXT, 0, 0, 0, text="Line 1\nLine 2\nLine 3")
        
        # fit_text_box is called in constructor
        # Should have height for 3 lines
        assert ann._base_height > ann._font_size_px * 2
        
        # Verify width is based on widest line
        assert ann._base_width > 0
    
    def test_signature_object_bounding_box(self):
        """Test SignatureObject bounding box."""
        # Create a test image
        img = Image.new("RGBA", (200, 100), (255, 0, 0, 255))
        
        sig = SignatureObject(img, "test.png", 50, 50, 0)
        
        assert sig._base_width == 200
        assert sig._base_height == 100
        assert sig.scaled_width == 200
        assert sig.scaled_height == 100
        
        sig.scale = 0.5
        assert sig.scaled_width == 100
        assert sig.scaled_height == 50

    def test_vector_annotation_hit_test_ignores_transparent_pixels(self):
        """Transparent pixels should not count as a hit for selection."""
        ann = VectorAnnotation(AnnotationType.CROSSMARK, 0, 0, 0)
        img = ann.render_to_pil()

        transparent = None
        opaque = None
        for y in range(img.height):
            for x in range(img.width):
                alpha = img.getpixel((x, y))[3]
                if alpha == 0 and transparent is None:
                    transparent = (x, y)
                if alpha > 0 and opaque is None:
                    opaque = (x, y)
            if transparent is not None and opaque is not None:
                break

        assert transparent is not None
        assert opaque is not None
        assert not ann.hit_test_point(0, 0, ann.scaled_width, ann.scaled_height, QPointF(*transparent))
        assert ann.hit_test_point(0, 0, ann.scaled_width, ann.scaled_height, QPointF(*opaque))

    def test_nearest_visible_annotation_is_selected_when_overlapping(self, canvas):
        """Clicking on overlapping line/arrow should pick the nearer visible annotation."""
        canvas._pages = [Image.new("RGB", (500, 500), (255, 255, 255))]
        canvas._page_objects[0] = []
        canvas._fit_scale = 1.0
        canvas._doc_offset_x = 0.0
        canvas._doc_offset_y = 0.0

        line = VectorAnnotation(AnnotationType.LINE, 90, 90, 0)
        line._angle = 45.0
        line.set_scaled_size(200, 200)

        arrow = VectorAnnotation(AnnotationType.ARROW, 90, 90, 0)
        arrow._angle = 0.0
        arrow.set_scaled_size(200, 200)

        canvas._page_objects[0] = [line, arrow]

        assert canvas._hit_test_object_at_point(QPointF(150, 150)) is line
        assert canvas._hit_test_object_at_point(QPointF(220, 190)) is arrow
        # Transparent space inside the annotation bounding box is selectable.
        assert canvas._hit_test_object_at_point(QPointF(220, 170)) is arrow
        # Overlapping bounding boxes choose the annotation nearest to visible content.
        assert canvas._hit_test_object_at_point(QPointF(145, 135)) is line


class TestHandleRectangles:
    """Tests for handle rectangle calculations."""
    
    def test_handle_positions(self):
        """Test handle position fractions."""
        # 8 handles: TL, TC, TR, ML, MR, BL, BC, BR
        # HANDLE_FX = [0.0, 0.5, 1.0, 0.0, 1.0, 0.0, 0.5, 1.0]
        # HANDLE_FY = [0.0, 0.0, 0.0, 0.5, 0.5, 1.0, 1.0, 1.0]
        
        assert HANDLE_FX[0] == 0.0 and HANDLE_FY[0] == 0.0  # TL
        assert HANDLE_FX[1] == 0.5 and HANDLE_FY[1] == 0.0  # TC
        assert HANDLE_FX[2] == 1.0 and HANDLE_FY[2] == 0.0  # TR
        assert HANDLE_FX[3] == 0.0 and HANDLE_FY[3] == 0.5  # ML
        assert HANDLE_FX[4] == 1.0 and HANDLE_FY[4] == 0.5  # MR
        assert HANDLE_FX[5] == 0.0 and HANDLE_FY[5] == 1.0  # BL
        assert HANDLE_FX[6] == 0.5 and HANDLE_FY[6] == 1.0  # BC
        assert HANDLE_FX[7] == 1.0 and HANDLE_FY[7] == 1.0  # BR
    
    def test_anchor_handles(self):
        """Test anchor handle mapping (opposite handles)."""
        # ANCHOR_HANDLE = [7, 6, 5, 4, 3, 2, 1, 0]
        # Handle 0 (TL) anchors to 7 (BR)
        # Handle 1 (TC) anchors to 6 (BC)
        # etc.
        
        assert ANCHOR_HANDLE[0] == 7
        assert ANCHOR_HANDLE[1] == 6
        assert ANCHOR_HANDLE[2] == 5
        assert ANCHOR_HANDLE[3] == 4
        assert ANCHOR_HANDLE[4] == 3
        assert ANCHOR_HANDLE[5] == 2
        assert ANCHOR_HANDLE[6] == 1
        assert ANCHOR_HANDLE[7] == 0
    
    def test_handle_rects_viewport(self):
        """Test handle rectangles in viewport coordinates."""
        obj = CanvasObject(0, 0, 100, 100, 0)
        
        # Viewport rect at (10, 10) with size (100, 100)
        handles = obj.handle_rects_viewport(10, 10, 100, 100)
        
        assert len(handles) == 8
        
        # Handle size is 10, so each handle rect is 10x10
        # Handle 0 (TL): center at (10, 10), rect at (5, 5, 10, 10)
        assert handles[0].x() == 5.0
        assert handles[0].y() == 5.0
        assert handles[0].width() == 10.0
        assert handles[0].height() == 10.0
        
        # Handle 2 (TR): center at (110, 10), rect at (105, 5, 10, 10)
        assert handles[2].x() == 105.0
        assert handles[2].y() == 5.0
        
        # Handle 7 (BR): center at (110, 110), rect at (105, 105, 10, 10)
        assert handles[7].x() == 105.0
        assert handles[7].y() == 105.0
    
    def test_hit_test_handle(self):
        """Test handle hit testing."""
        obj = CanvasObject(0, 0, 100, 100, 0)
        
        # Viewport rect at (10, 10) with size (100, 100)
        # Handle 0 at (10, 10) with size 10x10 -> rect (5, 5, 10, 10)
        
        # Click in handle 0
        hit = obj.hit_test_handle(10, 10, 100, 100, QPointF(10, 10))
        assert hit == 0
        
        # Click in handle 7 (BR) at (110, 110)
        hit = obj.hit_test_handle(10, 10, 100, 100, QPointF(110, 110))
        assert hit == 7
        
        # Click in center - no handle
        hit = obj.hit_test_handle(10, 10, 100, 100, QPointF(60, 60))
        assert hit == -1
        
        # Click near handle but outside
        hit = obj.hit_test_handle(10, 10, 100, 100, QPointF(0, 0))
        assert hit == -1


class TestResizeCalculations:
    """Tests for resize calculations during handle dragging."""
    
    def test_proportional_resize_corner(self):
        """Test proportional resize from corner handle."""
        obj = VectorAnnotation(AnnotationType.CHECKMARK, 100, 100, 0)
        obj._base_width = 100
        obj._base_height = 100
        obj.scale = 1.0
        
        # Simulate dragging BR handle (handle 7) to double size
        # Anchor is TL (handle 0)
        # New width = 200, new height = 200
        obj.set_scaled_size(200, 200)
        
        assert obj.scale == 2.0
        assert obj.scaled_width == 200
        assert obj.scaled_height == 200
    
    def test_proportional_resize_edge(self):
        """Test proportional resize from edge handle."""
        obj = VectorAnnotation(AnnotationType.CHECKMARK, 100, 100, 0)
        obj._base_width = 100
        obj._base_height = 100
        obj.scale = 1.0
        
        # Drag right edge (handle 4, MR) - anchor is ML (handle 3)
        # Only width changes, height stays same -> proportional scale
        obj.set_scaled_size(200, 100)
        
        # Scale should be max(sx, sy) = max(2.0, 1.0) = 2.0
        assert obj.scale == 2.0
        assert obj.scaled_width == 200
        assert obj.scaled_height == 200
    
    def test_free_resize_text(self):
        """Test free resize for text annotations."""
        obj = VectorAnnotation(AnnotationType.TEXT, 0, 0, 0, text="Test")
        obj._base_width = 100
        obj._base_height = 50
        obj.scale = 1.0
        
        # Text supports free resize
        assert obj.supports_free_resize() is True
        
        # Resize non-proportionally
        obj.set_scaled_size(200, 100)
        
        assert obj._base_width == 200
        assert obj._base_height == 100
        assert obj.scale == 1.0
    
    def test_min_size_clamp(self):
        """Test minimum size clamping."""
        obj = VectorAnnotation(AnnotationType.CHECKMARK, 0, 0, 0)
        
        # Try to set very small size
        obj.set_scaled_size(1, 1)
        
        # Should be clamped to minimum 8x8
        assert obj.scaled_width >= 8
        assert obj.scaled_height >= 8


class TestSquareCircleSnapThreshold:
    """Tests for rectangle/ellipse snap-to-square threshold behavior."""

    @pytest.mark.parametrize(
        "new_w,new_h,handle,expected_w,expected_h,expected_snapped",
        [
            (79.0, 100.0, 4, 79.0, 100.0, False),
            (80.0, 100.0, 4, 100.0, 100.0, True),
            (120.0, 100.0, 4, 100.0, 100.0, True),
            (121.0, 100.0, 4, 121.0, 100.0, False),
        ],
    )
    def test_edge_handle_snap_threshold(self, new_w, new_h, handle, expected_w, expected_h, expected_snapped):
        """Right-edge drag snaps only inside the inclusive +/-20% window."""
        from signer.canvas import DocumentCanvas

        out_w, out_h, snapped = DocumentCanvas._snap_rect_ellipse_size(
            new_w, new_h, handle, modifier_pressed=False
        )

        assert snapped is expected_snapped
        assert out_w == pytest.approx(expected_w)
        assert out_h == pytest.approx(expected_h)

    def test_modifier_prevents_snap_inside_threshold(self):
        """Any modifier key disables snapping even when ratio is in threshold."""
        from signer.canvas import DocumentCanvas

        out_w, out_h, snapped = DocumentCanvas._snap_rect_ellipse_size(
            105.0, 100.0, 4, modifier_pressed=True
        )

        assert snapped is False
        assert out_w == pytest.approx(105.0)
        assert out_h == pytest.approx(100.0)


class TestObjectRectangles:
    """Tests for object rectangle calculations."""
    
    def test_object_view_rect(self):
        """Test _object_view_rect calculation."""
        from signer.canvas import DocumentCanvas
        from PySide6.QtCore import QRectF
        
        canvas = DocumentCanvas()
        canvas._pages = [type('obj', (object,), {'size': (1000, 1000)})()]
        canvas._fit_scale = 0.5
        canvas._doc_offset_x = 100
        canvas._doc_offset_y = 50
        
        obj = CanvasObject(200, 300, 100, 50, 0)
        
        rect = canvas._object_view_rect(obj)
        
        assert isinstance(rect, QRectF)
        assert rect.x() == 200.0  # 100 + 200 * 0.5
        assert rect.y() == 200.0  # 50 + 300 * 0.5
        assert rect.width() == 50.0  # 100 * 0.5
        assert rect.height() == 25.0  # 50 * 0.5
    
    def test_duplicate_preserves_bounds(self):
        """Test that duplicate preserves size and position (offset)."""
        obj = VectorAnnotation(AnnotationType.CHECKMARK, 100, 100, 0)
        obj.scale = 2.0
        obj.color = obj.color  # Keep color
        
        dup = obj.duplicate()
        
        # Duplicate should be offset by 20,20
        assert dup.x == 120
        assert dup.y == 120
        assert dup.scale == 2.0
        assert dup.scaled_width == obj.scaled_width
        assert dup.scaled_height == obj.scaled_height
    
    def test_signature_duplicate_preserves_bounds(self):
        """Test SignatureObject duplicate preserves bounds."""
        img = Image.new("RGBA", (100, 100), (255, 0, 0, 255))
        sig = SignatureObject(img, "test.png", 50, 50, 0)
        sig.scale = 1.5
        
        dup = sig.duplicate()
        
        assert dup.x == 70
        assert dup.y == 70
        assert dup.scale == 1.5
        assert dup.scaled_width == sig.scaled_width
        assert dup.scaled_height == sig.scaled_height


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
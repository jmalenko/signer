"""Unit tests for coordinate transformations."""

import pytest
from PySide6.QtCore import QPointF

from signer.canvas import DocumentCanvas
from signer.objects import CanvasObject, VectorAnnotation, AnnotationType


class TestCoordinateTransforms:
    """Tests for coordinate transformation functions."""
    
    def test_viewport_to_doc_basic(self, canvas):
        """Test basic viewport to document coordinate conversion."""
        # Set up a known state
        canvas._pages = [type('obj', (object,), {'size': (1000, 1000)})()]
        canvas._fit_scale = 0.5
        canvas._doc_offset_x = 100
        canvas._doc_offset_y = 50
        
        # Viewport point (200, 150) should map to doc point (200, 200)
        # (200 - 100) / 0.5 = 200
        # (150 - 50) / 0.5 = 200
        vp_point = QPointF(200, 150)
        doc_point = canvas._view_to_doc(vp_point)
        
        assert doc_point.x() == 200.0
        assert doc_point.y() == 200.0
    
    def test_viewport_to_doc_identity(self, canvas):
        """Test viewport to doc with identity transform."""
        canvas._pages = [type('obj', (object,), {'size': (1000, 1000)})()]
        canvas._fit_scale = 1.0
        canvas._doc_offset_x = 0
        canvas._doc_offset_y = 0
        
        vp_point = QPointF(100, 200)
        doc_point = canvas._view_to_doc(vp_point)
        
        assert doc_point.x() == 100.0
        assert doc_point.y() == 200.0
    
    def test_object_view_rect(self, canvas):
        """Test object view rectangle calculation."""
        canvas._pages = [type('obj', (object,), {'size': (1000, 1000)})()]
        canvas._fit_scale = 0.5
        canvas._doc_offset_x = 100
        canvas._doc_offset_y = 50
        
        obj = CanvasObject(200, 300, 100, 50, 0)
        
        rect = canvas._object_view_rect(obj)
        
        # x = 100 + 200 * 0.5 = 200
        # y = 50 + 300 * 0.5 = 200
        # w = 100 * 0.5 = 50
        # h = 50 * 0.5 = 25
        assert rect.x() == 200.0
        assert rect.y() == 200.0
        assert rect.width() == 50.0
        assert rect.height() == 25.0
    
    def test_recompute_fit(self, canvas):
        """Test fit scale computation."""
        # Create a mock page
        mock_page = type('obj', (object,), {'size': (2000, 1000)})()
        canvas._pages = [mock_page]
        canvas.resize(800, 600)
        
        canvas._recompute_fit()
        
        # Scale should be min(800/2000, 600/1000) = min(0.4, 0.6) = 0.4
        assert canvas._fit_scale == 0.4
        # Offset x = (800 - 2000*0.4)/2 = 0
        # Offset y = (600 - 1000*0.4)/2 = 100
        assert canvas._doc_offset_x == 0.0
        assert canvas._doc_offset_y == 100.0
    
    def test_recompute_fit_no_pages(self, canvas):
        """Test recompute fit with no pages."""
        canvas._pages = []
        canvas._recompute_fit()
        
        assert canvas._fit_scale == 1.0
        assert canvas._doc_offset_x == 0.0
        assert canvas._doc_offset_y == 0.0
    
    def test_default_position_for(self, canvas):
        """Test default position calculation for centered placement."""
        canvas._pages = [type('obj', (object,), {'size': (1000, 1000)})()]
        
        obj = CanvasObject(0, 0, 200, 100, 0)
        
        x, y = canvas.default_position_for(obj)
        
        # Centered: (1000 - 200) / 2 = 400, (1000 - 100) / 2 = 450
        assert x == 400.0
        assert y == 450.0
    
    def test_default_signature_position_for(self, canvas):
        """Test default signature position (80% from top)."""
        canvas._pages = [type('obj', (object,), {'size': (1000, 1000)})()]
        
        obj = CanvasObject(0, 0, 200, 100, 0)
        
        x, y = canvas.default_signature_position_for(obj)
        
        # Centered horizontally: (1000 - 200) / 2 = 400
        # 80% from top: 0.8 * 1000 - 100/2 = 800 - 50 = 750
        assert x == 400.0
        assert y == 750.0
    
    def test_default_position_clamped(self, canvas):
        """Test default position is clamped to page bounds."""
        canvas._pages = [type('obj', (object,), {'size': (100, 100)})()]
        
        # Object larger than page
        obj = CanvasObject(0, 0, 200, 200, 0)
        
        x, y = canvas.default_position_for(obj)
        
        # Should be clamped to 0, 0
        assert x == 0.0
        assert y == 0.0


class TestHandlePositions:
    """Tests for handle position calculations."""
    
    def test_handle_rects_viewport(self, canvas):
        """Test handle rectangle calculation in viewport coordinates."""
        obj = CanvasObject(100, 100, 200, 100, 0)
        
        # Viewport rect at (100, 100) with size (200, 100)
        handles = obj.handle_rects_viewport(100, 100, 200, 100)
        
        # Should have 8 handles
        assert len(handles) == 8
        
        # Handle 0 (TL): at (100, 100) - center of handle
        # Handle size is 10, so rect is (95, 95, 10, 10)
        assert handles[0].x() == 95.0
        assert handles[0].y() == 95.0
        
        # Handle 2 (TR): at (300, 100)
        assert handles[2].x() == 295.0
        assert handles[2].y() == 95.0
        
        # Handle 5 (BL): at (100, 200)
        assert handles[5].x() == 95.0
        assert handles[5].y() == 195.0
        
        # Handle 7 (BR): at (300, 200)
        assert handles[7].x() == 295.0
        assert handles[7].y() == 195.0
    
    def test_hit_test_handle(self, canvas):
        """Test handle hit testing."""
        obj = CanvasObject(100, 100, 200, 100, 0)
        
        # Click on handle 0 (TL) at (100, 100)
        hit = obj.hit_test_handle(100, 100, 200, 100, QPointF(100, 100))
        assert hit == 0
        
        # Click on handle 7 (BR) at (300, 200)
        hit = obj.hit_test_handle(100, 100, 200, 100, QPointF(300, 200))
        assert hit == 7
        
        # Click in middle - no handle
        hit = obj.hit_test_handle(100, 100, 200, 100, QPointF(200, 150))
        assert hit == -1


class TestScaleCalculations:
    """Tests for scale factor calculations during resize."""
    
    def test_set_scaled_size_proportional(self):
        """Test proportional resize (non-text annotations)."""
        obj = VectorAnnotation(AnnotationType.CHECKMARK, 0, 0, 0)
        # Default base size for checkmark is 20 points, scaled to 300 DPI: 83.33 px
        
        # Resize to 166.67 (2x scale)
        obj.set_scaled_size(166.67, 166.67)
        
        assert abs(obj.scale - 2.0) < 0.01
        assert abs(obj.scaled_width - 166.67) < 0.01
        assert abs(obj.scaled_height - 166.67) < 0.01
    
    def test_set_scaled_size_free_resize(self):
        """Test free resize (text annotations)."""
        obj = VectorAnnotation(AnnotationType.TEXT, 0, 0, 0, text="Test")
        obj._base_width = 100
        obj._base_height = 50
        
        # Resize to 200x100 (non-proportional)
        obj.set_scaled_size(200, 100)
        
        assert obj._base_width == 200.0
        assert obj._base_height == 100.0
        assert obj.scale == 1.0
    
    def test_set_scaled_size_min_max_clamp(self):
        """Test scale clamping to min/max."""
        obj = VectorAnnotation(AnnotationType.CHECKMARK, 0, 0, 0)
        # Base size for CHECKMARK is 20 points, scaled to 300 DPI: 83.33 px
        # Minimum width/height is 8 pixels, so minimum scale is 8/83.33 ≈ 0.096
        
        # Try to scale too small
        obj.set_scaled_size(1, 1)
        # Expected: 8 / 83.33 ≈ 0.096 (clamped to min 0.05, but 0.096 > 0.05)
        assert abs(obj.scale - 0.096) < 0.01
        
        # Try to scale too large
        obj.set_scaled_size(10000, 10000)
        assert obj.scale == 10.0  # Maximum scale (clamped to max 10.0)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
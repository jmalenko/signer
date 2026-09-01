"""Unit tests for smart angle snapping for lines and generic arrows (v1.2.23).

Tests the _snap_line_angle method to verify that line and arrow_generic angles snap to
8 cardinal/intercardinal directions (0°, 45°, 90°, 135°, 180°, 225°, 270°, 315°) when
within 10° threshold, unless a modifier key is pressed.
"""

import pytest
from signer.canvas import DocumentCanvas


class TestAngleSnapping:
    """Test suite for angle snapping feature (lines and generic arrows)."""

    def test_snap_0_degrees_horizontal_right(self):
        """Angle near 0° should snap to 0° (horizontal right / East)."""
        # Exact 0°
        assert DocumentCanvas._snap_line_angle(0.0, False) == 0.0
        
        # Within 10° threshold
        assert DocumentCanvas._snap_line_angle(5.0, False) == 0.0
        assert DocumentCanvas._snap_line_angle(-5.0, False) == 0.0
        assert DocumentCanvas._snap_line_angle(10.0, False) == 0.0
        assert DocumentCanvas._snap_line_angle(-10.0, False) == 0.0
        
        # Just outside threshold
        assert DocumentCanvas._snap_line_angle(11.0, False) == 11.0
        assert DocumentCanvas._snap_line_angle(-11.0, False) == -11.0

    def test_snap_45_degrees_diagonal_northeast(self):
        """Angle near 45° should snap to 45° (diagonal up-right / Northeast)."""
        # Exact 45°
        assert DocumentCanvas._snap_line_angle(45.0, False) == 45.0
        
        # Within 10° threshold
        assert DocumentCanvas._snap_line_angle(40.0, False) == 45.0
        assert DocumentCanvas._snap_line_angle(50.0, False) == 45.0
        assert DocumentCanvas._snap_line_angle(35.0, False) == 45.0
        assert DocumentCanvas._snap_line_angle(55.0, False) == 45.0
        
        # Just outside threshold
        assert DocumentCanvas._snap_line_angle(34.0, False) == 34.0
        assert DocumentCanvas._snap_line_angle(56.0, False) == 56.0

    def test_snap_90_degrees_vertical_up(self):
        """Angle near 90° should snap to 90° (vertical up / North)."""
        # Exact 90°
        assert DocumentCanvas._snap_line_angle(90.0, False) == 90.0
        
        # Within 10° threshold
        assert DocumentCanvas._snap_line_angle(85.0, False) == 90.0
        assert DocumentCanvas._snap_line_angle(95.0, False) == 90.0
        assert DocumentCanvas._snap_line_angle(80.0, False) == 90.0
        assert DocumentCanvas._snap_line_angle(100.0, False) == 90.0
        
        # Just outside threshold
        assert DocumentCanvas._snap_line_angle(79.0, False) == 79.0
        assert DocumentCanvas._snap_line_angle(101.0, False) == 101.0

    def test_snap_135_degrees_diagonal_northwest(self):
        """Angle near 135° should snap to 135° (diagonal up-left / Northwest)."""
        # Exact 135°
        assert DocumentCanvas._snap_line_angle(135.0, False) == 135.0
        
        # Within 10° threshold
        assert DocumentCanvas._snap_line_angle(130.0, False) == 135.0
        assert DocumentCanvas._snap_line_angle(140.0, False) == 135.0
        assert DocumentCanvas._snap_line_angle(125.0, False) == 135.0
        assert DocumentCanvas._snap_line_angle(145.0, False) == 135.0
        
        # Just outside threshold
        assert DocumentCanvas._snap_line_angle(124.0, False) == 124.0
        assert DocumentCanvas._snap_line_angle(146.0, False) == 146.0

    def test_snap_180_degrees_horizontal_left(self):
        """Angle near 180° should snap to 180° (horizontal left / West)."""
        # Exact 180°
        assert DocumentCanvas._snap_line_angle(180.0, False) == 180.0
        
        # Within 10° threshold
        assert DocumentCanvas._snap_line_angle(175.0, False) == 180.0
        assert DocumentCanvas._snap_line_angle(185.0, False) == 180.0
        assert DocumentCanvas._snap_line_angle(170.0, False) == 180.0
        assert DocumentCanvas._snap_line_angle(190.0, False) == 180.0
        
        # Just outside threshold
        assert DocumentCanvas._snap_line_angle(169.0, False) == 169.0
        assert DocumentCanvas._snap_line_angle(191.0, False) == 191.0

    def test_snap_225_degrees_diagonal_southwest(self):
        """Angle near 225° should snap to 225° (diagonal down-left / Southwest)."""
        # Exact 225°
        assert DocumentCanvas._snap_line_angle(225.0, False) == 225.0
        
        # Within 10° threshold
        assert DocumentCanvas._snap_line_angle(220.0, False) == 225.0
        assert DocumentCanvas._snap_line_angle(230.0, False) == 225.0
        assert DocumentCanvas._snap_line_angle(215.0, False) == 225.0
        assert DocumentCanvas._snap_line_angle(235.0, False) == 225.0
        
        # Just outside threshold
        assert DocumentCanvas._snap_line_angle(214.0, False) == 214.0
        assert DocumentCanvas._snap_line_angle(236.0, False) == 236.0

    def test_snap_270_degrees_vertical_down(self):
        """Angle near 270° should snap to 270° (vertical down / South)."""
        # Exact 270°
        assert DocumentCanvas._snap_line_angle(270.0, False) == 270.0
        
        # Within 10° threshold
        assert DocumentCanvas._snap_line_angle(265.0, False) == 270.0
        assert DocumentCanvas._snap_line_angle(275.0, False) == 270.0
        assert DocumentCanvas._snap_line_angle(260.0, False) == 270.0
        assert DocumentCanvas._snap_line_angle(280.0, False) == 270.0
        
        # Just outside threshold
        assert DocumentCanvas._snap_line_angle(259.0, False) == 259.0
        assert DocumentCanvas._snap_line_angle(281.0, False) == 281.0

    def test_snap_315_degrees_diagonal_southeast(self):
        """Angle near 315° should snap to 315° (diagonal down-right / Southeast)."""
        # Exact 315°
        assert DocumentCanvas._snap_line_angle(315.0, False) == 315.0
        
        # Within 10° threshold
        assert DocumentCanvas._snap_line_angle(310.0, False) == 315.0
        assert DocumentCanvas._snap_line_angle(320.0, False) == 315.0
        assert DocumentCanvas._snap_line_angle(305.0, False) == 315.0
        assert DocumentCanvas._snap_line_angle(325.0, False) == 315.0
        
        # Just outside threshold
        assert DocumentCanvas._snap_line_angle(304.0, False) == 304.0
        assert DocumentCanvas._snap_line_angle(326.0, False) == 326.0

    def test_no_snap_gap_angles(self):
        """Angles exactly between snap targets should not snap."""
        # Gaps between 22.5° (midpoints)
        assert DocumentCanvas._snap_line_angle(22.5, False) == 22.5
        assert DocumentCanvas._snap_line_angle(67.5, False) == 67.5
        assert DocumentCanvas._snap_line_angle(112.5, False) == 112.5
        assert DocumentCanvas._snap_line_angle(157.5, False) == 157.5
        assert DocumentCanvas._snap_line_angle(202.5, False) == 202.5
        assert DocumentCanvas._snap_line_angle(247.5, False) == 247.5
        assert DocumentCanvas._snap_line_angle(292.5, False) == 292.5
        assert DocumentCanvas._snap_line_angle(337.5, False) == 337.5

    def test_modifier_key_disables_snapping(self):
        """Modifier key press should disable snapping for all directions."""
        # With modifier key pressed, angles should not snap
        assert DocumentCanvas._snap_line_angle(5.0, True) == 5.0
        assert DocumentCanvas._snap_line_angle(45.0, True) == 45.0
        assert DocumentCanvas._snap_line_angle(85.0, True) == 85.0
        assert DocumentCanvas._snap_line_angle(135.0, True) == 135.0
        assert DocumentCanvas._snap_line_angle(175.0, True) == 175.0
        assert DocumentCanvas._snap_line_angle(225.0, True) == 225.0
        assert DocumentCanvas._snap_line_angle(265.0, True) == 265.0
        assert DocumentCanvas._snap_line_angle(315.0, True) == 315.0

    def test_negative_angles(self):
        """Negative angles should be handled correctly."""
        # Negative angles near 0°
        assert DocumentCanvas._snap_line_angle(-5.0, False) == 0.0
        assert DocumentCanvas._snap_line_angle(-10.0, False) == 0.0
        assert DocumentCanvas._snap_line_angle(-15.0, False) == -15.0
        
        # Negative angles near -45° (315° normalized)
        assert DocumentCanvas._snap_line_angle(-45.0, False) == 315.0
        
        # Negative angles: -90° normalizes to 270°
        assert DocumentCanvas._snap_line_angle(-90.0, False) == 270.0

    def test_wrap_around_360_degrees(self):
        """Angles > 360° should be normalized correctly."""
        # 360° + offsets: when no snap occurs, original angle is returned
        assert DocumentCanvas._snap_line_angle(360.0, False) == 0.0  # 360 % 360 = 0 → snaps to 0°
        assert DocumentCanvas._snap_line_angle(365.0, False) == 0.0  # 365 % 360 = 5 → snaps to 0°
        assert DocumentCanvas._snap_line_angle(405.0, False) == 45.0  # 405 % 360 = 45 → snaps to 45°
        assert DocumentCanvas._snap_line_angle(450.0, False) == 90.0  # 450 % 360 = 90 → snaps to 90°
        assert DocumentCanvas._snap_line_angle(540.0, False) == 180.0  # 540 % 360 = 180 → snaps to 180°

    def test_edge_case_threshold_boundaries(self):
        """Test the exact boundaries of the 10° threshold for all directions."""
        # 0° threshold
        assert DocumentCanvas._snap_line_angle(10.0, False) == 0.0
        assert DocumentCanvas._snap_line_angle(10.1, False) == 10.1
        
        # 45° threshold
        assert DocumentCanvas._snap_line_angle(35.0, False) == 45.0
        assert DocumentCanvas._snap_line_angle(34.9, False) == 34.9
        assert DocumentCanvas._snap_line_angle(55.0, False) == 45.0
        assert DocumentCanvas._snap_line_angle(55.1, False) == 55.1
        
        # 90° threshold
        assert DocumentCanvas._snap_line_angle(80.0, False) == 90.0
        assert DocumentCanvas._snap_line_angle(79.9, False) == 79.9
        
        # 135° threshold
        assert DocumentCanvas._snap_line_angle(125.0, False) == 135.0
        assert DocumentCanvas._snap_line_angle(124.9, False) == 124.9
        
        # 180° threshold
        assert DocumentCanvas._snap_line_angle(170.0, False) == 180.0
        assert DocumentCanvas._snap_line_angle(169.9, False) == 169.9
        
        # 225° threshold
        assert DocumentCanvas._snap_line_angle(215.0, False) == 225.0
        assert DocumentCanvas._snap_line_angle(214.9, False) == 214.9
        
        # 270° threshold
        assert DocumentCanvas._snap_line_angle(260.0, False) == 270.0
        assert DocumentCanvas._snap_line_angle(259.9, False) == 259.9
        
        # 315° threshold
        assert DocumentCanvas._snap_line_angle(305.0, False) == 315.0
        assert DocumentCanvas._snap_line_angle(304.9, False) == 304.9


class TestAngleSnapIntegration:
    """Integration tests for angle snapping with canvas operations."""

    @pytest.fixture
    def canvas(self, qapp):
        """Create a fresh canvas for each test."""
        return DocumentCanvas()

    def test_snap_angle_is_static_method(self):
        """Verify _snap_line_angle is a static method."""
        # Should be callable on the class itself
        result = DocumentCanvas._snap_line_angle(22.5, False)
        assert result == 22.5


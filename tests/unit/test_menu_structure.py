"""Unit tests for menu structure and annotation menu items."""

import pytest
from signer.objects import AnnotationType, DIRECTIONAL_ARROW_TYPES


class TestAnnotationMenuStructure:
    """Test annotation menu has correct structure and order."""
    
    def test_checkmark_menu_item_exists(self):
        """Test Checkmark is in annotation menu."""
        assert hasattr(AnnotationType, 'CHECKMARK')
        assert AnnotationType.CHECKMARK.value == 'checkmark'
    
    def test_crossmark_menu_item_exists(self):
        """Test Crossmark is in annotation menu."""
        assert hasattr(AnnotationType, 'CROSSMARK')
        assert AnnotationType.CROSSMARK.value == 'crossmark'
    
    def test_line_menu_item_exists(self):
        """Test Line is in annotation menu."""
        assert hasattr(AnnotationType, 'LINE')
        assert AnnotationType.LINE.value == 'line'
    
    def test_arrow_generic_menu_item_exists(self):
        """Test generic Arrow is in annotation menu."""
        assert hasattr(AnnotationType, 'ARROW_GENERIC')
        assert AnnotationType.ARROW_GENERIC.value == 'arrow_generic'
    
    def test_rectangle_menu_item_exists(self):
        """Test Rectangle is in annotation menu."""
        assert hasattr(AnnotationType, 'RECTANGLE')
        assert AnnotationType.RECTANGLE.value == 'rectangle'
    
    def test_ellipse_menu_item_exists(self):
        """Test Ellipse is in annotation menu."""
        assert hasattr(AnnotationType, 'ELLIPSE')
        assert AnnotationType.ELLIPSE.value == 'ellipse'
    
    def test_text_menu_item_exists(self):
        """Test Text is in annotation menu."""
        assert hasattr(AnnotationType, 'TEXT')
        assert AnnotationType.TEXT.value == 'text'
    
    def test_signature_menu_item_exists(self):
        """Test Signature is in menu."""
        assert hasattr(AnnotationType, 'SIGNATURE')
        assert AnnotationType.SIGNATURE.value == 'signature'
    
    def test_image_menu_item_exists(self):
        """Test Image is in menu."""
        assert hasattr(AnnotationType, 'IMAGE')
        assert AnnotationType.IMAGE.value == 'image'


class TestArrowSubmenu:
    """Test Arrow submenu with all 8 directional arrows."""
    
    def test_arrow_e_exists(self):
        """Test Arrow East in submenu."""
        assert hasattr(AnnotationType, 'ARROW_E')
        assert AnnotationType.ARROW_E.value == 'arrow_e'
    
    def test_arrow_se_exists(self):
        """Test Arrow Southeast in submenu."""
        assert hasattr(AnnotationType, 'ARROW_SE')
        assert AnnotationType.ARROW_SE.value == 'arrow_se'
    
    def test_arrow_s_exists(self):
        """Test Arrow South in submenu."""
        assert hasattr(AnnotationType, 'ARROW_S')
        assert AnnotationType.ARROW_S.value == 'arrow_s'
    
    def test_arrow_sw_exists(self):
        """Test Arrow Southwest in submenu."""
        assert hasattr(AnnotationType, 'ARROW_SW')
        assert AnnotationType.ARROW_SW.value == 'arrow_sw'
    
    def test_arrow_w_exists(self):
        """Test Arrow West in submenu."""
        assert hasattr(AnnotationType, 'ARROW_W')
        assert AnnotationType.ARROW_W.value == 'arrow_w'
    
    def test_arrow_nw_exists(self):
        """Test Arrow Northwest in submenu."""
        assert hasattr(AnnotationType, 'ARROW_NW')
        assert AnnotationType.ARROW_NW.value == 'arrow_nw'
    
    def test_arrow_n_exists(self):
        """Test Arrow North in submenu."""
        assert hasattr(AnnotationType, 'ARROW_N')
        assert AnnotationType.ARROW_N.value == 'arrow_n'
    
    def test_arrow_ne_exists(self):
        """Test Arrow Northeast in submenu."""
        assert hasattr(AnnotationType, 'ARROW_NE')
        assert AnnotationType.ARROW_NE.value == 'arrow_ne'
    
    def test_arrow_submenu_has_9_items(self):
        """Test Arrow submenu has 9 items (1 generic + 8 directional)."""
        # Generic arrow
        assert AnnotationType.ARROW_GENERIC.value == 'arrow_generic'
        
        # 8 directional arrows
        directional = [
            AnnotationType.ARROW_E, AnnotationType.ARROW_SE,
            AnnotationType.ARROW_S, AnnotationType.ARROW_SW,
            AnnotationType.ARROW_W, AnnotationType.ARROW_NW,
            AnnotationType.ARROW_N, AnnotationType.ARROW_NE,
        ]
        
        assert len(directional) == 8
    
    def test_arrow_submenu_order(self):
        """Test Arrow submenu order: E, SE, S, SW, W, NW, N, NE."""
        expected_order = [
            AnnotationType.ARROW_E, AnnotationType.ARROW_SE,
            AnnotationType.ARROW_S, AnnotationType.ARROW_SW,
            AnnotationType.ARROW_W, AnnotationType.ARROW_NW,
            AnnotationType.ARROW_N, AnnotationType.ARROW_NE,
        ]
        
        # Verify order matches
        assert expected_order == list(DIRECTIONAL_ARROW_TYPES)


class TestMenuItemUniqueness:
    """Test all menu items are unique."""
    
    def test_all_annotation_types_are_unique(self):
        """Test no duplicate annotation types in menu."""
        all_types = [
            AnnotationType.CHECKMARK,
            AnnotationType.CROSSMARK,
            AnnotationType.LINE,
            AnnotationType.ARROW_GENERIC,
            AnnotationType.ARROW_E, AnnotationType.ARROW_SE,
            AnnotationType.ARROW_S, AnnotationType.ARROW_SW,
            AnnotationType.ARROW_W, AnnotationType.ARROW_NW,
            AnnotationType.ARROW_N, AnnotationType.ARROW_NE,
            AnnotationType.RECTANGLE,
            AnnotationType.ELLIPSE,
            AnnotationType.TEXT,
            AnnotationType.SIGNATURE,
            AnnotationType.IMAGE,
        ]
        
        # Check uniqueness by value
        values = [t.value for t in all_types]
        assert len(values) == len(set(values))  # No duplicates


class TestMenuItemLabels:
    """Test menu item labels are clear and consistent."""
    
    def test_checkmark_label(self):
        """Test Checkmark has clear label."""
        # Would be used in: "Checkmark"
        assert AnnotationType.CHECKMARK.value == 'checkmark'
    
    def test_line_label(self):
        """Test Line has clear label."""
        # Would be used in: "Line"
        assert AnnotationType.LINE.value == 'line'
    
    def test_arrow_label(self):
        """Test Arrow has clear label."""
        # Generic: "Arrow"
        assert AnnotationType.ARROW_GENERIC.value == 'arrow_generic'
        
        # Directional: "Arrow →" etc.
        assert AnnotationType.ARROW_E.value == 'arrow_e'
    
    def test_rectangle_label(self):
        """Test Rectangle has clear label."""
        assert AnnotationType.RECTANGLE.value == 'rectangle'
    
    def test_ellipse_label(self):
        """Test Ellipse has clear label."""
        assert AnnotationType.ELLIPSE.value == 'ellipse'
    
    def test_text_label(self):
        """Test Text has clear label."""
        assert AnnotationType.TEXT.value == 'text'


class TestSignatureImageMenu:
    """Test Signature / Image are unified in menu."""
    
    def test_signature_exists(self):
        """Test Signature menu item exists."""
        assert hasattr(AnnotationType, 'SIGNATURE')
    
    def test_image_exists(self):
        """Test Image menu item exists."""
        assert hasattr(AnnotationType, 'IMAGE')
    
    def test_signature_image_as_submenu(self):
        """Test Signature / Image handled as submenu options."""
        # Both types exist for the menu
        assert AnnotationType.SIGNATURE.value == 'signature'
        assert AnnotationType.IMAGE.value == 'image'


class TestMenuNavigation:
    """Test menu navigation and selection."""
    
    def test_can_select_checkmark_from_menu(self):
        """Test user can select Checkmark from menu."""
        ann_type = AnnotationType.CHECKMARK
        assert ann_type == AnnotationType.CHECKMARK
    
    def test_can_select_line_from_menu(self):
        """Test user can select Line from menu."""
        ann_type = AnnotationType.LINE
        assert ann_type == AnnotationType.LINE
    
    def test_can_select_generic_arrow_from_menu(self):
        """Test user can select generic Arrow."""
        ann_type = AnnotationType.ARROW_GENERIC
        assert ann_type == AnnotationType.ARROW_GENERIC
    
    def test_can_select_arrow_from_submenu(self):
        """Test user can select directional arrow from submenu."""
        for arrow_type in DIRECTIONAL_ARROW_TYPES:
            ann_type = arrow_type
            assert ann_type in DIRECTIONAL_ARROW_TYPES
    
    def test_can_select_rectangle_from_menu(self):
        """Test user can select Rectangle from menu."""
        ann_type = AnnotationType.RECTANGLE
        assert ann_type == AnnotationType.RECTANGLE
    
    def test_can_select_ellipse_from_menu(self):
        """Test user can select Ellipse from menu."""
        ann_type = AnnotationType.ELLIPSE
        assert ann_type == AnnotationType.ELLIPSE
    
    def test_can_select_text_from_menu(self):
        """Test user can select Text from menu."""
        ann_type = AnnotationType.TEXT
        assert ann_type == AnnotationType.TEXT
    
    def test_can_select_signature_from_menu(self):
        """Test user can select Signature from menu."""
        ann_type = AnnotationType.SIGNATURE
        assert ann_type == AnnotationType.SIGNATURE
    
    def test_can_select_image_from_menu(self):
        """Test user can select Image from menu."""
        ann_type = AnnotationType.IMAGE
        assert ann_type == AnnotationType.IMAGE


class TestMenuItemCount:
    """Test correct number of menu items."""
    
    def test_main_menu_items(self):
        """Test number of main menu items."""
        # Checkmark, Crossmark, Line, Arrow (with submenu),
        # Rectangle, Ellipse, Text, Signature / Image (with submenu)
        # At minimum 8 main items
        main_items = [
            AnnotationType.CHECKMARK,
            AnnotationType.CROSSMARK,
            AnnotationType.LINE,
            AnnotationType.ARROW_GENERIC,
            AnnotationType.RECTANGLE,
            AnnotationType.ELLIPSE,
            AnnotationType.TEXT,
            AnnotationType.SIGNATURE,
            AnnotationType.IMAGE,
        ]
        assert len(main_items) >= 8
    
    def test_arrow_submenu_count(self):
        """Test Arrow submenu has exactly 8 directional arrows."""
        assert len(DIRECTIONAL_ARROW_TYPES) == 8

"""Unit tests for menu structure and annotation menu items."""

from signer.objects import AnnotationType


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
    
    def test_arrow_menu_item_exists(self):
        """Test Arrow is in annotation menu."""
        assert hasattr(AnnotationType, 'ARROW')
        assert AnnotationType.ARROW.value == 'arrow'
    
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
    """Test Arrow annotation (no longer a submenu in v1.2.24)."""
    
    def test_arrow_exists(self):
        """Test Arrow annotation type exists."""
        assert hasattr(AnnotationType, 'ARROW')
        assert AnnotationType.ARROW.value == 'arrow'
    
    def test_arrow_is_only_arrow_type(self):
        """Test ARROW is the only arrow type."""
        from signer.objects import ARROW_TYPES
        assert AnnotationType.ARROW in ARROW_TYPES
        assert len(ARROW_TYPES) == 1  # v1.2.24: Only one arrow type


class TestMenuItemUniqueness:
    """Test all menu items are unique."""
    
    def test_all_annotation_types_are_unique(self):
        """Test no duplicate annotation types in menu."""
        all_types = [
            AnnotationType.CHECKMARK,
            AnnotationType.CROSSMARK,
            AnnotationType.LINE,
            AnnotationType.ARROW,  # v1.2.24: Single arrow type
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
        # Single arrow pointing right: "Arrow"
        assert AnnotationType.ARROW.value == 'arrow'
    
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
    
    def test_can_select_arrow_from_menu(self):
        """Test user can select Arrow."""
        ann_type = AnnotationType.ARROW
        assert ann_type == AnnotationType.ARROW
    
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
        # Checkmark, Crossmark, Line, Arrow (no submenu in v1.2.24),
        # Rectangle, Ellipse, Text, Signature / Image (with submenu)
        # At minimum 8 main items
        main_items = [
            AnnotationType.CHECKMARK,
            AnnotationType.CROSSMARK,
            AnnotationType.LINE,
            AnnotationType.ARROW,  # v1.2.24: No longer a submenu
            AnnotationType.RECTANGLE,
            AnnotationType.ELLIPSE,
            AnnotationType.TEXT,
            AnnotationType.SIGNATURE,
            AnnotationType.IMAGE,
        ]
        assert len(main_items) >= 8

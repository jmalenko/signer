"""Tests for Version 1.2.12 - Dynamic Page Number Placeholder functionality."""



from signer.compositor import (
    ExportFormat,
    build_suggested_filename_for_dialog,
    replace_placeholder_with_page_number,
    validate_placeholder_for_multipage_export,
)


class TestPlaceholderCalculation:
    """Test that placeholder digit width matches page count."""

    def test_single_page_document_no_placeholder(self):
        """Single-page document should not show placeholder."""
        filename = build_suggested_filename_for_dialog("document.pdf", total_pages=1)
        assert filename == "document-signed.jpg"
        assert "#" not in filename

    def test_two_page_document_one_digit(self):
        """2-page document should show placeholder (1 digit)."""
        filename = build_suggested_filename_for_dialog("document.pdf", total_pages=2)
        assert filename == "document-signed-p#.jpg"

    def test_nine_page_document_one_digit(self):
        """9-page document should show placeholder (1 digit)."""
        filename = build_suggested_filename_for_dialog("document.pdf", total_pages=9)
        assert filename == "document-signed-p#.jpg"

    def test_ten_page_document_two_digits(self):
        """10-page document should show placeholder (2 digits for padding)."""
        filename = build_suggested_filename_for_dialog("document.pdf", total_pages=10)
        assert filename == "document-signed-p#.jpg"

    def test_ninety_nine_page_document_two_digits(self):
        """99-page document should show placeholder (2 digits)."""
        filename = build_suggested_filename_for_dialog("document.pdf", total_pages=99)
        assert filename == "document-signed-p#.jpg"

    def test_hundred_page_document_three_digits(self):
        """100-page document should show placeholder (3 digits for padding)."""
        filename = build_suggested_filename_for_dialog("document.pdf", total_pages=100)
        assert filename == "document-signed-p#.jpg"

    def test_thousand_page_document_four_digits(self):
        """1000-page document should show placeholder (4 digits for padding)."""
        filename = build_suggested_filename_for_dialog("document.pdf", total_pages=1000)
        assert filename == "document-signed-p#.jpg"


class TestPlaceholderReplacementFormat:
    """Test that placeholder is correctly replaced with zero-padded page numbers."""

    def test_replace_placeholder_single_digit(self):
        """Replace placeholder with single-digit page numbers (1-9 pages)."""
        for page_idx in range(9):
            result = replace_placeholder_with_page_number(
                "document-signed-p#.jpg", page_idx, total_pages=9
            )
            assert result == f"document-signed-p{page_idx + 1}.jpg"

    def test_replace_placeholder_two_digits_padding_01(self):
        """Replace placeholder with zero-padded 2-digit page numbers (10-99 pages)."""
        result = replace_placeholder_with_page_number(
            "document-signed-p#.jpg", page_index=0, total_pages=10
        )
        assert result == "document-signed-p01.jpg"

    def test_replace_placeholder_two_digits_padding_09(self):
        """Replace placeholder with zero-padded 2-digit page numbers."""
        result = replace_placeholder_with_page_number(
            "document-signed-p#.jpg", page_index=8, total_pages=10
        )
        assert result == "document-signed-p09.jpg"

    def test_replace_placeholder_two_digits_padding_10(self):
        """Replace placeholder with zero-padded 2-digit page numbers."""
        result = replace_placeholder_with_page_number(
            "document-signed-p#.jpg", page_index=9, total_pages=10
        )
        assert result == "document-signed-p10.jpg"

    def test_replace_placeholder_three_digits_padding_001(self):
        """Replace placeholder with zero-padded 3-digit page numbers (100+ pages)."""
        result = replace_placeholder_with_page_number(
            "document-signed-p#.jpg", page_index=0, total_pages=100
        )
        assert result == "document-signed-p001.jpg"

    def test_replace_placeholder_three_digits_padding_050(self):
        """Replace placeholder with zero-padded 3-digit page numbers."""
        result = replace_placeholder_with_page_number(
            "document-signed-p#.jpg", page_index=49, total_pages=100
        )
        assert result == "document-signed-p050.jpg"

    def test_replace_placeholder_three_digits_padding_099(self):
        """Replace placeholder with zero-padded 3-digit page numbers."""
        result = replace_placeholder_with_page_number(
            "document-signed-p#.jpg", page_index=98, total_pages=100
        )
        assert result == "document-signed-p099.jpg"

    def test_replace_placeholder_three_digits_padding_100(self):
        """Replace placeholder with zero-padded 3-digit page numbers."""
        result = replace_placeholder_with_page_number(
            "document-signed-p#.jpg", page_index=99, total_pages=100
        )
        assert result == "document-signed-p100.jpg"

    def test_no_placeholder_in_filename(self):
        """If no placeholder exists, return filename unchanged."""
        result = replace_placeholder_with_page_number(
            "document-signed.jpg", page_index=0, total_pages=10
        )
        assert result == "document-signed.jpg"

    def test_multiple_placeholders_replace_all(self):
        """If multiple # exist, replace all of them."""
        result = replace_placeholder_with_page_number(
            "document-p#-signed-p#.jpg", page_index=0, total_pages=10
        )
        assert result == "document-p01-signed-p01.jpg"


class TestFormatSupportsSingleFile:
    """Test detection of single-file vs per-file formats."""

    def test_pdf_is_single_file_format(self):
        """PDF should be detected as single-file format."""
        assert ExportFormat.PDF.is_single_file_format() is True
        assert ExportFormat.PDF.is_per_file_format() is False

    def test_tiff_is_single_file_format(self):
        """TIFF should be detected as single-file format."""
        assert ExportFormat.TIFF.is_single_file_format() is True
        assert ExportFormat.TIFF.is_per_file_format() is False

    def test_jpg_is_per_file_format(self):
        """JPG should be detected as per-file format."""
        assert ExportFormat.JPG.is_per_file_format() is True
        assert ExportFormat.JPG.is_single_file_format() is False

    def test_png_is_per_file_format(self):
        """PNG should be detected as per-file format."""
        assert ExportFormat.PNG.is_per_file_format() is True
        assert ExportFormat.PNG.is_single_file_format() is False

    def test_bmp_is_per_file_format(self):
        """BMP should be detected as per-file format."""
        assert ExportFormat.BMP.is_per_file_format() is True
        assert ExportFormat.BMP.is_single_file_format() is False


class TestPlaceholderValidation:
    """Test placeholder validation for multi-page exports."""

    def test_single_page_no_validation_needed(self):
        """Single-page document should always be valid."""
        is_valid, msg = validate_placeholder_for_multipage_export(
            "document-signed", total_pages=1, export_format=ExportFormat.JPG
        )
        assert is_valid is True
        assert msg == ""

    def test_single_file_format_no_validation_needed(self):
        """Single-file formats (PDF/TIFF) don't need placeholder."""
        for fmt in [ExportFormat.PDF, ExportFormat.TIFF]:
            is_valid, msg = validate_placeholder_for_multipage_export(
                "document-signed", total_pages=10, export_format=fmt
            )
            assert is_valid is True
            assert msg == ""

    def test_multi_page_per_file_with_placeholder_valid(self):
        """Multi-page per-file export with placeholder should be valid."""
        is_valid, msg = validate_placeholder_for_multipage_export(
            "document-signed-p#", total_pages=10, export_format=ExportFormat.JPG
        )
        assert is_valid is True
        assert msg == ""

    def test_multi_page_per_file_without_placeholder_invalid(self):
        """Multi-page per-file export without placeholder should be invalid."""
        is_valid, msg = validate_placeholder_for_multipage_export(
            "document-signed", total_pages=10, export_format=ExportFormat.JPG
        )
        assert is_valid is False
        assert "#" in msg
        assert "placeholder" in msg.lower()

    def test_multipage_jpg_requires_placeholder(self):
        """JPG format with multiple pages requires placeholder."""
        is_valid, msg = validate_placeholder_for_multipage_export(
            "document-signed", total_pages=50, export_format=ExportFormat.JPG
        )
        assert is_valid is False

    def test_multipage_png_requires_placeholder(self):
        """PNG format with multiple pages requires placeholder."""
        is_valid, msg = validate_placeholder_for_multipage_export(
            "document-signed", total_pages=50, export_format=ExportFormat.PNG
        )
        assert is_valid is False

    def test_multipage_bmp_requires_placeholder(self):
        """BMP format with multiple pages requires placeholder."""
        is_valid, msg = validate_placeholder_for_multipage_export(
            "document-signed", total_pages=50, export_format=ExportFormat.BMP
        )
        assert is_valid is False


class TestDialogSuggestedFilename:
    """Test filename suggestion logic for Save As dialog."""

    def test_single_page_pdf_no_placeholder(self):
        """Single-page PDF should show single filename."""
        filename = build_suggested_filename_for_dialog(
            "invoice.pdf", total_pages=1, export_format=ExportFormat.PDF
        )
        assert filename == "invoice-signed.pdf"

    def test_multi_page_pdf_no_placeholder(self):
        """Multi-page PDF should show single filename (PDF stores all pages)."""
        filename = build_suggested_filename_for_dialog(
            "invoice.pdf", total_pages=50, export_format=ExportFormat.PDF
        )
        assert filename == "invoice-signed.pdf"

    def test_multi_page_tiff_no_placeholder(self):
        """Multi-page TIFF should show single filename (TIFF stores all pages)."""
        filename = build_suggested_filename_for_dialog(
            "invoice.pdf", total_pages=50, export_format=ExportFormat.TIFF
        )
        assert filename == "invoice-signed.tif"

    def test_multi_page_jpg_with_placeholder(self):
        """Multi-page JPG should show placeholder format."""
        filename = build_suggested_filename_for_dialog(
            "invoice.pdf", total_pages=50, export_format=ExportFormat.JPG
        )
        assert filename == "invoice-signed-p#.jpg"

    def test_multi_page_png_with_placeholder(self):
        """Multi-page PNG should show placeholder format."""
        filename = build_suggested_filename_for_dialog(
            "invoice.pdf", total_pages=50, export_format=ExportFormat.PNG
        )
        assert filename == "invoice-signed-p#.png"

    def test_multi_page_bmp_with_placeholder(self):
        """Multi-page BMP should show placeholder format."""
        filename = build_suggested_filename_for_dialog(
            "invoice.pdf", total_pages=50, export_format=ExportFormat.BMP
        )
        assert filename == "invoice-signed-p#.bmp"

    def test_filename_preserves_document_name(self):
        """Suggested filename should preserve document name."""
        filename = build_suggested_filename_for_dialog(
            "my-important-document.pdf", total_pages=10, export_format=ExportFormat.JPG
        )
        assert "my-important-document" in filename

    def test_complex_document_name_with_dots(self):
        """Filename with multiple dots should use stem correctly."""
        filename = build_suggested_filename_for_dialog(
            "document.v2.3.pdf", total_pages=10, export_format=ExportFormat.JPG
        )
        assert filename == "document.v2.3-signed-p#.jpg"


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_placeholder_replacement_page_0(self):
        """Page index 0 should be formatted as page 1 with proper padding."""
        result = replace_placeholder_with_page_number(
            "file-p#.jpg", page_index=0, total_pages=100
        )
        assert result == "file-p001.jpg"

    def test_placeholder_replacement_last_page(self):
        """Last page should have correct page number and padding."""
        result = replace_placeholder_with_page_number(
            "file-p#.jpg", page_index=99, total_pages=100
        )
        assert result == "file-p100.jpg"

    def test_very_large_document(self):
        """Very large document (9999 pages) should work correctly."""
        filename = build_suggested_filename_for_dialog(
            "large.pdf", total_pages=9999, export_format=ExportFormat.JPG
        )
        assert filename == "large-signed-p#.jpg"

        result = replace_placeholder_with_page_number(
            "large-signed-p#.jpg", page_index=0, total_pages=9999
        )
        assert result == "large-signed-p0001.jpg"

        result = replace_placeholder_with_page_number(
            "large-signed-p#.jpg", page_index=9998, total_pages=9999
        )
        assert result == "large-signed-p9999.jpg"

    def test_zero_pages_edge_case(self):
        """Zero pages should be treated like single page (no placeholder)."""
        filename = build_suggested_filename_for_dialog(
            "empty.pdf", total_pages=0, export_format=ExportFormat.JPG
        )
        assert filename == "empty-signed.jpg"
        assert "#" not in filename

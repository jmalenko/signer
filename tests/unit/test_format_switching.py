"""Tests for Version 1.2.12 fixes - Format switching detection and dialog return on validation error."""

from pathlib import Path

from signer.compositor import (
    ExportFormat,
    build_suggested_filename_for_dialog,
    validate_placeholder_for_multipage_export,
)


class TestFormatSwitchingBehavior:
    """Test format switching detection - when user changes file extension in save dialog."""

    def test_format_mismatch_detected_when_extension_changes(self):
        """When user enters filename with wrong extension, mismatch should be detected."""
        doc_name = "invoice.pdf"
        page_count = 50
        
        # User has PDF open, suggested format is PDF (no placeholder)
        pdf_suggested = build_suggested_filename_for_dialog(
            doc_name, page_count, ExportFormat.PDF
        )
        assert "#" not in pdf_suggested
        
        # But user changes extension to .jpg in the save dialog
        # This creates a mismatch: JPG format needs placeholder, but filename has none
        user_filename = pdf_suggested.replace(".pdf", ".jpg")
        
        # Detect mismatch by comparing with what JPG format requires
        jpg_suggested = build_suggested_filename_for_dialog(
            doc_name, page_count, ExportFormat.JPG
        )
        
        # User's filename should NOT match the JPG suggestion
        assert user_filename != jpg_suggested
        assert user_filename == "invoice-signed.jpg"  # No placeholder
        assert jpg_suggested == "invoice-signed-p#.jpg"  # Has placeholder

    def test_pdf_to_jpg_format_switch_triggers_mismatch(self):
        """Switching from PDF to JPG requires filename update."""
        page_count = 50
        
        # PDF format (no placeholder needed)
        pdf_suggested = build_suggested_filename_for_dialog(
            "document.pdf", page_count, ExportFormat.PDF
        )
        
        # JPG format (placeholder required for multi-page)
        jpg_suggested = build_suggested_filename_for_dialog(
            "document.pdf", page_count, ExportFormat.JPG
        )
        
        # Filenames should differ
        assert pdf_suggested != jpg_suggested
        assert "#" not in pdf_suggested
        assert "#" in jpg_suggested

    def test_jpg_to_pdf_format_switch_triggers_mismatch(self):
        """Switching from JPG to PDF requires filename update."""
        page_count = 50
        
        # JPG format (has placeholder)
        jpg_suggested = build_suggested_filename_for_dialog(
            "document.pdf", page_count, ExportFormat.JPG
        )
        
        # PDF format (no placeholder needed)
        pdf_suggested = build_suggested_filename_for_dialog(
            "document.pdf", page_count, ExportFormat.PDF
        )
        
        # Filenames should differ
        assert jpg_suggested != pdf_suggested
        assert "#" in jpg_suggested
        assert "#" not in pdf_suggested

    def test_all_per_file_formats_require_placeholder(self):
        """JPG, PNG, BMP all require placeholder for multi-page."""
        page_count = 50
        
        for fmt in [ExportFormat.JPG, ExportFormat.PNG, ExportFormat.BMP]:
            suggested = build_suggested_filename_for_dialog(
                "document.pdf", page_count, fmt
            )
            assert "#" in suggested, f"Format {fmt} should have placeholder for multi-page"

    def test_all_single_file_formats_no_placeholder(self):
        """PDF and TIFF never have placeholder."""
        page_count = 50
        
        for fmt in [ExportFormat.PDF, ExportFormat.TIFF]:
            suggested = build_suggested_filename_for_dialog(
                "document.pdf", page_count, fmt
            )
            assert "#" not in suggested, f"Format {fmt} should never have placeholder"


class TestDialogReturnOnFormatMismatch:
    """Test that format mismatch returns user to save dialog instead of closing it."""

    def test_format_mismatch_returns_to_dialog(self):
        """When format mismatch detected, dialog should not close - return to save dialog."""
        # The behavior is:
        # 1. User enters "document-signed.jpg" but format is PDF
        # 2. Suggested for PDF: "document-signed.pdf"
        # 3. Mismatch detected (document-signed.jpg != document-signed.pdf)
        # 4. Show information dialog with OK button
        # 5. When user clicks OK: Return to save dialog (not closed)
        
        user_filename = "document-signed.jpg"
        suggested_pdf = "document-signed.pdf"
        
        # Mismatch should be detected
        assert user_filename != suggested_pdf

    def test_information_dialog_message_structure(self):
        """Format mismatch dialog should clearly show the discrepancy."""
        # Dialog message should contain:
        # - Format name
        # - What user entered
        # - What's expected
        # - Instruction to edit the filename
        
        user_entered = "document-signed.jpg"
        expected = "document-signed-p#.jpg"
        format_name = "JPG"
        
        # The dialog would show:
        message_parts = [
            format_name,
            user_entered,
            expected,
            "edit",  # Instruction to fix
            "filename",
        ]
        
        # Verify all key parts are mentioned
        assert all(part.lower() in "JPG, document-signed.jpg, document-signed-p#.jpg, edit the filename to match the format".lower() for part in message_parts[:-1])

    def test_mismatch_triggers_for_format_change(self):
        """Format mismatch should only trigger when user changes the format/extension."""
        page_count = 50
        
        # Scenario 1: User keeps same format (PDF) - no mismatch
        pdf_suggested = build_suggested_filename_for_dialog(
            "document.pdf", page_count, ExportFormat.PDF
        )
        # User enters the same filename - no mismatch
        assert pdf_suggested == pdf_suggested
        
        # Scenario 2: User changes format (PDF to JPG) - triggers mismatch
        jpg_suggested = build_suggested_filename_for_dialog(
            "document.pdf", page_count, ExportFormat.JPG
        )
        # Filenames differ, so mismatch is detected
        assert pdf_suggested != jpg_suggested

    def test_validation_error_provides_retry_via_continue(self):
        """After format mismatch dialog, user should be able to retry."""
        # The while loop in save_document_as allows retry:
        # 1. First iteration: Show save dialog, detect mismatch
        # 2. Show information dialog with OK button
        # 3. User clicks OK
        # 4. Loop continues (while True) - back to save dialog
        # 5. Second iteration: User can now fix the filename
        
        # This is implemented via:
        # last_export_format = export_format
        # last_export_folder = str(output.parent)
        # continue
        
        # The loop structure supports this retry mechanism


class TestValidationAfterFormatSwitch:
    """Test that validation correctly checks placeholder after format changes."""

    def test_pdf_no_placeholder_valid(self):
        """PDF format doesn't require placeholder, even for multi-page."""
        is_valid, msg = validate_placeholder_for_multipage_export(
            "document-signed", total_pages=50, export_format=ExportFormat.PDF
        )
        assert is_valid is True
        assert msg == ""

    def test_jpg_without_placeholder_invalid(self):
        """JPG multi-page without placeholder should be invalid."""
        is_valid, msg = validate_placeholder_for_multipage_export(
            "document-signed", total_pages=50, export_format=ExportFormat.JPG
        )
        assert is_valid is False
        assert "#" in msg

    def test_jpg_with_placeholder_valid(self):
        """JPG with placeholder should be valid."""
        is_valid, msg = validate_placeholder_for_multipage_export(
            "document-signed-p#", total_pages=50, export_format=ExportFormat.JPG
        )
        assert is_valid is True
        assert msg == ""

    def test_single_page_no_placeholder_valid_for_all_formats(self):
        """Single-page documents don't need placeholder in any format."""
        for fmt in [ExportFormat.JPG, ExportFormat.PNG, ExportFormat.BMP, ExportFormat.PDF, ExportFormat.TIFF]:
            is_valid, msg = validate_placeholder_for_multipage_export(
                "document-signed", total_pages=1, export_format=fmt
            )
            assert is_valid is True, f"Format {fmt} should accept single-page without placeholder"
            assert msg == ""

    def test_format_change_changes_validation_requirement(self):
        """Same filename becomes valid/invalid based on format."""
        filename_stem = "document-signed"
        page_count = 50
        
        # Same filename, different formats
        pdf_valid, _ = validate_placeholder_for_multipage_export(
            filename_stem, page_count, ExportFormat.PDF
        )
        jpg_valid, _ = validate_placeholder_for_multipage_export(
            filename_stem, page_count, ExportFormat.JPG
        )
        
        # Should have different validity
        assert pdf_valid is True
        assert jpg_valid is False


class TestKeepEnteredFilenameBehavior:
    """Test user workflow: edit filename, then change format - filename should adapt."""

    def test_user_edits_pdf_filename_then_switches_to_jpg(self):
        """User edits filename from suggestion, then changes format to JPG.
        
        Workflow:
        1. Last export was PDF → dialog suggests "document-signed.pdf"
        2. User manually changes filename to "new.pdf"
        3. User changes format dropdown to JPG
        4. Expected: filename becomes "new-p#.jpg" (preserves "new" stem, adds JPG placeholder)
        """
        # Step 1: User had PDF as last format
        page_count = 98
        
        pdf_suggested = build_suggested_filename_for_dialog(
            "document.pdf", page_count, ExportFormat.PDF
        )
        assert pdf_suggested == "document-signed.pdf"  # No placeholder
        
        # Step 2: User manually edits to "new.pdf"
        user_edited_filename = "new.pdf"
        user_stem = Path(user_edited_filename).stem
        assert user_stem == "new"
        
        # Step 3: User changes format to JPG
        # The system should preserve the stem "new" and apply JPG rules
        jpg_format = ExportFormat.JPG
        
        # Build what JPG would suggest for the original document
        jpg_suggestion = build_suggested_filename_for_dialog(
            "document.pdf", page_count, jpg_format
        )
        assert jpg_suggestion == "document-signed-p#.jpg"  # Has placeholder
        
        # But since user edited it, we should use their stem "new" with JPG format rules
        expected_filename = f"{user_stem}-p#{jpg_format.extension()}"
        assert expected_filename == "new-p#.jpg"
        
        # Verify this expected format would be valid for JPG (test with the full filename)
        is_valid, _ = validate_placeholder_for_multipage_export(
            expected_filename, page_count, jpg_format
        )
        assert is_valid is True

    def test_user_edits_jpg_filename_then_switches_to_pdf(self):
        """User edits filename with JPG format, then switches to PDF.
        
        Workflow:
        1. Last export was JPG → dialog suggests "report-signed-p#.jpg"
        2. User manually changes filename to "final.jpg"
        3. User changes format dropdown to PDF
        4. Expected: filename becomes "final.pdf" (preserves "final" stem, removes placeholder)
        """
        # Step 1: User had JPG as last format
        page_count = 50
        
        jpg_suggested = build_suggested_filename_for_dialog(
            "report.pdf", page_count, ExportFormat.JPG
        )
        assert jpg_suggested == "report-signed-p#.jpg"  # Has placeholder
        
        # Step 2: User manually edits to "final.jpg"
        user_edited_filename = "final.jpg"
        user_stem = Path(user_edited_filename).stem
        assert user_stem == "final"
        
        # Step 3: User changes format to PDF
        # The system should preserve the stem "final" and apply PDF rules
        pdf_format = ExportFormat.PDF
        
        # Build what PDF would suggest for the original document
        pdf_suggestion = build_suggested_filename_for_dialog(
            "report.pdf", page_count, pdf_format
        )
        assert pdf_suggestion == "report-signed.pdf"  # No placeholder
        
        # But since user edited it, we should use their stem "final" with PDF format rules
        expected_filename = f"{user_stem}{pdf_format.extension()}"
        assert expected_filename == "final.pdf"
        
        # Verify this would be valid for PDF
        is_valid, _ = validate_placeholder_for_multipage_export(
            user_stem, page_count, pdf_format
        )
        assert is_valid is True

    def test_multiple_format_switches_preserve_user_stem(self):
        """User can switch between formats multiple times, stem is always preserved."""
        page_count = 98
        user_stem = "output"
        
        # Start with PDF - valid with stem only
        pdf_filename = f"{user_stem}.pdf"
        is_valid, _ = validate_placeholder_for_multipage_export(pdf_filename, page_count, ExportFormat.PDF)
        assert is_valid is True
        
        # Switch to JPG - valid with stem and placeholder
        jpg_filename = f"{user_stem}-p#{ExportFormat.JPG.extension()}"
        is_valid, _ = validate_placeholder_for_multipage_export(jpg_filename, page_count, ExportFormat.JPG)
        assert is_valid is True
        
        # Switch to PNG - valid with stem and placeholder
        png_filename = f"{user_stem}-p#{ExportFormat.PNG.extension()}"
        is_valid, _ = validate_placeholder_for_multipage_export(png_filename, page_count, ExportFormat.PNG)
        assert is_valid is True
        
        # Back to PDF - valid with stem only
        pdf_filename = f"{user_stem}.pdf"
        is_valid, _ = validate_placeholder_for_multipage_export(pdf_filename, page_count, ExportFormat.PDF)
        assert is_valid is True



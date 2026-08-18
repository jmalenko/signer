"""Tests for Version 1.2.13 - Enhanced Overwrite Confirmation Notifications.

Tests cover:
- File existence detection (single-file and multi-file formats)
- Older page file detection (multi-page exports with fewer pages)
- Dialog message building for all 5 scenarios (A-E)
- Cleanup checkbox behavior
- Edge cases and boundary conditions
"""

from pathlib import Path

import pytest

from signer.compositor import (
    ExportFormat,
    detect_existing_files,
    detect_older_page_files,
    build_overwrite_dialog_info,
)


class TestDetectExistingFiles:
    """Test file existence detection."""

    def test_single_file_format_file_exists(self, tmp_path):
        """Single-file format (PDF): file exists."""
        output_path = tmp_path / "document-signed.pdf"
        output_path.touch()

        existing = detect_existing_files(output_path, 10, ExportFormat.PDF)
        assert existing == [output_path]

    def test_single_file_format_file_not_exists(self, tmp_path):
        """Single-file format (PDF): file does not exist."""
        output_path = tmp_path / "document-signed.pdf"

        existing = detect_existing_files(output_path, 10, ExportFormat.PDF)
        assert existing == []

    def test_multifile_format_all_exist(self, tmp_path):
        """Multi-file format (JPG): all pages exist."""
        for i in range(1, 6):
            (tmp_path / f"document-p{i:01d}.jpg").touch()

        output_path = tmp_path / "document-p1.jpg"
        existing = detect_existing_files(output_path, 5, ExportFormat.JPG, "document-p#")

        assert len(existing) == 5
        assert all(f.exists() for f in existing)

    def test_multifile_format_partial_exist(self, tmp_path):
        """Multi-file format (PNG): only some pages exist."""
        (tmp_path / "document-p1.png").touch()
        (tmp_path / "document-p3.png").touch()

        output_path = tmp_path / "document-p1.png"
        existing = detect_existing_files(output_path, 5, ExportFormat.PNG, "document-p#")

        assert len(existing) == 2
        assert (tmp_path / "document-p1.png") in existing
        assert (tmp_path / "document-p3.png") in existing

    def test_multifile_format_none_exist(self, tmp_path):
        """Multi-file format (BMP): no files exist."""
        output_path = tmp_path / "document-p01.bmp"
        existing = detect_existing_files(output_path, 5, ExportFormat.BMP, "document-p#")

        assert existing == []

    def test_tiff_single_file(self, tmp_path):
        """TIFF format: single file."""
        output_path = tmp_path / "document-signed.tif"
        output_path.touch()

        existing = detect_existing_files(output_path, 10, ExportFormat.TIFF)
        assert existing == [output_path]


class TestDetectOlderPageFiles:
    """Test older page file detection."""

    def test_single_file_format_no_older_files(self, tmp_path):
        """Single-file formats (PDF/TIFF) never have older files."""
        for fmt in [ExportFormat.PDF, ExportFormat.TIFF]:
            older = detect_older_page_files(tmp_path, "document-p#", 10, fmt)
            assert older == []

    def test_no_older_files_when_exporting_more_pages(self, tmp_path):
        """No older files when exporting more pages than before."""
        # Previous export: 10 pages
        for i in range(1, 11):
            (tmp_path / f"document-p{i:02d}.jpg").touch()

        # Now exporting 20 pages (more than before)
        older = detect_older_page_files(tmp_path, "document-p#", 20, ExportFormat.JPG)
        assert older == []

    def test_detects_older_files_when_exporting_fewer_pages(self, tmp_path):
        """Detects older files when exporting fewer pages than before."""
        # Previous export: 50 pages
        for i in range(1, 51):
            (tmp_path / f"document-p{i:02d}.jpg").touch()

        # Now exporting 20 pages (fewer than before)
        older = detect_older_page_files(tmp_path, "document-p#", 20, ExportFormat.JPG)

        assert len(older) == 30
        for i in range(21, 51):
            assert (tmp_path / f"document-p{i:02d}.jpg") in older

    def test_older_files_with_padding_variation(self, tmp_path):
        """Correctly identifies older files with padding."""
        # Create files with padding for 100+ pages
        for i in range(1, 101):
            (tmp_path / f"report-p{i:03d}.jpg").touch()

        # Now exporting 50 pages
        older = detect_older_page_files(tmp_path, "report-p#", 50, ExportFormat.JPG)

        assert len(older) == 50
        for i in range(51, 101):
            assert (tmp_path / f"report-p{i:03d}.jpg") in older

    def test_ignores_different_filename_patterns(self, tmp_path):
        """Ignores files with different filename patterns."""
        # Create files for different document
        for i in range(1, 11):
            (tmp_path / f"other-doc-p{i:02d}.jpg").touch()

        # Search for "document" files
        older = detect_older_page_files(tmp_path, "document-p#", 5, ExportFormat.JPG)
        assert older == []

    def test_ignores_non_page_files(self, tmp_path):
        """Ignores files that don't match page number pattern."""
        (tmp_path / "document-p01.jpg").touch()
        (tmp_path / "document-padded.jpg").touch()
        (tmp_path / "document.jpg").touch()

        older = detect_older_page_files(tmp_path, "document-p#", 1, ExportFormat.JPG)
        # Should only find p01, not the padded or base file
        assert len(older) == 0  # p01 is within range, so no "older" files

    def test_handles_large_page_numbers(self, tmp_path):
        """Correctly handles large page numbers."""
        # Create files for 9999+ pages
        for i in [9998, 9999, 10000]:
            (tmp_path / f"bigdoc-p{i:05d}.jpg").touch()

        older = detect_older_page_files(tmp_path, "bigdoc-p#", 100, ExportFormat.JPG)
        assert len(older) == 3


class TestBuildOverwriteDialogInfo:
    """Test dialog message building."""

    def test_scenario_a_single_file_exists(self, tmp_path):
        """Scenario A: Single file (single-page or PDF/TIFF)."""
        output_path = tmp_path / "document-signed.pdf"
        output_path.touch()

        existing = [output_path]
        title, message, show_checkbox = build_overwrite_dialog_info(
            existing, [], 1, ExportFormat.PDF, output_path
        )

        assert title == "File Already Exists"
        assert "document-signed.pdf" in message
        assert "already exists" in message.lower()
        assert show_checkbox is False

    def test_scenario_b_multiple_files_few_overwrites(self, tmp_path):
        """Scenario B: Multiple files (few overwrites, <= 10)."""
        output_path = tmp_path / "document-signed.jpg"
        existing = [
            tmp_path / f"document-p{i:02d}.jpg"
            for i in [1, 2, 3]
        ]
        for f in existing:
            f.touch()

        title, message, show_checkbox = build_overwrite_dialog_info(
            existing, [], 5, ExportFormat.JPG, output_path
        )

        assert title == "Some Files Already Exist"
        assert "will be overwritten" in message.lower()
        assert "document-p01.jpg" in message
        assert "document-p02.jpg" in message
        assert "document-p03.jpg" in message
        assert show_checkbox is False

    def test_scenario_c_all_files_overwritten(self, tmp_path):
        """Scenario C: All files will be overwritten (optimized message)."""
        output_path = tmp_path / "document-signed.jpg"
        existing = [
            tmp_path / f"document-p{i:02d}.jpg"
            for i in range(1, 26)
        ]
        for f in existing:
            f.touch()

        title, message, show_checkbox = build_overwrite_dialog_info(
            existing, [], 25, ExportFormat.JPG, output_path
        )

        assert title == "All Files Will Be Overwritten"
        assert "25" in message
        assert "All 25 pages" in message
        assert show_checkbox is False

    def test_scenario_d_many_files_summary(self, tmp_path):
        """Scenario D: Large number of files (> 10) - summarized."""
        output_path = tmp_path / "document-signed.jpg"
        existing = [
            tmp_path / f"document-p{i:02d}.jpg"
            for i in range(1, 26)
        ]
        for f in existing:
            f.touch()

        title, message, show_checkbox = build_overwrite_dialog_info(
            existing, [], 20, ExportFormat.JPG, output_path
        )

        assert title == "Files Already Exist"
        assert "25 file(s)" in message
        assert "document-p01.jpg" in message
        assert "... (22 more files)" in message
        assert show_checkbox is False

    def test_scenario_e_older_files_cleanup_checkbox(self, tmp_path):
        """Scenario E: Older page files with cleanup checkbox."""
        output_path = tmp_path / "document-signed.jpg"

        # Create existing files (pages 1-20)
        existing = [
            tmp_path / f"document-p{i:02d}.jpg"
            for i in range(1, 21)
        ]
        for f in existing:
            f.touch()

        # Create older files (pages 21-50)
        older = [
            tmp_path / f"document-p{i:02d}.jpg"
            for i in range(21, 51)
        ]
        for f in older:
            f.touch()

        title, message, show_checkbox = build_overwrite_dialog_info(
            existing, older, 20, ExportFormat.JPG, output_path
        )

        assert title == "Replace Files and Clean Up Old Pages?"
        assert "will be overwritten" in message.lower()
        assert "older page files can be deleted" in message.lower()
        assert show_checkbox is True

    def test_scenario_e_shows_file_summaries(self, tmp_path):
        """Scenario E: Properly summarizes existing and older files."""
        output_path = tmp_path / "document-signed.jpg"

        # Create many existing and older files
        existing = [
            tmp_path / f"document-p{i:02d}.jpg"
            for i in range(1, 21)
        ]
        for f in existing:
            f.touch()

        older = [
            tmp_path / f"document-p{i:02d}.jpg"
            for i in range(21, 51)
        ]
        for f in older:
            f.touch()

        title, message, show_checkbox = build_overwrite_dialog_info(
            existing, older, 20, ExportFormat.JPG, output_path
        )

        # Should show first 3 existing files
        assert "document-p01.jpg" in message
        assert "document-p02.jpg" in message
        assert "document-p03.jpg" in message

        # Should show ellipsis for more
        assert "(17 more files)" in message

        # Should show older files summary
        assert "document-p21.jpg" in message
        assert "(27 more files)" in message

    def test_no_files_no_dialog_needed(self, tmp_path):
        """No overwrite dialog when no files exist."""
        output_path = tmp_path / "document-signed.jpg"

        title, message, show_checkbox = build_overwrite_dialog_info(
            [], [], 10, ExportFormat.JPG, output_path
        )

        assert title == ""
        assert message == ""
        assert show_checkbox is False


class TestOlderFileDetectionEdgeCases:
    """Test edge cases in older file detection."""

    def test_mixed_page_numbers_and_formats(self, tmp_path):
        """Handles mix of different file extensions correctly."""
        # Create JPG files
        for i in range(1, 26):
            (tmp_path / f"document-p{i:02d}.jpg").touch()

        # Create PNG files with same pattern (should not interfere)
        for i in range(1, 26):
            (tmp_path / f"document-p{i:02d}.png").touch()

        # Search for JPG older files
        older = detect_older_page_files(tmp_path, "document-p#", 20, ExportFormat.JPG)
        assert len(older) == 5  # Only JPG files 21-25

        # Search for PNG older files
        older = detect_older_page_files(tmp_path, "document-p#", 20, ExportFormat.PNG)
        assert len(older) == 5  # Only PNG files 21-25

    def test_filename_with_multiple_dashes(self, tmp_path):
        """Handles filenames with multiple dashes correctly."""
        # Create files with base name containing dashes
        for i in range(1, 11):
            (tmp_path / f"my-long-doc-name-p{i:02d}.jpg").touch()

        older = detect_older_page_files(
            tmp_path, "my-long-doc-name-p#", 5, ExportFormat.JPG
        )
        assert len(older) == 5
        for i in range(6, 11):
            assert (tmp_path / f"my-long-doc-name-p{i:02d}.jpg") in older

    def test_zero_padded_vs_not_padded(self, tmp_path):
        """Correctly detects padded page numbers."""
        # Create 100+ pages
        for i in range(1, 101):
            (tmp_path / f"doc-p{i:03d}.jpg").touch()

        # When exporting 50 pages, should find 51-100 as older
        older = detect_older_page_files(tmp_path, "doc-p#", 50, ExportFormat.JPG)
        assert len(older) == 50


class TestDialogScenarioSelection:
    """Test correct scenario selection logic."""

    def test_single_file_always_scenario_a(self, tmp_path):
        """Single-file formats always use Scenario A."""
        output_path = tmp_path / "document-signed.pdf"
        output_path.touch()

        existing = [output_path]

        for fmt in [ExportFormat.PDF, ExportFormat.TIFF]:
            title, _, show_checkbox = build_overwrite_dialog_info(
                existing, [], 100, fmt, output_path
            )

            assert title == "File Already Exists"
            assert show_checkbox is False

    def test_multifile_prefers_scenario_e_with_older_files(self, tmp_path):
        """Multi-file format prefers Scenario E when older files exist."""
        output_path = tmp_path / "document-signed.jpg"

        existing = [tmp_path / f"document-p{i:02d}.jpg" for i in range(1, 11)]
        older = [tmp_path / f"document-p{i:02d}.jpg" for i in range(11, 21)]

        for f in existing + older:
            f.touch()

        title, message, show_checkbox = build_overwrite_dialog_info(
            existing, older, 10, ExportFormat.JPG, output_path
        )

        assert title == "Replace Files and Clean Up Old Pages?"
        assert show_checkbox is True


class TestIntegration:
    """Integration tests combining detection and dialog building."""

    def test_full_workflow_single_file(self, tmp_path):
        """Full workflow: detect → dialog → result (single file)."""
        output_path = tmp_path / "document-signed.pdf"
        output_path.touch()

        existing = detect_existing_files(output_path, 10, ExportFormat.PDF)
        older = detect_older_page_files(
            output_path.parent, "document", 10, ExportFormat.PDF
        )

        title, message, show_checkbox = build_overwrite_dialog_info(
            existing, older, 10, ExportFormat.PDF, output_path
        )

        assert len(existing) == 1
        assert len(older) == 0
        assert title == "File Already Exists"
        assert show_checkbox is False

    def test_full_workflow_multifile_with_cleanup(self, tmp_path):
        """Full workflow: detect → dialog → cleanup (multi-page)."""
        # Create previous export of 50 pages
        for i in range(1, 51):
            (tmp_path / f"doc-p{i:02d}.jpg").touch()

        # Detect for new export of 20 pages
        output_path = tmp_path / "doc-p01.jpg"
        existing = detect_existing_files(output_path, 20, ExportFormat.JPG, "doc-p#")
        older = detect_older_page_files(tmp_path, "doc-p#", 20, ExportFormat.JPG)

        title, message, show_checkbox = build_overwrite_dialog_info(
            existing, older, 20, ExportFormat.JPG, output_path
        )

        assert len(existing) == 20
        assert len(older) == 30
        assert title == "Replace Files and Clean Up Old Pages?"
        assert show_checkbox is True

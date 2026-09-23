"""Regression test for the Save-As filename auto-correct bug (CODE_REVIEW_PLAN.md §2.4).

Bug: when the user picks a different format filter (e.g. PDF) in the Save As
dialog without editing the filename, the code was supposed to auto-correct the
suggested filename to match the new format's shape (single-file vs. per-page
placeholder). The comparison that triggers this auto-correction ran *after* the
filename's extension had already been mutated to the new format, so it could
never match the old suggested name and the auto-correct branch never fired.
"""

from pathlib import Path
from unittest.mock import patch

from PIL import Image

from signer.compositor import ExportFormat, build_suggested_filename_for_dialog
from signer.objects import AnnotationType, VectorAnnotation


def test_format_switch_auto_corrects_filename_to_single_file_form(main_window, tmp_path):
    doc_path = tmp_path / "document.pdf"
    doc_path.write_bytes(b"%PDF-1.4 fake")
    main_window.document_path = str(doc_path)

    main_window.canvas.set_pages([Image.new("RGB", (600, 800)) for _ in range(3)])
    main_window.canvas.add_object(VectorAnnotation(AnnotationType.CHECKMARK, 50, 50, page=0))

    main_window._settings.last_export_format = "jpg"
    main_window._settings.last_export_folder = str(tmp_path)

    total_pages = 3
    old_suggested = build_suggested_filename_for_dialog(str(doc_path), total_pages, ExportFormat.JPG)
    corrected_suggested = build_suggested_filename_for_dialog(str(doc_path), total_pages, ExportFormat.PDF)
    assert "#" in old_suggested and "#" not in corrected_suggested  # sanity check on fixtures

    pdf_filter = ExportFormat.PDF.file_filter()
    captured: dict[str, Path] = {}

    def fake_composite_pages_to_pdf(page_images, page_objects_list, output, quality):
        captured["output"] = Path(output)

    with patch("signer.main_window.QFileDialog.getSaveFileName") as mock_dialog, \
         patch("signer.main_window.composite_pages_to_pdf", side_effect=fake_composite_pages_to_pdf), \
         patch("signer.main_window.QMessageBox.information"):
        # First round: user picked the PDF filter but didn't edit the (still JPG-shaped)
        # suggested filename. Second round: dialog reopens pre-filled with the
        # corrected suggestion and the user accepts it as-is.
        mock_dialog.side_effect = [
            (str(tmp_path / old_suggested), pdf_filter),
            (str(tmp_path / corrected_suggested), pdf_filter),
        ]

        result = main_window.save_document_as()

    assert result is True
    assert captured["output"].name == corrected_suggested


def test_format_switch_reshows_dialog_with_corrected_default_filename(main_window, tmp_path):
    """Regression test (silent-failure review finding #4): once the filename has been
    auto-corrected for the new format, the re-shown dialog's pre-filled default must
    reflect that corrected name - not the stale, pre-correction one.
    """
    doc_path = tmp_path / "document.pdf"
    doc_path.write_bytes(b"%PDF-1.4 fake")
    main_window.document_path = str(doc_path)

    main_window.canvas.set_pages([Image.new("RGB", (600, 800)) for _ in range(3)])
    main_window.canvas.add_object(VectorAnnotation(AnnotationType.CHECKMARK, 50, 50, page=0))

    main_window._settings.last_export_format = "jpg"
    main_window._settings.last_export_folder = str(tmp_path)

    total_pages = 3
    old_suggested = build_suggested_filename_for_dialog(str(doc_path), total_pages, ExportFormat.JPG)
    corrected_suggested = build_suggested_filename_for_dialog(str(doc_path), total_pages, ExportFormat.PDF)
    pdf_filter = ExportFormat.PDF.file_filter()

    default_paths_seen: list[str] = []

    def fake_dialog(*args, **kwargs):
        default_paths_seen.append(args[2])
        if len(default_paths_seen) == 1:
            return (str(tmp_path / old_suggested), pdf_filter)
        return (str(tmp_path / corrected_suggested), pdf_filter)

    with patch("signer.main_window.QFileDialog.getSaveFileName", side_effect=fake_dialog), \
         patch("signer.main_window.composite_pages_to_pdf"), \
         patch("signer.main_window.QMessageBox.information"):
        main_window.save_document_as()

    assert len(default_paths_seen) == 2
    assert Path(default_paths_seen[1]).name == corrected_suggested

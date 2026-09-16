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

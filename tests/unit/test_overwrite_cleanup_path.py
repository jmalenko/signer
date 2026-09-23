"""Tests for the export overwrite/cleanup decision path.

`MainWindow._confirm_overwrite_and_cleanup()` short-circuits in test mode, so the
branch that actually calls the dialog helpers is never reached by the rest of the
suite. These tests drive it with test mode temporarily disabled.

See CODE_REVIEW_PLAN.md sections C9 and D2.
"""

from unittest.mock import patch

from signer.compositor import ExportFormat, build_overwrite_dialog_info, detect_older_page_files


def _write_pages(directory, stem_prefix, pages, ext=".jpg"):
    for page in pages:
        (directory / f"{stem_prefix}{page:02d}{ext}").write_bytes(b"x")


class TestOlderPageDetection:
    def test_finds_pages_beyond_the_new_export_range(self, tmp_path):
        _write_pages(tmp_path, "doc-p", [1, 2, 3, 4, 5])

        older = detect_older_page_files(tmp_path, "doc-p#", 3, ExportFormat.JPG)

        assert [p.name for p in older] == ["doc-p04.jpg", "doc-p05.jpg"]

    def test_finds_pages_when_the_placeholder_is_not_last(self, tmp_path):
        """A stem like `p#-doc` must still match its own output files."""
        for page in (1, 2, 3):
            (tmp_path / f"p{page:02d}-doc.jpg").write_bytes(b"x")

        older = detect_older_page_files(tmp_path, "p#-doc", 1, ExportFormat.JPG)

        assert [p.name for p in older] == ["p02-doc.jpg", "p03-doc.jpg"]

    def test_ignores_unrelated_files_with_digits(self, tmp_path):
        _write_pages(tmp_path, "doc-p", [4])
        (tmp_path / "other-p09.jpg").write_bytes(b"x")

        older = detect_older_page_files(tmp_path, "doc-p#", 1, ExportFormat.JPG)

        assert [p.name for p in older] == ["doc-p04.jpg"]

    def test_no_placeholder_means_no_older_files(self, tmp_path):
        _write_pages(tmp_path, "doc-p", [4, 5])

        assert detect_older_page_files(tmp_path, "doc", 1, ExportFormat.JPG) == []


class TestOverwriteDialogInfo:
    def test_offers_cleanup_when_only_older_files_exist(self, tmp_path):
        older = [tmp_path / "doc-p04.jpg", tmp_path / "doc-p05.jpg"]

        title, message, show_cleanup = build_overwrite_dialog_info(
            [], older, 3, ExportFormat.JPG, tmp_path / "doc-p#.jpg"
        )

        assert show_cleanup is True
        assert "doc-p04.jpg" in message
        assert title


class TestConfirmOverwriteIsActuallyReached:
    def test_cleanup_deletes_leftover_pages_when_confirmed(self, main_window, tmp_path):
        """The bypass is test-mode only: with it off, the cleanup really runs."""
        _write_pages(tmp_path, "doc-p", [1, 2, 3, 4, 5])
        output = tmp_path / "doc-p#.jpg"
        main_window._in_test_mode = False
        try:
            with patch.object(
                main_window, "_show_overwrite_cleanup_dialog", return_value=(True, True)
            ):
                proceed = main_window._confirm_overwrite_and_cleanup(
                    output, 3, ExportFormat.JPG, "doc-p#"
                )
        finally:
            main_window._in_test_mode = True

        assert proceed is True
        assert not (tmp_path / "doc-p04.jpg").exists()
        assert not (tmp_path / "doc-p05.jpg").exists()
        assert (tmp_path / "doc-p01.jpg").exists()

    def test_cancelling_the_dialog_stops_the_export(self, main_window, tmp_path):
        # A 3-page export writes unpadded names (pad width = len("3")).
        for page in (1, 2, 3):
            (tmp_path / f"doc-p{page}.jpg").write_bytes(b"x")
        output = tmp_path / "doc-p#.jpg"
        main_window._in_test_mode = False
        try:
            with patch.object(main_window, "_show_overwrite_confirm_dialog", return_value=False):
                proceed = main_window._confirm_overwrite_and_cleanup(
                    output, 3, ExportFormat.JPG, "doc-p#"
                )
        finally:
            main_window._in_test_mode = True

        assert proceed is False
        assert (tmp_path / "doc-p1.jpg").exists(), "cancelling must not delete anything"

    def test_nothing_to_confirm_proceeds_without_a_dialog(self, main_window, tmp_path):
        main_window._in_test_mode = False
        try:
            proceed = main_window._confirm_overwrite_and_cleanup(
                tmp_path / "doc-p#.jpg", 3, ExportFormat.JPG, "doc-p#"
            )
        finally:
            main_window._in_test_mode = True

        assert proceed is True

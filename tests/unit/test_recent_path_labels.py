"""Recent file menu labels: file name only, plus folders when names clash."""

from pathlib import Path

from signer.main_window import MainWindow


def _labels(paths):
    label = MainWindow._recent_path_labeler(paths)
    return [label(p) for p in paths]


def _p(*parts):
    return str(Path("/", *parts))


def test_unique_names_show_file_name_only():
    assert _labels([_p("a", "one.png"), _p("b", "two.png")]) == ["one.png", "two.png"]


def test_same_names_get_full_folder_path():
    assert _labels([_p("a", "b", "sig.png"), _p("c", "sig.png"), _p("c", "other.png")]) == [
        f"sig.png — {_p('a', 'b')}", f"sig.png — {_p('c')}", "other.png",
    ]


def test_only_clashing_names_get_folders():
    labels = _labels([_p("a", "sig.png"), _p("b", "sig.png"), _p("a", "doc.pdf"), _p("b", "doc2.pdf")])
    assert labels == [f"sig.png — {_p('a')}", f"sig.png — {_p('b')}", "doc.pdf", "doc2.pdf"]


def test_signature_and_document_menus_use_disambiguated_labels(main_window):
    main_window._settings.recent_signature_paths = [_p("a", "sig.png"), _p("b", "sig.png")]
    main_window._settings.recent_document_paths = [_p("a", "doc.pdf"), _p("b", "doc.pdf")]
    main_window._rebuild_recent_menus()

    assert [a.text() for a in main_window._sig_ann_menu.actions() if "sig.png" in a.text()] == [
        f"sig.png — {_p('a')}", f"sig.png — {_p('b')}",
    ]
    assert [a.text() for a in main_window._recent_docs_menu.actions()] == [
        f"doc.pdf — {_p('a')}", f"doc.pdf — {_p('b')}",
    ]

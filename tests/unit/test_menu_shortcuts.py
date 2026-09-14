"""Tests for menu shortcut presentation."""


def test_menu_shortcuts_are_native_and_do_not_embed_control_text(main_window):
    actions = {
        action.text(): action
        for action in main_window._hamburger_file_menu.actions()
        if action.text().split("\t", 1)[0] in {"Open Document…", "Save As…", "Print"}
    }

    assert set(actions) == {"Open Document…\tO", "Save As…\tS", "Print\tP"}
    assert actions["Open Document…\tO"].shortcut().toString() == "O"
    assert actions["Save As…\tS"].shortcut().toString() == "S"
    assert actions["Print\tP"].shortcut().toString() == "P"
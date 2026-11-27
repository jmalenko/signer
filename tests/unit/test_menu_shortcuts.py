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

def test_no_two_actions_share_a_shortcut(main_window):
    """Qt silently disables a shortcut that two actions share ("ambiguous shortcut")."""
    from collections import Counter

    from PySide6.QtGui import QAction

    sequences = Counter(
        shortcut.toString()
        for action in main_window.findChildren(QAction)
        for shortcut in action.shortcuts()
    )
    assert {key for key, count in sequences.items() if count > 1} == set()

"""History module for undo/redo with action coalescing."""

from .action import (
    Action,
    AddAnnotationAction,
    ChangeColorAction,
    ChangePageAction,
    ChangeFontFamilyAction,
    ChangeFontSizeAction,
    ChangeLineWidthAction,
    CutAnnotationAction,
    DeleteAnnotationAction,
    DuplicateAnnotationAction,
    MergeableAction,
    MoveAnnotationAction,
    PasteAnnotationAction,
    ResizeAnnotationAction,
    RotatePageAction,
    SelectAnnotationAction,
    SetTextAnnotationAction,
)
from .history_stack import HistoryStack

__all__ = [
    "Action",
    "MergeableAction",
    "MoveAnnotationAction",
    "ResizeAnnotationAction",
    "AddAnnotationAction",
    "DeleteAnnotationAction",
    "ChangeColorAction",
    "ChangeLineWidthAction",
    "ChangeFontSizeAction",
    "ChangeFontFamilyAction",
    "SetTextAnnotationAction",
    "SelectAnnotationAction",
    "DuplicateAnnotationAction",
    "CutAnnotationAction",
    "PasteAnnotationAction",
    "ChangePageAction",
    "RotatePageAction",
    "HistoryStack",
]

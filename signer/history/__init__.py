"""History module for undo/redo with action coalescing."""

from .action import (
    Action,
    AddAnnotationAction,
    ChangeColorAction,
    ChangePageAction,
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
    "SetTextAnnotationAction",
    "SelectAnnotationAction",
    "DuplicateAnnotationAction",
    "CutAnnotationAction",
    "PasteAnnotationAction",
    "ChangePageAction",
    "RotatePageAction",
    "HistoryStack",
]

"""History module for undo/redo with action coalescing."""

from .action import (
    Action,
    AddAnnotationAction,
    ChangeCharacterSpacingAction,
    ChangeColorAction,
    ChangeFontFamilyAction,
    ChangeFontSizeAction,
    ChangeLineWidthAction,
    ChangePageAction,
    CompositeAction,
    DeleteAnnotationAction,
    MergeableAction,
    MoveAnnotationAction,
    PasteAnnotationAction,
    ResizeAnnotationAction,
    RotateAnnotationAction,
    RotatePageAction,
    SetTextAnnotationAction,
)
from .history_stack import HistoryStack

__all__ = [
    "Action",
    "AddAnnotationAction",
    "ChangeCharacterSpacingAction",
    "ChangeColorAction",
    "ChangeFontFamilyAction",
    "ChangeFontSizeAction",
    "ChangeLineWidthAction",
    "ChangePageAction",
    "CompositeAction",
    "DeleteAnnotationAction",
    "HistoryStack",
    "MergeableAction",
    "MoveAnnotationAction",
    "PasteAnnotationAction",
    "ResizeAnnotationAction",
    "RotateAnnotationAction",
    "RotatePageAction",
    "SetTextAnnotationAction",
]

"""History stack for undo/redo with action coalescing.

The HistoryStack manages two stacks:
- undo_stack: Actions that have been performed
- redo_stack: Actions that were undone and can be re-done

Actions that support coalescing (move, resize) are merged with the last
stack element if they operate on the same object, reducing redundant
history entries.
"""

from __future__ import annotations

from typing import Any

from .action import Action, MoveAnnotationAction, ResizeAnnotationAction


class HistoryStack:
    """Manages undo/redo history with action coalescing."""

    def __init__(self) -> None:
        """Initialize empty history stacks."""
        self.undo_stack: list[Action] = []
        self.redo_stack: list[Action] = []

    def record_action(self, action: Action) -> None:
        """Record an action, coalescing with the last stack element if compatible.
        
        Args:
            action: The action to record
        
        Coalescing Rules:
        - Only move/resize actions coalesce
        - Last action must be same type and operate on same object
        - If compatible, merge() is called to update target state in-place
        - Otherwise, action is pushed to undo_stack as normal
        - redo_stack is always cleared when new action is recorded
        """
        # Check if this action can coalesce with the last action
        if isinstance(action, (MoveAnnotationAction, ResizeAnnotationAction)):
            if self.undo_stack and self.can_coalesce(self.undo_stack[-1], action):
                # Merge with last action by updating only its target state
                self.undo_stack[-1].merge(action)
                return  # Update in-place; don't push new action
        
        # Non-mergeable action or first in sequence: push to stack
        self.undo_stack.append(action)
        self.redo_stack.clear()  # Clear redo when new action recorded

    def can_coalesce(self, last_action: Action, new_action: Action) -> bool:
        """Check if a new action can coalesce with the last action on stack.
        
        Args:
            last_action: Last action on undo_stack
            new_action: New action being recorded
        
        Returns:
            True if both are same type and have same object_id
        """
        return (
            type(last_action) == type(new_action) and
            hasattr(last_action, "data") and
            hasattr(new_action, "data") and
            "object_id" in last_action.data and
            "object_id" in new_action.data and
            last_action.data["object_id"] == new_action.data["object_id"]
        )

    def undo(self, canvas: Any) -> bool:
        """Undo the last action.
        
        Args:
            canvas: The DocumentCanvas to apply undo to
        
        Returns:
            True if an action was undone, False if undo stack is empty
        """
        if not self.undo_stack:
            return False
        
        action = self.undo_stack.pop()
        action.undo(canvas)
        self.redo_stack.append(action)
        return True

    def redo(self, canvas: Any) -> bool:
        """Redo the last undone action.
        
        Args:
            canvas: The DocumentCanvas to apply redo to
        
        Returns:
            True if an action was redone, False if redo stack is empty
        """
        if not self.redo_stack:
            return False
        
        action = self.redo_stack.pop()
        action.execute(canvas)
        self.undo_stack.append(action)
        return True

    def can_undo(self) -> bool:
        """Check if there are actions to undo."""
        return bool(self.undo_stack)

    def can_redo(self) -> bool:
        """Check if there are actions to redo."""
        return bool(self.redo_stack)

    def clear(self) -> None:
        """Clear both undo and redo stacks."""
        self.undo_stack.clear()
        self.redo_stack.clear()

    def __len__(self) -> int:
        """Return the number of actions in undo stack."""
        return len(self.undo_stack)

    def __repr__(self) -> str:
        return f"HistoryStack(undo={len(self.undo_stack)}, redo={len(self.redo_stack)})"

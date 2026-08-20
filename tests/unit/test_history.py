"""Unit tests for undo/redo history stack and actions."""

import pytest
from unittest.mock import Mock, MagicMock
from signer.history import (
    HistoryStack,
    MoveAnnotationAction,
    ResizeAnnotationAction,
)


class TestHistoryStack:
    """Test HistoryStack functionality."""

    def test_record_action_basic(self) -> None:
        """Test recording a single action."""
        stack = HistoryStack()
        action = MoveAnnotationAction(object_id=0, x=100, y=100)
        
        stack.record_action(action)
        
        assert len(stack) == 1
        assert not stack.can_redo()
        assert stack.can_undo()

    def test_undo_redo_basic(self) -> None:
        """Test basic undo/redo cycle."""
        stack = HistoryStack()
        canvas = Mock()
        canvas.current_page_objects.return_value = [Mock(x=0, y=0)]
        canvas.objectChanged = Mock()
        canvas.objectChanged.emit = Mock()
        
        # Record a move action
        action = MoveAnnotationAction(object_id=0, from_x=0, from_y=0, to_x=100, to_y=100)
        stack.record_action(action)
        
        # Verify action is on undo stack
        assert len(stack.undo_stack) == 1
        assert not stack.redo_stack
        
        # Undo
        result = stack.undo(canvas)
        assert result is True
        assert not stack.undo_stack
        assert len(stack.redo_stack) == 1
        
        # Redo
        result = stack.redo(canvas)
        assert result is True
        assert len(stack.undo_stack) == 1
        assert not stack.redo_stack

    def test_move_action_coalescing(self) -> None:
        """Test that consecutive move actions on same object coalesce."""
        stack = HistoryStack()
        
        # Create two move actions on the same object
        action1 = MoveAnnotationAction(object_id=0, from_x=0, from_y=0, to_x=100, to_y=100)
        action2 = MoveAnnotationAction(object_id=0, x=150, y=150)  # Partial format
        
        stack.record_action(action1)
        assert len(stack) == 1
        
        stack.record_action(action2)
        # Should have coalesced - still only 1 action
        assert len(stack) == 1
        
        # Verify the action was updated with new target
        assert stack.undo_stack[0].data["to_x"] == 150
        assert stack.undo_stack[0].data["to_y"] == 150

    def test_move_different_objects_no_coalesce(self) -> None:
        """Test that moves on different objects don't coalesce."""
        stack = HistoryStack()
        
        action1 = MoveAnnotationAction(object_id=0, x=100, y=100)
        action2 = MoveAnnotationAction(object_id=1, x=200, y=200)
        
        stack.record_action(action1)
        stack.record_action(action2)
        
        # Should have 2 actions (no coalescing)
        assert len(stack) == 2

    def test_resize_action_coalescing(self) -> None:
        """Test that consecutive resize actions on same object coalesce."""
        stack = HistoryStack()
        
        action1 = ResizeAnnotationAction(object_id=0, from_width=100, from_height=100, to_width=150, to_height=150)
        action2 = ResizeAnnotationAction(object_id=0, width=200, height=200)  # Partial format
        
        stack.record_action(action1)
        assert len(stack) == 1
        
        stack.record_action(action2)
        # Should have coalesced
        assert len(stack) == 1
        
        # Verify the action was updated
        assert stack.undo_stack[0].data["to_width"] == 200
        assert stack.undo_stack[0].data["to_height"] == 200

    def test_move_then_resize_no_coalesce(self) -> None:
        """Test that move and resize don't coalesce."""
        stack = HistoryStack()
        
        action1 = MoveAnnotationAction(object_id=0, x=100, y=100)
        action2 = ResizeAnnotationAction(object_id=0, width=150, height=150)
        
        stack.record_action(action1)
        stack.record_action(action2)
        
        # Should have 2 actions (different types)
        assert len(stack) == 2

    def test_redo_stack_clears_on_new_action(self) -> None:
        """Test that redo stack is cleared when recording a new action after undo."""
        stack = HistoryStack()
        canvas = Mock()
        canvas.current_page_objects.return_value = [Mock(x=0, y=0)]
        canvas.objectChanged = Mock()
        canvas.objectChanged.emit = Mock()
        
        # Record, undo, then record a different action
        action1 = MoveAnnotationAction(object_id=0, from_x=0, from_y=0, to_x=100, to_y=100)
        action2 = MoveAnnotationAction(object_id=0, from_x=100, from_y=100, to_x=200, to_y=200)
        
        stack.record_action(action1)
        stack.undo(canvas)
        
        # Verify redo stack has the undone action
        assert len(stack.redo_stack) == 1
        
        # Record a new action
        stack.record_action(action2)
        
        # Redo stack should be cleared
        assert not stack.redo_stack

    def test_clear_history(self) -> None:
        """Test clearing undo/redo stacks."""
        stack = HistoryStack()
        
        action = MoveAnnotationAction(object_id=0, x=100, y=100)
        stack.record_action(action)
        
        assert len(stack) == 1
        
        stack.clear()
        
        assert len(stack) == 0
        assert not stack.can_undo()
        assert not stack.can_redo()


class TestMoveAnnotationAction:
    """Test MoveAnnotationAction functionality."""

    def test_full_format_action(self) -> None:
        """Test creating action with full format (initial + target)."""
        action = MoveAnnotationAction(
            object_id=0,
            from_x=100, from_y=100,
            to_x=200, to_y=200
        )
        
        assert action.data["object_id"] == 0
        assert action.data["from_x"] == 100
        assert action.data["from_y"] == 100
        assert action.data["to_x"] == 200
        assert action.data["to_y"] == 200

    def test_partial_format_action(self) -> None:
        """Test creating action with partial format (target only)."""
        action = MoveAnnotationAction(object_id=0, x=200, y=200)
        
        assert action.data["object_id"] == 0
        assert action.data["x"] == 200
        assert action.data["y"] == 200

    def test_has_initial_state_full_format(self) -> None:
        """Test has_initial_state for full format."""
        action = MoveAnnotationAction(
            object_id=0,
            from_x=100, from_y=100,
            to_x=200, to_y=200
        )
        
        assert action.has_initial_state()

    def test_has_initial_state_partial_format(self) -> None:
        """Test has_initial_state for partial format."""
        action = MoveAnnotationAction(object_id=0, x=200, y=200)
        
        assert not action.has_initial_state()

    def test_get_target_state_full_format(self) -> None:
        """Test get_target_state for full format."""
        action = MoveAnnotationAction(
            object_id=0,
            from_x=100, from_y=100,
            to_x=200, to_y=200
        )
        
        target = action.get_target_state()
        assert target["x"] == 200
        assert target["y"] == 200

    def test_get_target_state_partial_format(self) -> None:
        """Test get_target_state for partial format."""
        action = MoveAnnotationAction(object_id=0, x=200, y=200)
        
        target = action.get_target_state()
        assert target["x"] == 200
        assert target["y"] == 200

    def test_set_target_state_full_format(self) -> None:
        """Test set_target_state for full format."""
        action = MoveAnnotationAction(
            object_id=0,
            from_x=100, from_y=100,
            to_x=200, to_y=200
        )
        
        action.set_target_state({"x": 300, "y": 300})
        
        assert action.data["to_x"] == 300
        assert action.data["to_y"] == 300
        # Initial state should be unchanged
        assert action.data["from_x"] == 100
        assert action.data["from_y"] == 100

    def test_set_target_state_partial_format(self) -> None:
        """Test set_target_state for partial format."""
        action = MoveAnnotationAction(object_id=0, x=200, y=200)
        
        action.set_target_state({"x": 300, "y": 300})
        
        assert action.data["x"] == 300
        assert action.data["y"] == 300

    def test_merge_actions(self) -> None:
        """Test merging two move actions."""
        action1 = MoveAnnotationAction(
            object_id=0,
            from_x=100, from_y=100,
            to_x=200, to_y=200
        )
        
        action2 = MoveAnnotationAction(object_id=0, x=300, y=300)
        
        action1.merge(action2)
        
        # Initial state should be preserved
        assert action1.data["from_x"] == 100
        assert action1.data["from_y"] == 100
        # Target state should be updated
        assert action1.data["to_x"] == 300
        assert action1.data["to_y"] == 300


class TestResizeAnnotationAction:
    """Test ResizeAnnotationAction functionality."""

    def test_full_format_action(self) -> None:
        """Test creating action with full format."""
        action = ResizeAnnotationAction(
            object_id=0,
            from_width=100, from_height=100,
            to_width=200, to_height=200
        )
        
        assert action.data["object_id"] == 0
        assert action.data["from_width"] == 100
        assert action.data["from_height"] == 100
        assert action.data["to_width"] == 200
        assert action.data["to_height"] == 200

    def test_partial_format_action(self) -> None:
        """Test creating action with partial format."""
        action = ResizeAnnotationAction(object_id=0, width=200, height=200)
        
        assert action.data["object_id"] == 0
        assert action.data["width"] == 200
        assert action.data["height"] == 200

    def test_coalescing_preserves_initial_state(self) -> None:
        """Test that coalescing preserves the initial state."""
        stack = HistoryStack()
        
        action1 = ResizeAnnotationAction(
            object_id=0,
            from_width=100, from_height=100,
            to_width=150, to_height=150
        )
        action2 = ResizeAnnotationAction(object_id=0, width=200, height=200)
        action3 = ResizeAnnotationAction(object_id=0, width=250, height=250)
        
        stack.record_action(action1)
        stack.record_action(action2)
        stack.record_action(action3)
        
        # Should have only 1 action
        assert len(stack) == 1
        
        # Initial state preserved
        assert stack.undo_stack[0].data["from_width"] == 100
        assert stack.undo_stack[0].data["from_height"] == 100
        
        # Final target state updated
        assert stack.undo_stack[0].data["to_width"] == 250
        assert stack.undo_stack[0].data["to_height"] == 250

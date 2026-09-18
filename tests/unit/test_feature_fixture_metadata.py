import json
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures"


def _expected_action_fields(annotation_type: str) -> set[str]:
    base = {"width", "height"}
    if annotation_type == "text":
        return base | {"text", "font_family", "font_size_pt", "line_width_pt"}
    if annotation_type in {"checkmark", "crossmark", "line", "rectangle", "ellipse", "arrow"}:
        return base | {"color", "line_width_pt"}
    return base


@pytest.mark.parametrize("fixture_path", sorted(FIXTURES_DIR.glob("*.json")))
def test_feature_fixture_annotations_define_explicit_metadata(fixture_path: Path):
    data = json.loads(fixture_path.read_text())

    for action in data.get("actions", []):
        if action.get("type") == "add_annotation":
            annotation_type = action.get("annotation_type")
            assert annotation_type, f"{fixture_path.name}: add_annotation missing annotation_type"
            missing = sorted(_expected_action_fields(annotation_type) - action.keys())
            assert not missing, f"{fixture_path.name}: {annotation_type} is missing explicit metadata: {missing}"
        elif action.get("type") == "add_signature":
            missing = sorted({"path", "width", "height"} - action.keys())
            assert not missing, f"{fixture_path.name}: add_signature missing metadata: {missing}"

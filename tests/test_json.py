import json
from pathlib import Path

import pytest

data_path = Path("filter_keywords.json")


def load_json():
    assert data_path.exists(), f"File {data_path} not found!"
    with open(data_path, "r", encoding="utf-8") as f:
        return json.load(f)


def test_json_is_valid_format():
    try:
        data = load_json()
    except json.JSONDecodeError:
        pytest.fail("JSON file contains invalid syntax")

    assert isinstance(data, (list, dict)), "Top-level JSON must be an object or array"


def test_json_items_match_model():
    with open(str(data_path), "r", encoding="utf-8") as f:
        data = json.load(f)

    # Check if main keys exist
    assert "is_job_trigger" in data, "JSON must contain 'is_job_trigger' key"

    # Check if 'keywords' list exists inside 'is_job_trigger'
    keywords = data["is_job_trigger"].get("keywords")
    assert isinstance(keywords, list), "'keywords' in 'is_job_trigger' should be a list"

    # Additional test: check if the list is not empty
    assert len(keywords) > 0, "Keywords list cannot be empty!"

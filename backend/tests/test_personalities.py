import os
import tempfile
from pathlib import Path

import pytest

from backend.personalities import load_personalities, Personality


@pytest.fixture
def personality_dir(tmp_path):
    """Create a temp directory with sample personality files."""
    # Valid personality
    (tmp_path / "Therapist.md").write_text(
        "---\ndescription: Use for emotional support and reflective questions\n---\n"
        "You are a warm, empathetic therapist. Ask reflective questions.\n"
    )
    # Another valid one
    (tmp_path / "Analyst.md").write_text(
        "---\ndescription: Use for analytical or data-oriented queries\n---\n"
        "You are a sharp analytical thinker. Be precise and structured.\n"
    )
    return tmp_path


@pytest.fixture
def bad_personality_dir(tmp_path):
    """Directory with invalid personality files."""
    # Missing description
    (tmp_path / "NoDescript.md").write_text(
        "---\nfoo: bar\n---\nSome prompt.\n"
    )
    # Missing body
    (tmp_path / "NoBody.md").write_text(
        "---\ndescription: Has description but no body\n---\n"
    )
    # No frontmatter at all
    (tmp_path / "NoFrontmatter.md").write_text(
        "Just a plain markdown file with no frontmatter.\n"
    )
    return tmp_path


def test_load_personalities(personality_dir):
    personalities = load_personalities(str(personality_dir))
    assert len(personalities) == 2

    titles = {p.title for p in personalities}
    assert titles == {"Therapist", "Analyst"}

    therapist = next(p for p in personalities if p.title == "Therapist")
    assert "emotional support" in therapist.description
    assert "empathetic therapist" in therapist.prompt


def test_load_personalities_empty_dir(tmp_path):
    personalities = load_personalities(str(tmp_path))
    assert personalities == []


def test_load_personalities_missing_dir():
    personalities = load_personalities("/nonexistent/path/personalities")
    assert personalities == []


def test_load_personalities_skips_invalid(bad_personality_dir):
    personalities = load_personalities(str(bad_personality_dir))
    assert len(personalities) == 0


def test_load_personalities_sorted(personality_dir):
    """Files are loaded in sorted order."""
    personalities = load_personalities(str(personality_dir))
    assert personalities[0].title == "Analyst"
    assert personalities[1].title == "Therapist"

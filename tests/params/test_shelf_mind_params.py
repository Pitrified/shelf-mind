"""Test the ShelfMindParams class."""

from shelf_mind.params.shelf_mind_params import ShelfMindParams
from shelf_mind.params.shelf_mind_params import get_shelf_mind_params
from shelf_mind.params.shelf_mind_paths import ShelfMindPaths
from shelf_mind.params.sample_params import SampleParams


def test_shelf_mind_params_singleton() -> None:
    """Test that ShelfMindParams is a singleton."""
    params1 = ShelfMindParams()
    params2 = ShelfMindParams()
    assert params1 is params2
    assert get_shelf_mind_params() is params1


def test_shelf_mind_params_init() -> None:
    """Test initialization of ShelfMindParams."""
    params = ShelfMindParams()
    assert isinstance(params.paths, ShelfMindPaths)
    assert isinstance(params.sample, SampleParams)


def test_shelf_mind_params_str() -> None:
    """Test string representation."""
    params = ShelfMindParams()
    s = str(params)
    assert "ShelfMindParams:" in s
    assert "ShelfMindPaths:" in s
    assert "SampleParams:" in s

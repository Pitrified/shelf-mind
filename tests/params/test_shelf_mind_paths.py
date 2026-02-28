"""Test the shelf_mind paths."""

from shelf_mind.params.shelf_mind_params import get_shelf_mind_paths


def test_shelf_mind_paths() -> None:
    """Test the shelf_mind paths."""
    shelf_mind_paths = get_shelf_mind_paths()
    assert shelf_mind_paths.src_fol.name == "shelf_mind"
    assert shelf_mind_paths.root_fol.name == "shelf-mind"
    assert shelf_mind_paths.data_fol.name == "data"

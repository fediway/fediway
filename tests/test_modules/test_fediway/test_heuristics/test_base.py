import pytest

from modules.fediway.heuristics.base import Heuristic


def test_heuristic_without_tracked_params_raises():
    with pytest.raises(TypeError, match="must define _tracked_params"):
        class BadHeuristic(Heuristic):
            pass


def test_heuristic_with_empty_tracked_params_succeeds():
    class GoodHeuristic(Heuristic):
        _tracked_params = []

    heuristic = GoodHeuristic()
    assert heuristic.get_params() == {}


def test_heuristic_id_auto_derived():
    class DiversifyHeuristic(Heuristic):
        _tracked_params = []

    heuristic = DiversifyHeuristic()
    assert heuristic.id == "diversify_heuristic"


def test_heuristic_id_explicit_override():
    class DiversifyHeuristic(Heuristic):
        _id = "diversify"
        _tracked_params = []

    heuristic = DiversifyHeuristic()
    assert heuristic.id == "diversify"


def test_heuristic_display_name_auto_derived():
    class DiversifyHeuristic(Heuristic):
        _tracked_params = []

    heuristic = DiversifyHeuristic()
    assert heuristic.display_name == "Diversify"


def test_heuristic_display_name_explicit_override():
    class DiversifyHeuristic(Heuristic):
        _display_name = "Diversity Filter"
        _tracked_params = []

    heuristic = DiversifyHeuristic()
    assert heuristic.display_name == "Diversity Filter"


def test_heuristic_description_from_docstring():
    class DiversifyHeuristic(Heuristic):
        """Penalize repeated authors in feed."""
        _tracked_params = []

    heuristic = DiversifyHeuristic()
    assert heuristic.description == "Penalize repeated authors in feed."


def test_heuristic_description_explicit_override():
    class DiversifyHeuristic(Heuristic):
        """This docstring is ignored."""
        _description = "Custom description"
        _tracked_params = []

    heuristic = DiversifyHeuristic()
    assert heuristic.description == "Custom description"


def test_heuristic_description_none_without_docstring():
    class DiversifyHeuristic(Heuristic):
        _tracked_params = []

    heuristic = DiversifyHeuristic()
    assert heuristic.description is None


def test_heuristic_class_path():
    class DiversifyHeuristic(Heuristic):
        _tracked_params = []

    heuristic = DiversifyHeuristic()
    assert heuristic.class_path.endswith("DiversifyHeuristic")


def test_heuristic_get_params_with_tracked_params():
    class DiversifyHeuristic(Heuristic):
        _tracked_params = ["by", "penalty"]

        def __init__(self, by: str, penalty: float):
            self.by = by
            self.penalty = penalty

    heuristic = DiversifyHeuristic(by="account_id", penalty=0.5)
    assert heuristic.get_params() == {"by": "account_id", "penalty": 0.5}


def test_heuristic_features_class_attribute():
    class DiversifyHeuristic(Heuristic):
        features = ["status:account_id"]
        _tracked_params = []

    assert DiversifyHeuristic.features == ["status:account_id"]

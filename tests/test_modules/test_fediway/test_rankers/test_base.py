from modules.fediway.rankers.base import Ranker


def test_ranker_without_tracked_params_defaults_to_empty():
    class SimpleRanker(Ranker):
        pass

    ranker = SimpleRanker()
    assert ranker._tracked_params == []
    assert ranker.get_params() == {}


def test_ranker_with_empty_tracked_params_succeeds():
    class GoodRanker(Ranker):
        _tracked_params = []

    ranker = GoodRanker()
    assert ranker.get_params() == {}


def test_ranker_id_auto_derived():
    class SimpleStatsRanker(Ranker):
        _tracked_params = []

    ranker = SimpleStatsRanker()
    assert ranker.id == "simple_stats_ranker"


def test_ranker_id_explicit_override():
    class SimpleStatsRanker(Ranker):
        _id = "stats"
        _tracked_params = []

    ranker = SimpleStatsRanker()
    assert ranker.id == "stats"


def test_ranker_display_name_auto_derived():
    class SimpleStatsRanker(Ranker):
        _tracked_params = []

    ranker = SimpleStatsRanker()
    assert ranker.display_name == "Simple Stats"


def test_ranker_display_name_explicit_override():
    class SimpleStatsRanker(Ranker):
        _display_name = "Stats Ranker"
        _tracked_params = []

    ranker = SimpleStatsRanker()
    assert ranker.display_name == "Stats Ranker"


def test_ranker_description_from_docstring():
    class SimpleStatsRanker(Ranker):
        """A simple linear regression ranking model."""

        _tracked_params = []

    ranker = SimpleStatsRanker()
    assert ranker.description == "A simple linear regression ranking model."


def test_ranker_description_none_without_docstring():
    class SimpleStatsRanker(Ranker):
        _tracked_params = []

    ranker = SimpleStatsRanker()
    assert ranker.description is None


def test_ranker_class_path():
    class SimpleStatsRanker(Ranker):
        _tracked_params = []

    ranker = SimpleStatsRanker()
    assert ranker.class_path.endswith("SimpleStatsRanker")


def test_ranker_get_params_with_tracked_params():
    class SimpleStatsRanker(Ranker):
        _tracked_params = ["coef_fav", "decay_rate"]

        def __init__(self, coef_fav: float, decay_rate: float):
            self.coef_fav = coef_fav
            self.decay_rate = decay_rate

    ranker = SimpleStatsRanker(coef_fav=0.5, decay_rate=0.1)
    assert ranker.get_params() == {"coef_fav": 0.5, "decay_rate": 0.1}


def test_ranker_features_class_attribute():
    class SimpleStatsRanker(Ranker):
        features = ["status:favourites_count", "status:reblogs_count"]
        _tracked_params = []

    assert SimpleStatsRanker.features == ["status:favourites_count", "status:reblogs_count"]

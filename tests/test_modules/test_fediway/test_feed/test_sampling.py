import pytest

from modules.fediway.feed.sampling import (
    InverseTransformSampler,
    Sampler,
    TopKSampler,
    WeightedGroupSampler,
)


def test_sampler_without_tracked_params_raises():
    with pytest.raises(TypeError, match="must define _tracked_params"):

        class BadSampler(Sampler):
            pass


def test_sampler_with_empty_tracked_params_succeeds():
    class GoodSampler(Sampler):
        _tracked_params = []

    sampler = GoodSampler()
    assert sampler.get_params() == {}


def test_sampler_id_auto_derived():
    class WeightedGroupSampler(Sampler):
        _tracked_params = []

    sampler = WeightedGroupSampler()
    assert sampler.id == "weighted_group_sampler"


def test_sampler_id_explicit_override():
    class WeightedGroupSampler(Sampler):
        _id = "weighted"
        _tracked_params = []

    sampler = WeightedGroupSampler()
    assert sampler.id == "weighted"


def test_sampler_display_name_auto_derived():
    class WeightedGroupSampler(Sampler):
        _tracked_params = []

    sampler = WeightedGroupSampler()
    assert sampler.display_name == "Weighted Group"


def test_sampler_display_name_explicit_override():
    class WeightedGroupSampler(Sampler):
        _display_name = "Group Weighted"
        _tracked_params = []

    sampler = WeightedGroupSampler()
    assert sampler.display_name == "Group Weighted"


def test_sampler_description_from_docstring():
    class WeightedGroupSampler(Sampler):
        """Samples based on group weights."""

        _tracked_params = []

    sampler = WeightedGroupSampler()
    assert sampler.description == "Samples based on group weights."


def test_sampler_class_path():
    class WeightedGroupSampler(Sampler):
        _tracked_params = []

    sampler = WeightedGroupSampler()
    assert sampler.class_path.endswith("WeightedGroupSampler")


def test_sampler_get_params_with_tracked_params():
    class WeightedGroupSampler(Sampler):
        _tracked_params = ["weights"]

        def __init__(self, weights: dict):
            self.weights = weights

    sampler = WeightedGroupSampler(weights={"a": 0.5, "b": 0.5})
    assert sampler.get_params() == {"weights": {"a": 0.5, "b": 0.5}}


def test_top_k_sampler_has_tracked_params():
    sampler = TopKSampler()
    assert sampler._tracked_params == []
    assert sampler.get_params() == {}
    assert sampler.id == "top_k_sampler"
    assert sampler.display_name == "Top K"


def test_inverse_transform_sampler_has_tracked_params():
    sampler = InverseTransformSampler()
    assert sampler._tracked_params == []
    assert sampler.get_params() == {}
    assert sampler.id == "inverse_transform_sampler"
    assert sampler.display_name == "Inverse Transform"


def test_weighted_group_sampler_tracks_weights():
    sampler = WeightedGroupSampler(weights={"in-network": 0.5, "trending": 0.5})
    assert sampler._tracked_params == ["weights"]
    assert sampler.get_params() == {"weights": {"in-network": 0.5, "trending": 0.5}}
    assert sampler.id == "weighted_group_sampler"
    assert sampler.display_name == "Weighted Group"

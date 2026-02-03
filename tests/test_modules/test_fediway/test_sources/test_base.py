import pytest

from modules.fediway.sources.base import Source, RedisSource


def test_source_without_tracked_params_raises():
    with pytest.raises(TypeError, match="must define _tracked_params"):
        class BadSource(Source):
            pass


def test_source_with_empty_tracked_params_succeeds():
    class GoodSource(Source):
        _tracked_params = []

    source = GoodSource()
    assert source.get_params() == {}


def test_source_id_auto_derived():
    class ViralStatusesSource(Source):
        _tracked_params = []

    source = ViralStatusesSource()
    assert source.id == "viral_statuses_source"


def test_source_id_explicit_override():
    class ViralStatusesSource(Source):
        _id = "viral"
        _tracked_params = []

    source = ViralStatusesSource()
    assert source.id == "viral"


def test_source_display_name_auto_derived():
    class ViralStatusesSource(Source):
        _tracked_params = []

    source = ViralStatusesSource()
    assert source.display_name == "Viral Statuses"


def test_source_display_name_explicit_override():
    class ViralStatusesSource(Source):
        _display_name = "Trending Posts"
        _tracked_params = []

    source = ViralStatusesSource()
    assert source.display_name == "Trending Posts"


def test_source_description_from_docstring():
    class ViralStatusesSource(Source):
        """Trending posts with high engagement velocity."""
        _tracked_params = []

    source = ViralStatusesSource()
    assert source.description == "Trending posts with high engagement velocity."


def test_source_description_explicit_override():
    class ViralStatusesSource(Source):
        """This docstring is ignored."""
        _description = "Custom description"
        _tracked_params = []

    source = ViralStatusesSource()
    assert source.description == "Custom description"


def test_source_description_none_without_docstring():
    class ViralStatusesSource(Source):
        _tracked_params = []

    source = ViralStatusesSource()
    assert source.description is None


def test_source_class_path():
    class ViralStatusesSource(Source):
        _tracked_params = []

    source = ViralStatusesSource()
    assert source.class_path.endswith("ViralStatusesSource")


def test_source_get_params_with_tracked_params():
    class ViralStatusesSource(Source):
        _tracked_params = ["language", "top_n"]

        def __init__(self, language: str, top_n: int):
            self.language = language
            self.top_n = top_n

    source = ViralStatusesSource(language="en", top_n=100)
    assert source.get_params() == {"language": "en", "top_n": 100}


def test_redis_source_skips_validation():
    # RedisSource should not require _tracked_params
    # This test just verifies that importing RedisSource works
    assert RedisSource._skip_params_validation is True


def test_redis_source_subclass_requires_tracked_params():
    with pytest.raises(TypeError, match="must define _tracked_params"):
        class BadRedisSubclass(RedisSource):
            pass

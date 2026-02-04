import pytest

from modules.fediway.sources.base import RedisSource, Source


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


# ============================================================================
# Fallback Tests
# ============================================================================


def test_source_has_no_fallback_by_default():
    class SimpleSource(Source):
        _tracked_params = []

    source = SimpleSource()

    assert source.get_fallback() is None
    assert source.has_fallback() is False


def test_source_fallback_default_threshold():
    class SimpleSource(Source):
        _tracked_params = []

    source = SimpleSource()

    assert source.fallback_threshold == 0.5


def test_source_fallback_custom_class_threshold():
    class CustomThresholdSource(Source):
        _tracked_params = []
        _default_fallback_threshold = 0.3

    source = CustomThresholdSource()

    assert source.fallback_threshold == 0.3


def test_source_fallback_returns_self_for_chaining():
    class PrimarySource(Source):
        _tracked_params = []

    class FallbackSource(Source):
        _tracked_params = []

    primary = PrimarySource()
    fallback = FallbackSource()

    result = primary.fallback(fallback)

    assert result is primary


def test_source_fallback_sets_fallback_source():
    class PrimarySource(Source):
        _tracked_params = []

    class FallbackSource(Source):
        _tracked_params = []

    primary = PrimarySource()
    fallback = FallbackSource()

    primary.fallback(fallback)

    assert primary.get_fallback() is fallback
    assert primary.has_fallback() is True


def test_source_fallback_with_custom_threshold():
    class PrimarySource(Source):
        _tracked_params = []

    class FallbackSource(Source):
        _tracked_params = []

    primary = PrimarySource()
    fallback = FallbackSource()

    primary.fallback(fallback, threshold=0.7)

    assert primary.get_fallback() is fallback
    assert primary.fallback_threshold == 0.7


def test_source_fallback_chaining_multiple():
    class SourceA(Source):
        _tracked_params = []

    class SourceB(Source):
        _tracked_params = []

    class SourceC(Source):
        _tracked_params = []

    a = SourceA()
    b = SourceB()
    c = SourceC()

    # Chain: A -> B -> C
    a.fallback(b.fallback(c, threshold=0.3), threshold=0.5)

    assert a.get_fallback() is b
    assert a.fallback_threshold == 0.5
    assert b.get_fallback() is c
    assert b.fallback_threshold == 0.3
    assert c.get_fallback() is None


def test_source_fallback_fluent_syntax():
    class TagAffinitySource(Source):
        _tracked_params = []

    class InferredTagAffinitySource(Source):
        _tracked_params = []

    # Fluent syntax
    source = TagAffinitySource().fallback(InferredTagAffinitySource(), threshold=0.5)

    assert source.has_fallback()
    assert isinstance(source.get_fallback(), InferredTagAffinitySource)
    assert source.fallback_threshold == 0.5


def test_source_fallback_preserves_source_properties():
    class TagAffinitySource(Source):
        _id = "tag_affinity"
        _tracked_params = ["max_tags"]

        def __init__(self, max_tags: int = 50):
            self.max_tags = max_tags

    class FallbackSource(Source):
        _tracked_params = []

    source = TagAffinitySource(max_tags=100).fallback(FallbackSource())

    # Original properties preserved
    assert source.id == "tag_affinity"
    assert source.get_params() == {"max_tags": 100}
    # Fallback added
    assert source.has_fallback()


def test_source_fallback_threshold_not_affected_without_explicit_value():
    class PrimarySource(Source):
        _tracked_params = []

    class FallbackSource(Source):
        _tracked_params = []

    primary = PrimarySource()

    # Set fallback without threshold
    primary.fallback(FallbackSource())

    # Should use default threshold
    assert primary.fallback_threshold == 0.5


def test_source_fallback_can_be_replaced():
    class PrimarySource(Source):
        _tracked_params = []

    class FallbackA(Source):
        _tracked_params = []

    class FallbackB(Source):
        _tracked_params = []

    primary = PrimarySource()
    fallback_a = FallbackA()
    fallback_b = FallbackB()

    primary.fallback(fallback_a, threshold=0.3)
    assert primary.get_fallback() is fallback_a
    assert primary.fallback_threshold == 0.3

    # Replace fallback
    primary.fallback(fallback_b, threshold=0.6)
    assert primary.get_fallback() is fallback_b
    assert primary.fallback_threshold == 0.6

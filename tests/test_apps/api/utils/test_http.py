from apps.api.utils.http import parse_accept_language


def test_returns_none_for_empty_string():
    assert parse_accept_language("") is None


def test_returns_none_for_none():
    assert parse_accept_language(None) is None


def test_parses_single_language():
    assert parse_accept_language("en") == "en"


def test_parses_language_with_region():
    assert parse_accept_language("en-US") == "en"


def test_parses_multiple_languages_returns_first():
    assert parse_accept_language("en, fr, de") == "en"


def test_respects_quality_values():
    assert parse_accept_language("en;q=0.5, fr;q=0.9") == "fr"


def test_default_quality_is_1():
    assert parse_accept_language("fr;q=0.9, en") == "en"


def test_handles_complex_header():
    header = "en-US,en;q=0.9,fr;q=0.8,de;q=0.7"
    assert parse_accept_language(header) == "en"


def test_handles_whitespace():
    assert parse_accept_language("  en  ,  fr  ") == "en"


def test_handles_invalid_quality_value():
    assert parse_accept_language("en;q=invalid, fr;q=0.9") == "en"


def test_handles_quality_equal_to_zero():
    assert parse_accept_language("en;q=0, fr;q=0.5") == "fr"


def test_handles_asterisk_wildcard():
    assert parse_accept_language("*") == "*"


def test_handles_mixed_with_region_and_quality():
    header = "de-DE;q=0.8, en-US;q=0.9, fr;q=0.7"
    assert parse_accept_language(header) == "en"


def test_returns_highest_quality_when_tied():
    header = "en, fr"
    assert parse_accept_language(header) == "en"


def test_real_world_chrome_header():
    header = "en-US,en;q=0.9"
    assert parse_accept_language(header) == "en"


def test_real_world_firefox_header():
    header = "en-US,en;q=0.5"
    assert parse_accept_language(header) == "en"

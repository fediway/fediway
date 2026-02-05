from shared.utils.strings import camel_to_snake, humanize, snake_to_camel


def test_camel_to_snake_simple():
    assert camel_to_snake("ViralStatuses") == "viral_statuses"


def test_camel_to_snake_with_suffix():
    assert camel_to_snake("ViralStatusesSource") == "viral_statuses_source"


def test_camel_to_snake_acronym_at_start():
    assert camel_to_snake("HTTPRequest") == "http_request"


def test_camel_to_snake_acronym_in_middle():
    assert camel_to_snake("getHTTPResponse") == "get_http_response"


def test_camel_to_snake_acronym_at_end():
    assert camel_to_snake("parseXML") == "parse_xml"


def test_camel_to_snake_single_word():
    assert camel_to_snake("Source") == "source"


def test_camel_to_snake_already_snake():
    assert camel_to_snake("already_snake") == "already_snake"


def test_camel_to_snake_lowercase():
    assert camel_to_snake("lowercase") == "lowercase"


def test_camel_to_snake_with_numbers():
    assert camel_to_snake("Status2Source") == "status2_source"


def test_snake_to_camel_simple():
    assert snake_to_camel("viral_statuses") == "ViralStatuses"


def test_snake_to_camel_with_suffix():
    assert snake_to_camel("viral_statuses_source") == "ViralStatusesSource"


def test_snake_to_camel_single_word():
    assert snake_to_camel("source") == "Source"


def test_snake_to_camel_already_capitalized():
    assert snake_to_camel("HTTP") == "Http"


def test_snake_to_camel_empty():
    assert snake_to_camel("") == ""


def test_humanize_simple():
    assert humanize("viral_statuses") == "Viral Statuses"


def test_humanize_with_suffix():
    assert humanize("viral_statuses_source") == "Viral Statuses Source"


def test_humanize_single_word():
    assert humanize("source") == "Source"


def test_humanize_empty():
    assert humanize("") == ""


def test_humanize_already_spaced():
    assert humanize("already spaced") == "Already Spaced"

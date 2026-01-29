from unittest.mock import MagicMock, patch


@patch("apps.api.utils.response.config")
def test_sets_link_header(mock_config):
    from apps.api.utils.response import set_next_link

    mock_config.api.api_url = "https://api.example.com"

    mock_request = MagicMock()
    mock_request.url.path = "/api/v1/timelines/home"

    mock_response = MagicMock()
    mock_response.headers = {}

    params = {"max_id": "12345", "limit": "20"}

    set_next_link(mock_request, mock_response, params)

    assert "link" in mock_response.headers
    link = mock_response.headers["link"]

    assert "https://api.example.com/api/v1/timelines/home" in link
    assert "max_id=12345" in link
    assert "limit=20" in link
    assert 'rel="next"' in link


@patch("apps.api.utils.response.config")
def test_formats_link_correctly(mock_config):
    from apps.api.utils.response import set_next_link

    mock_config.api.api_url = "https://example.com"

    mock_request = MagicMock()
    mock_request.url.path = "/items"

    mock_response = MagicMock()
    mock_response.headers = {}

    set_next_link(mock_request, mock_response, {"page": "2"})

    link = mock_response.headers["link"]
    assert link.startswith("<")
    assert '>; rel="next"' in link


@patch("apps.api.utils.response.config")
def test_handles_empty_params(mock_config):
    from apps.api.utils.response import set_next_link

    mock_config.api.api_url = "https://example.com"

    mock_request = MagicMock()
    mock_request.url.path = "/items"

    mock_response = MagicMock()
    mock_response.headers = {}

    set_next_link(mock_request, mock_response, {})

    link = mock_response.headers["link"]
    assert "https://example.com/items" in link


@patch("apps.api.utils.response.config")
def test_handles_special_characters_in_params(mock_config):
    from apps.api.utils.response import set_next_link

    mock_config.api.api_url = "https://example.com"

    mock_request = MagicMock()
    mock_request.url.path = "/search"

    mock_response = MagicMock()
    mock_response.headers = {}

    set_next_link(mock_request, mock_response, {"q": "hello world"})

    link = mock_response.headers["link"]
    assert "hello" in link and "world" in link

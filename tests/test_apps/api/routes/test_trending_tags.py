def test_trending_tags_returns_200(client):
    response = client.get("/api/v1/trends/tags")
    assert response.status_code == 200


def test_trending_tags_returns_list(client):
    response = client.get("/api/v1/trends/tags")
    assert isinstance(response.json(), list)


def test_trending_tags_returns_empty_list_by_default(client):
    response = client.get("/api/v1/trends/tags")
    assert response.json() == []


def test_trending_tags_does_not_require_auth(unauthenticated_client):
    response = unauthenticated_client.get("/api/v1/trends/tags")
    assert response.status_code == 200


def test_trending_tags_calls_feed_engine(client, mock_feed_engine, mock_trending_tags_feed):
    client.get("/api/v1/trends/tags")

    mock_feed_engine.run.assert_called_once()
    call_args = mock_feed_engine.run.call_args
    assert call_args[0][0] == mock_trending_tags_feed


def test_trending_tags_with_offset(client, mock_feed_engine):
    client.get("/api/v1/trends/tags?offset=10")

    call_kwargs = mock_feed_engine.run.call_args
    assert call_kwargs[1]["offset"] == 10
    assert call_kwargs[1]["flush"] is False


def test_trending_tags_offset_zero_flushes(client, mock_feed_engine):
    client.get("/api/v1/trends/tags?offset=0")

    call_kwargs = mock_feed_engine.run.call_args
    assert call_kwargs[1]["flush"] is True


def test_trending_tags_no_link_header_when_empty(client):
    response = client.get("/api/v1/trends/tags")
    assert "link" not in response.headers


def test_trending_tags_uses_request_state_key(client, mock_feed_engine):
    client.get("/api/v1/trends/tags")

    call_kwargs = mock_feed_engine.run.call_args
    assert "state_key" in call_kwargs[1]
    assert call_kwargs[1]["state_key"] is not None

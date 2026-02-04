def test_trending_statuses_returns_200(client):
    response = client.get("/api/v1/trends/statuses")
    assert response.status_code == 200


def test_trending_statuses_returns_list(client):
    response = client.get("/api/v1/trends/statuses")
    assert isinstance(response.json(), list)


def test_trending_statuses_returns_empty_list_by_default(client):
    response = client.get("/api/v1/trends/statuses")
    assert response.json() == []


def test_trending_statuses_does_not_require_auth(unauthenticated_client):
    response = unauthenticated_client.get("/api/v1/trends/statuses")
    assert response.status_code == 200


def test_trending_statuses_calls_feed_engine(client, mock_feed_engine, mock_trending_statuses_feed):
    client.get("/api/v1/trends/statuses")

    mock_feed_engine.run.assert_called_once()
    call_args = mock_feed_engine.run.call_args
    assert call_args[0][0] == mock_trending_statuses_feed


def test_trending_statuses_with_offset(client, mock_feed_engine):
    client.get("/api/v1/trends/statuses?offset=20")

    call_kwargs = mock_feed_engine.run.call_args
    assert call_kwargs[1]["offset"] == 20
    assert call_kwargs[1]["flush"] is False


def test_trending_statuses_offset_zero_flushes(client, mock_feed_engine):
    client.get("/api/v1/trends/statuses?offset=0")

    call_kwargs = mock_feed_engine.run.call_args
    assert call_kwargs[1]["flush"] is True


def test_trending_statuses_sets_link_header(client):
    response = client.get("/api/v1/trends/statuses")
    assert "link" in response.headers
    assert "offset=" in response.headers["link"]


def test_trending_statuses_uses_request_state_key(client, mock_feed_engine):
    client.get("/api/v1/trends/statuses")

    call_kwargs = mock_feed_engine.run.call_args
    assert "state_key" in call_kwargs[1]
    assert call_kwargs[1]["state_key"] is not None

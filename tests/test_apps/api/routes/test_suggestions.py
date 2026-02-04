from unittest.mock import AsyncMock

from modules.fediway.feed.candidates import CandidateList


def test_suggestions_returns_200(client):
    response = client.get("/api/v2/suggestions")
    assert response.status_code == 200


def test_suggestions_returns_list(client):
    response = client.get("/api/v2/suggestions")
    assert isinstance(response.json(), list)


def test_suggestions_returns_empty_list_by_default(client):
    response = client.get("/api/v2/suggestions")
    assert response.json() == []


def test_suggestions_requires_auth(unauthenticated_client):
    response = unauthenticated_client.get("/api/v2/suggestions")
    assert response.status_code == 401


def test_suggestions_calls_feed_engine(
    client, mock_feed_engine, mock_suggestions_feed, mock_account
):
    client.get("/api/v2/suggestions")

    mock_feed_engine.run.assert_called_once()
    call_args = mock_feed_engine.run.call_args
    assert call_args[0][0] == mock_suggestions_feed
    assert call_args[1]["state_key"] == str(mock_account.id)


def test_suggestions_with_offset(client, mock_feed_engine):
    client.get("/api/v2/suggestions?offset=20")

    call_kwargs = mock_feed_engine.run.call_args
    assert call_kwargs[1]["offset"] == 20
    assert call_kwargs[1]["flush"] is False


def test_suggestions_offset_zero_flushes(client, mock_feed_engine):
    client.get("/api/v2/suggestions?offset=0")

    call_kwargs = mock_feed_engine.run.call_args
    assert call_kwargs[1]["flush"] is True


def test_suggestions_sets_link_header(client):
    response = client.get("/api/v2/suggestions")
    assert "link" in response.headers
    assert "offset=" in response.headers["link"]


def test_suggestions_queries_db_with_account_ids(client, mock_db_session, mock_feed_engine):
    async def mock_run(feed, state_key, flush=False, **kwargs):
        candidates = CandidateList("account_id")
        candidates.append(100, score=1.0, source="test", source_group="test")
        candidates.append(200, score=0.9, source="test", source_group="test")
        return candidates

    mock_feed_engine.run = AsyncMock(side_effect=mock_run)

    client.get("/api/v2/suggestions")

    mock_db_session.exec.assert_called_once()

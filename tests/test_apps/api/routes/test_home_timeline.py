from unittest.mock import AsyncMock

from modules.fediway.feed.candidates import CandidateList


def test_home_timeline_returns_200(client):
    response = client.get("/api/v1/timelines/home")
    assert response.status_code == 200


def test_home_timeline_returns_list(client):
    response = client.get("/api/v1/timelines/home")
    assert isinstance(response.json(), list)


def test_home_timeline_returns_empty_list_by_default(client):
    response = client.get("/api/v1/timelines/home")
    assert response.json() == []


def test_home_timeline_requires_auth(unauthenticated_client):
    response = unauthenticated_client.get("/api/v1/timelines/home")
    assert response.status_code == 401


def test_home_timeline_calls_feed_engine(client, mock_feed_engine, mock_home_feed, mock_account):
    client.get("/api/v1/timelines/home")

    mock_feed_engine.run.assert_called_once()
    call_kwargs = mock_feed_engine.run.call_args
    assert call_kwargs[0][0] == mock_home_feed
    assert call_kwargs[1]["state_key"] == str(mock_account.id)
    assert call_kwargs[1]["flush"] is True


def test_home_timeline_with_max_id_does_not_flush(client, mock_feed_engine):
    client.get("/api/v1/timelines/home?max_id=100")

    call_kwargs = mock_feed_engine.run.call_args
    assert call_kwargs[1]["flush"] is False
    assert call_kwargs[1]["max_id"] == 100


def test_home_timeline_no_link_header_when_empty(client):
    response = client.get("/api/v1/timelines/home")
    assert "link" not in response.headers


def test_home_timeline_queries_db_with_status_ids(client, mock_db_session, mock_feed_engine):
    async def mock_run(feed, state_key, flush=False, **kwargs):
        candidates = CandidateList("status_id")
        candidates.append(100, score=1.0, source="test", source_group="test")
        candidates.append(200, score=0.9, source="test", source_group="test")
        return candidates

    mock_feed_engine.run = AsyncMock(side_effect=mock_run)

    client.get("/api/v1/timelines/home")

    mock_db_session.exec.assert_called_once()

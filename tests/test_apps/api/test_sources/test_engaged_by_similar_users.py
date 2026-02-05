from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

from apps.api.sources.statuses import EngagedBySimilarUsersSource, PopularPostsSource


class TestEngagedBySimilarUsersSource:
    def test_source_id(self):
        mock_rw = MagicMock()
        source = EngagedBySimilarUsersSource(rw=mock_rw, account_id=1)
        assert source.id == "engaged_by_similar_users"

    def test_source_tracked_params(self):
        mock_rw = MagicMock()
        source = EngagedBySimilarUsersSource(
            rw=mock_rw,
            account_id=1,
            min_similarity=0.1,
            max_per_author=3,
        )
        params = source.get_params()
        assert params == {"min_similarity": 0.1, "max_per_author": 3}

    def test_collect_empty_candidates(self):
        mock_rw = MagicMock()
        mock_rw.execute.return_value.fetchall.return_value = []

        source = EngagedBySimilarUsersSource(rw=mock_rw, account_id=1)
        result = source.collect(10)

        assert result == []

    def test_collect_filters_followed_authors(self):
        mock_rw = MagicMock()
        now = datetime.now(timezone.utc).replace(tzinfo=None)

        def mock_execute(query, params):
            query_str = str(query)
            mock_result = MagicMock()
            if "similar_user_recent_engagements" in query_str:
                mock_result.fetchall.return_value = [
                    (101, 201, 0.2, 2.0, now),  # author 201 is followed
                    (102, 202, 0.2, 2.0, now),  # author 202 is not followed
                ]
            elif "follows" in query_str:
                mock_result.fetchall.return_value = [(201,)]
            else:
                mock_result.fetchall.return_value = []
            return mock_result

        mock_rw.execute.side_effect = mock_execute

        source = EngagedBySimilarUsersSource(rw=mock_rw, account_id=1)
        result = source.collect(10)

        assert 101 not in result
        assert 102 in result

    def test_collect_aggregates_multiple_engagements(self):
        mock_rw = MagicMock()
        now = datetime.now(timezone.utc).replace(tzinfo=None)

        def mock_execute(query, params):
            query_str = str(query)
            mock_result = MagicMock()
            if "similar_user_recent_engagements" in query_str:
                mock_result.fetchall.return_value = [
                    (101, 201, 0.2, 2.0, now),
                    (101, 201, 0.3, 1.0, now),  # same status
                    (102, 202, 0.1, 1.0, now),
                ]
            elif "follows" in query_str:
                mock_result.fetchall.return_value = []
            else:
                mock_result.fetchall.return_value = []
            return mock_result

        mock_rw.execute.side_effect = mock_execute

        source = EngagedBySimilarUsersSource(rw=mock_rw, account_id=1)
        result = source.collect(10)

        # Status 101 has aggregated score, should rank higher
        assert result[0] == 101

    def test_diversity_limits_per_author(self):
        mock_rw = MagicMock()
        now = datetime.now(timezone.utc).replace(tzinfo=None)

        def mock_execute(query, params):
            query_str = str(query)
            mock_result = MagicMock()
            if "similar_user_recent_engagements" in query_str:
                mock_result.fetchall.return_value = [
                    (101, 201, 0.3, 3.0, now),
                    (102, 201, 0.3, 2.5, now),
                    (103, 201, 0.3, 2.0, now),
                    (104, 202, 0.3, 1.5, now),
                ]
            elif "follows" in query_str:
                mock_result.fetchall.return_value = []
            else:
                mock_result.fetchall.return_value = []
            return mock_result

        mock_rw.execute.side_effect = mock_execute

        source = EngagedBySimilarUsersSource(rw=mock_rw, account_id=1, max_per_author=2)
        result = source.collect(10)

        author_201_count = sum(1 for sid in result if sid in [101, 102, 103])
        assert author_201_count == 2
        assert 104 in result

    def test_scoring_uses_similarity_and_recency(self):
        mock_rw = MagicMock()
        now = datetime.now(timezone.utc).replace(tzinfo=None)

        def mock_execute(query, params):
            query_str = str(query)
            mock_result = MagicMock()
            if "similar_user_recent_engagements" in query_str:
                mock_result.fetchall.return_value = [
                    (101, 201, 0.5, 2.0, now - timedelta(hours=24)),
                    (102, 202, 0.5, 2.0, now),
                ]
            elif "follows" in query_str:
                mock_result.fetchall.return_value = []
            else:
                mock_result.fetchall.return_value = []
            return mock_result

        mock_rw.execute.side_effect = mock_execute

        source = EngagedBySimilarUsersSource(rw=mock_rw, account_id=1)
        result = source.collect(10)

        # More recent should rank higher
        assert result[0] == 102


class TestPopularPostsSource:
    def test_source_id(self):
        mock_rw = MagicMock()
        source = PopularPostsSource(rw=mock_rw, account_id=1)
        assert source.id == "popular_posts"

    def test_collect_empty(self):
        mock_rw = MagicMock()
        mock_rw.execute.return_value.fetchall.return_value = []

        source = PopularPostsSource(rw=mock_rw, account_id=1)
        result = source.collect(10)

        assert result == []

    def test_collect_filters_followed(self):
        mock_rw = MagicMock()

        def mock_execute(query, params):
            query_str = str(query)
            mock_result = MagicMock()
            if "follows" in query_str:
                mock_result.fetchall.return_value = [(201,)]
            elif "enriched_status_engagement_events" in query_str:
                mock_result.fetchall.return_value = [
                    (101, 201, 10, 25.0),  # followed
                    (102, 202, 8, 20.0),  # not followed
                ]
            else:
                mock_result.fetchall.return_value = []
            return mock_result

        mock_rw.execute.side_effect = mock_execute

        source = PopularPostsSource(rw=mock_rw, account_id=1)
        result = source.collect(10)

        assert 101 not in result
        assert 102 in result

    def test_collect_applies_diversity(self):
        mock_rw = MagicMock()

        def mock_execute(query, params):
            query_str = str(query)
            mock_result = MagicMock()
            if "follows" in query_str:
                mock_result.fetchall.return_value = []
            elif "enriched_status_engagement_events" in query_str:
                mock_result.fetchall.return_value = [
                    (101, 201, 10, 30.0),
                    (102, 201, 9, 25.0),
                    (103, 201, 8, 20.0),
                    (104, 202, 7, 15.0),
                ]
            else:
                mock_result.fetchall.return_value = []
            return mock_result

        mock_rw.execute.side_effect = mock_execute

        source = PopularPostsSource(rw=mock_rw, account_id=1, max_per_author=2)
        result = source.collect(10)

        author_201_count = sum(1 for sid in result if sid in [101, 102, 103])
        assert author_201_count == 2
        assert 104 in result

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch
from dataclasses import dataclass, field


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ============================================================================
# Data Models for Test Fixtures
# ============================================================================

@dataclass
class MockAccount:
    id: int
    username: str = "testuser"
    domain: str | None = None
    followers_count: int = 100
    following_count: int = 50
    statuses_count: int = 200
    created_at: datetime = field(default_factory=utcnow)


@dataclass
class MockStatus:
    id: int
    account_id: int
    text: str = "Test status"
    created_at: datetime = field(default_factory=utcnow)
    visibility: int = 0  # public
    reblog_of_id: int | None = None
    in_reply_to_id: int | None = None
    language: str = "en"


@dataclass
class MockFollow:
    id: int
    account_id: int
    target_account_id: int
    created_at: datetime = field(default_factory=utcnow)


@dataclass
class MockEngagement:
    account_id: int
    status_id: int
    author_id: int
    type: int  # 0=fav, 1=reblog, 2=reply, 3=poll, 4=bookmark, 5=quote
    event_time: datetime = field(default_factory=utcnow)


@dataclass
class MockTag:
    id: int
    name: str


@dataclass
class MockStatusTag:
    status_id: int
    tag_id: int


# ============================================================================
# Test Data Builder
# ============================================================================

class TestDataBuilder:
    """Builder for creating consistent test data scenarios."""

    def __init__(self):
        self._id_counter = 1000
        self.accounts: list[MockAccount] = []
        self.statuses: list[MockStatus] = []
        self.follows: list[MockFollow] = []
        self.engagements: list[MockEngagement] = []
        self.tags: list[MockTag] = []
        self.status_tags: list[MockStatusTag] = []

    def _next_id(self) -> int:
        self._id_counter += 1
        return self._id_counter

    def add_account(self, **kwargs) -> MockAccount:
        account = MockAccount(id=self._next_id(), **kwargs)
        self.accounts.append(account)
        return account

    def add_status(self, account: MockAccount, **kwargs) -> MockStatus:
        status = MockStatus(id=self._next_id(), account_id=account.id, **kwargs)
        self.statuses.append(status)
        return status

    def add_follow(self, follower: MockAccount, target: MockAccount) -> MockFollow:
        follow = MockFollow(
            id=self._next_id(),
            account_id=follower.id,
            target_account_id=target.id
        )
        self.follows.append(follow)
        return follow

    def add_engagement(
        self,
        account: MockAccount,
        status: MockStatus,
        engagement_type: int,
        **kwargs
    ) -> MockEngagement:
        engagement = MockEngagement(
            account_id=account.id,
            status_id=status.id,
            author_id=status.account_id,
            type=engagement_type,
            **kwargs
        )
        self.engagements.append(engagement)
        return engagement

    def add_tag(self, name: str) -> MockTag:
        tag = MockTag(id=self._next_id(), name=name)
        self.tags.append(tag)
        return tag

    def tag_status(self, status: MockStatus, tag: MockTag) -> MockStatusTag:
        status_tag = MockStatusTag(status_id=status.id, tag_id=tag.id)
        self.status_tags.append(status_tag)
        return status_tag

    def add_fav(self, account: MockAccount, status: MockStatus, **kwargs):
        return self.add_engagement(account, status, 0, **kwargs)

    def add_reblog(self, account: MockAccount, status: MockStatus, **kwargs):
        return self.add_engagement(account, status, 1, **kwargs)

    def add_reply(self, account: MockAccount, status: MockStatus, **kwargs):
        return self.add_engagement(account, status, 2, **kwargs)

    def add_bookmark(self, account: MockAccount, status: MockStatus, **kwargs):
        return self.add_engagement(account, status, 4, **kwargs)

    def add_quote(self, account: MockAccount, status: MockStatus, **kwargs):
        return self.add_engagement(account, status, 5, **kwargs)


# ============================================================================
# Mock Database Session
# ============================================================================

class MockQueryResult:
    """Mock for SQLAlchemy query results."""

    def __init__(self, rows: list):
        self._rows = rows

    def all(self) -> list:
        return self._rows

    def first(self):
        return self._rows[0] if self._rows else None

    def fetchall(self) -> list:
        return self._rows

    def __iter__(self):
        return iter(self._rows)


class MockDBSession:
    """Mock database session for unit testing sources."""

    def __init__(self, data: TestDataBuilder):
        self.data = data
        self._query_handlers: dict = {}

    def register_query_handler(self, pattern: str, handler):
        """Register a handler for queries matching a pattern."""
        self._query_handlers[pattern] = handler

    def exec(self, query) -> MockQueryResult:
        """Execute a query and return mock results."""
        query_str = str(query) if hasattr(query, '__str__') else ""

        for pattern, handler in self._query_handlers.items():
            if pattern.lower() in query_str.lower():
                return MockQueryResult(handler(query_str))

        return MockQueryResult([])

    def execute(self, query, params=None) -> MockQueryResult:
        """Alternative execute method for raw SQL."""
        return self.exec(query)


# ============================================================================
# Pytest Fixtures
# ============================================================================

@pytest.fixture
def test_data() -> TestDataBuilder:
    """Fresh test data builder for each test."""
    return TestDataBuilder()


@pytest.fixture
def mock_db(test_data) -> MockDBSession:
    """Mock database session."""
    return MockDBSession(test_data)


@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    redis = MagicMock()
    redis.exists.return_value = False
    redis.get.return_value = None
    redis.setex.return_value = True
    redis.delete.return_value = True
    return redis


# ============================================================================
# Pre-built Test Scenarios
# ============================================================================

@pytest.fixture
def basic_social_graph(test_data) -> dict:
    """
    Creates a basic social graph:
    - user: the main user
    - followed: 3 accounts the user follows
    - not_followed: 2 accounts the user doesn't follow
    - statuses: 2 statuses per account
    """
    user = test_data.add_account(username="main_user")

    followed = [
        test_data.add_account(username=f"followed_{i}")
        for i in range(3)
    ]

    not_followed = [
        test_data.add_account(username=f"not_followed_{i}")
        for i in range(2)
    ]

    for account in followed:
        test_data.add_follow(user, account)

    all_accounts = followed + not_followed
    statuses = {}
    for account in all_accounts:
        statuses[account.id] = [
            test_data.add_status(account, text=f"Status {i} from {account.username}")
            for i in range(2)
        ]

    return {
        "user": user,
        "followed": followed,
        "not_followed": not_followed,
        "statuses": statuses,
        "data": test_data,
    }


@pytest.fixture
def engagement_scenario(test_data) -> dict:
    """
    Creates a scenario with engagement history:
    - user: main user with engagement history
    - authors: 5 accounts with varying engagement levels
    - high_affinity: account user engages with a lot
    - low_affinity: account user rarely engages with
    """
    user = test_data.add_account(username="engaged_user")

    authors = [
        test_data.add_account(username=f"author_{i}")
        for i in range(5)
    ]

    high_affinity = authors[0]
    low_affinity = authors[4]

    for author in authors:
        test_data.add_follow(user, author)

    for author in authors:
        for i in range(3):
            status = test_data.add_status(author)

            if author == high_affinity:
                test_data.add_fav(user, status)
                test_data.add_reblog(user, status)
            elif author != low_affinity:
                if i == 0:
                    test_data.add_fav(user, status)

    return {
        "user": user,
        "authors": authors,
        "high_affinity": high_affinity,
        "low_affinity": low_affinity,
        "data": test_data,
    }


@pytest.fixture
def tag_scenario(test_data) -> dict:
    """
    Creates a scenario with tags:
    - user: main user
    - tags: rustlang, python, golang
    - statuses tagged with various tags
    - user engagements with tagged content
    """
    user = test_data.add_account(username="tag_user")

    tags = {
        "rust": test_data.add_tag("rustlang"),
        "python": test_data.add_tag("python"),
        "golang": test_data.add_tag("golang"),
    }

    authors = [
        test_data.add_account(username=f"tag_author_{i}")
        for i in range(3)
    ]

    for author in authors:
        test_data.add_follow(user, author)

    statuses_by_tag = {tag_name: [] for tag_name in tags}

    # Author 0 posts about rust
    for i in range(3):
        status = test_data.add_status(authors[0], text=f"Rust post {i}")
        test_data.tag_status(status, tags["rust"])
        statuses_by_tag["rust"].append(status)
        test_data.add_fav(user, status)

    # Author 1 posts about python
    for i in range(2):
        status = test_data.add_status(authors[1], text=f"Python post {i}")
        test_data.tag_status(status, tags["python"])
        statuses_by_tag["python"].append(status)
        if i == 0:
            test_data.add_fav(user, status)

    # Author 2 posts about golang (no engagement)
    status = test_data.add_status(authors[2], text="Golang post")
    test_data.tag_status(status, tags["golang"])
    statuses_by_tag["golang"].append(status)

    return {
        "user": user,
        "tags": tags,
        "authors": authors,
        "statuses_by_tag": statuses_by_tag,
        "data": test_data,
    }


@pytest.fixture
def second_degree_scenario(test_data) -> dict:
    """
    Creates a second-degree follows scenario:
    - user: main user
    - direct_follows: accounts user follows directly
    - second_degree: accounts followed by user's follows (but not by user)
    - mutual_counts: how many of user's follows follow each second_degree account
    """
    user = test_data.add_account(username="second_degree_user")

    direct_follows = [
        test_data.add_account(username=f"direct_{i}")
        for i in range(5)
    ]

    second_degree = [
        test_data.add_account(username=f"second_degree_{i}")
        for i in range(3)
    ]

    for df in direct_follows:
        test_data.add_follow(user, df)

    # second_degree[0] is followed by 4 of user's follows (high social proof)
    # second_degree[1] is followed by 2 of user's follows (medium)
    # second_degree[2] is followed by 1 of user's follows (low)
    mutual_counts = {
        second_degree[0].id: 4,
        second_degree[1].id: 2,
        second_degree[2].id: 1,
    }

    test_data.add_follow(direct_follows[0], second_degree[0])
    test_data.add_follow(direct_follows[1], second_degree[0])
    test_data.add_follow(direct_follows[2], second_degree[0])
    test_data.add_follow(direct_follows[3], second_degree[0])

    test_data.add_follow(direct_follows[0], second_degree[1])
    test_data.add_follow(direct_follows[1], second_degree[1])

    test_data.add_follow(direct_follows[0], second_degree[2])

    for sd in second_degree:
        test_data.add_status(sd, text=f"Post from {sd.username}")

    return {
        "user": user,
        "direct_follows": direct_follows,
        "second_degree": second_degree,
        "mutual_counts": mutual_counts,
        "data": test_data,
    }


@pytest.fixture
def trending_scenario(test_data) -> dict:
    """
    Creates a trending scenario:
    - viral_status: high engagement velocity
    - normal_status: moderate engagement
    - stale_status: old high engagement (should not trend)
    """
    authors = [
        test_data.add_account(username=f"trending_author_{i}")
        for i in range(3)
    ]

    engagers = [
        test_data.add_account(username=f"engager_{i}")
        for i in range(10)
    ]

    now = utcnow()

    viral_status = test_data.add_status(
        authors[0],
        text="This is going viral!",
        created_at=now - timedelta(hours=2)
    )
    for engager in engagers[:8]:
        test_data.add_fav(engager, viral_status, event_time=now - timedelta(hours=1))
        test_data.add_reblog(engager, viral_status, event_time=now - timedelta(minutes=30))

    normal_status = test_data.add_status(
        authors[1],
        text="Normal post",
        created_at=now - timedelta(hours=4)
    )
    for engager in engagers[:3]:
        test_data.add_fav(engager, normal_status, event_time=now - timedelta(hours=2))

    stale_status = test_data.add_status(
        authors[2],
        text="This was popular yesterday",
        created_at=now - timedelta(hours=30)
    )
    for engager in engagers:
        test_data.add_fav(engager, stale_status, event_time=now - timedelta(hours=25))

    return {
        "viral_status": viral_status,
        "normal_status": normal_status,
        "stale_status": stale_status,
        "authors": authors,
        "engagers": engagers,
        "data": test_data,
    }

"""
Demo tests showing how to use the source test fixtures.

These tests verify that the fixtures work correctly and serve as
documentation for how to write source tests.
"""


def test_test_data_builder_creates_accounts(test_data):
    account = test_data.add_account(username="alice")

    assert account.id > 0
    assert account.username == "alice"
    assert len(test_data.accounts) == 1


def test_test_data_builder_creates_follows(test_data):
    alice = test_data.add_account(username="alice")
    bob = test_data.add_account(username="bob")

    follow = test_data.add_follow(alice, bob)

    assert follow.account_id == alice.id
    assert follow.target_account_id == bob.id
    assert len(test_data.follows) == 1


def test_test_data_builder_creates_statuses(test_data):
    alice = test_data.add_account(username="alice")

    status1 = test_data.add_status(alice, text="Hello world")
    status2 = test_data.add_status(alice, text="Another post")

    assert status1.account_id == alice.id
    assert status1.text == "Hello world"
    assert status1.id != status2.id
    assert len(test_data.statuses) == 2


def test_test_data_builder_creates_engagements(test_data):
    alice = test_data.add_account(username="alice")
    bob = test_data.add_account(username="bob")

    status = test_data.add_status(bob, text="Great post")

    test_data.add_fav(alice, status)
    test_data.add_reblog(alice, status)
    test_data.add_reply(alice, status)

    assert len(test_data.engagements) == 3
    assert test_data.engagements[0].type == 0  # fav
    assert test_data.engagements[1].type == 1  # reblog
    assert test_data.engagements[2].type == 2  # reply


def test_test_data_builder_creates_tags(test_data):
    alice = test_data.add_account(username="alice")
    rust_tag = test_data.add_tag("rustlang")

    status = test_data.add_status(alice, text="Rust is great!")
    test_data.tag_status(status, rust_tag)

    assert len(test_data.tags) == 1
    assert len(test_data.status_tags) == 1
    assert test_data.status_tags[0].tag_id == rust_tag.id


def test_basic_social_graph_fixture(basic_social_graph):
    user = basic_social_graph["user"]
    followed = basic_social_graph["followed"]
    not_followed = basic_social_graph["not_followed"]
    data = basic_social_graph["data"]

    assert user.username == "main_user"
    assert len(followed) == 3
    assert len(not_followed) == 2

    # User follows 3 accounts
    assert len(data.follows) == 3

    # Each account has 2 statuses
    assert len(data.statuses) == 10  # 5 accounts * 2 statuses


def test_engagement_scenario_fixture(engagement_scenario):
    user = engagement_scenario["user"]
    high_affinity = engagement_scenario["high_affinity"]
    low_affinity = engagement_scenario["low_affinity"]
    data = engagement_scenario["data"]

    # Count engagements with high_affinity author
    high_affinity_engagements = [
        e for e in data.engagements if e.author_id == high_affinity.id and e.account_id == user.id
    ]

    # Count engagements with low_affinity author
    low_affinity_engagements = [
        e for e in data.engagements if e.author_id == low_affinity.id and e.account_id == user.id
    ]

    assert len(high_affinity_engagements) > len(low_affinity_engagements)
    assert len(low_affinity_engagements) == 0


def test_tag_scenario_fixture(tag_scenario):
    _user = tag_scenario["user"]  # noqa: F841
    tags = tag_scenario["tags"]
    statuses_by_tag = tag_scenario["statuses_by_tag"]
    data = tag_scenario["data"]

    assert "rust" in tags
    assert "python" in tags
    assert "golang" in tags

    assert len(statuses_by_tag["rust"]) == 3
    assert len(statuses_by_tag["python"]) == 2
    assert len(statuses_by_tag["golang"]) == 1

    # User has engagements with rust and python, not golang
    rust_engagements = [
        e for e in data.engagements if e.status_id in [s.id for s in statuses_by_tag["rust"]]
    ]
    golang_engagements = [
        e for e in data.engagements if e.status_id in [s.id for s in statuses_by_tag["golang"]]
    ]

    assert len(rust_engagements) == 3
    assert len(golang_engagements) == 0


def test_second_degree_scenario_fixture(second_degree_scenario):
    user = second_degree_scenario["user"]
    _direct_follows = second_degree_scenario["direct_follows"]  # noqa: F841
    second_degree = second_degree_scenario["second_degree"]
    mutual_counts = second_degree_scenario["mutual_counts"]
    data = second_degree_scenario["data"]

    # User follows 5 accounts directly
    user_follows = [f for f in data.follows if f.account_id == user.id]
    assert len(user_follows) == 5

    # High social proof account has 4 mutual follows
    assert mutual_counts[second_degree[0].id] == 4

    # All second degree accounts have at least one status
    for sd in second_degree:
        sd_statuses = [s for s in data.statuses if s.account_id == sd.id]
        assert len(sd_statuses) >= 1


def test_trending_scenario_fixture(trending_scenario):
    viral_status = trending_scenario["viral_status"]
    normal_status = trending_scenario["normal_status"]
    stale_status = trending_scenario["stale_status"]
    data = trending_scenario["data"]

    viral_engagements = [e for e in data.engagements if e.status_id == viral_status.id]
    normal_engagements = [e for e in data.engagements if e.status_id == normal_status.id]
    stale_engagements = [e for e in data.engagements if e.status_id == stale_status.id]

    # Viral has most recent engagements
    assert len(viral_engagements) > len(normal_engagements)

    # Stale has many engagements but they're old
    assert len(stale_engagements) >= len(normal_engagements)


def test_mock_db_session(mock_db, test_data):
    alice = test_data.add_account(username="alice")
    bob = test_data.add_account(username="bob")
    test_data.add_follow(alice, bob)

    # Register a query handler
    def handle_follows_query(query_str):
        return [(f.account_id, f.target_account_id) for f in test_data.follows]

    mock_db.register_query_handler("from follows", handle_follows_query)

    # Execute query
    result = mock_db.exec("SELECT * FROM follows")

    assert len(result.all()) == 1
    assert result.all()[0] == (alice.id, bob.id)


def test_mock_redis(mock_redis):
    assert mock_redis.exists("some_key") is False

    mock_redis.setex("some_key", 300, "value")
    mock_redis.setex.assert_called_with("some_key", 300, "value")

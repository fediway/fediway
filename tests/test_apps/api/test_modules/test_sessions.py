from unittest.mock import MagicMock

from apps.api.modules.sessions import Session


def test_session_no_shared_mutable_default():
    """Verify that data default is not shared between instances."""
    s1 = Session(id="1", key="k1", ipv4_address="1.1.1.1", user_agent="ua1")
    s2 = Session(id="2", key="k2", ipv4_address="2.2.2.2", user_agent="ua2")

    s1.data["key"] = "value"

    assert "key" in s1.data
    assert "key" not in s2.data, "data should not be shared between instances"


def test_session_accepts_custom_data():
    s = Session(id="1", key="k1", ipv4_address="1.1.1.1", user_agent="ua1", data={"foo": "bar"})

    assert s.data == {"foo": "bar"}


def test_session_from_request_generates_unique_ids():
    """Verify that from_request generates new UUIDs each call."""
    request = MagicMock()
    request.client.host = "1.1.1.1"
    request.headers.get.return_value = "test-agent"

    s1 = Session.from_request(request)
    s2 = Session.from_request(request)

    assert s1.id != s2.id, "Each call should generate a unique ID"


def test_session_from_request_accepts_custom_id():
    request = MagicMock()
    request.client.host = "1.1.1.1"
    request.headers.get.return_value = "test-agent"

    s = Session.from_request(request, id="custom-id")

    assert s.id == "custom-id"


def test_session_from_dict():
    data = {
        "ipv4_address": "1.1.1.1",
        "user_agent": "test-agent",
        "data": {"foo": "bar"},
    }

    s = Session.from_dict(id="123", key="abc", data=data)

    assert s.id == "123"
    assert s.key == "abc"
    assert s.ipv4_address == "1.1.1.1"
    assert s.user_agent == "test-agent"
    assert s.data == {"foo": "bar"}


def test_session_from_dict_handles_missing_data():
    data = {
        "ipv4_address": "1.1.1.1",
        "user_agent": "test-agent",
    }

    s = Session.from_dict(id="123", key="abc", data=data)

    assert s.data == {}


def test_session_setitem_marks_modified():
    s = Session(id="1", key="k1", ipv4_address="1.1.1.1", user_agent="ua1")

    assert not s.has_changed()

    s["key"] = "value"

    assert s.has_changed()
    assert s.data["key"] == "value"


def test_session_delitem_marks_modified():
    s = Session(id="1", key="k1", ipv4_address="1.1.1.1", user_agent="ua1", data={"key": "value"})
    s._modified = False

    del s["key"]

    assert s.has_changed()
    assert "key" not in s.data


def test_session_get_returns_default():
    s = Session(id="1", key="k1", ipv4_address="1.1.1.1", user_agent="ua1")

    assert s.get("missing") is None
    assert s.get("missing", "default") == "default"

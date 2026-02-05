from datetime import datetime
from unittest.mock import MagicMock

from modules.mastodon.items import (
    AccountItem,
    ApplicationItem,
    FieldItem,
    MediaAttachmentItem,
    StatusItem,
    TagItem,
)


class TestMediaAttachmentItem:
    def test_id_converted_to_string(self):
        mock_attachment = MagicMock()
        mock_attachment.id = 12345
        mock_attachment.type = 0
        mock_attachment.file_url = "https://example.com/file.jpg"
        mock_attachment.preview_url = "https://example.com/preview.jpg"
        mock_attachment.remote_url = None
        mock_attachment.file_meta = {"width": 100, "height": 100}
        mock_attachment.description = "A photo"
        mock_attachment.blurhash = "LEHV6nWB2yk8"

        item = MediaAttachmentItem.from_model(mock_attachment)

        assert item.id == "12345"
        assert isinstance(item.id, str)

    def test_type_image(self):
        mock_attachment = MagicMock()
        mock_attachment.id = 1
        mock_attachment.type = 0
        mock_attachment.file_url = "https://example.com/file.jpg"
        mock_attachment.preview_url = None
        mock_attachment.remote_url = None
        mock_attachment.file_meta = None
        mock_attachment.description = None
        mock_attachment.blurhash = None

        item = MediaAttachmentItem.from_model(mock_attachment)

        assert item.type == "image"

    def test_type_gifv(self):
        mock_attachment = MagicMock()
        mock_attachment.id = 1
        mock_attachment.type = 1
        mock_attachment.file_url = "https://example.com/file.gif"
        mock_attachment.preview_url = None
        mock_attachment.remote_url = None
        mock_attachment.file_meta = None
        mock_attachment.description = None
        mock_attachment.blurhash = None

        item = MediaAttachmentItem.from_model(mock_attachment)

        assert item.type == "gifv"

    def test_type_video(self):
        mock_attachment = MagicMock()
        mock_attachment.id = 1
        mock_attachment.type = 4
        mock_attachment.file_url = "https://example.com/file.mp4"
        mock_attachment.preview_url = None
        mock_attachment.remote_url = None
        mock_attachment.file_meta = None
        mock_attachment.description = None
        mock_attachment.blurhash = None

        item = MediaAttachmentItem.from_model(mock_attachment)

        assert item.type == "video"

    def test_nullable_fields(self):
        mock_attachment = MagicMock()
        mock_attachment.id = 1
        mock_attachment.type = 0
        mock_attachment.file_url = None
        mock_attachment.preview_url = None
        mock_attachment.remote_url = None
        mock_attachment.file_meta = None
        mock_attachment.description = None
        mock_attachment.blurhash = None

        item = MediaAttachmentItem.from_model(mock_attachment)

        assert item.url is None
        assert item.preview_url is None
        assert item.remote_url is None
        assert item.meta is None
        assert item.description is None
        assert item.blurhash is None

    def test_serializes_to_json(self):
        mock_attachment = MagicMock()
        mock_attachment.id = 999
        mock_attachment.type = 0
        mock_attachment.file_url = "https://example.com/file.jpg"
        mock_attachment.preview_url = "https://example.com/preview.jpg"
        mock_attachment.remote_url = None
        mock_attachment.file_meta = {"width": 100}
        mock_attachment.description = "Test"
        mock_attachment.blurhash = "ABC123"

        item = MediaAttachmentItem.from_model(mock_attachment)
        data = item.model_dump()

        assert data["id"] == "999"
        assert data["type"] == "image"
        assert data["description"] == "Test"
        assert data["blurhash"] == "ABC123"


class TestFieldItem:
    def test_basic_field(self):
        field = FieldItem(name="Website", value="https://example.com")

        assert field.name == "Website"
        assert field.value == "https://example.com"
        assert field.verified_at is None

    def test_verified_field(self):
        verified_time = datetime(2024, 1, 15, 12, 0, 0)
        field = FieldItem(name="Website", value="https://example.com", verified_at=verified_time)

        assert field.verified_at == verified_time

    def test_serializes_to_json(self):
        field = FieldItem(name="Location", value="Earth")
        data = field.model_dump()

        assert data["name"] == "Location"
        assert data["value"] == "Earth"
        assert data["verified_at"] is None


class TestApplicationItem:
    def test_basic_application(self):
        app = ApplicationItem(name="MyApp")

        assert app.name == "MyApp"
        assert app.website is None

    def test_application_with_website(self):
        app = ApplicationItem(name="MyApp", website="https://myapp.example.com")

        assert app.name == "MyApp"
        assert app.website == "https://myapp.example.com"

    def test_serializes_to_json(self):
        app = ApplicationItem(name="TestApp", website="https://test.com")
        data = app.model_dump()

        assert data["name"] == "TestApp"
        assert data["website"] == "https://test.com"


class TestAccountItem:
    def _mock_account(self, **overrides):
        mock = MagicMock()
        mock.id = overrides.get("id", 42)
        mock.username = overrides.get("username", "testuser")
        mock.pretty_acct = overrides.get("acct", "testuser")
        mock.local_url = overrides.get("url", "https://example.com/@testuser")
        mock.local_uri = overrides.get("uri", "https://example.com/users/testuser")
        mock.display_name = overrides.get("display_name", "Test User")
        mock.note = overrides.get("note", "A test account")
        mock.locked = overrides.get("locked", False)
        mock.bot = overrides.get("bot", False)
        mock.group = overrides.get("group", False)
        mock.discoverable = overrides.get("discoverable", True)
        mock.indexable = overrides.get("indexable", False)
        mock.fields = overrides.get("fields", None)
        mock.avatar_url = overrides.get("avatar_url", "https://example.com/avatar.png")
        mock.avatar_static_url = overrides.get(
            "avatar_static_url", "https://example.com/avatar.png"
        )
        mock.header_url = overrides.get("header_url", "https://example.com/header.png")
        mock.header_static_url = overrides.get(
            "header_static_url", "https://example.com/header.png"
        )
        mock.created_at = overrides.get("created_at", datetime(2023, 6, 15, 14, 30, 0))

        mock.stats = MagicMock()
        mock.stats.statuses_count = overrides.get("statuses_count", 100)
        mock.stats.followers_count = overrides.get("followers_count", 50)
        mock.stats.following_count = overrides.get("following_count", 25)
        mock.stats.last_status_at = overrides.get("last_status_at", datetime(2024, 1, 15))

        return mock

    def test_id_converted_to_string(self):
        mock_account = self._mock_account(id=12345)

        item = AccountItem.from_model(mock_account)

        assert item.id == "12345"
        assert isinstance(item.id, str)

    def test_group_field_exists(self):
        mock_account = self._mock_account(group=True)

        item = AccountItem.from_model(mock_account)

        assert item.group is True

    def test_group_defaults_to_false(self):
        mock_account = self._mock_account(group=False)

        item = AccountItem.from_model(mock_account)

        assert item.group is False

    def test_created_at_set_to_midnight(self):
        mock_account = self._mock_account(created_at=datetime(2023, 6, 15, 14, 30, 45))

        item = AccountItem.from_model(mock_account)

        assert item.created_at.hour == 0
        assert item.created_at.minute == 0
        assert item.created_at.second == 0
        assert item.created_at.microsecond == 0
        assert item.created_at.year == 2023
        assert item.created_at.month == 6
        assert item.created_at.day == 15

    def test_last_status_at_is_date_string(self):
        mock_account = self._mock_account(last_status_at=datetime(2024, 1, 15, 12, 30, 0))

        item = AccountItem.from_model(mock_account)

        assert item.last_status_at == "2024-01-15"

    def test_last_status_at_none(self):
        mock_account = self._mock_account()
        mock_account.stats.last_status_at = None

        item = AccountItem.from_model(mock_account)

        assert item.last_status_at is None

    def test_indexable_field_true(self):
        mock_account = self._mock_account(indexable=True)

        item = AccountItem.from_model(mock_account)

        assert item.indexable is True

    def test_indexable_field_false(self):
        mock_account = self._mock_account(indexable=False)

        item = AccountItem.from_model(mock_account)

        assert item.indexable is False

    def test_fields_empty_when_none(self):
        mock_account = self._mock_account(fields=None)

        item = AccountItem.from_model(mock_account)

        assert item.fields == []

    def test_fields_converted_to_field_items(self):
        mock_account = self._mock_account(
            fields=[
                {"name": "Website", "value": "https://example.com", "verified_at": None},
                {"name": "Location", "value": "Earth", "verified_at": None},
            ]
        )

        item = AccountItem.from_model(mock_account)

        assert len(item.fields) == 2
        assert isinstance(item.fields[0], FieldItem)
        assert item.fields[0].name == "Website"
        assert item.fields[0].value == "https://example.com"
        assert item.fields[1].name == "Location"

    def test_fields_with_verified_at(self):
        verified_time = datetime(2024, 1, 15, 12, 0, 0)
        mock_account = self._mock_account(
            fields=[
                {"name": "Website", "value": "https://example.com", "verified_at": verified_time},
            ]
        )

        item = AccountItem.from_model(mock_account)

        assert item.fields[0].verified_at == verified_time

    def test_serializes_to_json(self):
        mock_account = self._mock_account(id=999, username="jsontest")

        item = AccountItem.from_model(mock_account)
        data = item.model_dump()

        assert data["id"] == "999"
        assert data["username"] == "jsontest"
        assert data["group"] is False
        assert data["indexable"] is False
        assert data["fields"] == []
        assert "created_at" in data


class TestTagItem:
    def _mock_tag(self, **overrides):
        mock = MagicMock()
        mock.id = overrides.get("id", 1)
        mock.name = overrides.get("name", "test")
        mock.display_name = overrides.get("display_name", None)
        return mock

    def test_id_converted_to_string(self):
        mock_tag = self._mock_tag(id=12345)

        item = TagItem.from_model(mock_tag)

        assert item.id == "12345"
        assert isinstance(item.id, str)

    def test_url_generated(self):
        mock_tag = self._mock_tag(name="python")

        item = TagItem.from_model(mock_tag)

        assert "/tags/python" in item.url
        assert item.url.startswith("https://")

    def test_history_defaults_to_empty_list(self):
        mock_tag = self._mock_tag()

        item = TagItem.from_model(mock_tag)

        assert item.history == []
        assert isinstance(item.history, list)

    def test_uses_display_name_when_available(self):
        mock_tag = self._mock_tag(name="python", display_name="Python")

        item = TagItem.from_model(mock_tag)

        assert item.name == "Python"

    def test_falls_back_to_name_when_no_display_name(self):
        mock_tag = self._mock_tag(name="python", display_name=None)

        item = TagItem.from_model(mock_tag)

        assert item.name == "python"

    def test_serializes_to_json(self):
        mock_tag = self._mock_tag(id=999, name="mastodon")

        item = TagItem.from_model(mock_tag)
        data = item.model_dump()

        assert data["id"] == "999"
        assert data["name"] == "mastodon"
        assert data["history"] == []
        assert "url" in data


class TestStatusItem:
    def _mock_status(self, **overrides):
        mock = MagicMock()
        mock.id = overrides.get("id", 1)
        mock.uri = overrides.get("uri", "https://example.com/statuses/1")
        mock.local_url = overrides.get("url", "https://example.com/@user/1")
        mock.created_at = overrides.get("created_at", datetime(2024, 1, 15, 12, 0, 0))
        mock.edited_at = overrides.get("edited_at", None)
        mock.language = overrides.get("language", "en")
        mock.text = overrides.get("text", "Hello world")
        mock.visibility = overrides.get("visibility", 0)
        mock.sensitive = overrides.get("sensitive", False)
        mock.spoiler_text = overrides.get("spoiler_text", "")
        mock.in_reply_to_id = overrides.get("in_reply_to_id", None)
        mock.in_reply_to_account_id = overrides.get("in_reply_to_account_id", None)
        mock.reblog = overrides.get("reblog", None)
        mock.preview_card = overrides.get("preview_card", None)
        mock.quote = overrides.get("quote", None)
        mock.media_attachments = overrides.get("media_attachments", [])

        mock.account = MagicMock()
        mock.account.id = 42
        mock.account.username = "testuser"
        mock.account.pretty_acct = "testuser"
        mock.account.local_url = "https://example.com/@testuser"
        mock.account.local_uri = "https://example.com/users/testuser"
        mock.account.display_name = "Test User"
        mock.account.note = ""
        mock.account.locked = False
        mock.account.bot = False
        mock.account.group = False
        mock.account.discoverable = True
        mock.account.indexable = False
        mock.account.fields = None
        mock.account.avatar_url = "https://example.com/avatar.png"
        mock.account.avatar_static_url = "https://example.com/avatar.png"
        mock.account.header_url = "https://example.com/header.png"
        mock.account.header_static_url = "https://example.com/header.png"
        mock.account.created_at = datetime(2023, 1, 1)
        mock.account.stats = MagicMock()
        mock.account.stats.statuses_count = 10
        mock.account.stats.followers_count = 5
        mock.account.stats.following_count = 3
        mock.account.stats.last_status_at = None

        mock.stats = MagicMock()
        mock.stats.reblogs_count = overrides.get("reblogs_count", 0)
        mock.stats.untrusted_reblogs_count = overrides.get("untrusted_reblogs_count", None)
        mock.stats.favourites_count = overrides.get("favourites_count", 0)
        mock.stats.untrusted_favourites_count = overrides.get("untrusted_favourites_count", None)
        mock.stats.replies_count = overrides.get("replies_count", 0)
        mock.stats.quotes_count = overrides.get("quotes_count", 0)

        return mock

    def test_id_converted_to_string(self):
        mock_status = self._mock_status(id=12345)

        item = StatusItem.from_model(mock_status)

        assert item.id == "12345"
        assert isinstance(item.id, str)

    def test_in_reply_to_id_converted_to_string(self):
        mock_status = self._mock_status(in_reply_to_id=98765)

        item = StatusItem.from_model(mock_status)

        assert item.in_reply_to_id == "98765"
        assert isinstance(item.in_reply_to_id, str)

    def test_in_reply_to_id_none_when_not_reply(self):
        mock_status = self._mock_status(in_reply_to_id=None)

        item = StatusItem.from_model(mock_status)

        assert item.in_reply_to_id is None

    def test_in_reply_to_account_id_converted_to_string(self):
        mock_status = self._mock_status(in_reply_to_account_id=54321)

        item = StatusItem.from_model(mock_status)

        assert item.in_reply_to_account_id == "54321"
        assert isinstance(item.in_reply_to_account_id, str)

    def test_in_reply_to_account_id_none_when_not_reply(self):
        mock_status = self._mock_status(in_reply_to_account_id=None)

        item = StatusItem.from_model(mock_status)

        assert item.in_reply_to_account_id is None

    def test_spoiler_text_defaults_to_empty_string(self):
        mock_status = self._mock_status(spoiler_text=None)

        item = StatusItem.from_model(mock_status)

        assert item.spoiler_text == ""
        assert isinstance(item.spoiler_text, str)

    def test_spoiler_text_preserved_when_set(self):
        mock_status = self._mock_status(spoiler_text="Content warning")

        item = StatusItem.from_model(mock_status)

        assert item.spoiler_text == "Content warning"

    def test_visibility_public(self):
        mock_status = self._mock_status(visibility=0)

        item = StatusItem.from_model(mock_status)

        assert item.visibility == "public"

    def test_visibility_unlisted(self):
        mock_status = self._mock_status(visibility=1)

        item = StatusItem.from_model(mock_status)

        assert item.visibility == "unlisted"

    def test_visibility_private(self):
        mock_status = self._mock_status(visibility=2)

        item = StatusItem.from_model(mock_status)

        assert item.visibility == "private"

    def test_visibility_direct(self):
        mock_status = self._mock_status(visibility=3)

        item = StatusItem.from_model(mock_status)

        assert item.visibility == "direct"

    def test_uses_untrusted_counts_when_available(self):
        mock_status = self._mock_status(
            reblogs_count=10,
            untrusted_reblogs_count=15,
            favourites_count=20,
            untrusted_favourites_count=25,
        )

        item = StatusItem.from_model(mock_status)

        assert item.reblogs_count == 15
        assert item.favourites_count == 25

    def test_falls_back_to_trusted_counts(self):
        mock_status = self._mock_status(
            reblogs_count=10,
            untrusted_reblogs_count=None,
            favourites_count=20,
            untrusted_favourites_count=None,
        )

        item = StatusItem.from_model(mock_status)

        assert item.reblogs_count == 10
        assert item.favourites_count == 20

    def test_handles_missing_stats(self):
        mock_status = self._mock_status()
        mock_status.stats = None

        item = StatusItem.from_model(mock_status)

        assert item.reblogs_count == 0
        assert item.favourites_count == 0
        assert item.replies_count == 0
        assert item.quotes_count == 0

    def test_account_id_is_string(self):
        mock_status = self._mock_status()

        item = StatusItem.from_model(mock_status)

        assert isinstance(item.account.id, str)

    def test_application_defaults_to_none(self):
        mock_status = self._mock_status()

        item = StatusItem.from_model(mock_status)

        assert item.application is None

    def test_serializes_to_json(self):
        mock_status = self._mock_status(
            id=999,
            in_reply_to_id=888,
            in_reply_to_account_id=777,
        )

        item = StatusItem.from_model(mock_status)
        data = item.model_dump()

        assert data["id"] == "999"
        assert data["in_reply_to_id"] == "888"
        assert data["in_reply_to_account_id"] == "777"
        assert data["spoiler_text"] == ""
        assert isinstance(data["account"], dict)
        assert data["account"]["id"] == "42"

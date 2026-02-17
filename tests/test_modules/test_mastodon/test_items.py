from datetime import datetime
from unittest.mock import MagicMock

import pytest

from modules.mastodon.items import (
    AccountItem,
    ApplicationItem,
    EmojiItem,
    FieldItem,
    MediaAttachmentItem,
    StatusItem,
    TagItem,
)
from modules.mastodon.items.mention import MentionItem
from modules.mastodon.items.preview_card import PreviewCardItem
from modules.mastodon.items.quote import QuoteItem

# -- Fixtures --


@pytest.fixture()
def mock_account():
    def _make(**overrides):
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

    return _make


@pytest.fixture()
def mock_status(mock_account):
    def _make(**overrides):
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
        mock.reblog_of_id = overrides.get("reblog_of_id", None)
        mock.preview_card = overrides.get("preview_card", None)
        mock.quote = overrides.get("quote", None)
        mock.media_attachments = overrides.get("media_attachments", [])

        mock.account = mock_account()

        mock.stats = MagicMock()
        mock.stats.reblogs_count = overrides.get("reblogs_count", 0)
        mock.stats.untrusted_reblogs_count = overrides.get("untrusted_reblogs_count", None)
        mock.stats.favourites_count = overrides.get("favourites_count", 0)
        mock.stats.untrusted_favourites_count = overrides.get("untrusted_favourites_count", None)
        mock.stats.replies_count = overrides.get("replies_count", 0)
        mock.stats.quotes_count = overrides.get("quotes_count", 0)

        return mock

    return _make


@pytest.fixture()
def mock_attachment():
    def _make(**overrides):
        mock = MagicMock()
        mock.id = overrides.get("id", 1)
        mock.type = overrides.get("type", 0)
        mock.file_url = overrides.get("file_url", "https://example.com/file.jpg")
        mock.preview_url = overrides.get("preview_url", None)
        mock.remote_url = overrides.get("remote_url", None)
        mock.file_meta = overrides.get("file_meta", None)
        mock.description = overrides.get("description", None)
        mock.blurhash = overrides.get("blurhash", None)
        return mock

    return _make


@pytest.fixture()
def mock_card():
    def _make(**overrides):
        mock = MagicMock()
        mock.url = overrides.get("url", "https://example.com/article")
        mock.title = overrides.get("title", "Example Article")
        mock.description = overrides.get("description", "An article")
        mock.type = overrides.get("type", 0)
        mock.author_name = overrides.get("author_name", "Author")
        mock.author_url = overrides.get("author_url", "https://example.com/@author")
        mock.provider_name = overrides.get("provider_name", "Example")
        mock.provider_url = overrides.get("provider_url", "https://example.com")
        mock.html = overrides.get("html", "")
        mock.width = overrides.get("width", 400)
        mock.height = overrides.get("height", 200)
        mock.image_url = overrides.get("image_url", "https://example.com/image.jpg")
        mock.embed_url = overrides.get("embed_url", None)
        mock.blurhash = overrides.get("blurhash", None)
        return mock

    return _make


# -- MediaAttachmentItem --


def test_media_attachment_id_converted_to_string(mock_attachment):
    item = MediaAttachmentItem.from_model(mock_attachment(id=12345))

    assert item.id == "12345"
    assert isinstance(item.id, str)


def test_media_attachment_type_image(mock_attachment):
    assert MediaAttachmentItem.from_model(mock_attachment(type=0)).type == "image"


def test_media_attachment_type_gifv(mock_attachment):
    assert MediaAttachmentItem.from_model(mock_attachment(type=1)).type == "gifv"


def test_media_attachment_type_video(mock_attachment):
    assert MediaAttachmentItem.from_model(mock_attachment(type=4)).type == "video"


def test_media_attachment_nullable_fields(mock_attachment):
    item = MediaAttachmentItem.from_model(
        mock_attachment(file_url=None, preview_url=None, remote_url=None, file_meta=None)
    )

    assert item.url is None
    assert item.preview_url is None
    assert item.remote_url is None
    assert item.meta is None


def test_media_attachment_serializes_to_json(mock_attachment):
    item = MediaAttachmentItem.from_model(
        mock_attachment(
            id=999, file_url="https://example.com/file.jpg", description="Test", blurhash="ABC123"
        )
    )
    data = item.model_dump()

    assert data["id"] == "999"
    assert data["type"] == "image"
    assert data["description"] == "Test"
    assert data["blurhash"] == "ABC123"


# -- FieldItem --


def test_field_basic():
    field = FieldItem(name="Website", value="https://example.com")

    assert field.name == "Website"
    assert field.value == "https://example.com"
    assert field.verified_at is None


def test_field_verified():
    verified_time = datetime(2024, 1, 15, 12, 0, 0)
    field = FieldItem(name="Website", value="https://example.com", verified_at=verified_time)

    assert field.verified_at == verified_time


def test_field_serializes_to_json():
    data = FieldItem(name="Location", value="Earth").model_dump()

    assert data["name"] == "Location"
    assert data["value"] == "Earth"
    assert data["verified_at"] is None


# -- ApplicationItem --


def test_application_basic():
    app = ApplicationItem(name="MyApp")

    assert app.name == "MyApp"
    assert app.website is None


def test_application_with_website():
    app = ApplicationItem(name="MyApp", website="https://myapp.example.com")

    assert app.website == "https://myapp.example.com"


def test_application_serializes_to_json():
    data = ApplicationItem(name="TestApp", website="https://test.com").model_dump()

    assert data["name"] == "TestApp"
    assert data["website"] == "https://test.com"


# -- AccountItem --


def test_account_id_converted_to_string(mock_account):
    item = AccountItem.from_model(mock_account(id=12345))

    assert item.id == "12345"
    assert isinstance(item.id, str)


def test_account_group_field(mock_account):
    assert AccountItem.from_model(mock_account(group=True)).group is True
    assert AccountItem.from_model(mock_account(group=False)).group is False


def test_account_created_at_set_to_midnight(mock_account):
    item = AccountItem.from_model(mock_account(created_at=datetime(2023, 6, 15, 14, 30, 45)))

    assert item.created_at == datetime(2023, 6, 15, 0, 0, 0)


def test_account_last_status_at_is_date_string(mock_account):
    item = AccountItem.from_model(mock_account(last_status_at=datetime(2024, 1, 15, 12, 30, 0)))

    assert item.last_status_at == "2024-01-15"


def test_account_last_status_at_none(mock_account):
    m = mock_account()
    m.stats.last_status_at = None

    assert AccountItem.from_model(m).last_status_at is None


def test_account_indexable_field(mock_account):
    assert AccountItem.from_model(mock_account(indexable=True)).indexable is True
    assert AccountItem.from_model(mock_account(indexable=False)).indexable is False


def test_account_fields_empty_when_none(mock_account):
    assert AccountItem.from_model(mock_account(fields=None)).fields == []


def test_account_fields_converted_to_field_items(mock_account):
    item = AccountItem.from_model(
        mock_account(
            fields=[
                {"name": "Website", "value": "https://example.com", "verified_at": None},
                {"name": "Location", "value": "Earth", "verified_at": None},
            ]
        )
    )

    assert len(item.fields) == 2
    assert isinstance(item.fields[0], FieldItem)
    assert item.fields[0].name == "Website"
    assert item.fields[1].name == "Location"


def test_account_fields_with_verified_at(mock_account):
    verified_time = datetime(2024, 1, 15, 12, 0, 0)
    item = AccountItem.from_model(
        mock_account(
            fields=[
                {"name": "Website", "value": "https://example.com", "verified_at": verified_time}
            ]
        )
    )

    assert item.fields[0].verified_at == verified_time


def test_account_serializes_to_json(mock_account):
    data = AccountItem.from_model(mock_account(id=999, username="jsontest")).model_dump()

    assert data["id"] == "999"
    assert data["username"] == "jsontest"
    assert data["group"] is False
    assert data["indexable"] is False
    assert data["fields"] == []
    assert "created_at" in data


# -- TagItem --


def test_tag_id_converted_to_string():
    mock = MagicMock()
    mock.id = 12345
    mock.name = "test"
    mock.display_name = None

    assert TagItem.from_model(mock).id == "12345"


def test_tag_url_generated():
    mock = MagicMock()
    mock.id = 1
    mock.name = "python"
    mock.display_name = None

    item = TagItem.from_model(mock)

    assert "/tags/python" in item.url
    assert item.url.startswith("https://")


def test_tag_history_defaults_to_empty_list():
    mock = MagicMock()
    mock.id = 1
    mock.name = "test"
    mock.display_name = None

    assert TagItem.from_model(mock).history == []


def test_tag_uses_display_name_when_available():
    mock = MagicMock()
    mock.id = 1
    mock.name = "python"
    mock.display_name = "Python"

    assert TagItem.from_model(mock).name == "Python"


def test_tag_falls_back_to_name():
    mock = MagicMock()
    mock.id = 1
    mock.name = "python"
    mock.display_name = None

    assert TagItem.from_model(mock).name == "python"


def test_tag_serializes_to_json():
    mock = MagicMock()
    mock.id = 999
    mock.name = "mastodon"
    mock.display_name = None

    data = TagItem.from_model(mock).model_dump()

    assert data["id"] == "999"
    assert data["name"] == "mastodon"
    assert data["history"] == []
    assert "url" in data


# -- StatusItem --


def test_status_id_converted_to_string(mock_status):
    assert StatusItem.from_model(mock_status(id=12345)).id == "12345"


def test_status_in_reply_to_id_converted_to_string(mock_status):
    item = StatusItem.from_model(mock_status(in_reply_to_id=98765))

    assert item.in_reply_to_id == "98765"
    assert isinstance(item.in_reply_to_id, str)


def test_status_in_reply_to_id_none_when_not_reply(mock_status):
    assert StatusItem.from_model(mock_status(in_reply_to_id=None)).in_reply_to_id is None


def test_status_in_reply_to_account_id_converted_to_string(mock_status):
    item = StatusItem.from_model(mock_status(in_reply_to_account_id=54321))

    assert item.in_reply_to_account_id == "54321"
    assert isinstance(item.in_reply_to_account_id, str)


def test_status_in_reply_to_account_id_none_when_not_reply(mock_status):
    assert StatusItem.from_model(mock_status()).in_reply_to_account_id is None


def test_status_spoiler_text_defaults_to_empty_string(mock_status):
    item = StatusItem.from_model(mock_status(spoiler_text=None))

    assert item.spoiler_text == ""
    assert isinstance(item.spoiler_text, str)


def test_status_spoiler_text_preserved_when_set(mock_status):
    assert (
        StatusItem.from_model(mock_status(spoiler_text="Content warning")).spoiler_text
        == "Content warning"
    )


@pytest.mark.parametrize(
    "visibility_int, visibility_str",
    [(0, "public"), (1, "unlisted"), (2, "private"), (3, "direct")],
)
def test_status_visibility(mock_status, visibility_int, visibility_str):
    assert (
        StatusItem.from_model(mock_status(visibility=visibility_int)).visibility == visibility_str
    )


def test_status_uses_untrusted_counts_when_available(mock_status):
    item = StatusItem.from_model(
        mock_status(
            reblogs_count=10,
            untrusted_reblogs_count=15,
            favourites_count=20,
            untrusted_favourites_count=25,
        )
    )

    assert item.reblogs_count == 15
    assert item.favourites_count == 25


def test_status_falls_back_to_trusted_counts(mock_status):
    item = StatusItem.from_model(mock_status(reblogs_count=10, favourites_count=20))

    assert item.reblogs_count == 10
    assert item.favourites_count == 20


def test_status_handles_missing_stats(mock_status):
    s = mock_status()
    s.stats = None
    item = StatusItem.from_model(s)

    assert item.reblogs_count == 0
    assert item.favourites_count == 0
    assert item.replies_count == 0
    assert item.quotes_count == 0


def test_status_account_id_is_string(mock_status):
    assert isinstance(StatusItem.from_model(mock_status()).account.id, str)


def test_status_application_defaults_to_none(mock_status):
    assert StatusItem.from_model(mock_status()).application is None


def test_status_serializes_to_json(mock_status):
    data = StatusItem.from_model(
        mock_status(id=999, in_reply_to_id=888, in_reply_to_account_id=777)
    ).model_dump()

    assert data["id"] == "999"
    assert data["in_reply_to_id"] == "888"
    assert data["in_reply_to_account_id"] == "777"
    assert data["spoiler_text"] == ""
    assert isinstance(data["account"], dict)
    assert data["account"]["id"] == "42"


def test_status_with_reblog(mock_status):
    item = StatusItem.from_model(mock_status(id=1, reblog=mock_status(id=2, text="Original post")))

    assert item.reblog is not None
    assert item.reblog.id == "2"
    assert item.reblog.content == "Original post"


def test_status_with_quote(mock_status):
    quoted = mock_status(id=3, text="Quoted post")
    quote_mock = MagicMock()
    quote_mock.state = 1
    quote_mock.status = quoted
    quote_mock.quoted_status = quoted
    quote_mock.quoted_status.reblog_of_id = None

    item = StatusItem.from_model(mock_status(id=1, quote=quote_mock))

    assert item.quote is not None
    assert item.quote.state == "accepted"
    assert item.quote.quoted_status.id == "3"


def test_status_quote_serializes_to_json(mock_status):
    quoted = mock_status(id=3)
    quote_mock = MagicMock()
    quote_mock.state = 1
    quote_mock.status = quoted
    quote_mock.quoted_status = quoted
    quote_mock.quoted_status.reblog_of_id = None

    data = StatusItem.from_model(mock_status(id=1, quote=quote_mock)).model_dump()

    assert data["quote"]["state"] == "accepted"
    assert data["quote"]["quoted_status"]["id"] == "3"


def test_status_mastodon_api_required_fields_present(mock_status):
    data = StatusItem.from_model(mock_status()).model_dump()

    required_fields = [
        "id",
        "uri",
        "url",
        "created_at",
        "content",
        "visibility",
        "sensitive",
        "spoiler_text",
        "account",
        "media_attachments",
        "mentions",
        "tags",
        "emojis",
        "reblogs_count",
        "favourites_count",
        "replies_count",
        "favourited",
        "reblogged",
        "muted",
        "bookmarked",
        "poll",
        "filtered",
        "reblog",
        "card",
    ]
    for field in required_fields:
        assert field in data, f"Missing Mastodon API field: {field}"


def test_status_interaction_flags_default_to_false(mock_status):
    item = StatusItem.from_model(mock_status())

    assert item.favourited is False
    assert item.reblogged is False
    assert item.muted is False
    assert item.bookmarked is False
    assert item.pinned is False
    assert item.poll is None
    assert item.filtered == []


# -- PreviewCardItem --


@pytest.mark.parametrize(
    "type_int, type_str",
    [(0, "link"), (1, "photo"), (2, "video"), (3, "rich")],
)
def test_preview_card_type(mock_card, type_int, type_str):
    assert PreviewCardItem.from_model(mock_card(type=type_int)).type == type_str


def test_preview_card_nullable_fields(mock_card):
    item = PreviewCardItem.from_model(mock_card(image_url=None, embed_url=None, blurhash=None))

    assert item.image is None
    assert item.embed_url is None
    assert item.blurhash is None


def test_preview_card_serializes_to_json(mock_card):
    data = PreviewCardItem.from_model(mock_card()).model_dump()

    assert data["url"] == "https://example.com/article"
    assert data["title"] == "Example Article"
    assert data["type"] == "link"
    assert data["image"] == "https://example.com/image.jpg"
    assert data["authors"] == []


# -- QuoteItem --


def test_quote_accepted_includes_status(mock_status):
    s = mock_status(id=99, text="Quoted content")
    quote = MagicMock()
    quote.state = 1
    quote.status = s
    quote.quoted_status = s

    item = QuoteItem.from_model(quote)

    assert item.state == "accepted"
    assert item.quoted_status is not None
    assert item.quoted_status.id == "99"


def test_quote_pending_excludes_status(mock_status):
    quote = MagicMock()
    quote.state = 0
    quote.status = mock_status()
    quote.quoted_status = mock_status()

    item = QuoteItem.from_model(quote)

    assert item.state == "pending"
    assert item.quoted_status is None


def test_quote_rejected_excludes_status():
    quote = MagicMock()
    quote.state = 2

    item = QuoteItem.from_model(quote)

    assert item.state == "rejected"
    assert item.quoted_status is None


def test_quote_serializes_to_json(mock_status):
    s = mock_status(id=99, text="Quoted content")
    quote = MagicMock()
    quote.state = 1
    quote.status = s
    quote.quoted_status = s

    data = QuoteItem.from_model(quote).model_dump()

    assert data["state"] == "accepted"
    assert data["quoted_status"]["id"] == "99"
    assert data["quoted_status"]["content"] == "Quoted content"


# -- MentionItem --


def test_mention_serializes_to_json():
    data = MentionItem(
        id="1", username="user", url="https://example.com/@user", acct="user"
    ).model_dump()

    assert data["id"] == "1"
    assert data["username"] == "user"
    assert data["acct"] == "user"


# -- EmojiItem --


def test_emoji_serializes_to_json():
    data = EmojiItem(
        shortcode="smile",
        url="https://example.com/emoji/smile.png",
        static_url="https://example.com/emoji/smile_static.png",
        visible_in_picker=True,
    ).model_dump()

    assert data["shortcode"] == "smile"
    assert data["visible_in_picker"] is True
    assert data["category"] is None

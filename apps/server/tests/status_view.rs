mod common;

use sqlx::PgPool;
use state::statuses::fetch_by_ids;

async fn insert_account(
    pool: &PgPool,
    username: &str,
    domain: Option<&str>,
    display_name: &str,
    note: &str,
) -> i64 {
    let url = match domain {
        Some(d) => format!("https://{d}/@{username}"),
        None => format!("https://local.test/@{username}"),
    };
    let uri = match domain {
        Some(d) => format!("https://{d}/users/{username}"),
        None => format!("https://local.test/users/{username}"),
    };
    sqlx::query_scalar::<_, i64>(
        "INSERT INTO accounts
            (username, domain, display_name, note, url, uri, avatar_file_name, header_file_name, actor_type)
         VALUES ($1, $2, $3, $4, $5, $6, 'avatar.jpg', 'header.jpg', 'Person')
         RETURNING id",
    )
    .bind(username)
    .bind(domain)
    .bind(display_name)
    .bind(note)
    .bind(&url)
    .bind(&uri)
    .fetch_one(pool)
    .await
    .expect("insert account")
}

async fn insert_account_stats(
    pool: &PgPool,
    account_id: i64,
    statuses: i64,
    followers: i64,
    following: i64,
) {
    sqlx::query(
        "INSERT INTO account_stats (account_id, statuses_count, followers_count, following_count)
         VALUES ($1, $2, $3, $4)",
    )
    .bind(account_id)
    .bind(statuses)
    .bind(followers)
    .bind(following)
    .execute(pool)
    .await
    .expect("insert account_stats");
}

#[allow(clippy::too_many_arguments)]
async fn insert_status(
    pool: &PgPool,
    account_id: i64,
    text: &str,
    spoiler_text: &str,
    language: Option<&str>,
    visibility: i32,
    in_reply_to_id: Option<i64>,
    in_reply_to_account_id: Option<i64>,
) -> i64 {
    sqlx::query_scalar::<_, i64>(
        "INSERT INTO statuses
            (account_id, uri, url, text, spoiler_text, language, visibility,
             in_reply_to_id, in_reply_to_account_id)
         VALUES ($1, NULL, NULL, $2, $3, $4, $5, $6, $7)
         RETURNING id",
    )
    .bind(account_id)
    .bind(text)
    .bind(spoiler_text)
    .bind(language)
    .bind(visibility)
    .bind(in_reply_to_id)
    .bind(in_reply_to_account_id)
    .fetch_one(pool)
    .await
    .expect("insert status")
}

async fn insert_status_stats(
    pool: &PgPool,
    status_id: i64,
    replies: i64,
    reblogs: i64,
    favs: i64,
    quotes: i64,
) {
    sqlx::query(
        "INSERT INTO status_stats (status_id, replies_count, reblogs_count, favourites_count, quotes_count)
         VALUES ($1, $2, $3, $4, $5)",
    )
    .bind(status_id)
    .bind(replies)
    .bind(reblogs)
    .bind(favs)
    .bind(quotes)
    .execute(pool)
    .await
    .expect("insert status_stats");
}

async fn insert_media_attachment(
    pool: &PgPool,
    status_id: i64,
    account_id: i64,
    kind: i32,
    file_name: &str,
    description: &str,
    width: u32,
    height: u32,
) -> i64 {
    let meta = serde_json::json!({
        "original": { "width": width, "height": height }
    });
    sqlx::query_scalar::<_, i64>(
        "INSERT INTO media_attachments
            (status_id, account_id, type, file_file_name, description, file_meta, blurhash)
         VALUES ($1, $2, $3, $4, $5, $6, 'LEHV6n')
         RETURNING id",
    )
    .bind(status_id)
    .bind(account_id)
    .bind(kind)
    .bind(file_name)
    .bind(description)
    .bind(meta)
    .fetch_one(pool)
    .await
    .expect("insert media")
}

async fn set_ordered_media(pool: &PgPool, status_id: i64, media_ids: &[i64]) {
    sqlx::query("UPDATE statuses SET ordered_media_attachment_ids = $1 WHERE id = $2")
        .bind(media_ids)
        .bind(status_id)
        .execute(pool)
        .await
        .expect("update ordered_media");
}

async fn insert_tag(pool: &PgPool, name: &str) -> i64 {
    sqlx::query_scalar::<_, i64>("INSERT INTO tags (name) VALUES ($1) RETURNING id")
        .bind(name)
        .fetch_one(pool)
        .await
        .expect("insert tag")
}

async fn link_tag(pool: &PgPool, status_id: i64, tag_id: i64) {
    sqlx::query("INSERT INTO statuses_tags (status_id, tag_id) VALUES ($1, $2)")
        .bind(status_id)
        .bind(tag_id)
        .execute(pool)
        .await
        .expect("link tag");
}

async fn insert_mention(pool: &PgPool, status_id: i64, account_id: i64) {
    sqlx::query("INSERT INTO mentions (status_id, account_id) VALUES ($1, $2)")
        .bind(status_id)
        .bind(account_id)
        .execute(pool)
        .await
        .expect("insert mention");
}

#[allow(clippy::too_many_arguments)]
async fn insert_preview_card(
    pool: &PgPool,
    status_id: i64,
    url: &str,
    title: &str,
    description: &str,
    author_name: &str,
    provider_name: &str,
    image_file_name: &str,
) -> i64 {
    let card_id = sqlx::query_scalar::<_, i64>(
        "INSERT INTO preview_cards
            (url, title, description, type, author_name, provider_name, image_file_name, width, height)
         VALUES ($1, $2, $3, 0, $4, $5, $6, 1200, 630)
         RETURNING id",
    )
    .bind(url)
    .bind(title)
    .bind(description)
    .bind(author_name)
    .bind(provider_name)
    .bind(image_file_name)
    .fetch_one(pool)
    .await
    .expect("insert preview_card");

    sqlx::query("INSERT INTO preview_cards_statuses (preview_card_id, status_id) VALUES ($1, $2)")
        .bind(card_id)
        .bind(status_id)
        .execute(pool)
        .await
        .expect("link card");

    card_id
}

async fn insert_custom_emoji(pool: &PgPool, shortcode: &str, file_name: &str) -> i64 {
    sqlx::query_scalar::<_, i64>(
        "INSERT INTO custom_emojis (shortcode, image_file_name) VALUES ($1, $2) RETURNING id",
    )
    .bind(shortcode)
    .bind(file_name)
    .fetch_one(pool)
    .await
    .expect("insert emoji")
}

async fn insert_quote(
    pool: &PgPool,
    status_id: i64,
    quoted_status_id: i64,
    account_id: i64,
    quoted_account_id: i64,
) {
    sqlx::query(
        "INSERT INTO quotes (status_id, quoted_status_id, account_id, quoted_account_id, state)
         VALUES ($1, $2, $3, $4, 1)",
    )
    .bind(status_id)
    .bind(quoted_status_id)
    .bind(account_id)
    .bind(quoted_account_id)
    .execute(pool)
    .await
    .expect("insert quote");
}

#[sqlx::test]
async fn fetch_by_ids_populates_every_enrichment_dimension(pool: PgPool) {
    common::setup_mastodon_schema(&pool).await;

    let alice = insert_account(&pool, "alice", None, "Alice :rust:", "Hi there :rust:").await;
    let bob = insert_account(&pool, "bob", None, "Bob", "").await;
    let carol = insert_account(&pool, "carol", Some("remote.example"), "Carol", "").await;
    insert_account_stats(&pool, alice, 42, 100, 50).await;

    let _rust_emoji = insert_custom_emoji(&pool, "rust", "rust.png").await;

    let quoted = insert_status(&pool, bob, "quoted content", "", Some("en"), 0, None, None).await;
    insert_status_stats(&pool, quoted, 1, 2, 3, 0).await;

    let status_id = insert_status(
        &pool,
        alice,
        "hello world :rust: @bob",
        "cw note",
        Some("en"),
        0,
        None,
        None,
    )
    .await;
    insert_status_stats(&pool, status_id, 5, 10, 42, 3).await;

    let m1 =
        insert_media_attachment(&pool, status_id, alice, 0, "photo.jpg", "A photo", 800, 600).await;
    let m2 =
        insert_media_attachment(&pool, status_id, alice, 2, "vid.mp4", "A video", 1920, 1080).await;
    set_ordered_media(&pool, status_id, &[m2, m1]).await;

    let tag_rust = insert_tag(&pool, "rust").await;
    let tag_programming = insert_tag(&pool, "programming").await;
    link_tag(&pool, status_id, tag_rust).await;
    link_tag(&pool, status_id, tag_programming).await;

    insert_mention(&pool, status_id, bob).await;
    insert_mention(&pool, status_id, carol).await;

    insert_preview_card(
        &pool,
        status_id,
        "https://example.com/article",
        "Example Article",
        "A great article",
        "Alice Author",
        "Example News",
        "og.jpg",
    )
    .await;

    insert_quote(&pool, status_id, quoted, alice, bob).await;

    let media = common::test_media();
    let statuses = fetch_by_ids(&pool, "local.test", &media, &[status_id]).await;

    assert_eq!(statuses.len(), 1);
    let s = &statuses[0];

    assert_eq!(s.id, status_id.to_string());
    assert_eq!(s.visibility, "public");
    assert_eq!(s.language.as_deref(), Some("en"));
    assert!(s.content.contains("hello world"));
    assert_eq!(s.text.as_deref(), Some("hello world :rust: @bob"));
    assert_eq!(s.spoiler_text, "cw note");

    assert_eq!(s.favourites_count, 42);
    assert_eq!(s.reblogs_count, 10);
    assert_eq!(s.replies_count, 5);
    assert_eq!(s.quotes_count, 3);

    assert_eq!(s.account.username, "alice");
    assert_eq!(s.account.acct, "alice");
    assert_eq!(s.account.statuses_count, 42);
    assert_eq!(s.account.followers_count, 100);
    assert_eq!(s.account.following_count, 50);
    assert!(s.account.avatar.contains("/accounts/avatars/"));
    assert!(s.account.avatar.ends_with("avatar.jpg"));
    assert!(s.account.header.ends_with("header.jpg"));

    assert_eq!(s.media_attachments.len(), 2);
    assert_eq!(s.media_attachments[0].id, m2.to_string());
    assert_eq!(s.media_attachments[0].media_type, "video");
    assert_eq!(s.media_attachments[1].id, m1.to_string());
    assert_eq!(s.media_attachments[1].media_type, "image");
    assert_eq!(
        s.media_attachments[1].description.as_deref(),
        Some("A photo")
    );
    assert!(
        s.media_attachments[1]
            .url
            .as_deref()
            .unwrap()
            .contains("/media_attachments/files/")
    );

    let tag_names: Vec<&str> = s.tags.iter().map(|t| t.name.as_str()).collect();
    assert!(tag_names.contains(&"rust"));
    assert!(tag_names.contains(&"programming"));

    assert_eq!(s.mentions.len(), 2);
    let mention_usernames: Vec<&str> = s.mentions.iter().map(|m| m.username.as_str()).collect();
    assert!(mention_usernames.contains(&"bob"));
    assert!(mention_usernames.contains(&"carol"));
    let carol_mention = s.mentions.iter().find(|m| m.username == "carol").unwrap();
    assert_eq!(carol_mention.acct, "carol@remote.example");

    let card = s.card.as_ref().expect("card present");
    assert_eq!(card.title, "Example Article");
    assert_eq!(card.description, "A great article");
    assert_eq!(card.provider_name, "Example News");
    assert!(card.image.as_deref().unwrap().contains("/preview_cards/"));

    assert_eq!(s.emojis.len(), 1);
    assert_eq!(s.emojis[0].shortcode, "rust");
    assert!(s.emojis[0].url.contains("/custom_emojis/"));

    assert_eq!(s.account.emojis.len(), 1);
    assert_eq!(s.account.emojis[0].shortcode, "rust");

    let quote = s.quote.as_ref().expect("quote present");
    assert_eq!(quote.state, "accepted");
    assert_eq!(quote.quoted_status.id, quoted.to_string());
    assert_eq!(quote.quoted_status.text.as_deref(), Some("quoted content"));
    assert_eq!(quote.quoted_status.favourites_count, 3);
    assert!(quote.quoted_status.quote.is_none());

    assert!(!s.favourited);
    assert!(!s.bookmarked);
    assert!(s.filtered.is_empty());
}

#[sqlx::test]
async fn fetch_by_ids_preserves_input_order_and_skips_missing(pool: PgPool) {
    common::setup_mastodon_schema(&pool).await;

    let alice = insert_account(&pool, "alice", None, "Alice", "").await;
    let a = insert_status(&pool, alice, "first", "", None, 0, None, None).await;
    let b = insert_status(&pool, alice, "second", "", None, 0, None, None).await;
    let c = insert_status(&pool, alice, "third", "", None, 0, None, None).await;

    let media = common::test_media();
    let out = fetch_by_ids(&pool, "local.test", &media, &[b, 9_999_999, a, c]).await;
    let texts: Vec<&str> = out
        .iter()
        .map(|s| s.text.as_deref().unwrap_or(""))
        .collect();
    assert_eq!(texts, vec!["second", "first", "third"]);
}

#[sqlx::test]
async fn fetch_by_ids_excludes_deleted_suspended_silenced_private(pool: PgPool) {
    common::setup_mastodon_schema(&pool).await;

    let alice = insert_account(&pool, "alice", None, "Alice", "").await;
    let bob = insert_account(&pool, "bob", None, "Bob", "").await;
    let carol = insert_account(&pool, "carol", None, "Carol", "").await;

    sqlx::query("UPDATE accounts SET suspended_at = NOW() WHERE id = $1")
        .bind(bob)
        .execute(&pool)
        .await
        .unwrap();
    sqlx::query("UPDATE accounts SET silenced_at = NOW() WHERE id = $1")
        .bind(carol)
        .execute(&pool)
        .await
        .unwrap();

    let alive = insert_status(&pool, alice, "alive", "", None, 0, None, None).await;
    let deleted = insert_status(&pool, alice, "deleted", "", None, 0, None, None).await;
    sqlx::query("UPDATE statuses SET deleted_at = NOW() WHERE id = $1")
        .bind(deleted)
        .execute(&pool)
        .await
        .unwrap();
    let private = insert_status(&pool, alice, "private", "", None, 2, None, None).await;
    let suspended_post = insert_status(&pool, bob, "suspended", "", None, 0, None, None).await;
    let silenced_post = insert_status(&pool, carol, "silenced", "", None, 0, None, None).await;

    let media = common::test_media();
    let out = fetch_by_ids(
        &pool,
        "local.test",
        &media,
        &[alive, deleted, private, suspended_post, silenced_post],
    )
    .await;
    assert_eq!(out.len(), 1);
    assert_eq!(out[0].text.as_deref(), Some("alive"));
}

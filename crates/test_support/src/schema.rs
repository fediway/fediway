use sqlx::PgPool;

/// Subset of the Mastodon schema covering only the columns and indexes
/// fediway's local sources query. Mirror real Mastodon when adding more.
#[allow(clippy::too_many_lines)]
pub async fn setup_mastodon_schema(pool: &PgPool) {
    for stmt in [
        r"CREATE TABLE IF NOT EXISTS accounts (
            id                  BIGSERIAL PRIMARY KEY,
            username            TEXT NOT NULL DEFAULT '',
            domain              TEXT,
            display_name        TEXT NOT NULL DEFAULT '',
            note                TEXT NOT NULL DEFAULT '',
            url                 TEXT,
            uri                 TEXT NOT NULL DEFAULT '',
            suspended_at        TIMESTAMP,
            silenced_at         TIMESTAMP,
            memorial            BOOLEAN NOT NULL DEFAULT FALSE,
            moved_to_account_id BIGINT,
            avatar_file_name    TEXT,
            avatar_remote_url   TEXT,
            header_file_name    TEXT,
            header_remote_url   TEXT NOT NULL DEFAULT '',
            created_at          TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_at          TIMESTAMP NOT NULL DEFAULT NOW(),
            discoverable        BOOLEAN,
            indexable           BOOLEAN NOT NULL DEFAULT FALSE,
            locked              BOOLEAN NOT NULL DEFAULT FALSE,
            actor_type                      TEXT,
            fields                          JSONB,
            avatar_storage_schema_version   INTEGER,
            header_storage_schema_version   INTEGER
        )",
        r"CREATE TABLE IF NOT EXISTS account_stats (
            id                  BIGSERIAL PRIMARY KEY,
            account_id          BIGINT NOT NULL,
            statuses_count      BIGINT NOT NULL DEFAULT 0,
            following_count     BIGINT NOT NULL DEFAULT 0,
            followers_count     BIGINT NOT NULL DEFAULT 0,
            last_status_at      TIMESTAMP,
            created_at          TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_at          TIMESTAMP NOT NULL DEFAULT NOW()
        )",
        r"CREATE TABLE IF NOT EXISTS statuses (
            id                              BIGSERIAL PRIMARY KEY,
            account_id                      BIGINT NOT NULL,
            uri                             TEXT,
            url                             TEXT,
            text                            TEXT NOT NULL DEFAULT '',
            spoiler_text                    TEXT NOT NULL DEFAULT '',
            sensitive                       BOOLEAN NOT NULL DEFAULT FALSE,
            language                        TEXT,
            visibility                      INTEGER NOT NULL DEFAULT 0,
            reblog_of_id                    BIGINT,
            in_reply_to_id                  BIGINT,
            in_reply_to_account_id          BIGINT,
            ordered_media_attachment_ids    BIGINT[],
            created_at                      TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_at                      TIMESTAMP NOT NULL DEFAULT NOW(),
            edited_at                       TIMESTAMP,
            deleted_at                      TIMESTAMP
        )",
        r"CREATE TABLE IF NOT EXISTS media_attachments (
            id                      BIGSERIAL PRIMARY KEY,
            status_id               BIGINT,
            account_id              BIGINT,
            type                    INTEGER NOT NULL DEFAULT 0,
            description             TEXT,
            remote_url              TEXT NOT NULL DEFAULT '',
            blurhash                TEXT,
            file_file_name          TEXT,
            file_meta               JSON,
            thumbnail_file_name             TEXT,
            file_storage_schema_version     INTEGER,
            created_at                      TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_at                      TIMESTAMP NOT NULL DEFAULT NOW()
        )",
        r"CREATE TABLE IF NOT EXISTS preview_cards (
            id                  BIGSERIAL PRIMARY KEY,
            url                 TEXT NOT NULL DEFAULT '',
            title               TEXT NOT NULL DEFAULT '',
            description         TEXT NOT NULL DEFAULT '',
            type                INTEGER NOT NULL DEFAULT 0,
            html                TEXT NOT NULL DEFAULT '',
            author_name         TEXT NOT NULL DEFAULT '',
            author_url          TEXT NOT NULL DEFAULT '',
            provider_name       TEXT NOT NULL DEFAULT '',
            provider_url        TEXT NOT NULL DEFAULT '',
            image_file_name     TEXT,
            image_description   TEXT NOT NULL DEFAULT '',
            width               INTEGER NOT NULL DEFAULT 0,
            height              INTEGER NOT NULL DEFAULT 0,
            embed_url                       TEXT NOT NULL DEFAULT '',
            blurhash                        TEXT,
            language                        TEXT,
            image_storage_schema_version    INTEGER,
            created_at                      TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_at                      TIMESTAMP NOT NULL DEFAULT NOW()
        )",
        r"CREATE TABLE IF NOT EXISTS preview_cards_statuses (
            preview_card_id     BIGINT NOT NULL,
            status_id           BIGINT NOT NULL,
            PRIMARY KEY (preview_card_id, status_id)
        )",
        r"CREATE TABLE IF NOT EXISTS custom_emojis (
            id                      BIGSERIAL PRIMARY KEY,
            shortcode               TEXT NOT NULL,
            domain                  TEXT,
            image_file_name         TEXT,
            image_remote_url        TEXT,
            disabled                        BOOLEAN NOT NULL DEFAULT FALSE,
            visible_in_picker               BOOLEAN NOT NULL DEFAULT TRUE,
            image_storage_schema_version    INTEGER,
            created_at                      TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_at                      TIMESTAMP NOT NULL DEFAULT NOW()
        )",
        r"CREATE TABLE IF NOT EXISTS quotes (
            id                  BIGSERIAL PRIMARY KEY,
            account_id          BIGINT NOT NULL,
            status_id           BIGINT NOT NULL,
            quoted_account_id   BIGINT,
            quoted_status_id    BIGINT,
            state               INTEGER NOT NULL DEFAULT 0,
            legacy              BOOLEAN NOT NULL DEFAULT FALSE,
            activity_uri        TEXT,
            approval_uri        TEXT,
            created_at          TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_at          TIMESTAMP NOT NULL DEFAULT NOW()
        )",
        r"CREATE TABLE IF NOT EXISTS tags (
            id              BIGSERIAL PRIMARY KEY,
            name            TEXT NOT NULL UNIQUE
        )",
        r"CREATE TABLE IF NOT EXISTS statuses_tags (
            status_id       BIGINT NOT NULL,
            tag_id          BIGINT NOT NULL,
            PRIMARY KEY (tag_id, status_id)
        )",
        r"CREATE TABLE IF NOT EXISTS status_stats (
            id                  BIGSERIAL PRIMARY KEY,
            status_id           BIGINT NOT NULL,
            replies_count       BIGINT NOT NULL DEFAULT 0,
            reblogs_count       BIGINT NOT NULL DEFAULT 0,
            favourites_count    BIGINT NOT NULL DEFAULT 0,
            quotes_count        BIGINT NOT NULL DEFAULT 0,
            created_at          TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_at          TIMESTAMP NOT NULL DEFAULT NOW()
        )",
        r"CREATE TABLE IF NOT EXISTS favourites (
            id              BIGSERIAL PRIMARY KEY,
            account_id      BIGINT NOT NULL,
            status_id       BIGINT NOT NULL,
            created_at      TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_at      TIMESTAMP NOT NULL DEFAULT NOW()
        )",
        r"CREATE TABLE IF NOT EXISTS bookmarks (
            id              BIGSERIAL PRIMARY KEY,
            account_id      BIGINT NOT NULL,
            status_id       BIGINT NOT NULL,
            created_at      TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_at      TIMESTAMP NOT NULL DEFAULT NOW()
        )",
        r"CREATE TABLE IF NOT EXISTS mentions (
            id              BIGSERIAL PRIMARY KEY,
            status_id       BIGINT NOT NULL,
            account_id      BIGINT NOT NULL,
            silent          BOOLEAN NOT NULL DEFAULT FALSE,
            created_at      TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_at      TIMESTAMP NOT NULL DEFAULT NOW()
        )",
        r"CREATE TABLE IF NOT EXISTS follows (
            id                  BIGSERIAL PRIMARY KEY,
            account_id          BIGINT NOT NULL,
            target_account_id   BIGINT NOT NULL,
            show_reblogs        BOOLEAN NOT NULL DEFAULT TRUE,
            notify              BOOLEAN NOT NULL DEFAULT FALSE,
            uri                 TEXT,
            created_at          TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_at          TIMESTAMP NOT NULL DEFAULT NOW()
        )",
        r"CREATE TABLE IF NOT EXISTS blocks (
            id                  BIGSERIAL PRIMARY KEY,
            account_id          BIGINT NOT NULL,
            target_account_id   BIGINT NOT NULL,
            uri                 TEXT,
            created_at          TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_at          TIMESTAMP NOT NULL DEFAULT NOW()
        )",
        r"CREATE TABLE IF NOT EXISTS mutes (
            id                  BIGSERIAL PRIMARY KEY,
            account_id          BIGINT NOT NULL,
            target_account_id   BIGINT NOT NULL,
            hide_notifications  BOOLEAN NOT NULL DEFAULT TRUE,
            created_at          TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_at          TIMESTAMP NOT NULL DEFAULT NOW()
        )",
        r"CREATE TABLE IF NOT EXISTS account_domain_blocks (
            id                  BIGSERIAL PRIMARY KEY,
            account_id          BIGINT NOT NULL,
            domain              TEXT NOT NULL,
            created_at          TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_at          TIMESTAMP NOT NULL DEFAULT NOW()
        )",
        r"CREATE UNIQUE INDEX IF NOT EXISTS index_status_stats_on_status_id
            ON status_stats (status_id)",
        r"CREATE UNIQUE INDEX IF NOT EXISTS index_favourites_on_account_id_and_status_id
            ON favourites (account_id, status_id)",
        r"CREATE INDEX IF NOT EXISTS index_favourites_on_status_id
            ON favourites (status_id)",
        r"CREATE UNIQUE INDEX IF NOT EXISTS index_bookmarks_on_account_id_and_status_id
            ON bookmarks (account_id, status_id)",
        r"CREATE INDEX IF NOT EXISTS index_bookmarks_on_status_id
            ON bookmarks (status_id)",
        r"CREATE UNIQUE INDEX IF NOT EXISTS index_mentions_on_account_id_and_status_id
            ON mentions (account_id, status_id)",
        r"CREATE INDEX IF NOT EXISTS index_mentions_on_status_id
            ON mentions (status_id)",
        r"CREATE UNIQUE INDEX IF NOT EXISTS index_follows_on_account_id_and_target_account_id
            ON follows (account_id, target_account_id)",
        r"CREATE INDEX IF NOT EXISTS index_follows_on_target_account_id_and_account_id
            ON follows (target_account_id, account_id)",
        r"CREATE INDEX IF NOT EXISTS index_statuses_on_account_id
            ON statuses (account_id)",
        r"CREATE INDEX IF NOT EXISTS index_statuses_on_reblog_of_id_and_account_id
            ON statuses (reblog_of_id, account_id)",
        r"CREATE INDEX IF NOT EXISTS index_statuses_on_in_reply_to_account_id
            ON statuses (in_reply_to_account_id) WHERE in_reply_to_account_id IS NOT NULL",
        r"CREATE UNIQUE INDEX IF NOT EXISTS index_blocks_on_account_id_and_target_account_id
            ON blocks (account_id, target_account_id)",
        r"CREATE UNIQUE INDEX IF NOT EXISTS index_mutes_on_account_id_and_target_account_id
            ON mutes (account_id, target_account_id)",
        r"CREATE UNIQUE INDEX IF NOT EXISTS index_account_domain_blocks_on_account_id_and_domain
            ON account_domain_blocks (account_id, domain)",
        r"CREATE INDEX IF NOT EXISTS index_media_attachments_on_status_id
            ON media_attachments (status_id) WHERE status_id IS NOT NULL",
        r"CREATE INDEX IF NOT EXISTS index_preview_cards_statuses_on_status_id
            ON preview_cards_statuses (status_id)",
        r"CREATE INDEX IF NOT EXISTS index_custom_emojis_on_shortcode_and_domain
            ON custom_emojis (shortcode, domain)",
    ] {
        sqlx::query(stmt)
            .execute(pool)
            .await
            .expect("failed to create mastodon schema");
    }
}

/// Minimal Mastodon-compatible schema for auth tests.
///
/// Mirrors only the columns `apps/server/src/auth.rs` actually reads. No FKs
/// to upstream tables, no extra columns, no `timestamp_id` defaults — just
/// enough to exercise the token resolver and its user-state guards.
const MASTODON_FIXTURE_DDL: &str = "
CREATE TABLE IF NOT EXISTS accounts (
    id BIGSERIAL PRIMARY KEY,
    username VARCHAR NOT NULL DEFAULT '',
    suspended_at TIMESTAMP,
    memorial BOOLEAN NOT NULL DEFAULT FALSE,
    moved_to_account_id BIGINT
);

CREATE TABLE IF NOT EXISTS users (
    id BIGSERIAL PRIMARY KEY,
    account_id BIGINT NOT NULL REFERENCES accounts(id),
    confirmed_at TIMESTAMP,
    approved BOOLEAN NOT NULL DEFAULT TRUE,
    disabled BOOLEAN NOT NULL DEFAULT FALSE,
    chosen_languages VARCHAR[],
    locale VARCHAR
);

CREATE TABLE IF NOT EXISTS oauth_access_tokens (
    id BIGSERIAL PRIMARY KEY,
    token VARCHAR NOT NULL UNIQUE,
    refresh_token VARCHAR,
    expires_in INTEGER,
    revoked_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    scopes VARCHAR,
    application_id BIGINT,
    resource_owner_id BIGINT,
    last_used_at TIMESTAMP,
    last_used_ip INET
);
";

/// Create the minimal Mastodon-compatible tables `auth.rs` queries.
/// Call this in any test that needs a working bearer-token flow.
pub async fn setup_mastodon_fixture(pool: &PgPool) {
    sqlx::raw_sql(MASTODON_FIXTURE_DDL)
        .execute(pool)
        .await
        .expect("failed to create mastodon test fixture");
}

/// Install a Postgres stub of Mastodon's `timestamp_id()` function.
///
/// Mastodon defines `timestamp_id(table_name text) -> bigint` in its migrations;
/// fediway's own migrations use it as a `DEFAULT` on snowflake columns. Test
/// databases need the function to exist before those migrations can run.
pub async fn install_timestamp_id(pool: &PgPool) {
    sqlx::query(
        r"DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_proc WHERE proname = 'timestamp_id') THEN
                CREATE FUNCTION timestamp_id(table_name text) RETURNS bigint AS $fn$
                DECLARE
                    time_part bigint;
                    tail bigint;
                BEGIN
                    time_part := (date_part('epoch', now()) * 1000)::bigint << 16;
                    tail := nextval(table_name || '_id_seq') & 65535;
                    RETURN time_part | tail;
                END;
                $fn$ LANGUAGE plpgsql VOLATILE;
            END IF;
        END
        $$",
    )
    .execute(pool)
    .await
    .expect("failed to create timestamp_id stub");
}

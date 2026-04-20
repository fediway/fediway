pub(super) const BASE_QUERY: &str = r"
    SELECT
        s.id,
        s.account_id,
        s.uri,
        s.url,
        s.text,
        s.spoiler_text,
        s.sensitive,
        s.language,
        s.in_reply_to_id,
        s.in_reply_to_account_id,
        s.created_at,
        s.edited_at,
        a.username,
        a.domain,
        a.display_name,
        a.note,
        a.url AS account_url,
        a.uri AS account_uri,
        a.avatar_file_name,
        a.avatar_remote_url,
        a.header_file_name,
        a.header_remote_url,
        a.created_at AS account_created_at,
        a.discoverable,
        a.indexable,
        a.locked,
        a.actor_type,
        a.fields,
        COALESCE(ast.statuses_count, 0)::bigint  AS statuses_count,
        COALESCE(ast.following_count, 0)::bigint AS following_count,
        COALESCE(ast.followers_count, 0)::bigint AS followers_count,
        ast.last_status_at
    FROM statuses s
    JOIN accounts a ON a.id = s.account_id
    LEFT JOIN account_stats ast ON ast.account_id = a.id
    WHERE s.id = ANY($1::bigint[])
      AND s.deleted_at IS NULL
      AND a.suspended_at IS NULL
      AND a.silenced_at IS NULL
      AND s.visibility IN (0, 1)
      AND s.reblog_of_id IS NULL
    ORDER BY array_position($1::bigint[], s.id)
";

pub(super) const MEDIA_QUERY: &str = r"
    SELECT
        ma.id,
        ma.status_id,
        ma.type AS media_type,
        ma.description,
        ma.remote_url,
        ma.blurhash,
        ma.file_file_name,
        ma.file_meta,
        ma.thumbnail_file_name,
        (a.domain IS NULL) AS account_is_local
    FROM media_attachments ma
    JOIN statuses s ON s.id = ma.status_id
    JOIN accounts a ON a.id = s.account_id
    WHERE ma.status_id = ANY($1::bigint[])
    ORDER BY
        ma.status_id,
        array_position(s.ordered_media_attachment_ids, ma.id) NULLS LAST,
        ma.id
";

pub(super) const CARD_QUERY: &str = r"
    SELECT DISTINCT ON (pcs.status_id)
        pcs.status_id,
        pc.id,
        pc.url,
        pc.title,
        pc.description,
        pc.type AS card_type,
        pc.html,
        pc.author_name,
        pc.author_url,
        pc.provider_name,
        pc.provider_url,
        pc.image_file_name,
        pc.image_description,
        pc.width,
        pc.height,
        pc.embed_url,
        pc.blurhash
    FROM preview_cards_statuses pcs
    JOIN preview_cards pc ON pc.id = pcs.preview_card_id
    WHERE pcs.status_id = ANY($1::bigint[])
    ORDER BY pcs.status_id, pc.id
";

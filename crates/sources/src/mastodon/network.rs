use std::collections::HashMap;

use async_trait::async_trait;
use chrono::Utc;
use common::types::Post;
use feed::candidate::Candidate;
use feed::source::Source;
use sqlx::PgPool;

use crate::mastodon::row::{StatusRow, row_to_post};

const TOP_AUTHORS: i64 = 200;
const POSTS_PER_AUTHOR: i64 = 3;
const RECENCY_HALF_LIFE_HOURS: f64 = 12.0;
const W_AFFINITY: f64 = 0.55;
const W_NETWORK: f64 = 0.25;
const W_RECENCY: f64 = 0.20;

const AFFINITY_QUERY: &str = r"
    WITH
      fav AS (
        SELECT s.account_id AS author_id, count(*)::float * 1.0 AS score
        FROM favourites f JOIN statuses s ON s.id = f.status_id
        WHERE f.account_id = $1 AND f.created_at > now() - interval '90 days'
        GROUP BY s.account_id
      ),
      bookmark AS (
        SELECT s.account_id, count(*)::float * 1.5
        FROM bookmarks b JOIN statuses s ON s.id = b.status_id
        WHERE b.account_id = $1 AND b.created_at > now() - interval '90 days'
        GROUP BY s.account_id
      ),
      reblog AS (
        SELECT orig.account_id, count(*)::float * 3.0
        FROM statuses r JOIN statuses orig ON orig.id = r.reblog_of_id
        WHERE r.account_id = $1
          AND r.reblog_of_id IS NOT NULL
          AND r.created_at > now() - interval '90 days'
        GROUP BY orig.account_id
      ),
      reply AS (
        SELECT in_reply_to_account_id AS author_id, count(*)::float * 4.0
        FROM statuses
        WHERE account_id = $1
          AND in_reply_to_account_id IS NOT NULL
          AND in_reply_to_account_id != $1
          AND created_at > now() - interval '90 days'
        GROUP BY in_reply_to_account_id
      ),
      mention AS (
        SELECT m.account_id, count(*)::float * 1.5
        FROM mentions m JOIN statuses s ON s.id = m.status_id
        WHERE s.account_id = $1
          AND m.account_id != $1
          AND s.visibility != 3
          AND s.created_at > now() - interval '90 days'
        GROUP BY m.account_id
      ),
      dm AS (
        SELECT m.account_id, count(*)::float * 5.0
        FROM mentions m JOIN statuses s ON s.id = m.status_id
        WHERE s.account_id = $1
          AND s.visibility = 3
          AND m.account_id != $1
          AND s.created_at > now() - interval '90 days'
        GROUP BY m.account_id
      )
    SELECT author_id, sum(score) AS affinity
    FROM (
      SELECT * FROM fav
      UNION ALL SELECT * FROM bookmark
      UNION ALL SELECT * FROM reblog
      UNION ALL SELECT * FROM reply
      UNION ALL SELECT * FROM mention
      UNION ALL SELECT * FROM dm
    ) combined
    GROUP BY author_id
    ORDER BY affinity DESC
    LIMIT $2
";

const NETWORK_ENGAGEMENT_QUERY: &str = r"
    SELECT status_id, count(*)::bigint AS net_eng
    FROM (
      SELECT f.status_id
      FROM favourites f
      JOIN follows fol ON fol.target_account_id = f.account_id
      WHERE fol.account_id = $1
        AND f.status_id = ANY($2)

      UNION ALL

      SELECT r.reblog_of_id AS status_id
      FROM statuses r
      JOIN follows fol ON fol.target_account_id = r.account_id
      WHERE fol.account_id = $1
        AND r.reblog_of_id IS NOT NULL
        AND r.reblog_of_id = ANY($2)
    ) e
    GROUP BY status_id
";

const CANDIDATE_QUERY: &str = r"
    WITH ranked AS (
      SELECT
        s.id,
        s.account_id,
        s.uri,
        COALESCE(s.url, s.uri) AS url,
        s.text,
        s.spoiler_text,
        s.sensitive,
        s.language,
        s.created_at,
        a.username,
        a.domain,
        a.display_name,
        a.url AS account_url,
        ROW_NUMBER() OVER (
          PARTITION BY s.account_id
          ORDER BY
            (COALESCE(ss.favourites_count, 0) + COALESCE(ss.reblogs_count, 0)) DESC,
            s.created_at DESC
        ) AS rn
      FROM statuses s
      JOIN accounts a ON a.id = s.account_id
      LEFT JOIN status_stats ss ON ss.status_id = s.id
      LEFT JOIN blocks bl
        ON bl.account_id = $4 AND bl.target_account_id = s.account_id
      LEFT JOIN mutes mu
        ON mu.account_id = $4 AND mu.target_account_id = s.account_id
      LEFT JOIN account_domain_blocks dbl
        ON dbl.account_id = $4 AND dbl.domain = a.domain
      WHERE s.account_id = ANY($1)
        AND s.created_at > now() - interval '48 hours'
        AND s.visibility IN (0, 1)
        AND (s.in_reply_to_id IS NULL OR s.in_reply_to_account_id = s.account_id)
        AND s.reblog_of_id IS NULL
        AND s.deleted_at IS NULL
        AND a.suspended_at IS NULL
        AND a.silenced_at IS NULL
        AND bl.id IS NULL
        AND mu.id IS NULL
        AND dbl.id IS NULL
    )
    SELECT
      id, account_id, uri, url, text, spoiler_text, sensitive, language,
      created_at, username, domain, display_name, account_url
    FROM ranked
    WHERE rn <= $2
    ORDER BY created_at DESC
    LIMIT $3
";

fn log_normalize(rows: Vec<(i64, f64)>) -> HashMap<i64, f64> {
    let max = rows.iter().map(|(_, v)| *v).fold(0.0_f64, f64::max);
    let log_max = (1.0_f64 + max).ln();
    rows.into_iter()
        .map(|(id, v)| {
            let norm = if log_max > 0.0 {
                (1.0_f64 + v).ln() / log_max
            } else {
                0.0
            };
            (id, norm)
        })
        .collect()
}

pub struct NetworkSource {
    db: PgPool,
    user_id: i64,
    instance_domain: String,
}

impl NetworkSource {
    #[must_use]
    pub fn new(db: PgPool, user_id: i64, instance_domain: String) -> Self {
        Self {
            db,
            user_id,
            instance_domain,
        }
    }
}

#[async_trait]
impl Source<Post> for NetworkSource {
    fn name(&self) -> &'static str {
        "local/network"
    }

    async fn collect(&self, limit: usize) -> Vec<Candidate<Post>> {
        let affinity_rows: Vec<(i64, f64)> = match sqlx::query_as(AFFINITY_QUERY)
            .bind(self.user_id)
            .bind(TOP_AUTHORS)
            .fetch_all(&self.db)
            .await
        {
            Ok(rows) => rows,
            Err(e) => {
                tracing::warn!(
                    error = %e,
                    user_id = self.user_id,
                    "network affinity query failed"
                );
                return Vec::new();
            }
        };

        if affinity_rows.is_empty() {
            return Vec::new();
        }

        let affinity = log_normalize(affinity_rows);
        let author_ids: Vec<i64> = affinity.keys().copied().collect();

        let candidate_rows: Vec<StatusRow> = match sqlx::query_as(CANDIDATE_QUERY)
            .bind(&author_ids[..])
            .bind(POSTS_PER_AUTHOR)
            .bind(i64::try_from(limit).unwrap_or(i64::MAX))
            .bind(self.user_id)
            .fetch_all(&self.db)
            .await
        {
            Ok(rows) => rows,
            Err(e) => {
                tracing::warn!(
                    error = %e,
                    user_id = self.user_id,
                    "network candidate query failed"
                );
                return Vec::new();
            }
        };

        let candidate_ids: Vec<i64> = candidate_rows.iter().map(|r| r.id).collect();

        let net_eng_rows: Vec<(i64, i64)> = match sqlx::query_as(NETWORK_ENGAGEMENT_QUERY)
            .bind(self.user_id)
            .bind(&candidate_ids[..])
            .fetch_all(&self.db)
            .await
        {
            Ok(rows) => rows,
            Err(e) => {
                tracing::warn!(
                    error = %e,
                    user_id = self.user_id,
                    "network engagement query failed; degrading to affinity+recency only"
                );
                Vec::new()
            }
        };

        #[allow(clippy::cast_precision_loss)]
        let log_max_net = net_eng_rows
            .iter()
            .map(|(_, n)| *n)
            .max()
            .map_or(0.0, |m| (1.0_f64 + m as f64).ln());
        let net_eng: HashMap<i64, f64> = net_eng_rows
            .into_iter()
            .map(|(id, n)| {
                #[allow(clippy::cast_precision_loss)]
                let log_n = (1.0_f64 + n as f64).ln();
                let norm = if log_max_net > 0.0 {
                    log_n / log_max_net
                } else {
                    0.0
                };
                (id, norm)
            })
            .collect();

        let now = Utc::now();
        candidate_rows
            .into_iter()
            .map(|row| {
                let affinity_norm = affinity.get(&row.account_id).copied().unwrap_or(0.0);
                let net_eng_norm = net_eng.get(&row.id).copied().unwrap_or(0.0);
                #[allow(clippy::cast_precision_loss)]
                let age_hours = (now - row.created_at).num_seconds() as f64 / 3600.0;
                let recency = (-age_hours / RECENCY_HALF_LIFE_HOURS).exp();
                let score =
                    W_AFFINITY * affinity_norm + W_NETWORK * net_eng_norm + W_RECENCY * recency;

                let post = row_to_post(row, &self.instance_domain);
                let mut candidate = Candidate::new(post, "local/network");
                candidate.score = score;
                candidate
            })
            .collect()
    }
}

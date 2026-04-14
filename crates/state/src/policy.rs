use std::collections::HashSet;

use sqlx::PgPool;

#[derive(Debug, Default, Clone)]
pub struct UserPolicy {
    pub blocked_handles: HashSet<String>,
    pub muted_handles: HashSet<String>,
    pub blocked_domains: HashSet<String>,
}

impl UserPolicy {
    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.blocked_handles.is_empty()
            && self.muted_handles.is_empty()
            && self.blocked_domains.is_empty()
    }
}

pub async fn load(db: &PgPool, user_id: i64, instance_domain: &str) -> UserPolicy {
    let (blocks, mutes, domains) = tokio::join!(
        load_handles(db, user_id, BLOCKS_QUERY, instance_domain),
        load_handles(db, user_id, MUTES_QUERY, instance_domain),
        load_blocked_domains(db, user_id),
    );

    UserPolicy {
        blocked_handles: blocks,
        muted_handles: mutes,
        blocked_domains: domains,
    }
}

const BLOCKS_QUERY: &str = r"
    SELECT a.username, a.domain
    FROM blocks b JOIN accounts a ON a.id = b.target_account_id
    WHERE b.account_id = $1
";

const MUTES_QUERY: &str = r"
    SELECT a.username, a.domain
    FROM mutes m JOIN accounts a ON a.id = m.target_account_id
    WHERE m.account_id = $1
";

async fn load_handles(
    db: &PgPool,
    user_id: i64,
    query: &str,
    instance_domain: &str,
) -> HashSet<String> {
    match sqlx::query_as::<_, (String, Option<String>)>(query)
        .bind(user_id)
        .fetch_all(db)
        .await
    {
        Ok(rows) => rows
            .into_iter()
            .map(|(username, domain)| match domain {
                Some(d) => format!("{username}@{d}"),
                None => format!("{username}@{instance_domain}"),
            })
            .collect(),
        Err(e) => {
            tracing::warn!(error = %e, user_id, "policy handle query failed");
            HashSet::new()
        }
    }
}

async fn load_blocked_domains(db: &PgPool, user_id: i64) -> HashSet<String> {
    match sqlx::query_scalar::<_, String>(
        "SELECT domain FROM account_domain_blocks WHERE account_id = $1",
    )
    .bind(user_id)
    .fetch_all(db)
    .await
    {
        Ok(rows) => rows.into_iter().collect(),
        Err(e) => {
            tracing::warn!(error = %e, user_id, "blocked domains query failed");
            HashSet::new()
        }
    }
}

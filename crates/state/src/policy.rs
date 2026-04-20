use std::collections::HashSet;

use common::ids::AccountId;
use sqlx::{Executor, PgPool, Postgres};

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

#[tracing::instrument(
    skip(db),
    name = "db.policy.load",
    fields(account = ?account, instance_domain = %instance_domain),
)]
pub async fn load(
    db: &PgPool,
    account: AccountId,
    instance_domain: &str,
) -> Result<UserPolicy, crate::Error> {
    let (blocked_handles, muted_handles, blocked_domains) = tokio::try_join!(
        load_handles(db, account, BLOCKS_QUERY, instance_domain),
        load_handles(db, account, MUTES_QUERY, instance_domain),
        load_blocked_domains(db, account),
    )?;

    Ok(UserPolicy {
        blocked_handles,
        muted_handles,
        blocked_domains,
    })
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

#[tracing::instrument(
    skip(e, query),
    name = "db.policy.load_handles",
    fields(account = ?account, instance_domain = %instance_domain),
)]
async fn load_handles(
    e: impl Executor<'_, Database = Postgres>,
    account: AccountId,
    query: &str,
    instance_domain: &str,
) -> Result<HashSet<String>, crate::Error> {
    let rows = sqlx::query_as::<_, (String, Option<String>)>(query)
        .bind(account)
        .fetch_all(e)
        .await?;
    Ok(rows
        .into_iter()
        .map(|(username, domain)| match domain {
            Some(d) => format!("{username}@{d}"),
            None => format!("{username}@{instance_domain}"),
        })
        .collect())
}

#[tracing::instrument(
    skip(e),
    name = "db.policy.load_blocked_domains",
    fields(account = ?account),
)]
async fn load_blocked_domains(
    e: impl Executor<'_, Database = Postgres>,
    account: AccountId,
) -> Result<HashSet<String>, crate::Error> {
    let rows = sqlx::query_scalar::<_, String>(
        "SELECT domain FROM account_domain_blocks WHERE account_id = $1",
    )
    .bind(account)
    .fetch_all(e)
    .await?;
    Ok(rows.into_iter().collect())
}

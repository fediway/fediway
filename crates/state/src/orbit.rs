use common::ids::AccountId;
use sqlx::{Executor, Postgres};

/// Load a user's interest vector and engagement count.
///
/// `Ok(None)` means cold start (no row); `Err` means the query itself failed.
#[tracing::instrument(
    skip(e),
    name = "db.orbit.load_vector",
    fields(account = ?account),
)]
pub async fn load_vector(
    e: impl Executor<'_, Database = Postgres>,
    account: AccountId,
) -> Result<Option<(Vec<f32>, i64)>, crate::Error> {
    Ok(sqlx::query_as::<_, (Vec<f32>, i64)>(
        "SELECT vector, engagement_count FROM orbit_user_vectors WHERE account_id = $1",
    )
    .bind(account)
    .fetch_optional(e)
    .await?)
}

/// Drop every orbit polling cursor.
///
/// Next orbit worker startup re-initializes cursors from `ORBIT_REPLAY_HOURS`,
/// which is how an operator rebuilds state after fixing data issues or
/// changing the embedding model.
#[tracing::instrument(skip(e), name = "db.orbit.wipe_cursors")]
pub async fn wipe_cursors(e: impl Executor<'_, Database = Postgres>) -> Result<u64, crate::Error> {
    let result = sqlx::query("DELETE FROM orbit_cursors").execute(e).await?;
    Ok(result.rows_affected())
}

/// Drop every user vector.
///
/// Pairs with [`wipe_cursors`] for a full rebuild — running either alone
/// is almost never what you want, because the remaining table desyncs
/// from the data that produced it.
#[tracing::instrument(skip(e), name = "db.orbit.wipe_vectors")]
pub async fn wipe_vectors(e: impl Executor<'_, Database = Postgres>) -> Result<u64, crate::Error> {
    let result = sqlx::query("DELETE FROM orbit_user_vectors")
        .execute(e)
        .await?;
    Ok(result.rows_affected())
}

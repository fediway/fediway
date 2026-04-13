use sqlx::PgPool;

/// Load a user's interest vector and engagement count.
///
/// Returns `None` if the user has no vector (cold start).
pub async fn load_vector(db: &PgPool, account_id: i64) -> Option<(Vec<f32>, i64)> {
    sqlx::query_as::<_, (Vec<f32>, i64)>(
        "SELECT vector, engagement_count FROM orbit_user_vectors WHERE account_id = $1",
    )
    .bind(account_id)
    .fetch_optional(db)
    .await
    .ok()
    .flatten()
}

/// Drop every orbit polling cursor.
///
/// Next orbit worker startup re-initializes cursors from `ORBIT_REPLAY_HOURS`,
/// which is how an operator rebuilds state after fixing data issues or
/// changing the embedding model.
pub async fn wipe_cursors(db: &PgPool) -> Result<u64, sqlx::Error> {
    let result = sqlx::query("DELETE FROM orbit_cursors").execute(db).await?;
    Ok(result.rows_affected())
}

/// Drop every user vector.
///
/// Pairs with [`wipe_cursors`] for a full rebuild — running either alone
/// is almost never what you want, because the remaining table desyncs
/// from the data that produced it.
pub async fn wipe_vectors(db: &PgPool) -> Result<u64, sqlx::Error> {
    let result = sqlx::query("DELETE FROM orbit_user_vectors")
        .execute(db)
        .await?;
    Ok(result.rows_affected())
}

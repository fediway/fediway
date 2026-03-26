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

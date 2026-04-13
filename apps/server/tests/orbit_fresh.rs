mod common;

use sqlx::PgPool;

async fn insert_cursor(pool: &PgPool, source: &str, last_id: i64) {
    sqlx::query(
        "INSERT INTO orbit_cursors (source_name, last_id, updated_at)
         VALUES ($1, $2, now())",
    )
    .bind(source)
    .bind(last_id)
    .execute(pool)
    .await
    .unwrap();
}

async fn insert_vector(pool: &PgPool, account_id: i64) {
    let vec = vec![0.1f32; 64];
    sqlx::query(
        "INSERT INTO orbit_user_vectors (account_id, vector, engagement_count, updated_at)
         VALUES ($1, $2, 5, now())",
    )
    .bind(account_id)
    .bind(&vec[..])
    .execute(pool)
    .await
    .unwrap();
}

async fn count(pool: &PgPool, table: &str) -> i64 {
    sqlx::query_scalar::<_, i64>(&format!("SELECT COUNT(*) FROM {table}"))
        .fetch_one(pool)
        .await
        .unwrap()
}

#[sqlx::test]
async fn wipe_cursors_empties_the_table(pool: PgPool) {
    common::setup_db(&pool).await;
    insert_cursor(&pool, "like", 100).await;
    insert_cursor(&pool, "repost", 200).await;

    let deleted = state::orbit::wipe_cursors(&pool).await.unwrap();
    assert_eq!(deleted, 2);
    assert_eq!(count(&pool, "orbit_cursors").await, 0);
}

#[sqlx::test]
async fn wipe_vectors_empties_the_table(pool: PgPool) {
    common::setup_db(&pool).await;
    insert_vector(&pool, 1).await;
    insert_vector(&pool, 2).await;
    insert_vector(&pool, 3).await;

    let deleted = state::orbit::wipe_vectors(&pool).await.unwrap();
    assert_eq!(deleted, 3);
    assert_eq!(count(&pool, "orbit_user_vectors").await, 0);
}

#[sqlx::test]
async fn wipe_on_empty_table_reports_zero(pool: PgPool) {
    common::setup_db(&pool).await;

    let cursors = state::orbit::wipe_cursors(&pool).await.unwrap();
    let vectors = state::orbit::wipe_vectors(&pool).await.unwrap();

    assert_eq!(cursors, 0);
    assert_eq!(vectors, 0);
}

#[sqlx::test]
async fn wipe_cursors_does_not_touch_vectors(pool: PgPool) {
    common::setup_db(&pool).await;
    insert_cursor(&pool, "like", 100).await;
    insert_vector(&pool, 42).await;

    state::orbit::wipe_cursors(&pool).await.unwrap();

    assert_eq!(count(&pool, "orbit_cursors").await, 0);
    assert_eq!(count(&pool, "orbit_user_vectors").await, 1);
}

#[sqlx::test]
async fn wipe_vectors_does_not_touch_cursors(pool: PgPool) {
    common::setup_db(&pool).await;
    insert_cursor(&pool, "like", 100).await;
    insert_vector(&pool, 42).await;

    state::orbit::wipe_vectors(&pool).await.unwrap();

    assert_eq!(count(&pool, "orbit_cursors").await, 1);
    assert_eq!(count(&pool, "orbit_user_vectors").await, 0);
}

use sqlx::PgPool;

#[allow(unused_imports)]
pub use test_support::media::{test_media, test_media_s3};
#[allow(unused_imports)]
pub use test_support::schema::setup_mastodon_schema;

#[allow(dead_code)]
pub async fn setup_db(pool: &PgPool) {
    test_support::schema::install_timestamp_id(pool).await;
    state::db::migrate(pool).await.expect("migrations failed");
}

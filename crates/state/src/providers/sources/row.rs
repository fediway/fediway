use sqlx::FromRow;

#[derive(FromRow)]
pub(super) struct BoundProviderRow {
    pub(super) domain: String,
    pub(super) base_url: String,
    pub(super) api_key: String,
    pub(super) max_results: i32,
    pub(super) filters: Vec<String>,
    pub(super) algorithm: String,
}

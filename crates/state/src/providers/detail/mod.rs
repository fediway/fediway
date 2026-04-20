mod fetch;

pub use fetch::{find_base_url, find_by_domain, find_registration};

#[derive(Debug, sqlx::FromRow)]
pub struct Registration {
    pub api_key: Option<String>,
    pub status: Option<String>,
}

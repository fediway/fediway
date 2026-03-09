use config::DatabaseConfig;
use sqlx::PgPool;
use sqlx::postgres::PgPoolOptions;

pub async fn connect(config: &DatabaseConfig) -> Result<PgPool, sqlx::Error> {
    let url = format!(
        "postgres://{}{}@{}:{}/{}",
        config.db_user,
        config
            .db_pass
            .as_ref()
            .map_or(String::new(), |p| format!(":{p}")),
        config.db_host,
        config.db_port,
        config.db_name,
    );

    PgPoolOptions::new()
        .max_connections(config.db_pool_size)
        .connect(&url)
        .await
}

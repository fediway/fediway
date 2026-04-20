use std::str::FromStr;
use std::time::Duration;

use config::DatabaseConfig;
use log::LevelFilter;
use sqlx::ConnectOptions;
use sqlx::PgPool;
use sqlx::postgres::{PgConnectOptions, PgPoolOptions, PgSslMode};

pub async fn check(pool: &PgPool) -> Result<(), sqlx::Error> {
    sqlx::query_scalar::<_, i32>("SELECT 1")
        .fetch_one(pool)
        .await?;
    Ok(())
}

pub async fn migrate(pool: &PgPool) -> Result<(), sqlx::migrate::MigrateError> {
    sqlx::migrate!("src/migrations").run(pool).await
}

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

    let ssl_mode = PgSslMode::from_str(&config.db_ssl_mode).map_err(|_| {
        sqlx::Error::Configuration(format!("invalid sslmode: {}", config.db_ssl_mode).into())
    })?;

    let connect_options = PgConnectOptions::from_str(&url)?
        .ssl_mode(ssl_mode)
        .log_statements(LevelFilter::Debug)
        .log_slow_statements(LevelFilter::Warn, Duration::from_millis(50));

    let timeout_secs = config.db_statement_timeout_secs;
    PgPoolOptions::new()
        .max_connections(config.db_pool_size)
        .min_connections(config.db_pool_min)
        .acquire_timeout(Duration::from_secs(config.db_acquire_timeout_secs))
        .idle_timeout(Duration::from_secs(config.db_idle_timeout_secs))
        .max_lifetime(Duration::from_secs(config.db_max_lifetime_secs))
        .after_connect(move |conn, _meta| {
            Box::pin(async move {
                let timeout_ms = timeout_secs * 1000;
                sqlx::query(&format!("SET statement_timeout = {timeout_ms}"))
                    .execute(&mut *conn)
                    .await?;
                sqlx::query("SET lock_timeout = '1s'")
                    .execute(&mut *conn)
                    .await?;
                sqlx::query("SET idle_in_transaction_session_timeout = '10s'")
                    .execute(&mut *conn)
                    .await?;
                Ok(())
            })
        })
        .connect_with(connect_options)
        .await
}

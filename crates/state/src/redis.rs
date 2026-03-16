use config::RedisConfig;
use redis::aio::ConnectionManager;

pub async fn connect(config: &RedisConfig) -> Result<ConnectionManager, redis::RedisError> {
    let client = redis::Client::open(config.url())?;
    ConnectionManager::new(client).await
}

/// Verify Redis is reachable by sending a PING command.
pub async fn check(conn: &ConnectionManager) -> Result<(), redis::RedisError> {
    let mut conn = conn.clone();
    let _: String = redis::cmd("PING").query_async(&mut conn).await?;
    Ok(())
}

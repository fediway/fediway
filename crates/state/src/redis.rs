use config::RedisConfig;
use redis::aio::ConnectionManager;

pub async fn connect(config: &RedisConfig) -> Result<ConnectionManager, redis::RedisError> {
    let url = format!("redis://{}:{}", config.redis_host, config.redis_port);
    let client = redis::Client::open(url)?;
    ConnectionManager::new(client).await
}

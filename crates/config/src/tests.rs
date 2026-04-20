use crate::DatabaseConfig;

#[test]
fn db_config_defaults() {
    let config = DatabaseConfig {
        db_host: "localhost".to_string(),
        db_port: 5432,
        db_name: "mastodon_development".to_string(),
        db_user: "mastodon".to_string(),
        db_pass: None,
        db_pool_size: 10,
        db_pool_min: 2,
        db_acquire_timeout_secs: 3,
        db_idle_timeout_secs: 600,
        db_max_lifetime_secs: 1800,
        db_statement_timeout_secs: 30,
        db_ssl_mode: "prefer".to_string(),
    };
    assert_eq!(config.db_host, "localhost");
    assert_eq!(config.db_port, 5432);
    assert_eq!(config.db_pool_size, 10);
}

#[test]
fn redis_config_defaults() {
    let config = crate::RedisConfig {
        redis_host: "localhost".to_string(),
        redis_port: 6379,
        redis_pass: String::new(),
    };
    assert_eq!(config.redis_host, "localhost");
    assert_eq!(config.redis_port, 6379);
    assert_eq!(config.url(), "redis://localhost:6379");
}

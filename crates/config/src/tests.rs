use crate::FediwayConfig;

#[test]
fn defaults_for_local_dev() {
    let config = FediwayConfig::load();
    assert_eq!(config.db.db_host, "localhost");
    assert_eq!(config.db.db_port, 5432);
    assert_eq!(config.db.db_pool_size, 5);
    assert_eq!(config.redis.redis_host, "localhost");
    assert_eq!(config.redis.redis_port, 6379);
}

#[test]
fn db_config_defaults_via_serde() {
    let config: crate::DatabaseConfig = serde_json::from_str("{}").unwrap();
    assert_eq!(config.db_host, "localhost");
    assert_eq!(config.db_port, 5432);
    assert_eq!(config.db_name, "mastodon_development");
    assert_eq!(config.db_user, "mastodon");
    assert!(config.db_pass.is_none());
    assert_eq!(config.db_pool_size, 5);
}

#[test]
fn db_config_custom_pool_size() {
    let config: crate::DatabaseConfig = serde_json::from_str(r#"{"db_pool_size": 20}"#).unwrap();
    assert_eq!(config.db_pool_size, 20);
}

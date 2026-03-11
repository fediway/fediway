mod db;
mod instance;
pub mod metrics;
mod redis;

pub use self::redis::RedisConfig;
pub use db::DatabaseConfig;
pub use instance::InstanceConfig;

#[derive(Debug)]
pub struct FediwayConfig {
    pub db: DatabaseConfig,
    pub redis: RedisConfig,
    pub instance: InstanceConfig,
}

impl FediwayConfig {
    #[must_use]
    pub fn load() -> Self {
        Self {
            db: DatabaseConfig::load(),
            redis: RedisConfig::load(),
            instance: InstanceConfig::load(),
        }
    }
}

#[cfg(test)]
mod tests;

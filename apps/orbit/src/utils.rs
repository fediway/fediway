use serde::{Deserialize, Deserializer};
use std::time::{Duration, SystemTime, UNIX_EPOCH};

pub fn deserialize_timestamp<'de, D>(deserializer: D) -> Result<SystemTime, D::Error>
where
    D: Deserializer<'de>,
{
    let timestamp = i64::deserialize(deserializer)?;

    // Convert milliseconds to SystemTime
    let duration = Duration::from_millis(timestamp as u64);
    Ok(UNIX_EPOCH + duration)
}

pub fn duration_since_or_zero(a: SystemTime, b: SystemTime) -> u64 {
    match a.duration_since(b) {
        Ok(duration) => duration.as_secs(),
        Err(_) => 0,
    }
}

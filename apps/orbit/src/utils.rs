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

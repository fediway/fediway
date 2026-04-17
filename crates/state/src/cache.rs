use std::collections::HashMap;
use std::sync::Arc;
use std::sync::Mutex;
use std::sync::atomic::{AtomicI64, AtomicU32, Ordering};
use std::time::{Duration, SystemTime, UNIX_EPOCH};

use redis::aio::ConnectionManager;
use serde::Serialize;
use serde::de::DeserializeOwned;

const FAILURE_THRESHOLD: u32 = 5;
const COOLDOWN: Duration = Duration::from_secs(30);

#[derive(Default)]
struct CircuitState {
    consecutive_failures: AtomicU32,
    skip_until_unix: AtomicI64,
}

impl CircuitState {
    fn is_open(&self) -> bool {
        self.skip_until_unix.load(Ordering::Relaxed) > now_unix()
    }

    fn record_success(&self) {
        self.consecutive_failures.store(0, Ordering::Relaxed);
    }

    fn record_failure(&self) {
        let prev = self.consecutive_failures.fetch_add(1, Ordering::Relaxed);
        if prev + 1 >= FAILURE_THRESHOLD {
            self.skip_until_unix.store(
                now_unix() + COOLDOWN.as_secs().cast_signed(),
                Ordering::Relaxed,
            );
        }
    }
}

fn now_unix() -> i64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_secs().cast_signed())
        .unwrap_or(0)
}

#[derive(Clone)]
enum Backend {
    Redis(ConnectionManager),
    Memory(Arc<Mutex<HashMap<String, String>>>),
    Disabled,
}

#[derive(Clone)]
pub struct Cache {
    backend: Backend,
    prefix: String,
    breaker: Arc<CircuitState>,
}

impl Cache {
    #[must_use]
    pub fn new(conn: ConnectionManager, prefix: impl Into<String>) -> Self {
        Self {
            backend: Backend::Redis(conn),
            prefix: prefix.into(),
            breaker: Arc::new(CircuitState::default()),
        }
    }

    #[must_use]
    pub fn disabled() -> Self {
        Self {
            backend: Backend::Disabled,
            prefix: String::new(),
            breaker: Arc::new(CircuitState::default()),
        }
    }

    /// In-memory cache for tests. TTL is ignored — entries persist for
    /// the lifetime of the handle.
    #[must_use]
    pub fn in_memory() -> Self {
        Self {
            backend: Backend::Memory(Arc::new(Mutex::new(HashMap::new()))),
            prefix: String::new(),
            breaker: Arc::new(CircuitState::default()),
        }
    }

    pub async fn get<T: DeserializeOwned>(&self, key: &str) -> Option<T> {
        let full_key = self.full_key(key);
        match &self.backend {
            Backend::Disabled => None,
            Backend::Memory(store) => {
                let json = store.lock().ok()?.get(&full_key).cloned()?;
                serde_json::from_str(&json).ok()
            }
            Backend::Redis(conn) => {
                if self.breaker.is_open() {
                    return None;
                }
                let mut conn = conn.clone();
                match redis::cmd("GET")
                    .arg(&full_key)
                    .query_async::<Option<String>>(&mut conn)
                    .await
                {
                    Ok(Some(json)) => {
                        self.breaker.record_success();
                        match serde_json::from_str(&json) {
                            Ok(value) => Some(value),
                            Err(e) => {
                                tracing::warn!(key = %full_key, error = %e, "cache deserialize failed");
                                None
                            }
                        }
                    }
                    Ok(None) => {
                        self.breaker.record_success();
                        None
                    }
                    Err(e) => {
                        self.breaker.record_failure();
                        tracing::warn!(key = %full_key, error = %e, "cache get failed");
                        None
                    }
                }
            }
        }
    }

    pub async fn set<T: Serialize>(&self, key: &str, value: &T, ttl: Duration) {
        let full_key = self.full_key(key);
        let json = match serde_json::to_string(value) {
            Ok(s) => s,
            Err(e) => {
                tracing::warn!(key = %full_key, error = %e, "cache serialize failed");
                return;
            }
        };
        match &self.backend {
            Backend::Disabled => {}
            Backend::Memory(store) => {
                if let Ok(mut map) = store.lock() {
                    map.insert(full_key, json);
                }
            }
            Backend::Redis(conn) => {
                if self.breaker.is_open() {
                    return;
                }
                let ttl_secs = ttl.as_secs().max(1);
                let mut conn = conn.clone();
                match redis::cmd("SET")
                    .arg(&full_key)
                    .arg(json)
                    .arg("EX")
                    .arg(ttl_secs)
                    .query_async::<()>(&mut conn)
                    .await
                {
                    Ok(()) => self.breaker.record_success(),
                    Err(e) => {
                        self.breaker.record_failure();
                        tracing::warn!(key = %full_key, error = %e, "cache set failed");
                    }
                }
            }
        }
    }

    fn full_key(&self, key: &str) -> String {
        format!("{}:{}", self.prefix, key)
    }
}

use thiserror::Error;

#[derive(Debug, Error)]
pub enum FediwayError {
    #[error("config error: {0}")]
    Config(String),

    #[error("state error: {0}")]
    State(String),

    #[error("source error: {0}")]
    Source(String),

    #[error("database error: {0}")]
    Database(String),
}

#[derive(Debug, thiserror::Error)]
pub enum Error {
    #[error("not found")]
    NotFound,

    #[error("conflict on constraint `{constraint}`")]
    Conflict { constraint: String },

    #[error("invalid reference on constraint `{constraint}`")]
    InvalidReference { constraint: String },

    #[error("check violation on constraint `{constraint}`")]
    CheckViolation { constraint: String },

    #[error("serialization failure")]
    Serialization,

    #[error("deadlock detected")]
    Deadlock,

    #[error("query timeout")]
    Timeout,

    #[error("database unavailable")]
    Unavailable,

    #[error("authentication failure")]
    AuthFailure,

    #[error(transparent)]
    Internal(sqlx::Error),
}

impl From<sqlx::Error> for Error {
    fn from(err: sqlx::Error) -> Self {
        use sqlx::Error as E;
        match err {
            E::RowNotFound => Self::NotFound,
            E::PoolTimedOut => Self::Unavailable,
            E::Database(db_err) => {
                let code = db_err.code();
                let constraint = db_err.constraint().map(str::to_owned).unwrap_or_default();
                match code.as_deref() {
                    Some("23505") => Self::Conflict { constraint },
                    Some("23503") => Self::InvalidReference { constraint },
                    Some("23514") => Self::CheckViolation { constraint },
                    Some("40001") => Self::Serialization,
                    Some("40P01") => Self::Deadlock,
                    Some("57014") => Self::Timeout,
                    Some("28000" | "28P01") => Self::AuthFailure,
                    _ => Self::Internal(E::Database(db_err)),
                }
            }
            other => Self::Internal(other),
        }
    }
}

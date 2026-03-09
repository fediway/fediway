use axum::http::StatusCode;

use crate::auth::Account;

pub async fn handle(_account: Account) -> StatusCode {
    StatusCode::OK
}

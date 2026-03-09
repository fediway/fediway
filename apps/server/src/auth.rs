use axum::extract::{FromRequestParts, OptionalFromRequestParts};
use axum::http::StatusCode;
use axum::http::request::Parts;
use sqlx::PgPool;

#[derive(Debug, Clone)]
pub struct Account {
    pub id: i64,
    pub username: String,
    pub chosen_languages: Vec<String>,
}

impl FromRequestParts<PgPool> for Account {
    type Rejection = StatusCode;

    async fn from_request_parts(parts: &mut Parts, db: &PgPool) -> Result<Self, Self::Rejection> {
        let token = extract_token(parts).ok_or(StatusCode::UNAUTHORIZED)?;
        resolve_account(db, &token)
            .await
            .ok_or(StatusCode::UNAUTHORIZED)
    }
}

impl OptionalFromRequestParts<PgPool> for Account {
    type Rejection = StatusCode;

    async fn from_request_parts(
        parts: &mut Parts,
        db: &PgPool,
    ) -> Result<Option<Self>, Self::Rejection> {
        let account = match extract_token(parts) {
            Some(token) => resolve_account(db, &token).await,
            None => None,
        };
        Ok(account)
    }
}

fn extract_token(parts: &Parts) -> Option<String> {
    let header = parts.headers.get("authorization")?.to_str().ok()?;
    let token = header.strip_prefix("Bearer ")?.trim();
    if token.is_empty() {
        return None;
    }
    Some(token.to_string())
}

#[derive(sqlx::FromRow)]
struct TokenRow {
    account_id: i64,
    username: String,
    chosen_languages: Option<Vec<String>>,
}

async fn resolve_account(db: &PgPool, token: &str) -> Option<Account> {
    let row = sqlx::query_as::<_, TokenRow>(
        "SELECT u.account_id, a.username, u.chosen_languages
         FROM oauth_access_tokens t
         JOIN users u ON u.id = t.resource_owner_id
         JOIN accounts a ON a.id = u.account_id
         WHERE t.token = $1
           AND t.revoked_at IS NULL
           AND (t.expires_in IS NULL OR t.created_at + t.expires_in * INTERVAL '1 second' > NOW())",
    )
    .bind(token)
    .fetch_optional(db)
    .await
    .ok()
    .flatten()?;

    Some(Account {
        id: row.account_id,
        username: row.username,
        chosen_languages: row.chosen_languages.unwrap_or_default(),
    })
}

#[cfg(test)]
mod tests {
    use axum::http::{HeaderMap, HeaderName};

    use super::*;

    fn parts_with_header(key: &'static str, value: &str) -> Parts {
        let mut headers = HeaderMap::new();
        headers.insert(HeaderName::from_static(key), value.parse().unwrap());
        let mut parts = axum::http::Request::new(()).into_parts().0;
        parts.headers = headers;
        parts
    }

    #[test]
    fn extracts_bearer_token() {
        let parts = parts_with_header("authorization", "Bearer abc123");
        assert_eq!(extract_token(&parts).as_deref(), Some("abc123"));
    }

    #[test]
    fn rejects_missing_header() {
        let parts = axum::http::Request::new(()).into_parts().0;
        assert!(extract_token(&parts).is_none());
    }

    #[test]
    fn rejects_wrong_scheme() {
        let parts = parts_with_header("authorization", "Basic abc123");
        assert!(extract_token(&parts).is_none());
    }

    #[test]
    fn rejects_empty_token() {
        let parts = parts_with_header("authorization", "Bearer ");
        assert!(extract_token(&parts).is_none());
    }

    #[test]
    fn rejects_no_space_after_bearer() {
        let parts = parts_with_header("authorization", "Bearerabc123");
        assert!(extract_token(&parts).is_none());
    }
}

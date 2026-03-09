use axum::body::Bytes;
use axum::extract::State;
use axum::http::{HeaderMap, StatusCode};
use common::types::ProviderStatus;
use hmac::{Hmac, Mac};
use sha2::Sha256;
use sqlx::PgPool;

#[derive(serde::Deserialize)]
struct CallbackPayload {
    status: ProviderStatus,
    domain: String,
}

pub async fn handle(State(db): State<PgPool>, headers: HeaderMap, body: Bytes) -> StatusCode {
    let signature = match headers
        .get("x-commonfeed-signature")
        .and_then(|v| v.to_str().ok())
    {
        Some(sig) => sig.to_string(),
        None => return StatusCode::UNAUTHORIZED,
    };

    let payload: CallbackPayload = match serde_json::from_slice(&body) {
        Ok(p) => p,
        Err(_) => return StatusCode::BAD_REQUEST,
    };

    let Ok(Some(api_key)) = sqlx::query_scalar::<_, String>(
        "SELECT api_key FROM commonfeed_providers WHERE domain = $1 AND api_key IS NOT NULL",
    )
    .bind(&payload.domain)
    .fetch_optional(&db)
    .await
    else {
        return StatusCode::NOT_FOUND;
    };

    if !verify_signature(&api_key, &body, &signature) {
        return StatusCode::UNAUTHORIZED;
    }

    let status_str = serde_json::to_value(payload.status)
        .ok()
        .and_then(|v| v.as_str().map(String::from))
        .unwrap_or_default();

    let result = sqlx::query(
        "UPDATE commonfeed_providers SET status = $1, updated_at = now() WHERE domain = $2",
    )
    .bind(&status_str)
    .bind(&payload.domain)
    .execute(&db)
    .await;

    match result {
        Ok(_) => {
            tracing::info!(domain = %payload.domain, status = %status_str, "provider callback received");
            StatusCode::OK
        }
        Err(e) => {
            tracing::error!(error = %e, "failed to update provider status");
            StatusCode::INTERNAL_SERVER_ERROR
        }
    }
}

fn verify_signature(api_key: &str, body: &[u8], signature: &str) -> bool {
    try_verify(api_key, body, signature).unwrap_or(false)
}

fn try_verify(api_key: &str, body: &[u8], signature: &str) -> Option<bool> {
    let expected_hex = signature.strip_prefix("sha256=")?;
    let expected_bytes = hex::decode(expected_hex).ok()?;
    let mut mac = Hmac::<Sha256>::new_from_slice(api_key.as_bytes()).ok()?;
    mac.update(body);
    Some(mac.verify_slice(&expected_bytes).is_ok())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn sign(api_key: &str, body: &[u8]) -> String {
        let mut mac = Hmac::<Sha256>::new_from_slice(api_key.as_bytes()).unwrap();
        mac.update(body);
        let result = mac.finalize().into_bytes();
        format!("sha256={}", hex::encode(result))
    }

    #[test]
    fn valid_signature() {
        let key = "cf_live_abc123";
        let body = b"test body";
        let sig = sign(key, body);
        assert!(verify_signature(key, body, &sig));
    }

    #[test]
    fn wrong_key_rejected() {
        let body = b"test body";
        let sig = sign("correct_key", body);
        assert!(!verify_signature("wrong_key", body, &sig));
    }

    #[test]
    fn tampered_body_rejected() {
        let key = "cf_live_abc123";
        let sig = sign(key, b"original body");
        assert!(!verify_signature(key, b"tampered body", &sig));
    }

    #[test]
    fn missing_prefix_rejected() {
        assert!(!verify_signature("key", b"body", "abc123"));
    }

    #[test]
    fn invalid_hex_rejected() {
        assert!(!verify_signature("key", b"body", "sha256=not_valid_hex!!!"));
    }

    #[test]
    fn empty_signature_rejected() {
        assert!(!verify_signature("key", b"body", ""));
    }

    #[test]
    fn empty_body_valid() {
        let key = "cf_live_abc123";
        let body = b"";
        let sig = sign(key, body);
        assert!(verify_signature(key, body, &sig));
    }

    #[test]
    fn invalid_status_rejected() {
        let result: Result<CallbackPayload, _> =
            serde_json::from_str(r#"{"status": "hacked", "domain": "example.com"}"#);
        assert!(result.is_err());
    }

    #[test]
    fn valid_status_parses() {
        let result: CallbackPayload =
            serde_json::from_str(r#"{"status": "approved", "domain": "example.com"}"#).unwrap();
        assert_eq!(result.status, ProviderStatus::Approved);
    }
}

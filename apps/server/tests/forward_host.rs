use std::sync::Arc;
use std::time::Duration;

use axum::Router;
use axum::extract::Request;
use axum::http::{HeaderMap, HeaderValue, Method};
use axum::routing::get;
use tokio::sync::Mutex;

use server::mastodon::forward::forward;

#[tokio::test]
async fn forward_propagates_inbound_host_header_verbatim() {
    let captured = Arc::new(Mutex::new(None::<String>));
    let captured_clone = captured.clone();

    let router = Router::new().route(
        "/probe",
        get(move |req: Request| {
            let captured = captured_clone.clone();
            async move {
                let host = req
                    .headers()
                    .get("host")
                    .and_then(|v| v.to_str().ok())
                    .map(String::from);
                *captured.lock().await = host;
                "ok"
            }
        }),
    );

    let listener = tokio::net::TcpListener::bind("127.0.0.1:0").await.unwrap();
    let port = listener.local_addr().unwrap().port();
    tokio::spawn(async move {
        axum::serve(listener, router).await.unwrap();
    });

    let http = reqwest::Client::builder()
        .timeout(Duration::from_secs(5))
        .build()
        .unwrap();

    let mut inbound_headers = HeaderMap::new();
    inbound_headers.insert("host", HeaderValue::from_static("fediway.com"));
    inbound_headers.insert("authorization", HeaderValue::from_static("Bearer tok"));

    let base = format!("http://127.0.0.1:{port}");
    forward(&http, &base, Method::GET, "/probe", &inbound_headers, None)
        .await
        .expect("forward errored");

    assert_eq!(
        captured.lock().await.as_deref(),
        Some("fediway.com"),
        "upstream must receive the inbound Host header, not the URL authority"
    );
}

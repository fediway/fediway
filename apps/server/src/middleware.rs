use std::future::Future;
use std::pin::Pin;
use std::task::{Context, Poll};
use std::time::Instant;

use axum::extract::MatchedPath;
use axum::http::{Request, Response};
use tower::{Layer, Service};

/// Tower layer that records HTTP request count, duration, and status for every route.
#[derive(Clone)]
pub struct MetricsLayer;

impl<S> Layer<S> for MetricsLayer {
    type Service = MetricsService<S>;

    fn layer(&self, inner: S) -> Self::Service {
        MetricsService { inner }
    }
}

#[derive(Clone)]
pub struct MetricsService<S> {
    inner: S,
}

impl<S, ReqBody, ResBody> Service<Request<ReqBody>> for MetricsService<S>
where
    S: Service<Request<ReqBody>, Response = Response<ResBody>> + Clone + Send + 'static,
    S::Future: Send,
    ReqBody: Send + 'static,
    ResBody: Send + 'static,
{
    type Response = S::Response;
    type Error = S::Error;
    type Future = Pin<Box<dyn Future<Output = Result<Self::Response, Self::Error>> + Send>>;

    fn poll_ready(&mut self, cx: &mut Context<'_>) -> Poll<Result<(), Self::Error>> {
        self.inner.poll_ready(cx)
    }

    fn call(&mut self, req: Request<ReqBody>) -> Self::Future {
        let endpoint = req
            .extensions()
            .get::<MatchedPath>()
            .map_or_else(|| req.uri().path().to_string(), |p| p.as_str().to_string());

        let mut inner = self.inner.clone();
        let start = Instant::now();

        Box::pin(async move {
            let response = inner.call(req).await?;
            let status = response.status().as_u16().to_string();
            let elapsed = start.elapsed().as_secs_f64();

            metrics::counter!(
                "fediway_http_requests_total",
                "endpoint" => endpoint.clone(),
                "status" => status
            )
            .increment(1);

            metrics::histogram!(
                "fediway_http_request_duration_seconds",
                "endpoint" => endpoint
            )
            .record(elapsed);

            Ok(response)
        })
    }
}

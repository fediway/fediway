use std::time::Duration;

use config::TeiConfig;

pub struct TeiClient {
    client: reqwest::Client,
    url: String,
}

impl TeiClient {
    #[must_use]
    pub fn new(config: &TeiConfig) -> Self {
        let client = reqwest::Client::builder()
            .timeout(Duration::from_secs(config.tei_timeout_secs))
            .build()
            .expect("tei http client");
        Self {
            client,
            url: config.tei_url.clone(),
        }
    }

    pub async fn embed_batch(&self, texts: &[String]) -> anyhow::Result<Vec<Vec<f32>>> {
        let body = serde_json::json!({
            "inputs": texts,
            "truncate": true
        });

        let resp = self
            .client
            .post(format!("{}/embed", self.url))
            .json(&body)
            .send()
            .await?;

        if !resp.status().is_success() {
            anyhow::bail!("TEI returned {}", resp.status());
        }

        resp.json::<Vec<Vec<f32>>>().await.map_err(Into::into)
    }
}

use std::collections::{HashMap, HashSet};

use minijinja::{Environment, context};

use crate::engagement::{RawEngagement, TargetPost};
use crate::tei::TeiClient;

const TEMPLATE: &str = include_str!("../templates/embedding.j2");

pub struct EmbeddingTemplate {
    env: Environment<'static>,
}

impl EmbeddingTemplate {
    #[must_use]
    pub fn new() -> Self {
        let mut env = Environment::new();
        env.add_template("embedding", TEMPLATE)
            .expect("invalid embedding template");
        Self { env }
    }

    pub fn render(&self, target: &TargetPost) -> String {
        let tags = if target.tags.is_empty() {
            String::new()
        } else {
            target
                .tags
                .iter()
                .map(|t| format!("#{t}"))
                .collect::<Vec<_>>()
                .join(" ")
        };

        let tmpl = self
            .env
            .get_template("embedding")
            .expect("template missing");
        let result = tmpl.render(context! {
            author => context! {
                name => &target.author_name,
                handle => &target.author_handle,
            },
            post => context! {
                text => &target.text,
                content_warning => &target.spoiler_text,
                title => "",
                summary => "",
            },
            media => context! {
                alt_texts => &target.alt_texts,
            },
            tags => &tags,
        });

        match result {
            Ok(s) => s.trim().to_string(),
            Err(e) => {
                tracing::warn!(error = %e, "template render failed, falling back to text");
                target.text.clone()
            }
        }
    }
}

#[must_use]
pub fn truncate_and_normalize(full: &[f32], dims: usize) -> Vec<f32> {
    let truncated = &full[..dims.min(full.len())];
    let norm = truncated.iter().map(|x| x * x).sum::<f32>().sqrt();
    if norm < f32::EPSILON {
        return vec![0.0; dims];
    }
    truncated.iter().map(|x| x / norm).collect()
}

/// Embed engagement targets, deduplicating by rendered text.
///
/// Returns a map from rendered text to normalized embedding vector.
/// If TEI fails for a batch, those texts are skipped with a warning.
pub async fn embed_engagements(
    tei: &TeiClient,
    template: &EmbeddingTemplate,
    engagements: &[RawEngagement],
    dims: usize,
    batch_size: usize,
) -> HashMap<String, Vec<f32>> {
    let mut unique_texts: Vec<String> = Vec::new();
    let mut seen: HashSet<String> = HashSet::new();

    for e in engagements {
        let rendered = template.render(&e.target);
        if !rendered.is_empty() && seen.insert(rendered.clone()) {
            unique_texts.push(rendered);
        }
    }

    let mut results: HashMap<String, Vec<f32>> = HashMap::with_capacity(unique_texts.len());

    for chunk in unique_texts.chunks(batch_size) {
        let texts: Vec<String> = chunk.to_vec();
        let tei_start = std::time::Instant::now();
        match tei.embed_batch(&texts).await {
            Ok(embeddings) => {
                metrics::histogram!("fediway_orbit_tei_request_duration_seconds")
                    .record(tei_start.elapsed().as_secs_f64());
                #[allow(clippy::cast_precision_loss)]
                metrics::histogram!("fediway_orbit_tei_batch_size").record(chunk.len() as f64);
                for (text, embedding) in texts.into_iter().zip(embeddings) {
                    results.insert(text, truncate_and_normalize(&embedding, dims));
                }
            }
            Err(e) => {
                metrics::counter!("fediway_orbit_tei_errors_total").increment(1);
                tracing::warn!(
                    batch_size = chunk.len(),
                    error = %e,
                    "TEI batch failed, skipping"
                );
            }
        }
    }

    results
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::engagement::TargetPost;

    fn target(text: &str) -> TargetPost {
        TargetPost {
            text: text.into(),
            spoiler_text: String::new(),
            author_name: String::new(),
            author_handle: String::new(),
            alt_texts: vec![],
            tags: vec![],
        }
    }

    #[test]
    fn minimal_produces_text_only() {
        let tmpl = EmbeddingTemplate::new();
        assert_eq!(tmpl.render(&target("Hello world")), "Hello world");
    }

    #[test]
    fn full_event() {
        let tmpl = EmbeddingTemplate::new();
        let t = TargetPost {
            text: "Hello world".into(),
            spoiler_text: "politics".into(),
            author_name: "Jane Doe".into(),
            author_handle: "jane@mastodon.social".into(),
            alt_texts: vec!["A sunset".into(), "A mountain".into()],
            tags: vec!["photography".into(), "nature".into()],
        };
        let text = tmpl.render(&t);

        assert!(text.contains("Jane Doe (@jane@mastodon.social)"));
        assert!(text.contains("[CW: politics]"));
        assert!(text.contains("Hello world"));
        assert!(text.contains("[Image: A sunset]"));
        assert!(text.contains("[Image: A mountain]"));
        assert!(text.contains("#photography #nature"));
    }

    #[test]
    fn handle_only() {
        let tmpl = EmbeddingTemplate::new();
        let t = TargetPost {
            author_handle: "jane@mastodon.social".into(),
            ..target("Hello world")
        };
        let text = tmpl.render(&t);
        assert!(text.starts_with("@jane@mastodon.social"));
    }

    #[test]
    fn empty_fields_skipped() {
        let tmpl = EmbeddingTemplate::new();
        let text = tmpl.render(&target("Hello world"));
        assert_eq!(text, "Hello world");
    }

    #[test]
    fn truncate_768d_to_256d() {
        let full: Vec<f32> = (0..768).map(|i| (i as f32) * 0.01).collect();
        let result = truncate_and_normalize(&full, 256);
        assert_eq!(result.len(), 256);

        let norm: f32 = result.iter().map(|x| x * x).sum::<f32>().sqrt();
        assert!(
            (norm - 1.0).abs() < 1e-5,
            "L2 norm should be ~1.0, got {norm}"
        );
    }

    #[test]
    fn truncate_zero_vector() {
        let full = vec![0.0_f32; 768];
        let result = truncate_and_normalize(&full, 256);
        assert_eq!(result.len(), 256);
        assert!(result.iter().all(|&x| x == 0.0));
    }

    #[test]
    #[ignore = "requires feeds repo (local dev only)"]
    fn contract_embedding_template_matches_feeds() {
        let feeds_template = std::fs::read_to_string(format!(
            "{}/../../../feeds/workers/orbit/templates/embedding.j2",
            env!("CARGO_MANIFEST_DIR")
        ))
        .expect("feeds embedding.j2 must exist");

        assert_eq!(
            TEMPLATE, feeds_template,
            "embedding.j2 templates have diverged between feeds and fediway"
        );
    }

    #[test]
    #[ignore = "requires feeds repo (local dev only)"]
    fn contract_vector_config_matches_defaults() {
        let path = format!(
            "{}/../../../feeds/fixtures/orbit/vector-config.json",
            env!("CARGO_MANIFEST_DIR")
        );
        let json: serde_json::Value = serde_json::from_str(
            &std::fs::read_to_string(&path).unwrap_or_else(|e| panic!("fixture {path}: {e}")),
        )
        .unwrap();

        // Fediway defaults must match feeds' vector config fixture
        assert_eq!(json["model_name"], "bge_small_64d");
        assert_eq!(json["dims"], 64);
    }
}

use std::{
    sync::Arc,
    time::{Duration, SystemTime},
};

use tokio::sync::mpsc::UnboundedSender;

use crate::{
    config::Config,
    embedding::{Embedding, EmbeddingType, Embeddings, EngagementEvent, StatusEvent},
    workers::kafka::Event,
    workers::qdrant::QdrantTask,
};

pub struct EmbeddingWorker {
    config: Config,
    qdrant_tx: UnboundedSender<QdrantTask>,
    consumers_collection: String,
    producers_collection: String,
    statuses_collection: String,
    tags_collection: String,
}

impl EmbeddingWorker {
    pub fn new(
        config: Config,
        qdrant_tx: UnboundedSender<QdrantTask>,
        collection_prefix: String,
    ) -> Self {
        Self {
            config,
            qdrant_tx,
            consumers_collection: format!("{}_consumers", collection_prefix),
            producers_collection: format!("{}_producers", collection_prefix),
            statuses_collection: format!("{}_statuses", collection_prefix),
            tags_collection: format!("{}_tags", collection_prefix),
        }
    }

    pub async fn process_event(&self, event: Event, embeddings: &Arc<Embeddings>) {
        match event {
            Event::Status(status) => self.process_status(status, embeddings).await,
            Event::Engagement(engagement) => self.process_engagement(engagement, embeddings).await,
        };
    }

    async fn process_status(&self, status: StatusEvent, embeddings: &Arc<Embeddings>) {
        // skip when status age exceeds threshold
        if status.age_in_seconds() > self.config.max_status_age {
            return;
        }

        embeddings.push_status(status);
    }

    async fn process_engagement(&self, engagement: EngagementEvent, embeddings: &Arc<Embeddings>) {
        let account_id = engagement.account_id;
        let status_id = engagement.status_id;

        embeddings.push_engagement(engagement);

        if let Some(mut embedding) = embeddings.consumers.get_mut(&account_id) {
            self.upsert_embedding_if_needed(
                account_id,
                embedding.value_mut(),
                EmbeddingType::Consumer,
            );
        }

        if let (Some(mut embedding), Some(created_at)) = (
            embeddings.statuses.get_mut(&status_id),
            embeddings.statuses_dt.get(&status_id),
        ) {
            self.upsert_embedding_if_needed(
                status_id,
                embedding.value_mut(),
                EmbeddingType::Status {
                    created_at: created_at.clone(),
                },
            );
        }
    }

    pub fn should_upsert_embedding(
        &self,
        embedding: &Embedding,
        embedding_type: &EmbeddingType,
    ) -> bool {
        if !embedding.is_dirty || embedding.vec.is_zero() {
            return false;
        }

        if let Some(last_stored) = embedding.last_stored {
            let now = SystemTime::now();
            let update_delay = Duration::from_secs(self.config.qdrant_update_delay);

            if last_stored < now - update_delay {
                return false;
            }
        }

        if embedding.engagements < self.config.engagement_threshold(embedding_type) {
            return false;
        }

        match embedding_type {
            EmbeddingType::Status { created_at } => {
                let status_age = created_at.elapsed().unwrap().as_secs();
                if status_age > self.config.max_status_age {
                    return false;
                }
            }
            _ => {}
        }

        true
    }

    pub fn upsert_embedding_if_needed<'a>(
        &self,
        id: i64,
        embedding: &mut Embedding,
        embedding_type: EmbeddingType,
    ) {
        if self.should_upsert_embedding(&embedding, &embedding_type) {
            self.upsert_embedding(id, embedding, embedding_type);
        }
    }

    fn get_collection_for_type(&self, embedding_type: &EmbeddingType) -> String {
        match embedding_type {
            EmbeddingType::Consumer => self.consumers_collection.clone(),
            EmbeddingType::Producer => self.producers_collection.clone(),
            EmbeddingType::Status { .. } => self.statuses_collection.clone(),
            EmbeddingType::Tag => self.tags_collection.clone(),
        }
        .clone()
    }

    pub fn upsert_embedding<'a>(
        &self,
        id: i64,
        embedding: &mut Embedding,
        embedding_type: EmbeddingType,
    ) {
        embedding.is_dirty = false;
        embedding
            .vec
            .keep_top_n(self.config.max_communities(&embedding_type));
        embedding.last_stored = Some(SystemTime::now());

        self.qdrant_tx
            .send(QdrantTask::Upsert {
                id: id as u64,
                collection: self.get_collection_for_type(&embedding_type),
                embedding: embedding.vec.to_owned(),
                metadata: serde_json::Value::default(),
            })
            .unwrap();
    }
}

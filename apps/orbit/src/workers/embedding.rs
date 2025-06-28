use std::{
    sync::Arc,
    time::{Duration, SystemTime},
};

use tokio::{
    sync::{
        Mutex,
        mpsc::{UnboundedReceiver, UnboundedSender},
    },
    task::JoinHandle,
};

use crate::{
    config::Config,
    embedding::{Embedding, EmbeddingType, Embeddings, EngagementEvent, StatusEvent},
    workers::kafka::Event,
    workers::qdrant::QdrantTask,
};

pub struct EmbeddingWorker {
    config: Config,
    worker_id: usize,
    qdrant_tx: UnboundedSender<QdrantTask>,
    consumers_collection: String,
    producers_collection: String,
    statuses_collection: String,
    tags_collection: String,
}

impl EmbeddingWorker {
    pub fn new(
        worker_id: usize,
        config: Config,
        qdrant_tx: UnboundedSender<QdrantTask>,
        collection_prefix: String,
    ) -> Self {
        Self {
            config,
            qdrant_tx,
            worker_id,
            consumers_collection: format!("{}_consumers", collection_prefix),
            producers_collection: format!("{}_producers", collection_prefix),
            statuses_collection: format!("{}_statuses", collection_prefix),
            tags_collection: format!("{}_tags", collection_prefix),
        }
    }

    pub fn start(
        self,
        event_rx: Arc<Mutex<UnboundedReceiver<Event>>>,
        embeddings: Arc<Embeddings>,
    ) -> JoinHandle<()> {
        tracing::info!("Starting embedding worker {}", self.worker_id);

        tokio::spawn(async move {
            if let Err(e) = self.run_event_consumer(event_rx, embeddings).await {
                tracing::error!("Embedding worker {} failed: {}", self.worker_id, e);
            }
        })
    }

    async fn run_event_consumer(
        &self,
        event_rx: Arc<Mutex<UnboundedReceiver<Event>>>,
        embeddings: Arc<Embeddings>,
    ) -> Result<(), Box<dyn std::error::Error>> {
        loop {
            let mut rx = event_rx.lock().await;

            match rx.recv().await {
                Some(event) => {
                    self.process_event(event, &embeddings).await;
                }
                None => {
                    tracing::info!("Shutting down embedding worker {}", self.worker_id);
                    break;
                }
            }
        }

        Ok(())
    }

    async fn process_event(&self, event: Event, embeddings: &Arc<Embeddings>) {
        match event {
            Event::Status(status) => self.process_status(status, embeddings).await,
            Event::Engagement(engagement) => self.process_engagement(engagement, embeddings).await,
        };
    }

    async fn process_status(&self, status: StatusEvent, embeddings: &Arc<Embeddings>) {
        tracing::info!(
            "Processing status {} in worker {}",
            status.status_id,
            self.worker_id
        );

        // skip when status age exceeds threshold
        if status.age_in_seconds() > self.config.max_status_age {
            tracing::info!(
                "Skipping status {}: age {} exceeds limit {}",
                status.status_id,
                status.age_in_seconds(),
                self.config.max_status_age,
            );
            return;
        }

        embeddings.push_status(status);
    }

    async fn process_engagement(&self, engagement: EngagementEvent, embeddings: &Arc<Embeddings>) {
        tracing::info!(
            "Processing engagement {} -> {} in worker {}",
            engagement.account_id,
            engagement.status_id,
            self.worker_id
        );

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
                    created_at: *created_at,
                },
            );
        }
    }

    pub fn should_upsert_embedding(
        &self,
        embedding: &Embedding,
        embedding_type: &EmbeddingType,
    ) -> bool {
        // skip updating embeddings that:
        // - have not been changed since last udpate
        // - are zero
        if !embedding.is_dirty || embedding.vec.is_zero() {
            tracing::info!("Skip upserting {:?}: engaments empty", embedding_type,);
            return false;
        }

        // skip updating embeddings that have been updated recently
        if let Some(last_stored) = embedding.last_stored {
            let now = SystemTime::now();
            let update_delay = Duration::from_secs(self.config.qdrant_update_delay);

            if last_stored < now - update_delay {
                tracing::info!(
                    "Skip upserting {:?}: last stored {:?}",
                    embedding_type,
                    last_stored.elapsed()
                );

                return false;
            }
        }

        // skip updating embeddings of entities that have to few engagments
        if embedding.engagements < self.config.engagement_threshold(embedding_type) {
            tracing::info!(
                "Skip upserting {:?}: engaments {} below threshold {}",
                embedding_type,
                embedding.engagements,
                self.config.engagement_threshold(embedding_type)
            );
            return false;
        }

        // skip updating embeddings of statuses that are to old
        if let EmbeddingType::Status { created_at } = embedding_type {
            let status_age = created_at.elapsed().unwrap().as_secs();
            if status_age > self.config.max_status_age {
                tracing::info!("Skip upserting {:?}: status to old", embedding_type,);

                return false;
            }
        }

        true
    }

    pub fn upsert_embedding_if_needed(
        &self,
        id: i64,
        embedding: &mut Embedding,
        embedding_type: EmbeddingType,
    ) {
        if self.should_upsert_embedding(embedding, &embedding_type) {
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

    pub fn upsert_embedding(
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

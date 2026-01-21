use std::{sync::Arc, time::SystemTime};

use tokio::{
    sync::{
        Mutex,
        mpsc::{UnboundedReceiver, UnboundedSender},
    },
    task::JoinHandle,
};

use crate::{
    config::Config,
    debezium::DebeziumEvent,
    embedding::{Embedded, Embeddings, EngagementEvent, StatusEvent},
    entities::{Entity, EntityType, Upsertable},
    workers::{kafka::Event, qdrant::QdrantTask},
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

    async fn process_status(
        &self,
        event: DebeziumEvent<StatusEvent>,
        embeddings: &Arc<Embeddings>,
    ) {
        if let Some(payload) = &event.payload {
            if let Some(status) = &payload.after {
                // skip when status is not trendable
                if status.visibility != 0 {
                    tracing::info!(
                        "Skipping status {}: visibility not public",
                        status.status_id,
                    );
                    return;
                }

                // skip when status is sensible
                if status.sensitive.unwrap_or(false) {
                    tracing::info!("Skipping status {}: sensitive", status.status_id,);
                    return;
                }

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

                tracing::info!(
                    "Processing status {} in worker {}",
                    status.status_id,
                    self.worker_id
                );
            }
        }

        embeddings.push_status(event);
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

        if let Some(mut consumer) = embeddings.consumers.get_mut(&account_id) {
            self.upsert_embedding_if_needed(
                account_id,
                consumer.value_mut(),
                &EntityType::Consumer,
            );
        }

        if let Some(mut status) = embeddings.statuses.get_mut(&status_id) {
            self.upsert_embedding_if_needed(status_id, status.value_mut(), &EntityType::Status);
        }
    }

    pub fn upsert_embedding_if_needed<E: Upsertable>(
        &self,
        id: i64,
        entity: &mut E,
        entity_type: &EntityType,
    ) {
        if entity.should_upsert(&self.config) {
            self.upsert_embedding(id, entity, entity_type);
        } else {
        }
    }

    fn get_collection_for_type(&self, entity_type: &EntityType) -> String {
        match entity_type {
            EntityType::Consumer => self.consumers_collection.clone(),
            EntityType::Producer => self.producers_collection.clone(),
            EntityType::Status => self.statuses_collection.clone(),
            EntityType::Tag => self.tags_collection.clone(),
        }
    }

    pub fn upsert_embedding<E: Entity + Embedded>(
        &self,
        id: i64,
        entity: &mut E,
        entity_type: &EntityType,
    ) {
        *entity.is_dirty_mut() = false;
        *entity.last_upserted_mut() = Some(SystemTime::now());

        let mut embedding = entity.embedding().to_owned();

        match entity_type {
            EntityType::Consumer => {
                embedding.keep_top_n(self.config.consumer_sparsity);
                embedding.normalize();
            }
            EntityType::Producer => {
                embedding.keep_top_n(self.config.producer_sparsity);
            }
            EntityType::Status => {
                embedding.keep_top_n(self.config.status_sparsity);
            }
            EntityType::Tag => {
                embedding.keep_top_n(self.config.tag_sparsity);
            }
        }

        self.qdrant_tx
            .send(QdrantTask::Upsert {
                id: id as u64,
                collection: self.get_collection_for_type(entity_type),
                embedding,
                metadata: serde_json::Value::default(),
            })
            .unwrap();
    }
}

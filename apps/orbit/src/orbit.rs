use crate::config::Config;
use crate::embedding::{EmbeddingType, Embeddings};
use crate::workers::embedding::EmbeddingWorker;
use crate::workers::kafka::{Event, KafkaWorker};
use crate::workers::qdrant::{QdrantTask, QdrantWorker};
use crate::workers::status_purge::StatusPurgeWorker;

use qdrant_client::qdrant::{
    CreateCollectionBuilder, SparseVectorParamsBuilder, SparseVectorsConfigBuilder,
};
use qdrant_client::{Qdrant, QdrantError};
use redis::{Commands, RedisError};

use std::sync::Arc;
use tokio::sync::{mpsc, mpsc::UnboundedSender};
use tokio::task::JoinHandle;

pub struct Orbit {
    embeddings: Arc<Embeddings>,
    collection_prefix: String,
    config: Config,
}

impl Orbit {
    pub fn new(config: Config, embeddings: Embeddings) -> Self {
        let collection_prefix = config.qdrant_collection_name(&embeddings.communities);

        Self {
            embeddings: Arc::new(embeddings),
            collection_prefix,
            config,
        }
    }

    pub async fn start(&self) {
        self.create_qdrant_collections().await.unwrap();

        let (event_tx, event_rx) = mpsc::unbounded_channel::<Event>();
        let (qdrant_tx, qdrant_rx) = mpsc::unbounded_channel::<QdrantTask>();
        let shared_event_rx = Arc::new(tokio::sync::Mutex::new(event_rx));

        // start qdrant worker
        let qdrant_worker = QdrantWorker::new(self.config.clone())
            .await
            .start(qdrant_rx);

        // store initial embeddings
        self.store_initial_embeddings(qdrant_tx.clone()).await;

        // publish embedding version
        if let Err(e) = self.publish() {
            tracing::error!("Failed to publish embedding version to redis: {}", e);
            return;
        }

        // start embedding workers
        let embedding_workers: Vec<JoinHandle<()>> = (0..self.config.workers)
            .map(|worker_id| {
                EmbeddingWorker::new(
                    worker_id,
                    self.config.clone(),
                    qdrant_tx.clone(),
                    self.collection_prefix.clone(),
                )
                .start(shared_event_rx.clone(), self.embeddings.clone())
            })
            .collect();

        // start status purge worker
        let status_purge_worker = StatusPurgeWorker::new(
            self.config.clone(),
            format!("{}_statuses", self.collection_prefix),
        )
        .start(qdrant_tx, self.embeddings.clone())
        .await;

        // start kafka event consumer
        let kafka_worker = KafkaWorker::new(self.config.clone()).start(event_tx);

        // delete old collections
        self.purge_outdated_qdrant_collections().await;

        qdrant_worker.await.unwrap();
        for worker in embedding_workers {
            worker.await.unwrap();
        }
        status_purge_worker.await.unwrap();
        kafka_worker.await.unwrap();
    }

    fn publish(&self) -> Result<(), RedisError> {
        let mut redis = redis::Client::open(self.config.redis_conn())?;
        let version = self.embeddings.communities.version();
        let _: () = redis.set("orbit:version", version.clone())?;

        tracing::info!(
            "Published communities version {} to redis key 'orbit:version'",
            version
        );

        Ok(())
    }

    async fn store_initial_embeddings(&self, qdrant_tx: UnboundedSender<QdrantTask>) {
        let collection_prefix = self
            .config
            .qdrant_collection_name(&self.embeddings.communities);

        let worker = EmbeddingWorker::new(
            0,
            self.config.clone(),
            qdrant_tx.clone(),
            collection_prefix.clone(),
        );

        for mut row in self.embeddings.consumers.iter_mut() {
            worker.upsert_embedding(*row.key(), row.value_mut(), EmbeddingType::Consumer);
        }

        for mut row in self.embeddings.producers.iter_mut() {
            worker.upsert_embedding(*row.key(), row.value_mut(), EmbeddingType::Producer);
        }

        for mut row in self.embeddings.statuses.iter_mut() {
            let status_id = *row.key();
            if let Some(created_at) = self.embeddings.statuses_dt.get(&status_id) {
                let embedding_type = EmbeddingType::Status {
                    created_at: *created_at,
                };
                worker.upsert_embedding_if_needed(status_id, row.value_mut(), embedding_type);
            }
        }

        for mut row in self.embeddings.tags.iter_mut() {
            worker.upsert_embedding_if_needed(*row.key(), row.value_mut(), EmbeddingType::Tag);
        }
    }

    async fn create_qdrant_collections(&self) -> Result<(), QdrantError> {
        let client = Qdrant::new(self.config.qdrant_config()).unwrap();

        for entity in ["consumers", "statuses", "producers", "tags"] {
            let collection_name = format!("{}_{}", self.collection_prefix, entity);

            tracing::info!("Creating qdrant collection '{}'", collection_name);

            let mut sparse_vector_config = SparseVectorsConfigBuilder::default();

            sparse_vector_config
                .add_named_vector_params("embedding", SparseVectorParamsBuilder::default());

            let collection = CreateCollectionBuilder::new(collection_name)
                .sparse_vectors_config(sparse_vector_config);

            let response = client.create_collection(collection).await;

            match response {
                Ok(_) => tracing::info!("Collection created successfully."),
                Err(e) => {
                    tracing::error!("Failed to create collection: {:?}", e);
                    return Err(e);
                }
            }
        }

        Ok(())
    }

    async fn purge_outdated_qdrant_collections(&self) {
        let client = Qdrant::new(self.config.qdrant_config()).unwrap();

        let response = client.list_collections().await.unwrap();

        for collection in response.collections {
            if collection.name.starts_with(&self.collection_prefix) {
                continue;
            }

            // only delete collections that start with the configured prefix
            if collection
                .name
                .starts_with(&self.config.qdrant_collection_prefix)
            {
                client
                    .delete_collection(collection.name.clone())
                    .await
                    .unwrap();
                tracing::info!("Deleted outdated collection: {}", collection.name);
            }
        }
    }
}

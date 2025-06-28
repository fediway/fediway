use crate::config::Config;
use crate::embedding::{self, EmbeddingType, Embeddings};
use crate::workers::embedding::EmbeddingWorker;
use crate::workers::kafka::Event;
use crate::workers::qdrant::{QdrantTask, QdrantWorker};
use crate::workers::status_purge::StatusPurgeWorker;

use qdrant_client::qdrant::{
    CreateCollectionBuilder, SparseVectorParamsBuilder, SparseVectorsConfigBuilder,
};
use qdrant_client::{Qdrant, QdrantError};

use std::sync::Arc;
use tokio::sync::{mpsc, mpsc::UnboundedReceiver, mpsc::UnboundedSender};
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

        // start qdrant worker
        let qdrant_handle = self.start_qdrant_worker(qdrant_rx).await;

        // store initial embeddings
        self.store_initial_embeddings(qdrant_tx.clone()).await;

        // delete old collections
        self.purge_outdated_qdrant_collections().await;

        // start embedding workers
        let embedding_handles = self
            .start_embedding_workers(event_rx, qdrant_tx.clone(), self.config.workers)
            .await;

        // start status purge worker
        let status_purge_handle = self.start_status_purge_worker(qdrant_tx.clone()).await;

        //

        // let kafka_handle = self.start_kafka_worker(event_tx.clone()).await;

        qdrant_handle.await.unwrap();
        for handle in embedding_handles {
            handle.await.unwrap();
        }
        status_purge_handle.await.unwrap();
    }

    async fn start_status_purge_worker(
        &self,
        qdrant_tx: UnboundedSender<QdrantTask>,
    ) -> JoinHandle<()> {
        StatusPurgeWorker::new(
            self.config.clone(),
            format!("{}_statuses", self.collection_prefix),
        )
        .start(qdrant_tx, self.embeddings.clone())
        .await
    }

    async fn start_embedding_workers(
        &self,
        event_rx: UnboundedReceiver<Event>,
        qdrant_tx: UnboundedSender<QdrantTask>,
        num_threads: usize,
    ) -> Vec<JoinHandle<()>> {
        let mut handles = Vec::new();
        let event_rx = Arc::new(tokio::sync::Mutex::new(event_rx));

        for worker_id in 0..num_threads {
            let worker_event_rx = Arc::clone(&event_rx);
            let embeddings = self.embeddings.clone();
            let worker = EmbeddingWorker::new(
                self.config.clone(),
                qdrant_tx.clone(),
                self.collection_prefix.clone(),
            );

            let handle = tokio::spawn(async move {
                loop {
                    let mut rx = worker_event_rx.lock().await;

                    match rx.recv().await {
                        Some(event) => {
                            worker.process_event(event, &embeddings).await;
                        }
                        None => {
                            tracing::info!("Embedding worker {} shutting down", worker_id);
                            break;
                        }
                    }
                }
            });

            handles.push(handle);
        }

        handles
    }

    async fn start_kafka_worker(&self, event_tx: UnboundedSender<Event>) {
        //
    }

    async fn store_initial_embeddings(&self, qdrant_tx: UnboundedSender<QdrantTask>) {
        let collection_prefix = self
            .config
            .qdrant_collection_name(&self.embeddings.communities);

        let worker = EmbeddingWorker::new(
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
                    created_at: created_at.clone(),
                };
                worker.upsert_embedding_if_needed(status_id, row.value_mut(), embedding_type);
            }
        }

        for mut row in self.embeddings.tags.iter_mut() {
            worker.upsert_embedding_if_needed(*row.key(), row.value_mut(), EmbeddingType::Tag);
        }
    }

    async fn start_qdrant_worker(
        &self,
        qdrant_rx: UnboundedReceiver<QdrantTask>,
    ) -> JoinHandle<()> {
        let config = self.config.clone();

        tokio::spawn(async move {
            let worker = QdrantWorker::new(config).await;

            worker.start_batch_processor(qdrant_rx).await;
        })
    }

    async fn create_qdrant_collections(&self) -> Result<(), QdrantError> {
        let client = Qdrant::new(self.config.qdrant_config()).unwrap();

        for entity in vec!["consumers", "statuses", "producers", "tags"] {
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

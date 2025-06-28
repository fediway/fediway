use crate::config::Config;
use crate::sparse::SparseVec;
use crate::types::FastHashMap;

use tokio::sync::mpsc::UnboundedReceiver;

use qdrant_client::qdrant::{
    DeletePointsBuilder, NamedVectors, PointId, PointStruct, PointsIdsList, UpsertPointsBuilder,
    Vector,
};
use qdrant_client::{Payload, Qdrant, QdrantError};
use tokio::task::JoinHandle;
use tokio::time::{Duration, Instant, sleep};

const MAX_WAIT_TIME: Duration = Duration::from_secs(1);

pub struct QdrantWorker {
    config: Config,
    client: Qdrant,
}

impl QdrantWorker {
    pub async fn new(config: Config) -> Self {
        let client = Qdrant::from_url(&config.qdrant_url()).build().unwrap();

        Self { config, client }
    }

    pub fn start(self, rx: UnboundedReceiver<QdrantTask>) -> JoinHandle<()> {
        tracing::info!("Starting qdrant worker");

        tokio::spawn(async move {
            if let Err(e) = self.run_batch_processor(rx).await {
                tracing::error!("Qdrant worker failed: {}", e);
            }
        })
    }

    async fn run_batch_processor(
        &self,
        mut rx: UnboundedReceiver<QdrantTask>,
    ) -> Result<(), Box<dyn std::error::Error>> {
        let mut buffer: Vec<QdrantTask> = Vec::with_capacity(self.config.qdrant_max_batch_size);
        let deadline = sleep(MAX_WAIT_TIME);
        let client = &self.client;
        tokio::pin!(deadline);

        loop {
            tokio::select! {
                msg = rx.recv() => {
                    match msg {
                        Some(task) => {
                            buffer.push(task);

                            // flush immediately if batch is full
                            if buffer.len() >= self.config.qdrant_max_batch_size {
                                Self::update_batch(std::mem::take(&mut buffer), client).await;
                                deadline.as_mut().reset(Instant::now() + MAX_WAIT_TIME);
                            }
                        },
                        _ => {
                            tracing::info!("Shutting down qdrant worker.");

                            if !buffer.is_empty() {
                                Self::update_batch(std::mem::take(&mut buffer), client).await;
                            }

                            break;
                        }
                    }
                },
                _ = &mut deadline => {
                    if !buffer.is_empty() {
                        Self::update_batch(std::mem::take(&mut buffer), client).await;
                    }

                    // Reset timer
                    deadline.as_mut().reset(Instant::now() + MAX_WAIT_TIME);
                }
            }
        }

        Ok(())
    }

    async fn update_batch(tasks: Vec<QdrantTask>, client: &Qdrant) {
        let mut upsert_batches: FastHashMap<String, Vec<PointStruct>> = FastHashMap::default();
        let mut delete_batches: FastHashMap<String, Vec<PointId>> = FastHashMap::default();

        for task in tasks {
            let point: Option<PointStruct> = task.clone().into();

            match task {
                QdrantTask::Delete { collection, id } => {
                    delete_batches
                        .entry(collection.clone())
                        .or_default()
                        .push(id.into());
                }
                QdrantTask::Upsert { collection, .. } => {
                    upsert_batches
                        .entry(collection.clone())
                        .or_default()
                        .push(point.unwrap());
                }
            }
        }

        for (collection, points) in upsert_batches {
            if let Err(e) = Self::upsert_batch(client, &collection, points).await {
                tracing::error!("Failed to delete from {}: {}", collection, e);
            }
        }

        for (collection, ids) in delete_batches {
            if let Err(e) = Self::delete_batch(client, &collection, ids).await {
                tracing::error!("Failed to delete from {}: {}", collection, e);
            }
        }
    }

    async fn upsert_batch(
        client: &Qdrant,
        collection: &String,
        points: Vec<PointStruct>,
    ) -> Result<(), QdrantError> {
        let num_points = points.len();

        let response = client
            .upsert_points(UpsertPointsBuilder::new(collection.clone(), points))
            .await?;

        tracing::info!(
            "Upserted {} embeddings in {} in {:.3} milliseconds",
            num_points,
            collection,
            response.time * 1000.0
        );

        Ok(())
    }

    async fn delete_batch(
        client: &Qdrant,
        collection: &String,
        ids: Vec<PointId>,
    ) -> Result<(), QdrantError> {
        let num_ids = ids.len();

        let response = client
            .delete_points(
                DeletePointsBuilder::new(collection.clone())
                    .points(PointsIdsList { ids })
                    .wait(true),
            )
            .await?;

        tracing::info!(
            "Deleted {} embeddings from {} in {:.3} milliseconds",
            num_ids,
            collection,
            response.time * 1000.0
        );

        Ok(())
    }
}

#[derive(Clone)]
pub enum QdrantTask {
    Upsert {
        id: u64,
        collection: String,
        embedding: SparseVec,
        metadata: serde_json::Value,
    },
    Delete {
        id: u64,
        collection: String,
    },
}

#[allow(clippy::from_over_into)]
impl Into<Option<PointStruct>> for QdrantTask {
    fn into(self) -> Option<PointStruct> {
        match self {
            Self::Delete { .. } => None,
            Self::Upsert {
                id,
                embedding,
                metadata,
                ..
            } => {
                let indices: Vec<u32> = embedding.0.indices().iter().map(|i| *i as u32).collect();
                let data: Vec<f32> = embedding.0.data().iter().map(|v| *v as f32).collect();

                // TODO: add payload
                Some(PointStruct::new(
                    id,
                    NamedVectors::default()
                        .add_vector("embedding", Vector::new_sparse(indices, data)),
                    Payload::new(),
                ))
            }
        }
    }
}

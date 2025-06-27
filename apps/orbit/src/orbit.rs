use crate::config::Config;
use crate::embedding::Embeddings;
use crate::kafka::{EngagementEvent, Event, StatusEvent};
use crate::qdrant::QdrantTask;

use std::sync::Arc;
use tokio::sync::{Mutex, RwLock, mpsc, mpsc::UnboundedReceiver, mpsc::UnboundedSender};

pub struct Orbit {
    embeddings: Arc<Embeddings>,
    config: Config,
}

impl Orbit {
    pub fn new(config: Config, embeddings: Embeddings) -> Self {
        Self {
            embeddings: Arc::new(embeddings),
            config,
        }
    }

    pub async fn start(&self) {
        let (event_tx, event_rx) = mpsc::unbounded_channel::<Event>();
        let (qdrant_tx, qdrant_rx) = mpsc::unbounded_channel::<QdrantTask>();

        // Start
        let embedding_handles = self
            .start_embedding_workers(event_rx, qdrant_tx.clone(), self.config.workers)
            .await;
        let kafka_handle = self.start_kafka_worker(event_tx.clone()).await;
        let qdrant_handle = self.start_qdrant_worker(qdrant_rx).await;
    }

    async fn start_embedding_workers(
        &self,
        event_rx: UnboundedReceiver<Event>,
        qdrant_tx: UnboundedSender<QdrantTask>,
        num_threads: usize,
    ) {
        let event_rx = Arc::new(tokio::sync::Mutex::new(event_rx));

        let mut handles = Vec::new();

        for worker_id in 0..num_threads {
            let worker_event_rx = Arc::clone(&event_rx);
            let worker_qdrant_tx = qdrant_tx.clone();
            let worker_config = self.config.clone();
            let worker_embeddings = self.embeddings.clone();

            let handle = tokio::spawn(async move {
                loop {
                    let mut rx = worker_event_rx.lock().await;

                    match rx.recv().await {
                        Some(event) => {
                            Self::process_event(
                                event,
                                &worker_embeddings,
                                &worker_qdrant_tx,
                                &worker_config,
                            )
                            .await
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
    }

    async fn start_kafka_worker(&self, event_tx: UnboundedSender<Event>) {}

    async fn start_qdrant_worker(&self, qdrant_rx: UnboundedReceiver<QdrantTask>) {}

    async fn process_event(
        event: Event,
        embeddings: &Arc<Embeddings>,
        qdrant_tx: &UnboundedSender<QdrantTask>,
        config: &Config,
    ) {
        match event {
            Event::Status(status) => Self::process_status(status, embeddings, config).await,
            Event::Engagement(engagement) => {
                Self::process_engagement(engagement, embeddings, qdrant_tx, config).await
            }
        };
    }

    async fn process_status(status: StatusEvent, embeddings: &Arc<Embeddings>, config: &Config) {
        //
        embeddings.push_status(status);
    }

    async fn process_engagement(
        engagement: EngagementEvent,
        embeddings: &Arc<Embeddings>,
        qdrant_tx: &UnboundedSender<QdrantTask>,
        config: &Config,
    ) {
        embeddings.push_engagement(engagement);
    }
}

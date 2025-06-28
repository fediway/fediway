use std::sync::Arc;

use tokio::sync::mpsc::UnboundedSender;
use tokio::task::JoinHandle;
use tokio::time::{Duration, interval};

use crate::workers::qdrant::QdrantTask;
use crate::{config::Config, embedding::Embeddings};

pub struct StatusPurgeWorker {
    config: Config,
    collection: String,
}

impl StatusPurgeWorker {
    pub fn new(config: Config, collection: String) -> Self {
        Self { config, collection }
    }

    pub async fn start(
        self,
        qdrant_tx: UnboundedSender<QdrantTask>,
        embeddings: Arc<Embeddings>,
    ) -> JoinHandle<()> {
        let mut interval = interval(Duration::from_secs(300));

        tokio::spawn(async move {
            loop {
                interval.tick().await;

                self.purge_old_statuses(&qdrant_tx, &embeddings);
            }
        })
    }

    fn purge_old_statuses(
        &self,
        qdrant_tx: &UnboundedSender<QdrantTask>,
        embeddings: &Arc<Embeddings>,
    ) {
        let statuses_to_delete: Vec<i64> = embeddings
            .statuses_dt
            .iter()
            .filter(|row| row.elapsed().unwrap().as_secs() > self.config.max_status_age)
            .map(|row| *row.key())
            .collect();

        for status_id in statuses_to_delete {
            embeddings.statuses.remove(&status_id);
            embeddings.statuses_dt.remove(&status_id);
            embeddings.statuses_tags.remove(&status_id);

            qdrant_tx
                .send(QdrantTask::Delete {
                    id: status_id as u64,
                    collection: self.collection.clone(),
                })
                .unwrap();
        }
    }
}

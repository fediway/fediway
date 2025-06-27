use crate::communities::Communities;
use crate::config::Config;
use crate::kafka::{EngagementEvent, StatusEvent};
use crate::sparse::{SparseVec, cosine_similarity};
use crate::types::FastDashMap;

const ALPHA: f64 = 0.01;
const BETA: f64 = 0.1;
const DECAY: f64 = 0.005;

pub struct Embedding {
    pub vec: SparseVec,
    pub confidence: f64,
    pub updates: usize,
}

impl Embedding {
    pub fn empty(dim: usize) -> Self {
        Self {
            vec: SparseVec::empty(dim),
            confidence: 0.0,
            updates: 0,
        }
    }

    pub fn new(vec: SparseVec, confidence: f64) -> Self {
        Self {
            vec,
            confidence,
            updates: 0,
        }
    }

    pub fn update(&mut self, embedding: &Embedding) {
        let beta = (ALPHA * embedding.confidence)
            .max(1.0 / ((self.updates as f64) + 1.0))
            .max(DECAY);
        self.vec *= 1.0 - DECAY;
        self.vec += &(embedding.vec.to_owned() * beta);
        self.vec.l1_normalize();
        self.updates += 1;
        self.confidence += (1.0 - self.confidence) * BETA * embedding.confidence;

        // self.vec.keep_top_n(25);
    }

    pub fn is_zero(&self) -> bool {
        self.vec.is_zero()
    }
}

pub struct Embeddings {
    config: Config,
    communities: Communities,
    consumers: FastDashMap<i64, Embedding>,
    producers: FastDashMap<i64, Embedding>,
    tags: FastDashMap<i64, Embedding>,
    statuses: FastDashMap<i64, Embedding>,
    statuses_tags: FastDashMap<i64, Vec<i64>>,
    dim: usize,
}

impl Embeddings {
    pub fn initial(
        config: Config,
        communities: Communities,
        consumers: FastDashMap<i64, Embedding>,
        producers: FastDashMap<i64, Embedding>,
        tags: FastDashMap<i64, Embedding>,
    ) -> Self {
        Self {
            dim: communities.0.values().max().unwrap() + 1,
            config,
            communities: communities,
            consumers: consumers,
            producers: producers,
            tags: tags,
            statuses: FastDashMap::default(),
            statuses_tags: FastDashMap::default(),
        }
    }

    fn get_weighted_statuses_tags_embedding(&self, status_id: &i64) -> Option<Embedding> {
        if let Some(tags) = self.statuses_tags.get(status_id) {
            self.get_weighted_tags_embedding(tags.value())
        } else {
            None
        }
    }

    fn get_statuses_tags(&self, status_id: &i64) -> Vec<i64> {
        if let Some(tags) = self.statuses_tags.get(status_id) {
            tags.clone()
        } else {
            Vec::new()
        }
    }

    fn get_weighted_tags_embedding(&self, tags: &[i64]) -> Option<Embedding> {
        let tag_embeddings: Vec<(SparseVec, f64)> = tags
            .iter()
            .filter_map(|t| match self.tags.get(t) {
                Some(e) => Some((e.vec.clone(), e.confidence)),
                _ => None,
            })
            .collect();

        if tag_embeddings.is_empty() {
            return None;
        }

        let mut vec: SparseVec = SparseVec::empty(self.dim);

        let confidence_scores: Vec<f64> = tag_embeddings.iter().map(|(_, confidence)| *confidence).collect();
        let total_confidence: f64 = confidence_scores.iter().sum();
        let avg_confidence: f64 = total_confidence / (confidence_scores.len() as f64);

        for (c, (e, _)) in confidence_scores
            .into_iter()
            .zip(tag_embeddings.into_iter())
        {
            vec += &(e * (c / total_confidence));
        }

        Some(Embedding::new(vec, avg_confidence))
    }

    pub async fn push_status(&self, status: StatusEvent) {
        let mut status_embedding = Embedding::empty(self.dim);
        let tags: Vec<i64> = status.tags.iter().cloned().collect();

        if let Some(p_embedding) = self.producers.get(&status.account_id) {
            status_embedding.update(p_embedding.value());
        }

        if let Some(t_embedding) = self.get_weighted_tags_embedding(&tags) {
            status_embedding.update(&t_embedding);
        }

        self.statuses.insert(status.status_id, status_embedding);

        if !status.tags.is_empty() {
            self.statuses_tags.insert(status.status_id, tags);
        }
    }

    pub async fn push_engagement(&self, engagement: EngagementEvent) {
        let account_id = engagement.account_id;
        let status_id = engagement.status_id;
        let author_id = engagement.author_id;

        {
            let a_embedding = self
                .consumers
                .entry(account_id)
                .or_insert_with(|| Embedding::empty(self.dim));

            if a_embedding.is_zero() {
                return;
            }
        }

        // update status embedding
        if let (Some(a_embedding), Some(mut s_embedding)) = (
            self.consumers.get(&account_id),
            self.statuses.get_mut(&status_id),
        ) {
            s_embedding.update(a_embedding.value());
        }

        // update consumer embedding
        if let (Some(mut a_embedding), Some(s_embedding)) = (
            self.consumers.get_mut(&account_id),
            self.statuses.get(&status_id),
        ) {
            a_embedding.update(s_embedding.value());

            // Add tag embedding if available
            if let Some(t_embedding) =
                self.get_weighted_statuses_tags_embedding(&engagement.status_id)
            {
                a_embedding.update(&t_embedding);
            }
        }

        // update producer embedding
        if let (Some(a_embedding), Some(mut p_embedding)) = (
            self.consumers.get(&account_id),
            self.producers.get_mut(&author_id),
        ) {
            p_embedding.update(a_embedding.value());
            println!("update producer");
        }

        // update tag embeddings
        if let (Some(tags), Some(a_embedding)) = (
            self.statuses_tags.get(&engagement.status_id),
            self.consumers.get(&account_id),
        ) {
            for tag in tags.value() {
                if let Some(mut t_embedding) = self.tags.get_mut(tag) {
                    // 4. update tag embedding
                    t_embedding.update(a_embedding.value());
                }
            }
        }
    }
}

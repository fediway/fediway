use crate::communities::Communities;
use crate::config::Config;
use crate::sparse::SparseVec;
use crate::types::{FastDashMap, FastHashSet};
use std::time::SystemTime;

const ALPHA: f64 = 0.01;
const BETA: f64 = 0.1;
const DECAY: f64 = 0.005;

pub enum EmbeddingType {
    Consumer,
    Producer,
    Status { created_at: SystemTime },
    Tag,
}

pub struct Embedding {
    pub vec: SparseVec,
    pub confidence: f64,
    pub updates: usize,
    pub engagements: usize,
    pub is_dirty: bool,
    pub last_stored: Option<SystemTime>,
}

impl Embedding {
    pub fn empty(dim: usize) -> Self {
        Self {
            vec: SparseVec::empty(dim),
            confidence: 0.0,
            updates: 0,
            engagements: 0,
            is_dirty: false,
            last_stored: None,
        }
    }

    pub fn new(vec: SparseVec, confidence: f64) -> Self {
        Self {
            vec,
            confidence,
            updates: 0,
            engagements: 0,
            is_dirty: false,
            last_stored: None,
        }
    }

    pub fn update(&mut self, embedding: &Embedding) {
        let beta = (ALPHA * embedding.confidence)
            .max(1.0 / ((self.updates as f64) + 1.0))
            .max(DECAY);
        let decay = DECAY.min(beta);
        // let decay = 0.2;

        // self.vec *= 0.9;
        // self.vec += &SparseVec::new(
        //     embedding.vec.0.dim(),
        //     embedding.vec.0.indices().iter().cloned().collect(),
        //     embedding.vec.0.data().iter().map(|_| 1.0).collect()
        // );

        self.vec *= 1.0 - decay;
        self.vec += &(embedding.vec.to_owned() * beta);
        self.vec.l1_normalize();
        self.updates += 1;
        self.confidence += (1.0 - self.confidence) * BETA * embedding.confidence;
        self.is_dirty = true;
        self.vec.keep_top_n(15);
    }

    pub fn is_zero(&self) -> bool {
        self.vec.is_zero()
    }
}

#[derive(Debug)]
pub struct StatusEvent {
    pub status_id: i64,
    pub account_id: i64,
    pub tags: FastHashSet<i64>,
    pub created_at: SystemTime,
}

impl StatusEvent {
    pub fn age_in_seconds(&self) -> u64 {
        self.created_at.elapsed().unwrap().as_secs()
    }
}

#[derive(Debug)]
pub struct EngagementEvent {
    pub account_id: i64,
    pub status_id: i64,
    pub author_id: i64,
    pub event_time: SystemTime,
}

pub struct Embeddings {
    pub config: Config,
    pub communities: Communities,
    pub consumers: FastDashMap<i64, Embedding>,
    pub producers: FastDashMap<i64, Embedding>,
    pub tags: FastDashMap<i64, Embedding>,
    pub statuses: FastDashMap<i64, Embedding>,
    pub statuses_tags: FastDashMap<i64, Vec<i64>>,
    pub statuses_dt: FastDashMap<i64, SystemTime>,
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
            config,
            communities: communities,
            consumers: consumers,
            producers: producers,
            tags: tags,
            statuses: FastDashMap::default(),
            statuses_tags: FastDashMap::default(),
            statuses_dt: FastDashMap::default(),
        }
    }

    fn get_weighted_statuses_tags_embedding(&self, status_id: &i64) -> Option<Embedding> {
        if let Some(tags) = self.statuses_tags.get(status_id) {
            self.get_weighted_tags_embedding(tags.value())
        } else {
            None
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

        let mut vec: SparseVec = SparseVec::empty(self.communities.dim);

        let confidence_scores: Vec<f64> = tag_embeddings
            .iter()
            .map(|(_, confidence)| *confidence)
            .collect();
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

    pub fn push_status(&self, status: StatusEvent) {
        // do nothing when status embedding already exists
        if self.statuses.contains_key(&status.status_id) {
            return;
        }

        let mut status_embedding = Embedding::empty(self.communities.dim);
        let tags: Vec<i64> = status.tags.iter().cloned().collect();

        if let Some(p_embedding) = self.producers.get(&status.account_id) {
            status_embedding.update(p_embedding.value());
        }

        if let Some(t_embedding) = self.get_weighted_tags_embedding(&tags) {
            status_embedding.update(&t_embedding);
        }

        self.statuses.insert(status.status_id, status_embedding);
        self.statuses_dt.insert(status.status_id, status.created_at);

        if !status.tags.is_empty() {
            self.statuses_tags.insert(status.status_id, tags);
        }
    }

    pub fn push_engagement(&self, engagement: EngagementEvent) {
        let account_id = engagement.account_id;
        let status_id = engagement.status_id;
        let author_id = engagement.author_id;

        {
            let a_embedding = self
                .consumers
                .entry(account_id)
                .or_insert_with(|| Embedding::empty(self.communities.dim));

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
            s_embedding.engagements += 1;
        }

        // update consumer embedding
        if let (Some(mut a_embedding), Some(s_embedding)) = (
            self.consumers.get_mut(&account_id),
            self.statuses.get(&status_id),
        ) {
            a_embedding.update(s_embedding.value());
            a_embedding.engagements += 1;

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
            p_embedding.engagements += 1;
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
                    t_embedding.engagements += 1;
                }
            }
        }
    }
}

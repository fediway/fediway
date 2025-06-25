
use std::collections::{HashMap, HashSet};
use crate::utils::{SortedPair, BloomCounter, HashSetDeque};
use crate::models::{Status, Engagement};

pub struct State {
    status_tags: HashMap<i64, HashSet<i64>>,
    latest_engaged_tags: HashMap<i64, HashSetDeque<i64>>,
    tag_engagements: HashMap<i64, usize>,
    shared_tag_engagements: HashMap<SortedPair, usize>,
}

impl State {
    pub fn new() -> Self {
        Self {
            status_tags: HashMap::default(),
            latest_engaged_tags: HashMap::default(),
            tag_engagements: HashMap::default(),
            shared_tag_engagements: HashMap::default()
        }
    }

    pub fn add_status(&mut self, status: Status) {
        for tag in status.tags.iter() {
            if !self.tag_engagements.contains_key(tag) {
                self.tag_engagements.insert(*tag, 0);
            }
        }

        self.status_tags.insert(status.status_id, status.tags);

        tracing::info!("Added status {}", status.status_id);
    }

    pub fn add_engagement(&mut self, engagement: Engagement) {
        if !self.status_tags.contains_key(&engagement.status_id) {
            tracing::info!("Skipped engagement {} -> {} (no tags)", engagement.account_id, engagement.status_id);
            return;
        }

        let tags = self.status_tags.get(&engagement.status_id).unwrap();

        if tags.len() == 0 {
            tracing::info!("Skipped engagement {} -> {} (no tags)", engagement.account_id, engagement.status_id);
            return;
        }

        if !self.latest_engaged_tags.contains_key(&engagement.account_id) {
            self.latest_engaged_tags.insert(engagement.account_id, HashSetDeque::new(1000));
        }

        let latest_engaged_tags = self.latest_engaged_tags
            .get_mut(&engagement.account_id)
            .unwrap();

        for tag in tags.iter() {
            latest_engaged_tags.push(*tag);
            
            *self.tag_engagements.entry(*tag).or_insert(0) += 1;
        }

        for (i, &tag1) in latest_engaged_tags.iter().enumerate() {
            for &tag2 in latest_engaged_tags.iter().skip(i + 1) {
                *self.shared_tag_engagements
                    .entry(SortedPair::new(tag1, tag2))
                    .or_insert(0) += 1;
            }
        }

        tracing::info!("Added engagement {} -> {}", engagement.account_id, engagement.status_id);
    }
}
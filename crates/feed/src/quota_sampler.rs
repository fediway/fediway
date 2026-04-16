use std::cmp::Ordering;

use crate::candidate::Candidate;
use crate::sampler::Sampler;

#[derive(Debug, Clone)]
pub struct GroupQuota {
    group: &'static str,
    weight: f64,
}

impl GroupQuota {
    #[must_use]
    pub fn new(group: &'static str, weight: f64) -> Self {
        Self { group, weight }
    }
}

pub struct QuotaSampler {
    quotas: Vec<GroupQuota>,
    total_weight: f64,
}

impl QuotaSampler {
    #[must_use]
    pub fn new(quotas: impl IntoIterator<Item = GroupQuota>) -> Self {
        let quotas: Vec<_> = quotas.into_iter().collect();
        let total_weight = quotas.iter().map(|q| q.weight).sum();
        Self {
            quotas,
            total_weight,
        }
    }
}

impl<Item: Send + Sync> Sampler<Item> for QuotaSampler {
    fn pick(&self, remaining: &[Candidate<Item>], selected: &[Candidate<Item>]) -> Option<usize> {
        if remaining.is_empty() {
            return None;
        }

        if self.total_weight <= 0.0 {
            return highest_scored(remaining);
        }

        let n = selected.len() + 1;
        let mut best_group: Option<&'static str> = None;
        let mut best_deficit = f64::NEG_INFINITY;

        for quota in &self.quotas {
            if !remaining.iter().any(|c| c.group == quota.group) {
                continue;
            }
            let target = quota.weight / self.total_weight;
            #[allow(clippy::cast_precision_loss)]
            let actual =
                selected.iter().filter(|c| c.group == quota.group).count() as f64 / n as f64;
            let deficit = target - actual;
            if deficit > best_deficit {
                best_deficit = deficit;
                best_group = Some(quota.group);
            }
        }

        match best_group {
            Some(group) => remaining
                .iter()
                .enumerate()
                .filter(|(_, c)| c.group == group)
                .max_by(|a, b| a.1.score.partial_cmp(&b.1.score).unwrap_or(Ordering::Equal))
                .map(|(i, _)| i),
            None => highest_scored(remaining),
        }
    }
}

fn highest_scored<Item>(candidates: &[Candidate<Item>]) -> Option<usize> {
    candidates
        .iter()
        .enumerate()
        .max_by(|a, b| a.1.score.partial_cmp(&b.1.score).unwrap_or(Ordering::Equal))
        .map(|(i, _)| i)
}

#[cfg(test)]
mod tests {
    use crate::sampler::sample;

    use super::*;

    fn candidate(id: &'static str, group: &'static str, score: f64) -> Candidate<&'static str> {
        let mut c = Candidate::new(id, "test");
        c.group = group;
        c.score = score;
        c
    }

    fn group_count(output: &[Candidate<&'static str>], group: &str) -> usize {
        output.iter().filter(|c| c.group == group).count()
    }

    #[test]
    fn empty_input() {
        let out = sample(
            &QuotaSampler::new([GroupQuota::new("a", 1.0)]),
            Vec::<Candidate<&str>>::new(),
            5,
        );
        assert!(out.is_empty());
    }

    #[test]
    fn zero_limit() {
        let out = sample(&QuotaSampler::new([]), vec![candidate("x", "a", 1.0)], 0);
        assert!(out.is_empty());
    }

    #[test]
    fn proportional_allocation() {
        let input = vec![
            candidate("n1", "network", 10.0),
            candidate("n2", "network", 9.0),
            candidate("n3", "network", 8.0),
            candidate("n4", "network", 7.0),
            candidate("n5", "network", 6.0),
            candidate("n6", "network", 5.0),
            candidate("r1", "recommended", 20.0),
            candidate("r2", "recommended", 19.0),
            candidate("r3", "recommended", 18.0),
            candidate("r4", "recommended", 17.0),
            candidate("t1", "trending", 15.0),
            candidate("t2", "trending", 14.0),
        ];
        let out = sample(
            &QuotaSampler::new([
                GroupQuota::new("network", 0.6),
                GroupQuota::new("recommended", 0.3),
                GroupQuota::new("trending", 0.1),
            ]),
            input,
            10,
        );

        assert_eq!(out.len(), 10);
        assert_eq!(group_count(&out, "network"), 6);
        assert_eq!(group_count(&out, "recommended"), 3);
        assert_eq!(group_count(&out, "trending"), 1);
    }

    #[test]
    fn high_score_group_respects_weight() {
        let input = vec![
            candidate("n1", "network", 1.0),
            candidate("n2", "network", 0.9),
            candidate("n3", "network", 0.8),
            candidate("r1", "recommended", 100.0),
            candidate("r2", "recommended", 99.0),
            candidate("r3", "recommended", 98.0),
        ];
        let out = sample(
            &QuotaSampler::new([
                GroupQuota::new("network", 0.6),
                GroupQuota::new("recommended", 0.4),
            ]),
            input,
            5,
        );

        assert_eq!(group_count(&out, "network"), 3);
        assert_eq!(group_count(&out, "recommended"), 2);
    }

    #[test]
    fn surplus_goes_to_other_groups() {
        let input = vec![
            candidate("n1", "network", 10.0),
            candidate("n2", "network", 9.0),
            candidate("n3", "network", 8.0),
            candidate("n4", "network", 7.0),
            candidate("n5", "network", 6.0),
            candidate("r1", "recommended", 5.0),
        ];
        let out = sample(
            &QuotaSampler::new([
                GroupQuota::new("network", 0.6),
                GroupQuota::new("recommended", 0.3),
                GroupQuota::new("trending", 0.1),
            ]),
            input,
            6,
        );

        assert_eq!(out.len(), 6);
        assert_eq!(group_count(&out, "network"), 5);
        assert_eq!(group_count(&out, "recommended"), 1);
    }

    #[test]
    fn picks_highest_scored_within_group() {
        let input = vec![
            candidate("n_lo", "network", 1.0),
            candidate("n_hi", "network", 10.0),
            candidate("r1", "recommended", 5.0),
        ];
        let out = sample(
            &QuotaSampler::new([
                GroupQuota::new("network", 0.5),
                GroupQuota::new("recommended", 0.5),
            ]),
            input,
            2,
        );

        let ids: Vec<&str> = out.iter().map(|c| c.item).collect();
        assert!(ids.contains(&"n_hi"));
        assert!(!ids.contains(&"n_lo"));
    }

    #[test]
    fn unquoted_groups_fill_when_quoted_exhausted() {
        let input = vec![
            candidate("n1", "network", 10.0),
            candidate("x1", "other", 5.0),
            candidate("x2", "other", 4.0),
        ];
        let out = sample(
            &QuotaSampler::new([GroupQuota::new("network", 1.0)]),
            input,
            3,
        );

        assert_eq!(out.len(), 3);
        assert_eq!(group_count(&out, "network"), 1);
        assert_eq!(group_count(&out, "other"), 2);
    }

    #[test]
    fn realistic_home_feed_scenario() {
        let mut input = Vec::new();
        for i in 0..15 {
            input.push(candidate(
                Box::leak(format!("n{i}").into_boxed_str()),
                "network",
                5.0 - (i as f64 * 0.1),
            ));
        }
        for i in 0..100 {
            input.push(candidate(
                Box::leak(format!("r{i}").into_boxed_str()),
                "recommended",
                50.0 - (i as f64 * 0.3),
            ));
        }
        for i in 0..10 {
            input.push(candidate(
                Box::leak(format!("t{i}").into_boxed_str()),
                "trending",
                8.0 - (i as f64 * 0.5),
            ));
        }

        let out = sample(
            &QuotaSampler::new([
                GroupQuota::new("network", 0.60),
                GroupQuota::new("recommended", 0.30),
                GroupQuota::new("trending", 0.10),
            ]),
            input,
            20,
        );

        let nc = group_count(&out, "network");
        let rc = group_count(&out, "recommended");
        let tc = group_count(&out, "trending");

        assert_eq!(out.len(), 20);
        assert_eq!(nc, 12, "network should get 60% of 20 = 12, got {nc}");
        assert_eq!(rc, 6, "recommended should get 30% of 20 = 6, got {rc}");
        assert_eq!(tc, 2, "trending should get 10% of 20 = 2, got {tc}");
    }
}

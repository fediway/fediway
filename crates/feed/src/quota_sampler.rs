use std::cmp::Ordering;
use std::collections::HashMap;

use crate::candidate::Candidate;
use crate::sampler::Sampler;

/// Per-group weight for [`QuotaSampler`].
///
/// Each group receives a proportional share of the output slots based
/// on its weight relative to the total. For example, weights of 0.6,
/// 0.3, 0.1 allocate 60%, 30%, 10% of slots respectively.
///
/// If a group has fewer candidates than its allocation, the surplus
/// slots are redistributed to other groups proportionally.
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

/// Deterministic proportional group sampler.
///
/// Allocates output slots to groups by weight, then fills each group's
/// allocation with its highest-scoring candidates. Surplus slots from
/// under-filled groups are redistributed by weight. Output is sorted
/// by score descending.
///
/// Given identical input, output is bit-identical — no randomness.
/// Groups without a quota entry receive no allocation but can fill
/// surplus slots during redistribution.
pub struct QuotaSampler {
    quotas: Vec<GroupQuota>,
}

impl QuotaSampler {
    #[must_use]
    pub fn new(quotas: impl IntoIterator<Item = GroupQuota>) -> Self {
        Self {
            quotas: quotas.into_iter().collect(),
        }
    }
}

impl<Item: Send + Sync + Clone> Sampler<Item> for QuotaSampler {
    fn sample(&self, candidates: Vec<Candidate<Item>>, n: usize) -> Vec<Candidate<Item>> {
        if n == 0 || candidates.is_empty() {
            return Vec::new();
        }

        let mut by_group: HashMap<&'static str, Vec<Candidate<Item>>> = HashMap::new();
        for c in candidates {
            by_group.entry(c.group).or_default().push(c);
        }
        for items in by_group.values_mut() {
            items.sort_by(|a, b| b.score.partial_cmp(&a.score).unwrap_or(Ordering::Equal));
        }

        let mut output: Vec<Candidate<Item>> = Vec::with_capacity(n);
        let mut remaining = n;

        let total_weight: f64 = self.quotas.iter().map(|q| q.weight).sum();
        if total_weight <= 0.0 {
            return top_k(&mut by_group, n);
        }

        let mut allocations: Vec<(&'static str, usize)> = self
            .quotas
            .iter()
            .map(|q| {
                #[allow(
                    clippy::cast_precision_loss,
                    clippy::cast_sign_loss,
                    clippy::cast_possible_truncation
                )]
                let slots = ((q.weight / total_weight) * n as f64).floor() as usize;
                (q.group, slots)
            })
            .collect();

        // Fill each group's allocation with its top candidates.
        // Track surplus from groups that can't fill their allocation.
        let mut surplus = 0usize;
        for (group, slots) in &mut allocations {
            let items = by_group.get_mut(group);
            let available = items.as_ref().map_or(0, |v| v.len());
            let take = (*slots).min(available).min(remaining);
            if let Some(items) = items {
                output.extend(items.drain(..take));
            }
            surplus += *slots - take;
            remaining -= take;
            *slots = 0;
        }

        // Redistribute surplus slots by weight among groups that still have candidates.
        if surplus > 0 && remaining > 0 {
            let active_weight: f64 = self
                .quotas
                .iter()
                .filter(|q| by_group.get(q.group).is_some_and(|v| !v.is_empty()))
                .map(|q| q.weight)
                .sum();

            if active_weight > 0.0 {
                for quota in &self.quotas {
                    if remaining == 0 {
                        break;
                    }
                    if let Some(items) = by_group.get_mut(quota.group) {
                        if items.is_empty() {
                            continue;
                        }
                        #[allow(
                            clippy::cast_precision_loss,
                            clippy::cast_sign_loss,
                            clippy::cast_possible_truncation
                        )]
                        let extra =
                            ((quota.weight / active_weight) * surplus as f64).ceil() as usize;
                        let take = extra.min(items.len()).min(remaining);
                        output.extend(items.drain(..take));
                        remaining -= take;
                    }
                }
            }
        }

        // If still short, take remaining by score from any group.
        if remaining > 0 {
            let mut leftover: Vec<Candidate<Item>> = by_group.into_values().flatten().collect();
            leftover.sort_by(|a, b| b.score.partial_cmp(&a.score).unwrap_or(Ordering::Equal));
            output.extend(leftover.into_iter().take(remaining));
        }

        output.sort_by(|a, b| b.score.partial_cmp(&a.score).unwrap_or(Ordering::Equal));
        output
    }
}

fn top_k<Item: Clone>(
    by_group: &mut HashMap<&'static str, Vec<Candidate<Item>>>,
    n: usize,
) -> Vec<Candidate<Item>> {
    let mut all: Vec<Candidate<Item>> = by_group.drain().flat_map(|(_, v)| v).collect();
    all.sort_by(|a, b| b.score.partial_cmp(&a.score).unwrap_or(Ordering::Equal));
    all.truncate(n);
    all
}

#[cfg(test)]
mod tests {
    use super::*;

    fn candidate(id: &'static str, group: &'static str, score: f64) -> Candidate<&'static str> {
        let mut c = Candidate::new(id, "test");
        c.group = group;
        c.score = score;
        c
    }

    fn ids(output: &[Candidate<&'static str>]) -> Vec<&'static str> {
        output.iter().map(|c| c.item).collect()
    }

    fn group_count(output: &[Candidate<&'static str>], group: &str) -> usize {
        output.iter().filter(|c| c.group == group).count()
    }

    #[test]
    fn empty_input() {
        let out =
            QuotaSampler::new([GroupQuota::new("a", 1.0)]).sample(Vec::<Candidate<&str>>::new(), 5);
        assert!(out.is_empty());
    }

    #[test]
    fn zero_limit() {
        let out = QuotaSampler::new([]).sample(vec![candidate("x", "a", 1.0)], 0);
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
        let out = QuotaSampler::new([
            GroupQuota::new("network", 0.6),
            GroupQuota::new("recommended", 0.3),
            GroupQuota::new("trending", 0.1),
        ])
        .sample(input, 10);

        assert_eq!(out.len(), 10);
        assert_eq!(group_count(&out, "network"), 6);
        assert_eq!(group_count(&out, "recommended"), 3);
        assert_eq!(group_count(&out, "trending"), 1);
    }

    #[test]
    fn surplus_redistributed_when_group_short() {
        let input = vec![
            candidate("n1", "network", 10.0),
            candidate("n2", "network", 9.0),
            candidate("n3", "network", 8.0),
            candidate("n4", "network", 7.0),
            candidate("n5", "network", 6.0),
            candidate("r1", "recommended", 5.0),
        ];
        // recommended gets 30% = 3 slots, but only has 1 candidate
        // surplus 2 slots redistributed to network
        let out = QuotaSampler::new([
            GroupQuota::new("network", 0.6),
            GroupQuota::new("recommended", 0.3),
            GroupQuota::new("trending", 0.1),
        ])
        .sample(input, 6);

        assert_eq!(out.len(), 6);
        assert_eq!(group_count(&out, "network"), 5);
        assert_eq!(group_count(&out, "recommended"), 1);
    }

    #[test]
    fn high_score_group_respects_weight() {
        // recommended has much higher scores but only gets 30%
        let input = vec![
            candidate("n1", "network", 1.0),
            candidate("n2", "network", 0.9),
            candidate("n3", "network", 0.8),
            candidate("r1", "recommended", 100.0),
            candidate("r2", "recommended", 99.0),
            candidate("r3", "recommended", 98.0),
        ];
        let out = QuotaSampler::new([
            GroupQuota::new("network", 0.6),
            GroupQuota::new("recommended", 0.4),
        ])
        .sample(input, 5);

        assert_eq!(group_count(&out, "network"), 3);
        assert_eq!(group_count(&out, "recommended"), 2);
    }

    #[test]
    fn picks_highest_scored_within_group() {
        let input = vec![
            candidate("n_lo", "network", 1.0),
            candidate("n_hi", "network", 10.0),
            candidate("r1", "recommended", 5.0),
        ];
        let out = QuotaSampler::new([
            GroupQuota::new("network", 0.5),
            GroupQuota::new("recommended", 0.5),
        ])
        .sample(input, 2);

        assert!(ids(&out).contains(&"n_hi"));
        assert!(!ids(&out).contains(&"n_lo"));
    }

    #[test]
    fn output_sorted_by_score() {
        let input = vec![
            candidate("n1", "network", 3.0),
            candidate("r1", "recommended", 9.0),
            candidate("n2", "network", 7.0),
            candidate("r2", "recommended", 1.0),
        ];
        let out = QuotaSampler::new([
            GroupQuota::new("network", 0.5),
            GroupQuota::new("recommended", 0.5),
        ])
        .sample(input, 4);

        let scores: Vec<f64> = out.iter().map(|c| c.score).collect();
        assert!(scores.windows(2).all(|w| w[0] >= w[1]));
    }

    #[test]
    fn deterministic() {
        let build = || {
            vec![
                candidate("n1", "network", 4.2),
                candidate("r1", "recommended", 7.1),
                candidate("n2", "network", 2.0),
                candidate("r2", "recommended", 6.5),
                candidate("t1", "trending", 3.3),
            ]
        };
        let s = QuotaSampler::new([
            GroupQuota::new("network", 0.5),
            GroupQuota::new("recommended", 0.3),
            GroupQuota::new("trending", 0.2),
        ]);
        assert_eq!(ids(&s.sample(build(), 4)), ids(&s.sample(build(), 4)));
    }

    #[test]
    fn unquoted_groups_fill_surplus() {
        let input = vec![
            candidate("n1", "network", 10.0),
            candidate("x1", "other", 5.0),
            candidate("x2", "other", 4.0),
        ];
        // "other" has no quota — gets no allocation but fills surplus
        let out = QuotaSampler::new([GroupQuota::new("network", 1.0)]).sample(input, 3);

        assert_eq!(out.len(), 3);
        assert_eq!(group_count(&out, "network"), 1);
        assert_eq!(group_count(&out, "other"), 2);
    }
}

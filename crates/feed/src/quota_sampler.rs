use std::cmp::Ordering;
use std::collections::HashMap;

use crate::candidate::Candidate;
use crate::sampler::Sampler;

/// Per-group constraint for [`QuotaSampler`].
///
/// `min` is an absolute floor — the sampler emits at least this many
/// items from the group when candidates exist. `cap` is a fraction of
/// total output that the group cannot exceed during normal sampling;
/// when caps would leave the output short, they are ignored rather
/// than yielding an incomplete page.
#[derive(Debug, Clone)]
pub struct GroupQuota {
    group: &'static str,
    min: usize,
    cap: Option<f64>,
}

impl GroupQuota {
    #[must_use]
    pub fn new(group: &'static str) -> Self {
        Self {
            group,
            min: 0,
            cap: None,
        }
    }

    #[must_use]
    pub fn min(mut self, min: usize) -> Self {
        self.min = min;
        self
    }

    #[must_use]
    pub fn cap(mut self, fraction: f64) -> Self {
        self.cap = Some(fraction.clamp(0.0, 1.0));
        self
    }
}

/// Deterministic group-aware sampler.
///
/// Emits candidates in three passes over a score-sorted pool:
///
/// 1. **Minimums** — for each group with `min > 0`, emit up to `min`
///    highest-scoring candidates from that group.
/// 2. **Caps** — fill remaining slots by score, skipping candidates
///    whose group has reached its `cap` allotment.
/// 3. **Overflow** — if slots remain unfilled, emit highest-scoring
///    candidates ignoring caps.
///
/// Output is then re-sorted by score descending for presentation.
/// Given identical input, output is bit-identical — no randomness.
///
/// Groups with no [`GroupQuota`] entry have no constraints (effectively
/// `min = 0`, no cap). `"_fallback"` candidates (produced by
/// `PipelineBuilder::fallback`) are treated like any other group and
/// can be constrained separately.
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

        let mut sorted = candidates;
        sorted.sort_by(|a, b| b.score.partial_cmp(&a.score).unwrap_or(Ordering::Equal));

        #[allow(
            clippy::cast_precision_loss,
            clippy::cast_sign_loss,
            clippy::cast_possible_truncation
        )]
        let caps: HashMap<&'static str, usize> = self
            .quotas
            .iter()
            .filter_map(|q| {
                q.cap.map(|frac| {
                    let count = (frac * n as f64).floor() as usize;
                    (q.group, count.max(1))
                })
            })
            .collect();

        let mins: Vec<(&'static str, usize)> = self
            .quotas
            .iter()
            .filter(|q| q.min > 0)
            .map(|q| (q.group, q.min))
            .collect();

        let mut consumed = vec![false; sorted.len()];
        let mut output: Vec<Candidate<Item>> = Vec::with_capacity(n);
        let mut emitted: HashMap<&'static str, usize> = HashMap::new();

        for (group, min_count) in &mins {
            let mut from_group = 0usize;
            for (i, c) in sorted.iter().enumerate() {
                if output.len() >= n || from_group >= *min_count {
                    break;
                }
                if consumed[i] {
                    continue;
                }
                if c.group == *group {
                    output.push(sorted[i].clone());
                    consumed[i] = true;
                    from_group += 1;
                    *emitted.entry(c.group).or_insert(0) += 1;
                }
            }
        }

        for (i, c) in sorted.iter().enumerate() {
            if output.len() >= n {
                break;
            }
            if consumed[i] {
                continue;
            }
            let used = emitted.get(&c.group).copied().unwrap_or(0);
            if let Some(&cap) = caps.get(&c.group)
                && used >= cap
            {
                continue;
            }
            output.push(sorted[i].clone());
            consumed[i] = true;
            *emitted.entry(c.group).or_insert(0) += 1;
        }

        for (i, _c) in sorted.iter().enumerate() {
            if output.len() >= n {
                break;
            }
            if consumed[i] {
                continue;
            }
            output.push(sorted[i].clone());
            consumed[i] = true;
        }

        output.sort_by(|a, b| b.score.partial_cmp(&a.score).unwrap_or(Ordering::Equal));
        output
    }
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

    fn sampler(quotas: impl IntoIterator<Item = GroupQuota>) -> QuotaSampler {
        QuotaSampler::new(quotas)
    }

    #[test]
    fn empty_input_returns_empty() {
        let out = sampler([GroupQuota::new("a").min(2)]).sample(Vec::<Candidate<&str>>::new(), 5);
        assert!(out.is_empty());
    }

    #[test]
    fn zero_limit_returns_empty() {
        let input = vec![candidate("x", "a", 1.0)];
        let out = sampler([]).sample(input, 0);
        assert!(out.is_empty());
    }

    #[test]
    fn no_quotas_behaves_like_topk() {
        let input = vec![
            candidate("low", "a", 1.0),
            candidate("high", "a", 9.0),
            candidate("mid", "a", 5.0),
        ];
        let out = sampler([]).sample(input, 2);
        assert_eq!(
            out.iter().map(|c| c.item).collect::<Vec<_>>(),
            ["high", "mid"]
        );
    }

    #[test]
    fn minimum_guarantees_group_presence() {
        let input = vec![
            candidate("a1", "a", 10.0),
            candidate("a2", "a", 9.0),
            candidate("b1", "b", 1.0),
            candidate("b2", "b", 0.5),
            candidate("b3", "b", 0.1),
        ];
        let out = sampler([GroupQuota::new("b").min(2)]).sample(input, 3);
        let groups: Vec<&str> = out.iter().map(|c| c.group).collect();
        assert_eq!(groups.iter().filter(|g| **g == "b").count(), 2);
        assert_eq!(groups.iter().filter(|g| **g == "a").count(), 1);
    }

    #[test]
    fn cap_limits_group_share() {
        let input = vec![
            candidate("a1", "a", 10.0),
            candidate("a2", "a", 9.0),
            candidate("a3", "a", 8.0),
            candidate("a4", "a", 7.0),
            candidate("b1", "b", 1.0),
            candidate("b2", "b", 0.5),
        ];
        let out = sampler([GroupQuota::new("a").cap(0.5)]).sample(input, 4);
        let a_count = out.iter().filter(|c| c.group == "a").count();
        assert_eq!(a_count, 2);
    }

    #[test]
    fn cap_yields_to_prevent_short_page() {
        let input = vec![
            candidate("a1", "a", 10.0),
            candidate("a2", "a", 9.0),
            candidate("a3", "a", 8.0),
            candidate("a4", "a", 7.0),
        ];
        let out = sampler([GroupQuota::new("a").cap(0.25)]).sample(input, 4);
        assert_eq!(out.len(), 4);
    }

    #[test]
    fn minimum_exceeds_available_takes_what_exists() {
        let input = vec![
            candidate("a1", "a", 10.0),
            candidate("a2", "a", 9.0),
            candidate("b1", "b", 5.0),
        ];
        let out = sampler([GroupQuota::new("b").min(5)]).sample(input, 3);
        assert_eq!(out.len(), 3);
        assert_eq!(out.iter().filter(|c| c.group == "b").count(), 1);
    }

    #[test]
    fn deterministic_output_order_is_score_sorted() {
        let input = vec![
            candidate("a1", "a", 3.0),
            candidate("b1", "b", 9.0),
            candidate("a2", "a", 7.0),
            candidate("b2", "b", 1.0),
        ];
        let out = sampler([GroupQuota::new("a").min(1)]).sample(input, 4);
        let ids: Vec<&str> = out.iter().map(|c| c.item).collect();
        assert_eq!(ids, ["b1", "a2", "a1", "b2"]);
    }

    #[test]
    fn minimum_pass_picks_highest_score_within_group() {
        let input = vec![
            candidate("a_hi", "a", 10.0),
            candidate("a_lo", "a", 1.0),
            candidate("b_hi", "b", 50.0),
            candidate("b_lo", "b", 0.5),
        ];
        let out = sampler([GroupQuota::new("a").min(1)]).sample(input, 2);
        let ids: Vec<&str> = out.iter().map(|c| c.item).collect();
        assert!(ids.contains(&"a_hi"));
        assert!(!ids.contains(&"a_lo"));
    }

    #[test]
    fn reproducible_runs() {
        let build_input = || {
            vec![
                candidate("x1", "a", 4.2),
                candidate("x2", "b", 7.1),
                candidate("x3", "a", 2.0),
                candidate("x4", "b", 6.5),
                candidate("x5", "c", 3.3),
            ]
        };
        let s = sampler([GroupQuota::new("a").min(1), GroupQuota::new("b").cap(0.4)]);
        let out1 = s.sample(build_input(), 4);
        let out2 = s.sample(build_input(), 4);
        let ids1: Vec<&str> = out1.iter().map(|c| c.item).collect();
        let ids2: Vec<&str> = out2.iter().map(|c| c.item).collect();
        assert_eq!(ids1, ids2);
    }
}

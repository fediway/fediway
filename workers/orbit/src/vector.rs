use std::collections::HashMap;

use sqlx::PgPool;

use crate::embed::EmbeddingTemplate;
use crate::engagement::RawEngagement;

#[must_use]
pub fn ema_update(current: &[f32], embedding: &[f32], alpha: f32, weight: f32) -> Vec<f32> {
    let aw = alpha * weight;
    let decay = 1.0 - alpha;

    let updated: Vec<f32> = current
        .iter()
        .zip(embedding.iter())
        .map(|(c, e)| aw.mul_add(*e, decay * c))
        .collect();

    normalize(&updated)
}

#[must_use]
fn normalize(v: &[f32]) -> Vec<f32> {
    let norm = v.iter().map(|x| x * x).sum::<f32>().sqrt();
    if norm < f32::EPSILON {
        return v.to_vec();
    }
    v.iter().map(|x| x / norm).collect()
}

struct UserState {
    vector: Vec<f32>,
    engagement_count: i64,
}

async fn batch_load_vectors(db: &PgPool, account_ids: &[i64]) -> HashMap<i64, UserState> {
    #[derive(sqlx::FromRow)]
    struct Row {
        account_id: i64,
        vector: Vec<f32>,
        engagement_count: i64,
    }

    let rows = sqlx::query_as::<_, Row>(
        "SELECT account_id, vector, engagement_count
         FROM orbit_user_vectors
         WHERE account_id = ANY($1)",
    )
    .bind(account_ids)
    .fetch_all(db)
    .await
    .unwrap_or_default();

    rows.into_iter()
        .map(|r| {
            (
                r.account_id,
                UserState {
                    vector: r.vector,
                    engagement_count: r.engagement_count,
                },
            )
        })
        .collect()
}

async fn upsert_vector(db: &PgPool, account_id: i64, vector: &[f32], engagement_count: i64) {
    if let Err(e) = sqlx::query(
        "INSERT INTO orbit_user_vectors (account_id, vector, engagement_count, updated_at)
         VALUES ($1, $2, $3, now())
         ON CONFLICT (account_id) DO UPDATE SET
             vector = EXCLUDED.vector,
             engagement_count = EXCLUDED.engagement_count,
             updated_at = now()",
    )
    .bind(account_id)
    .bind(vector)
    .bind(engagement_count)
    .execute(db)
    .await
    {
        tracing::warn!(account_id, error = %e, "failed to upsert user vector");
        metrics::counter!("fediway_orbit_vector_upsert_errors_total").increment(1);
    }
}

pub async fn process_engagements(
    db: &PgPool,
    engagements: &[RawEngagement],
    embeddings: &HashMap<String, Vec<f32>>,
    template: &EmbeddingTemplate,
    alpha: f32,
    dims: usize,
) {
    let mut by_account: HashMap<i64, Vec<&RawEngagement>> = HashMap::new();
    for e in engagements {
        by_account.entry(e.account_id).or_default().push(e);
    }

    for user_engagements in by_account.values() {
        #[allow(clippy::cast_precision_loss)]
        metrics::histogram!("fediway_orbit_engagements_per_user")
            .record(user_engagements.len() as f64);
    }

    let account_ids: Vec<i64> = by_account.keys().copied().collect();
    let mut states = batch_load_vectors(db, &account_ids).await;

    let found = states.len() as u64;
    let miss = account_ids.len() as u64 - found;
    metrics::counter!("fediway_orbit_vectors_loaded_total", "result" => "hit").increment(found);
    metrics::counter!("fediway_orbit_vectors_loaded_total", "result" => "miss").increment(miss);

    let mut updated_count = 0u64;

    for (&account_id, user_engagements) in &by_account {
        let state = states.entry(account_id).or_insert_with(|| UserState {
            vector: vec![0.0; dims],
            engagement_count: 0,
        });

        let mut changed = false;

        for e in user_engagements {
            let rendered = template.render(&e.target);
            let Some(embedding) = embeddings.get(&rendered) else {
                continue;
            };

            state.vector = ema_update(&state.vector, embedding, alpha, e.kind.weight());
            state.engagement_count += 1;
            changed = true;
        }

        if changed {
            upsert_vector(db, account_id, &state.vector, state.engagement_count).await;
            updated_count += 1;
        }
    }

    if updated_count > 0 {
        metrics::counter!("fediway_orbit_vectors_updated_total").increment(updated_count);
        tracing::info!(vectors_updated = updated_count, "EMA update complete");
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    const DIMS: usize = 256;
    const ALPHA: f32 = 0.05;

    fn unit_vec(dim: usize) -> Vec<f32> {
        let mut v = vec![0.0; DIMS];
        v[dim] = 1.0;
        v
    }

    fn l2_norm(v: &[f32]) -> f32 {
        v.iter().map(|x| x * x).sum::<f32>().sqrt()
    }

    #[test]
    fn first_update_from_zero_sets_direction() {
        let zero = vec![0.0; DIMS];
        let embedding = unit_vec(0);
        let result = ema_update(&zero, &embedding, ALPHA, 1.0);

        assert!(result[0] > 0.9, "should point toward embedding");
        assert!(
            (l2_norm(&result) - 1.0).abs() < 1e-5,
            "should be normalized"
        );
    }

    #[test]
    fn decay_is_one_minus_alpha_not_one_minus_aw() {
        let existing = unit_vec(0);
        let embedding = unit_vec(1);

        let result = ema_update(&existing, &embedding, ALPHA, 1.0);

        // decay = 0.95, aw = 0.05
        // dim 0: 0.05 * 0.0 + 0.95 * 1.0 = 0.95 (before normalization)
        // dim 1: 0.05 * 1.0 + 0.95 * 0.0 = 0.05 (before normalization)
        // ratio should be 0.95 / 0.05 = 19
        let ratio = result[0] / result[1];
        assert!(
            (ratio - 19.0).abs() < 0.1,
            "decay should be (1 - alpha), got ratio {ratio}"
        );
    }

    #[test]
    fn reply_weight_amplifies_signal() {
        let existing = unit_vec(0);
        let embedding = unit_vec(1);

        let like_result = ema_update(&existing, &embedding, ALPHA, 1.0);
        let reply_result = ema_update(&existing, &embedding, ALPHA, 3.0);

        // Reply (weight 3.0) should push more toward dim 1 than like (weight 1.0)
        assert!(
            reply_result[1] > like_result[1],
            "reply should have stronger signal in dim 1"
        );
    }

    #[test]
    fn output_always_normalized() {
        let mut v = vec![0.0; DIMS];
        for i in 0..20 {
            let embedding = unit_vec(i % 4);
            let weight = if i % 3 == 0 { 3.0 } else { 1.0 };
            v = ema_update(&v, &embedding, ALPHA, weight);
        }

        let norm = l2_norm(&v);
        assert!(
            (norm - 1.0).abs() < 1e-5,
            "should be unit-normalized, got {norm}"
        );
    }

    #[test]
    fn normalize_zero_vector_returns_zero() {
        let zero = vec![0.0; DIMS];
        let result = normalize(&zero);
        assert!(result.iter().all(|&x| x == 0.0));
    }

    #[test]
    fn ema_blends_toward_recent() {
        let mut v = vec![0.0; DIMS];

        for _ in 0..50 {
            v = ema_update(&v, &unit_vec(0), ALPHA, 1.0);
        }
        for _ in 0..50 {
            v = ema_update(&v, &unit_vec(1), ALPHA, 1.0);
        }

        assert!(v[1] > v[0], "should blend toward more recent engagements");
    }
}

use crate::config::Config;
use crate::embeddings::{Embedding, Embeddings};
use crate::rw;
use crate::services::compute_communities::compute_communities;
use crate::sparse::SparseVec;
use itertools::Itertools;
use nalgebra_sparse::csr::CsrMatrix;
use std::collections::{HashMap, HashSet};
use std::time::Instant;

fn get_embeddings(
    dim: usize,
    matrix: CsrMatrix<f64>,
    id_mappings: HashMap<i64, usize>,
    confidence_scores: HashMap<i64, f64>,
) -> HashMap<i64, Embedding> {
    matrix
        .row_iter()
        .zip(
            id_mappings
                .iter()
                .sorted_by(|a, b| a.1.cmp(b.1))
                .map(|(account_id, _)| account_id),
        )
        .map(|(row, account_id)| {
            let indices: Vec<usize> = row.col_indices().into();
            let values: Vec<f64> = row.values().into();
            let confidence = confidence_scores.get(account_id).unwrap();
            let mut vec = SparseVec::new(dim, indices, values);
            vec.l1_normalize();
            let embedding = Embedding::new(vec, *confidence);
            (*account_id, embedding)
        })
        .collect()
}

pub async fn compute_initial_embeddings(config: &Config) {
    let (db, connection) = tokio_postgres::connect(&config.rw_conn(), tokio_postgres::NoTls)
        .await
        .unwrap();

    tokio::spawn(async move {
        if let Err(e) = connection.await {
            tracing::error!("risingwave connection error: {}", e);
        }
    });

    // 1. compute communities
    let communities = compute_communities(config, &db).await;

    let tags: Vec<_> = communities.0.keys().copied().collect();
    let tag_names = rw::get_tag_names(&db, &tags).await;
    let mut community_tags: HashMap<usize, HashSet<String>> = HashMap::new();
    for (tag, c) in communities.0.iter() {
        let tag_name = tag_names[tag].clone();
        community_tags
            .entry(*c)
            .or_insert(HashSet::from_iter(vec![tag_name.clone()]))
            .insert(tag_name);
    }

    // 2. compute initial consumer embeddings
    let (tc_matrix, t_indices): (CsrMatrix<f64>, HashMap<i64, usize>) = communities.clone().into();
    let (at_matrix, a_indices): (CsrMatrix<f64>, HashMap<i64, usize>) =
        rw::get_at_matrix(&db, &t_indices).await;
    let ac_matrix: CsrMatrix<f64> = &at_matrix * &tc_matrix;
    tracing::info!(
        "Computed initial consumer embeddings: {}x{}",
        ac_matrix.nrows(),
        ac_matrix.ncols()
    );

    // 3. compute initial tag embeddings
    let (ta_matrix, t2_indices): (CsrMatrix<f64>, HashMap<i64, usize>) =
        rw::get_ta_matrix(&db, &a_indices).await;
    let tc2_matrix = &ta_matrix * &ac_matrix;
    tracing::info!(
        "Computed initial tag embeddings: {}x{}",
        tc2_matrix.nrows(),
        tc2_matrix.ncols()
    );

    // 4. compute initial producer embeddings
    let (pa_matrix, p_indices): (CsrMatrix<f64>, HashMap<i64, usize>) =
        rw::get_pa_matrix(&db, &a_indices).await;
    let pt_matrix: CsrMatrix<f64> = rw::get_pt_matrix(&db, &p_indices, &t_indices).await;
    let pc_matrix = (&pa_matrix * &ac_matrix) + (&pt_matrix * &tc_matrix);
    tracing::info!(
        "Computed initial producer embeddings: {}x{}",
        pc_matrix.nrows(),
        pc_matrix.ncols()
    );

    // compute consumer confidence
    let mut a_confidence: HashMap<i64, f64> = at_matrix
        .row_iter()
        .zip(
            a_indices
                .iter()
                .sorted_by(|a, b| a.1.cmp(b.1))
                .map(|(account_id, _)| account_id),
        )
        .map(|(row, account_id)| {
            let x: f64 = row.values().iter().sum();
            let confidence = 1.0 - (-config.lambda * x).exp();
            (*account_id, confidence)
        })
        .collect();

    // compute tag confidence
    let mut t_confidence: HashMap<i64, f64> = ta_matrix
        .row_iter()
        .zip(
            t2_indices
                .iter()
                .sorted_by(|a, b| a.1.cmp(b.1))
                .map(|(tag_id, _)| tag_id),
        )
        .map(|(row, tag_id)| {
            let x: f64 = row.values().iter().sum();
            let confidence = 1.0 - (-config.lambda * x).exp();
            (*tag_id, confidence)
        })
        .collect();

    // compute producer confidence
    let mut p_confidence: HashMap<i64, f64> = pt_matrix
        .row_iter()
        .zip(
            p_indices
                .iter()
                .sorted_by(|a, b| a.1.cmp(b.1))
                .map(|(producer_id, _)| producer_id),
        )
        .map(|(row, producer_id)| {
            let x: f64 = row.values().iter().sum();
            let confidence = 1.0 - (-config.lambda * x).exp();
            (*producer_id, confidence)
        })
        .collect();

    let dim = communities.0.values().max().unwrap() + 1;
    let consumers: HashMap<i64, Embedding> =
        get_embeddings(dim, ac_matrix, a_indices, a_confidence);
    let producers: HashMap<i64, Embedding> =
        get_embeddings(dim, pc_matrix, p_indices, p_confidence);
    let mut tags: HashMap<i64, Embedding> =
        get_embeddings(dim, tc2_matrix, t2_indices, t_confidence);

    for tag in communities.0.keys() {
        tags.get_mut(tag).unwrap().confidence = 1.0;
    }

    let mut embeddings = Embeddings::initial(communities, consumers, producers, tags);
    let mut status_ids: HashSet<i64> = HashSet::new();

    let mut i = 0;
    let results = rw::get_initial_engagements(&db).await;
    tracing::info!("Start");
    let start = Instant::now();

    for (status, engagement) in results {
        if !status_ids.contains(&status.status_id) {
            status_ids.insert(status.status_id);

            embeddings.push_status(status);
            i += 1;
        }

        embeddings.push_engagement(engagement);
        i += 1;
    }

    let duration = start.elapsed();
    tracing::info!("Updates/second: {:?}", (i as f64) / duration.as_secs_f64());

    if let Some(e) = embeddings.consumers.get(&114712296598632158) {
        println!("{:?}", e.vec.0);

        for (i, score) in e
            .vec
            .0
            .iter()
            .sorted_by(|a, b| a.1.partial_cmp(b.1).unwrap_or(std::cmp::Ordering::Equal))
        {
            println!("{}: {} -> {:?}", i, score, community_tags.get(&i));
        }
    } else {
        println!("nope");
    }
}

use crate::config::Config;
use crate::rw;
use crate::services::compute_communities::compute_communities;
use itertools::Itertools;
use nalgebra_sparse::csr::CsrMatrix;
use std::collections::HashMap;
use tokio_postgres::Client;

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
    let communities = compute_communities(&config, &db).await;

    // 2. compute initial consumer embeddings
    let (tc_matrix, t_indices): (CsrMatrix<f64>, HashMap<i64, usize>) = communities.into();
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
    let tc2_matrix = &ta_matrix * &at_matrix;
    tracing::info!(
        "Computed initial tag embeddings: {}x{}",
        tc2_matrix.nrows(),
        tc2_matrix.ncols()
    );

    // 4. compute initial producer embeddings
    let (pa_matrix, p_indices): (CsrMatrix<f64>, HashMap<i64, usize>) =
        rw::get_pa_matrix(&db, &a_indices).await;
    tracing::info!("pa shape: {}x{}", pa_matrix.nrows(), pa_matrix.ncols());
    let pt_matrix: CsrMatrix<f64> = rw::get_pt_matrix(&db, &p_indices, &t_indices).await;
    tracing::info!("pt shape: {}x{}", pt_matrix.nrows(), pt_matrix.ncols());
    let pc_matrix = (&pa_matrix * &ac_matrix) + (&pt_matrix * &tc_matrix);
    tracing::info!(
        "Computed initial producer embeddings: {}x{}",
        pc_matrix.nrows(),
        pc_matrix.ncols()
    );

    // 5. compute consumer confidence
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

    // 6. compute tag confidence
    let mut t_confidence: HashMap<i64, f64> = pt_matrix
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
            println!("c({}) = {}", x, confidence);
            (*tag_id, confidence)
        })
        .collect();

    // 7. compute producer confidence
    let mut p_confidence: HashMap<i64, f64> = ta_matrix
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
            println!("c({}) = {}", x, confidence);
            (*producer_id, confidence)
        })
        .collect();
}

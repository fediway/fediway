use crate::communities::{Communities, weighted_louvain};
use crate::config::Config;
use crate::embedding::{Embedding, Embeddings};
use crate::rw;
use crate::sparse::SparseVec;
use crate::types::{FastDashMap, FastHashMap, FastHashSet};
use itertools::Itertools;
use nalgebra_sparse::csr::CsrMatrix;
use petgraph::graph::UnGraph;
use std::time::Instant;
use tokio_postgres::Client;

pub async fn get_initial_embeddings(config: Config) -> Embeddings {
    let (db, connection) = tokio_postgres::connect(&config.rw_conn(), tokio_postgres::NoTls)
        .await
        .unwrap();

    tokio::spawn(async move {
        if let Err(e) = connection.await {
            tracing::error!("risingwave connection error: {}", e);
        }
    });

    // 1. compute communities
    let communities = get_communities(&config, &db).await;

    // 2. compute initial consumer embeddings
    let (tc_matrix, t_indices): (CsrMatrix<f64>, FastHashMap<i64, usize>) =
        communities.clone().into();
    let (at_matrix, a_indices): (CsrMatrix<f64>, FastHashMap<i64, usize>) =
        rw::get_at_matrix(&db, &t_indices).await;
    let ac_matrix: CsrMatrix<f64> = &at_matrix * &tc_matrix;
    tracing::info!(
        "Computed initial embeddings for {} consumers",
        ac_matrix.nrows(),
    );

    // 3. compute initial tag embeddings
    let (ta_matrix, t2_indices): (CsrMatrix<f64>, FastHashMap<i64, usize>) =
        rw::get_ta_matrix(&db, &a_indices).await;
    let tc2_matrix = &ta_matrix * &ac_matrix;
    tracing::info!(
        "Computed initial embeddings for {} tags",
        tc2_matrix.nrows(),
    );

    // 4. compute initial producer embeddings
    let (pa_matrix, p_indices): (CsrMatrix<f64>, FastHashMap<i64, usize>) =
        rw::get_pa_matrix(&db, &a_indices).await;
    let pt_matrix: CsrMatrix<f64> = rw::get_pt_matrix(&db, &p_indices, &t_indices).await;
    let pc_matrix = (&pa_matrix * &ac_matrix) + (&pt_matrix * &tc_matrix);
    tracing::info!(
        "Computed initial embeddings for {} producers",
        pc_matrix.nrows(),
    );

    // compute initial confidence scores
    let a_confidence = get_confidence_scores(&at_matrix, &a_indices, config.lambda);
    let p_confidence = get_confidence_scores(&pt_matrix, &p_indices, config.lambda);
    let mut t_confidence = get_confidence_scores(&ta_matrix, &t2_indices, config.lambda);

    // set confidence for tags that are assigned to communities to 1
    for tag in communities.tags.keys() {
        if let Some(c) = t_confidence.get_mut(tag) {
            *c = 1.0;
        }
    }

    let consumers = get_embeddings(communities.dim, ac_matrix, a_indices, a_confidence);
    let producers = get_embeddings(communities.dim, pc_matrix, p_indices, p_confidence);
    let tags = get_embeddings(communities.dim, tc2_matrix, t2_indices, t_confidence);

    let embeddings = Embeddings::initial(config, communities, consumers, producers, tags);

    // return embeddings;

    tracing::info!("Loading initial engagements...");

    let mut i = 0;
    let mut status_ids: FastHashSet<i64> = FastHashSet::default();
    let results = rw::get_initial_engagements(&db).await;

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

    tracing::info!(
        "Seeded initial engagements with {} udpates/second.",
        (i as f64) / duration.as_secs_f64()
    );

    embeddings
}

async fn get_communities(config: &Config, db: &Client) -> Communities {
    let mut graph: UnGraph<i64, f64> = UnGraph::new_undirected();
    let mut tag_indices = FastHashMap::default();

    tracing::info!("Loading tag similarities.");

    for sim in rw::get_tag_similarities(db, config.min_tag_authors, config.min_tag_engagers).await {
        if sim.2 < config.tag_sim_threshold {
            continue;
        }

        let node_a = *tag_indices
            .entry(sim.0)
            .or_insert_with(|| graph.add_node(sim.0));
        let node_b = *tag_indices
            .entry(sim.1)
            .or_insert_with(|| graph.add_node(sim.1));

        graph.add_edge(node_a, node_b, sim.2);
    }

    let communities = weighted_louvain(
        &graph,
        config.louvain_resolution,
        config.louvain_max_iterations,
        config.random_state,
    );

    let num_communities = communities.tags.values().max().unwrap() + 1;
    let num_tags = communities.tags.len();
    let tags: Vec<_> = communities.tags.keys().copied().collect();
    let tag_names = rw::get_tag_names(db, &tags).await;

    let mut community_tags: FastHashMap<usize, FastHashSet<String>> = FastHashMap::default();

    for (tag, c) in communities.tags.iter() {
        let tag_name = tag_names[tag].clone();
        community_tags
            .entry(*c)
            .or_insert(FastHashSet::from_iter(vec![tag_name.clone()]))
            .insert(tag_name);
    }

    for (c, tags) in community_tags {
        println!("{}: {:?}", c, tags);
    }

    tracing::info!(
        "Computed {} communities for {} tags.",
        num_communities,
        num_tags
    );

    communities
}

fn get_embeddings(
    dim: usize,
    matrix: CsrMatrix<f64>,
    id_mappings: FastHashMap<i64, usize>,
    confidence_scores: FastHashMap<i64, f64>,
) -> FastDashMap<i64, Embedding> {
    matrix
        .row_iter()
        .zip(
            id_mappings
                .iter()
                .sorted_by(|a, b| a.1.cmp(b.1))
                .map(|(id, _)| id),
        )
        .map(|(row, id)| {
            let indices: Vec<usize> = row.col_indices().into();
            let values: Vec<f64> = row.values().into();
            let confidence = confidence_scores.get(id).unwrap();
            let mut vec = SparseVec::new(dim, indices, values);
            vec.l1_normalize();
            let embedding = Embedding::new(vec, *confidence);
            (*id, embedding)
        })
        .collect()
}

fn get_confidence_scores(
    matrix: &CsrMatrix<f64>,
    id_mappings: &FastHashMap<i64, usize>,
    lambda: f64,
) -> FastHashMap<i64, f64> {
    matrix
        .row_iter()
        .zip(
            id_mappings
                .iter()
                .sorted_by(|a, b| a.1.cmp(b.1))
                .map(|(id, _)| id),
        )
        .map(|(row, id)| {
            let x: f64 = row.values().iter().sum();
            let confidence = 1.0 - (-lambda * x).exp();
            (*id, confidence)
        })
        .collect()
}

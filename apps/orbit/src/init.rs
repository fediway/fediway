use crate::communities::{Communities, weighted_louvain};
use crate::config::Config;
use crate::embedding::{Embeddings, FromEmbedding};
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

    let consumers = get_embeddings(ac_matrix, a_indices);
    let producers = get_embeddings(pc_matrix, p_indices);
    let tags = get_embeddings(tc2_matrix, t2_indices);

    let embeddings = Embeddings::initial(communities, consumers, producers, tags);

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

    let blacklist: FastHashSet<i64> = rw::get_tag_ids(db, &config.tags_blacklist)
        .await
        .into_values()
        .collect();

    for sim in rw::get_tag_similarities(db, config.min_tag_authors, config.min_tag_engagers).await {
        if sim.2 < config.tag_sim_threshold {
            continue;
        }

        if blacklist.contains(&sim.0) || blacklist.contains(&sim.1) {
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

    for (c, tags) in community_tags.iter().sorted_by(|(a, _), (b, _)| a.cmp(b)) {
        println!("{}: {:?}", c, tags);
    }

    tracing::info!(
        "Computed {} communities for {} tags.",
        num_communities,
        num_tags
    );

    communities
}

fn get_embeddings<E: FromEmbedding>(
    matrix: CsrMatrix<f64>,
    id_mappings: FastHashMap<i64, usize>,
) -> FastDashMap<i64, E> {
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
            let mut vec = SparseVec::new(row.ncols(), indices, values);
            vec.normalize();
            (*id, E::from_embedding(vec))
        })
        .collect()
}

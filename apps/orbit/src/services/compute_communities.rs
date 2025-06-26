use crate::algo::weighted_louvain::{Communities, weighted_louvain};
use crate::config::Config;
use crate::rw;
use petgraph::graph::UnGraph;
use std::collections::{HashMap, HashSet};
use tokio_postgres::Client;

pub async fn compute_communities(config: &Config, db: &Client) -> Communities {
    let mut graph: UnGraph<i64, f64> = UnGraph::new_undirected();
    let mut tag_indices = std::collections::HashMap::new();

    tracing::info!("Loading tag similarities.");

    for sim in rw::get_tag_similarities(db).await {
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

    let num_communities = communities.0.iter().map(|(_, c)| c).max().unwrap() + 1;
    let num_tags = communities.0.len();
    let tags: Vec<_> = communities.0.iter().map(|(tag, _)| *tag).collect();
    let tag_names = rw::get_tag_names(db, &tags).await;

    let mut community_tags: HashMap<usize, HashSet<String>> = HashMap::new();

    for (tag, c) in communities.0.iter() {
        let tag_name = tag_names[tag].clone();
        community_tags
            .entry(*c)
            .or_insert(HashSet::from_iter(vec![tag_name.clone()]))
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

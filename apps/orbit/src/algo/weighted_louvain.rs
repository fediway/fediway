use petgraph::graph::{NodeIndex, UnGraph};
use std::collections::HashMap;
use itertools::{CombinationsWithReplacement, Itertools};
use rand::prelude::*;

pub struct Communities(HashMap<i64, usize>);

pub fn weighted_louvain(
    graph: &UnGraph<i64, f64>, 
    resolution: f64, 
    max_iterations: usize,
    random_state: u64
) -> Communities {
    // Initialize random number generator
    let mut rng = StdRng::seed_from_u64(random_state);

    // Initialize each node in its own community
    let mut communities: HashMap<_, _> = graph
        .node_indices()
        .enumerate()
        .map(|(i, node)| (node, i))
        .collect();

    // Precompute total edge weights and node degrees
    let total_weight: f64 = graph.edge_weights().sum();
    let node_weights: HashMap<_, _> = graph
        .node_indices()
        .map(|node| {
            let weight: f64 = graph
                .edges(node)
                .map(|edge| edge.weight())
                .sum();
            (node, weight)
        })
        .collect();

    let mut improved = true;
    let mut iteration = 0;
    
    while improved && iteration < max_iterations {
        improved = false;
        iteration += 1;

        // Randomize node order to avoid bias
        let mut nodes: Vec<_> = graph.node_indices().collect();
        nodes.shuffle(&mut rng);

        for node in nodes {
            let current_community = communities[&node];

            // Calculate weight of edges from node to each neighboring community
            let mut neighbor_communities: HashMap<usize, f64> = HashMap::new();
            
            for neighbor in graph.neighbors(node) {
                let neighbor_comm = communities[&neighbor];
                let edge_weight = *graph.edge_weight(graph.find_edge(node, neighbor).unwrap()).unwrap();
                *neighbor_communities.entry(neighbor_comm).or_insert(0.0) += edge_weight;
            }

            // Find the community that maximizes modularity gain
            let mut best_community = current_community;
            let mut best_gain = 0.0;

            // Consider moving to each neighboring community
            for (&community, &weight_to_comm) in neighbor_communities.iter() {
                if community == current_community {
                    continue;
                }

                // Calculate modularity gain for moving to this community
                let gain = calculate_modularity_gain(
                    graph,
                    node,
                    current_community,
                    community,
                    &communities,
                    weight_to_comm,
                    &node_weights,
                    total_weight,
                    resolution,
                );

                if gain > best_gain {
                    best_gain = gain;
                    best_community = community;
                }
            }

            // Move node to best community if it improves modularity
            if best_community != current_community {
                communities.insert(node, best_community);
                improved = true;
            }
        }
    }

    let mut community_indices: HashMap<usize, usize> = HashMap::new();

    for (_, c) in communities.iter() {
        if !community_indices.contains_key(c) {
            community_indices.insert(*c, community_indices.len());
        }
    }

    Communities(communities
        .iter()
        .map(|(node, community)| {
            (*graph.node_weight(*node).unwrap(), community_indices[community])
        })
        .collect())
}

/// Calculate the modularity gain from moving a node between communities.
fn calculate_modularity_gain(
    graph: &UnGraph<i64, f64>,
    node: NodeIndex,
    from_comm: usize,
    to_comm: usize,
    communities: &HashMap<NodeIndex, usize>,
    weight_to_comm: f64,
    node_weights: &HashMap<NodeIndex, f64>,
    total_weight: f64,
    resolution: f64,
) -> f64 {
    // Weight of edges from node to its current community (excluding self-loops)
    let mut weight_to_current: f64 = 0.0;
    for neighbor in graph.neighbors(node) {
        if communities[&neighbor] == from_comm && neighbor != node {
            let edge_weight = *graph.edge_weight(graph.find_edge(node, neighbor).unwrap()).unwrap();
            weight_to_current += edge_weight;
        }
    }
    
    // Total weight of edges in current and target communities
    let from_comm_weight: f64 = communities
        .iter()
        .filter(|(_, comm)| **comm == from_comm)
        .map(|(&n, _)| node_weights[&n])
        .sum();

    let to_comm_weight: f64 = communities
        .iter()
        .filter(|(_, comm)| **comm == to_comm)
        .map(|(&n, _)| node_weights[&n])
        .sum();

    let node_degree = node_weights[&node];

    // Modularity gain calculation
    let gain = (weight_to_comm - weight_to_current)
        - resolution
            * node_degree
            * ((to_comm_weight - from_comm_weight + node_degree) / (2.0 * total_weight));

    gain
}

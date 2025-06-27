use crate::sparse::SparseVec;

pub struct QdrantClient {}

impl QdrantClient {}

pub enum QdrantTask {
    Update {
        id: i64,
        collection: String,
        embedding: SparseVec,
        metadata: serde_json::Value,
    },
}

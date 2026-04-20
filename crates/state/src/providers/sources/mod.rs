pub mod fetch;
mod row;
mod sql;

pub use fetch::find_sources;

use common::types::Provider;

/// A provider bound to a route, including which algorithm to call.
pub struct BoundProvider {
    pub provider: Provider,
    pub algorithm: String,
}

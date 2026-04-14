mod mapping;
mod view;

pub use mapping::{
    CachedStatus, PostMapping, delete, find_by_id, map_post, map_posts, update_cache,
};
pub use view::fetch_by_ids;

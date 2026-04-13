use std::borrow::Cow;

use common::types::Post;
use feed::Feed;
use feed::candidate::Candidate;
use feed::pipeline::Pipeline;
use feed::scorer::Diversity;
use sources::commonfeed::posts::PostsSource;
use sources::commonfeed::types::QueryFilters;

use crate::feeds::timeline_feed::TimelineFeed;
use crate::state::AppState;

const POOL_SIZE: usize = 100;

pub struct TagTimelineFeed {
    pipeline: Pipeline<Post>,
    hashtag: String,
}

impl TagTimelineFeed {
    pub async fn new(state: &AppState, mut filters: QueryFilters, hashtag: String) -> Self {
        filters.tag = Some(hashtag.clone());

        let bound = state::providers::find_sources(&state.pool, "timelines/tag").await;
        let sources = bound
            .into_iter()
            .map(|b| PostsSource::new(b.provider, b.algorithm).with_filters(filters.clone()));

        let pipeline = Pipeline::builder()
            .name("timelines/tag")
            .sources(sources, POOL_SIZE)
            .score(Diversity::new(0.1, |post: &Post| {
                post.author.handle.clone()
            }))
            .build();

        Self { pipeline, hashtag }
    }
}

impl Feed for TagTimelineFeed {
    type Item = Post;

    async fn collect(&self) -> Vec<Candidate<Post>> {
        self.pipeline.execute(POOL_SIZE, &()).await.items
    }
}

impl TimelineFeed for TagTimelineFeed {
    const RESOURCE: &'static str = "tag";

    fn path(&self) -> Cow<'static, str> {
        Cow::Owned(format!("/api/v1/timelines/tag/{}", self.hashtag))
    }
}

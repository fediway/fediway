use std::borrow::Cow;

use common::types::Post;
use feed::Feed;
use feed::candidate::Candidate;
use feed::pipeline::Pipeline;
use feed::scorer::Diversity;
use sources::commonfeed::posts::PostsSource;
use sources::commonfeed::types::QueryFilters;
use sources::mastodon::PolicyFilter;
use state::policy::UserPolicy;

use crate::auth::Account;
use crate::feeds::timeline_feed::TimelineFeed;
use crate::state::AppState;

const POOL_SIZE: usize = 100;

pub struct LinkTimelineFeed {
    pipeline: Pipeline<Post>,
    viewer_id: Option<i64>,
}

impl LinkTimelineFeed {
    pub async fn new(
        state: &AppState,
        account: Option<&Account>,
        mut filters: QueryFilters,
        url: String,
    ) -> Self {
        filters.link = Some(url);

        let viewer_id = account.map(|a| a.id);
        let policy = match account {
            Some(a) => state::policy::load(&state.pool, a.id, &state.instance_domain).await,
            None => UserPolicy::default(),
        };

        let bound = state::providers::find_sources(&state.pool, "timelines/link").await;
        let sources = bound
            .into_iter()
            .map(|b| PostsSource::new(b.provider, b.algorithm).with_filters(filters.clone()));

        let pipeline = Pipeline::builder()
            .name("timelines/link")
            .sources(sources, POOL_SIZE)
            .filter(PolicyFilter::new(policy).without_mutes())
            .score(Diversity::new(0.1, |post: &Post| {
                post.author.handle.clone()
            }))
            .build();

        Self {
            pipeline,
            viewer_id,
        }
    }
}

impl Feed for LinkTimelineFeed {
    type Item = Post;

    async fn collect(&self) -> Vec<Candidate<Post>> {
        self.pipeline.execute(POOL_SIZE, &()).await.items
    }
}

impl TimelineFeed for LinkTimelineFeed {
    const RESOURCE: &'static str = "link";

    fn path(&self) -> Cow<'static, str> {
        Cow::Borrowed("/api/v1/timelines/link")
    }

    fn viewer_id(&self) -> Option<i64> {
        self.viewer_id
    }
}

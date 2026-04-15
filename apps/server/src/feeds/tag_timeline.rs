use std::borrow::Cow;

use common::types::Post;
use feed::Feed;
use feed::candidate::Candidate;
use feed::filter::Dedup;
use feed::pipeline::Pipeline;
use feed::quota_sampler::{GroupQuota, QuotaSampler};
use feed::scorer::Diversity;
use sources::commonfeed::posts::PostsSource;
use sources::commonfeed::types::QueryFilters;
use sources::mastodon::{FederatedTagSource, NativeTagSource, PolicyFilter};
use state::policy::UserPolicy;

use crate::auth::Account;
use crate::feeds::timeline_feed::TimelineFeed;
use crate::state::AppState;

const POOL_SIZE: usize = 100;
const LOCAL_PER_SOURCE_LIMIT: usize = 50;
const EXTERNAL_PER_SOURCE_LIMIT: usize = 100;

pub struct TagTimelineFeed {
    pipeline: Pipeline<Post>,
    hashtag: String,
    viewer_id: Option<i64>,
}

impl TagTimelineFeed {
    pub async fn new(
        state: &AppState,
        account: Option<&Account>,
        mut filters: QueryFilters,
        hashtag: String,
    ) -> Self {
        filters.tag = Some(hashtag.clone());

        let viewer_id = account.map(|a| a.id);
        let policy = match account {
            Some(a) => state::policy::load(&state.pool, a.id, &state.instance_domain).await,
            None => UserPolicy::default(),
        };

        let native = NativeTagSource::new(
            state.pool.clone(),
            hashtag.clone(),
            state.instance_domain.clone(),
            state.media.clone(),
        );
        let federated = FederatedTagSource::new(
            state.pool.clone(),
            hashtag.clone(),
            state.instance_domain.clone(),
            state.media.clone(),
        );

        let external_bindings = state::providers::find_sources(&state.pool, "timelines/tag").await;
        let external_sources = external_bindings
            .into_iter()
            .map(|b| PostsSource::new(b.provider, b.algorithm).with_filters(filters.clone()));

        let pipeline = Pipeline::builder()
            .name("timelines/tag")
            .group("native", [native], LOCAL_PER_SOURCE_LIMIT)
            .group("federated", [federated], LOCAL_PER_SOURCE_LIMIT)
            .group("external", external_sources, EXTERNAL_PER_SOURCE_LIMIT)
            .filter(
                Dedup::new(|c: &Candidate<Post>| {
                    c.item.uri.clone().unwrap_or_else(|| c.item.url.clone())
                })
                .prefer(|c| match c.group {
                    "native" => 0,
                    "federated" => 1,
                    _ => 2,
                }),
            )
            .filter(PolicyFilter::new(policy).without_mutes())
            .score(Diversity::new(0.1, |post: &Post| {
                post.author.handle.clone()
            }))
            .sampler(QuotaSampler::new([
                GroupQuota::new("native").min(3).cap(0.5),
                GroupQuota::new("federated").cap(0.4),
                GroupQuota::new("external").cap(0.7),
            ]))
            .build();

        Self {
            pipeline,
            hashtag,
            viewer_id,
        }
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

    fn viewer_id(&self) -> Option<i64> {
        self.viewer_id
    }
}

use crate::candidate::Candidate;

/// A named feed: the *what* of feed composition.
///
/// Each impl owns a `Pipeline<Self::Item>` internally and exposes a
/// single [`collect`] method that runs it. Pagination is deliberately
/// not a concern of this trait — supertraits in service layers own
/// their endpoint's pagination model (offset cursor, Mastodon keyset,
/// etc.) and compose on top.
///
/// [`collect`]: Feed::collect
pub trait Feed: Sync {
    type Item: Send + Sync + 'static;

    fn collect(&self) -> impl std::future::Future<Output = Vec<Candidate<Self::Item>>> + Send;
}

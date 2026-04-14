use common::types::Post;
use feed::candidate::Candidate;
use feed::filter::Filter;
use state::policy::UserPolicy;

pub struct PolicyFilter {
    policy: UserPolicy,
    apply_mutes: bool,
}

impl PolicyFilter {
    #[must_use]
    pub fn new(policy: UserPolicy) -> Self {
        Self {
            policy,
            apply_mutes: true,
        }
    }

    #[must_use]
    pub fn without_mutes(mut self) -> Self {
        self.apply_mutes = false;
        self
    }
}

impl<Ctx: Send + Sync> Filter<Post, Ctx> for PolicyFilter {
    fn apply(&self, candidates: &mut Vec<Candidate<Post>>, _ctx: &Ctx) {
        if self.policy.is_empty() {
            return;
        }
        candidates.retain(|c| {
            let handle = c.item.author.handle.trim_start_matches('@');
            if self.policy.blocked_handles.contains(handle) {
                return false;
            }
            if self.apply_mutes && self.policy.muted_handles.contains(handle) {
                return false;
            }
            if let Some(domain) = handle.rsplit('@').next()
                && self.policy.blocked_domains.contains(domain)
            {
                return false;
            }
            true
        });
    }
}

#[cfg(test)]
mod tests {
    use std::collections::HashSet;

    use common::types::{Author, Engagement, Post};

    use super::*;

    fn post_by(handle: &str) -> Candidate<Post> {
        let post = Post {
            provider_id: None,
            provider_domain: None,
            url: format!("https://example/{handle}"),
            uri: None,
            content: String::new(),
            text: String::new(),
            author: Author {
                handle: handle.into(),
                display_name: String::new(),
                url: String::new(),
                avatar_url: None,
                emojis: Vec::new(),
            },
            published_at: chrono::Utc::now(),
            language: None,
            sensitive: false,
            content_warning: None,
            media: Vec::new(),
            engagement: Engagement::default(),
            link: None,
            reply_to: None,
            quote: None,
            tags: Vec::new(),
            emojis: Vec::new(),
        };
        Candidate::new(post, "test")
    }

    fn policy(blocked: &[&str], muted: &[&str], blocked_domains: &[&str]) -> PolicyFilter {
        PolicyFilter::new(UserPolicy {
            blocked_handles: blocked.iter().map(|s| (*s).into()).collect(),
            muted_handles: muted.iter().map(|s| (*s).into()).collect(),
            blocked_domains: blocked_domains.iter().map(|s| (*s).into()).collect(),
        })
    }

    fn texts(candidates: &[Candidate<Post>]) -> HashSet<String> {
        candidates
            .iter()
            .map(|c| c.item.author.handle.clone())
            .collect()
    }

    #[test]
    fn empty_policy_is_a_no_op() {
        let filter = PolicyFilter::new(UserPolicy::default());
        let mut candidates = vec![post_by("alice@local.test"), post_by("bob@remote.test")];
        filter.apply(&mut candidates, &());
        assert_eq!(candidates.len(), 2);
    }

    #[test]
    fn blocked_handle_removed() {
        let filter = policy(&["bob@remote.test"], &[], &[]);
        let mut candidates = vec![post_by("alice@local.test"), post_by("bob@remote.test")];
        filter.apply(&mut candidates, &());
        let remaining = texts(&candidates);
        assert!(remaining.contains("alice@local.test"));
        assert!(!remaining.contains("bob@remote.test"));
    }

    #[test]
    fn muted_handle_removed() {
        let filter = policy(&[], &["bob@remote.test"], &[]);
        let mut candidates = vec![post_by("alice@local.test"), post_by("bob@remote.test")];
        filter.apply(&mut candidates, &());
        assert!(!texts(&candidates).contains("bob@remote.test"));
    }

    #[test]
    fn blocked_domain_removes_all_accounts_from_it() {
        let filter = policy(&[], &[], &["spam.example"]);
        let mut candidates = vec![
            post_by("alice@local.test"),
            post_by("bob@spam.example"),
            post_by("eve@spam.example"),
        ];
        filter.apply(&mut candidates, &());
        let remaining = texts(&candidates);
        assert_eq!(remaining.len(), 1);
        assert!(remaining.contains("alice@local.test"));
    }

    #[test]
    fn without_mutes_keeps_muted_handles_but_still_blocks() {
        let filter = policy(&["bob@remote.test"], &["carol@remote.test"], &[]).without_mutes();
        let mut candidates = vec![
            post_by("alice@local.test"),
            post_by("bob@remote.test"),
            post_by("carol@remote.test"),
        ];
        filter.apply(&mut candidates, &());
        let remaining = texts(&candidates);
        assert!(remaining.contains("alice@local.test"));
        assert!(remaining.contains("carol@remote.test"));
        assert!(!remaining.contains("bob@remote.test"));
    }

    #[test]
    fn handle_with_leading_at_is_normalized() {
        let filter = policy(&["bob@remote.test"], &[], &[]);
        let mut candidates = vec![post_by("@bob@remote.test")];
        filter.apply(&mut candidates, &());
        assert!(candidates.is_empty());
    }
}

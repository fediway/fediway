//! Server-side Mastodon response builders.
//!
//! Lives above the `state` crate (DB access) and the `mastodon` crate
//! (types) and encodes the server's response-shape policies. Callers
//! are feed `map()` impls in [`crate::feeds`] and HTTP handlers in
//! [`crate::routes::mastodon`] — shared glue lives here, not in either
//! caller module.

pub mod forward;
pub mod resolve;
pub mod statuses;
pub mod translate;

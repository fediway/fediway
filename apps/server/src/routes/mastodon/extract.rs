use axum::http::HeaderMap;
use sources::commonfeed::types::QueryFilters;

use crate::auth::Account;
use crate::language::resolve_languages;
use crate::observe;

pub fn request_filters(account: Option<&Account>, headers: &HeaderMap) -> QueryFilters {
    let languages = resolve_languages(account, headers);
    observe::language_requested(&languages);
    QueryFilters {
        language: languages,
        ..Default::default()
    }
}

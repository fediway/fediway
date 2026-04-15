mod common;

use axum::body::Body;
use axum::http::{Request, StatusCode};
use serde_json::json;
use sqlx::PgPool;

use common::mastodon::{
    MASTODON_BASE, MastodonReport, MastodonStatus, create_status, fetch_status, http_client,
    load_token, seed_commonfeed, seed_local_auth,
};
use server::mastodon::resolve::Resolver;

mod resolver {
    use super::*;

    #[ignore = "requires running Mastodon (repos/fediway/docker-compose.integration.yaml)"]
    #[sqlx::test]
    async fn resolve_finds_local_status(pool: PgPool) {
        common::setup_db(&pool).await;
        let token = load_token();
        let http = http_client();

        let created: MastodonStatus =
            create_status(&http, &token, "integration resolver test").await;
        let expected_id: i64 = created.id.parse().expect("numeric mastodon id");

        let snowflake = seed_commonfeed(&pool, &created.uri).await;

        let resolver = Resolver::new(pool.clone(), http, Some(MASTODON_BASE.into()));
        let resolved = resolver
            .resolve(snowflake, &token)
            .await
            .expect("resolve failed");

        assert_eq!(resolved, expected_id);

        let row = state::statuses::find_by_id(&pool, snowflake)
            .await
            .unwrap()
            .unwrap();
        assert_eq!(row.mastodon_local_id, Some(expected_id));
    }
}

mod engagement {
    use super::*;

    async fn prepare(
        pool: &PgPool,
        http: &reqwest::Client,
        token: &server::auth::BearerToken,
        text: &str,
    ) -> (common::TestApp, MastodonStatus, i64) {
        seed_local_auth(pool, token).await;
        let created = create_status(http, token, text).await;
        let app =
            common::TestApp::from_pool_with_mastodon(pool.clone(), Some(MASTODON_BASE.into()))
                .await;
        let snowflake = seed_commonfeed(pool, &created.uri).await;
        (app, created, snowflake)
    }

    fn authed(path: String, token: &server::auth::BearerToken) -> Request<Body> {
        Request::post(path)
            .header("authorization", format!("Bearer {}", token.as_str()))
            .header("x-forwarded-proto", "https")
            .body(Body::empty())
            .unwrap()
    }

    #[ignore = "requires running Mastodon (repos/fediway/docker-compose.integration.yaml)"]
    #[sqlx::test]
    async fn favourite_round_trip(pool: PgPool) {
        let token = load_token();
        let http = http_client();
        let (app, created, snowflake) =
            prepare(&pool, &http, &token, "integration favourite").await;
        let mastodon_id: i64 = created.id.parse().unwrap();

        let resp = app
            .raw_request(authed(
                format!("/api/v1/statuses/{snowflake}/favourite"),
                &token,
            ))
            .await;

        assert_eq!(resp.status, StatusCode::OK);
        let body = resp.json();
        assert_eq!(body["id"], snowflake.to_string());
        assert_eq!(body["favourited"], true);

        let after = fetch_status(&http, &token, &created.id).await;
        assert!(after.favourited);
        assert_eq!(after.favourites_count, 1);

        let row = state::statuses::find_by_id(&pool, snowflake)
            .await
            .unwrap()
            .unwrap();
        assert_eq!(row.mastodon_local_id, Some(mastodon_id));
    }

    #[ignore = "requires running Mastodon (repos/fediway/docker-compose.integration.yaml)"]
    #[sqlx::test]
    async fn reblog_round_trip(pool: PgPool) {
        let token = load_token();
        let http = http_client();
        let (app, created, snowflake) = prepare(&pool, &http, &token, "integration reblog").await;

        let resp = app
            .raw_request(authed(
                format!("/api/v1/statuses/{snowflake}/reblog"),
                &token,
            ))
            .await;

        assert_eq!(resp.status, StatusCode::OK);
        let body = resp.json();
        assert_ne!(
            body["id"],
            snowflake.to_string(),
            "reblog creates a wrapper status; its id is not the original's snowflake"
        );
        assert_eq!(body["reblogged"], true);
        assert_eq!(
            body["reblog"]["id"],
            snowflake.to_string(),
            "the wrapped original must appear under reblog.id rewritten to our snowflake"
        );

        let after = fetch_status(&http, &token, &created.id).await;
        assert!(after.reblogged);
        assert_eq!(after.reblogs_count, 1);
    }

    #[ignore = "requires running Mastodon (repos/fediway/docker-compose.integration.yaml)"]
    #[sqlx::test]
    async fn bookmark_round_trip(pool: PgPool) {
        let token = load_token();
        let http = http_client();
        let (app, created, snowflake) = prepare(&pool, &http, &token, "integration bookmark").await;

        let resp = app
            .raw_request(authed(
                format!("/api/v1/statuses/{snowflake}/bookmark"),
                &token,
            ))
            .await;

        assert_eq!(resp.status, StatusCode::OK);
        let body = resp.json();
        assert_eq!(body["id"], snowflake.to_string());
        assert_eq!(body["bookmarked"], true);

        let after = fetch_status(&http, &token, &created.id).await;
        assert!(after.bookmarked);
    }

    #[ignore = "requires running Mastodon (repos/fediway/docker-compose.integration.yaml)"]
    #[sqlx::test]
    async fn reblog_response_wrapper_id_is_not_rewritten(pool: PgPool) {
        let token = load_token();
        let http = http_client();
        let (app, _created, snowflake) = prepare(&pool, &http, &token, "wrapper id check").await;

        let resp = app
            .raw_request(authed(
                format!("/api/v1/statuses/{snowflake}/reblog"),
                &token,
            ))
            .await;

        assert_eq!(resp.status, StatusCode::OK);
        let body = resp.json();
        let wrapper_id = body["id"].as_str().unwrap();
        let original_id = body["reblog"]["id"].as_str().unwrap();

        assert_ne!(
            wrapper_id, original_id,
            "wrapper and original must remain distinct after translation"
        );
        assert_eq!(
            original_id,
            snowflake.to_string(),
            "the original (wrapped) status is known in commonfeed and must be rewritten to its snowflake"
        );
        assert!(
            wrapper_id.parse::<i64>().is_ok() && wrapper_id.parse::<i64>().unwrap() != snowflake,
            "wrapper id must stay as Mastodon's native id — clients use it for subsequent unreblog calls"
        );
    }

    #[ignore = "requires running Mastodon (repos/fediway/docker-compose.integration.yaml)"]
    #[sqlx::test]
    async fn native_mastodon_id_falls_through(pool: PgPool) {
        let token = load_token();
        let http = http_client();

        seed_local_auth(&pool, &token).await;
        let created = create_status(&http, &token, "integration native fall-through").await;

        let app =
            common::TestApp::from_pool_with_mastodon(pool.clone(), Some(MASTODON_BASE.into()))
                .await;

        let resp = app
            .raw_request(authed(
                format!("/api/v1/statuses/{}/favourite", created.id),
                &token,
            ))
            .await;

        assert_eq!(
            resp.status,
            StatusCode::OK,
            "a caller handing us a native Mastodon id must not be 404'd by the resolver — it should fall through and let Mastodon answer"
        );
        let body = resp.json();
        assert_eq!(
            body["id"], created.id,
            "native id stays unchanged when no commonfeed mapping exists"
        );
        assert_eq!(body["favourited"], true);

        let after = fetch_status(&http, &token, &created.id).await;
        assert!(after.favourited);
        assert_eq!(after.favourites_count, 1);
    }

    #[ignore = "requires running Mastodon (repos/fediway/docker-compose.integration.yaml)"]
    #[sqlx::test]
    async fn unfavourite_toggles_off(pool: PgPool) {
        let token = load_token();
        let http = http_client();
        let (app, created, snowflake) =
            prepare(&pool, &http, &token, "integration unfavourite").await;

        let fav = app
            .raw_request(authed(
                format!("/api/v1/statuses/{snowflake}/favourite"),
                &token,
            ))
            .await;
        assert_eq!(fav.status, StatusCode::OK);
        assert_eq!(
            fetch_status(&http, &token, &created.id)
                .await
                .favourites_count,
            1
        );

        let unfav = app
            .raw_request(authed(
                format!("/api/v1/statuses/{snowflake}/unfavourite"),
                &token,
            ))
            .await;
        assert_eq!(unfav.status, StatusCode::OK);
        let body = unfav.json();
        assert_eq!(body["id"], snowflake.to_string());
        assert_eq!(body["favourited"], false);

        let after = fetch_status(&http, &token, &created.id).await;
        assert!(!after.favourited);
        assert_eq!(after.favourites_count, 0);
    }
}

mod reply {
    use super::*;

    #[ignore = "requires running Mastodon (repos/fediway/docker-compose.integration.yaml)"]
    #[sqlx::test]
    async fn reply_translates_in_reply_to_snowflake(pool: PgPool) {
        let token = load_token();
        let http = http_client();

        seed_local_auth(&pool, &token).await;
        let parent = create_status(&http, &token, "parent for reply test").await;
        let parent_mastodon_id: i64 = parent.id.parse().unwrap();

        let app =
            common::TestApp::from_pool_with_mastodon(pool.clone(), Some(MASTODON_BASE.into()))
                .await;
        let parent_snowflake = seed_commonfeed(&pool, &parent.uri).await;

        let body = json!({
            "status": "integration reply",
            "in_reply_to_id": parent_snowflake.to_string(),
            "visibility": "public",
        });
        let req = Request::post("/api/v1/statuses")
            .header("authorization", format!("Bearer {}", token.as_str()))
            .header("x-forwarded-proto", "https")
            .header("content-type", "application/json")
            .body(Body::from(body.to_string()))
            .unwrap();
        let resp = app.raw_request(req).await;

        assert_eq!(resp.status, StatusCode::OK);
        let body = resp.json();
        assert_eq!(
            body["in_reply_to_id"],
            parent_snowflake.to_string(),
            "response must surface the parent reference as our snowflake, not Mastodon's id"
        );
        assert!(body["id"].is_string());

        let parent_after = fetch_status(&http, &token, &parent.id).await;
        assert_eq!(
            parent_after.replies_count, 1,
            "parent replies_count must have incremented on Mastodon's side"
        );

        let row = state::statuses::find_by_id(&pool, parent_snowflake)
            .await
            .unwrap()
            .unwrap();
        assert_eq!(row.mastodon_local_id, Some(parent_mastodon_id));
    }

    #[ignore = "requires running Mastodon (repos/fediway/docker-compose.integration.yaml)"]
    #[sqlx::test]
    async fn reply_with_native_in_reply_to_id_passes_through(pool: PgPool) {
        let token = load_token();
        let http = http_client();

        seed_local_auth(&pool, &token).await;
        let parent = create_status(&http, &token, "parent for native pass-through").await;

        let app =
            common::TestApp::from_pool_with_mastodon(pool.clone(), Some(MASTODON_BASE.into()))
                .await;

        let body = json!({
            "status": "integration native reply",
            "in_reply_to_id": parent.id,
            "visibility": "public",
        });
        let req = Request::post("/api/v1/statuses")
            .header("authorization", format!("Bearer {}", token.as_str()))
            .header("x-forwarded-proto", "https")
            .header("content-type", "application/json")
            .body(Body::from(body.to_string()))
            .unwrap();
        let resp = app.raw_request(req).await;

        assert_eq!(resp.status, StatusCode::OK);
        let body = resp.json();
        assert_eq!(
            body["in_reply_to_id"], parent.id,
            "a client passing Mastodon's native id must get it back unchanged"
        );
    }
}

mod report {
    use super::*;

    #[ignore = "requires running Mastodon (repos/fediway/docker-compose.integration.yaml)"]
    #[sqlx::test]
    async fn report_translates_and_restores_status_ids(pool: PgPool) {
        let token = load_token();
        let http = http_client();

        seed_local_auth(&pool, &token).await;
        let a = create_status(&http, &token, "report target a").await;
        let b = create_status(&http, &token, "report target b").await;

        let app =
            common::TestApp::from_pool_with_mastodon(pool.clone(), Some(MASTODON_BASE.into()))
                .await;
        let snow_a = seed_commonfeed(&pool, &a.uri).await;
        let snow_b = seed_commonfeed(&pool, &b.uri).await;

        let me: serde_json::Value = http
            .get(format!(
                "{MASTODON_BASE}/api/v1/accounts/verify_credentials"
            ))
            .bearer_auth(token.as_str())
            .send()
            .await
            .unwrap()
            .json()
            .await
            .unwrap();
        let account_id = me["id"].as_str().unwrap().to_string();

        let body = json!({
            "account_id": account_id,
            "status_ids": [snow_a.to_string(), snow_b.to_string()],
            "comment": "integration report",
        });
        let req = Request::post("/api/v1/reports")
            .header("authorization", format!("Bearer {}", token.as_str()))
            .header("x-forwarded-proto", "https")
            .header("content-type", "application/json")
            .body(Body::from(body.to_string()))
            .unwrap();
        let resp = app.raw_request(req).await;

        assert_eq!(resp.status, StatusCode::OK);
        let report: MastodonReport =
            serde_json::from_str(&resp.body).expect("deserialize MastodonReport");

        assert_eq!(report.comment, "integration report");
        assert_eq!(report.status_ids.len(), 2);
        assert!(
            report.status_ids.contains(&snow_a.to_string()),
            "reported status ids must be surfaced to the client as snowflakes, not Mastodon ids"
        );
        assert!(report.status_ids.contains(&snow_b.to_string()));
    }
}

mod context {
    use super::*;

    #[ignore = "requires running Mastodon (repos/fediway/docker-compose.integration.yaml)"]
    #[sqlx::test]
    async fn context_post_resolve_translates_descendant_reply_ids(pool: PgPool) {
        let token = load_token();
        let http = http_client();

        seed_local_auth(&pool, &token).await;
        let parent = create_status(&http, &token, "context parent").await;
        let parent_mastodon_id: i64 = parent.id.parse().unwrap();

        let reply_resp = http
            .post(format!("{MASTODON_BASE}/api/v1/statuses"))
            .bearer_auth(token.as_str())
            .json(&json!({
                "status": "context reply",
                "in_reply_to_id": parent.id,
                "visibility": "public",
            }))
            .send()
            .await
            .unwrap();
        assert!(reply_resp.status().is_success());
        let reply: MastodonStatus = reply_resp.json().await.unwrap();

        let app =
            common::TestApp::from_pool_with_mastodon(pool.clone(), Some(MASTODON_BASE.into()))
                .await;
        let parent_snowflake = seed_commonfeed(&pool, &parent.uri).await;
        state::statuses::set_mastodon_local_id(&pool, parent_snowflake, parent_mastodon_id)
            .await
            .unwrap();

        let resp = app
            .raw_request(
                Request::get(format!("/api/v1/statuses/{parent_snowflake}/context"))
                    .header("authorization", format!("Bearer {}", token.as_str()))
                    .header("x-forwarded-proto", "https")
                    .body(Body::empty())
                    .unwrap(),
            )
            .await;

        assert_eq!(resp.status, StatusCode::OK);
        let body = resp.json();

        assert!(body["ancestors"].as_array().unwrap().is_empty());
        let descendants = body["descendants"].as_array().unwrap();
        assert_eq!(descendants.len(), 1);

        let descendant = &descendants[0];
        assert_eq!(
            descendant["id"], reply.id,
            "reply's native Mastodon id has no commonfeed mapping and must pass through unchanged"
        );
        assert_eq!(
            descendant["in_reply_to_id"],
            parent_snowflake.to_string(),
            "the in_reply_to_id pointing at our mapped parent must be rewritten to its snowflake via reverse_map"
        );
    }
}

mod detail {
    use super::*;

    #[ignore = "requires running Mastodon (repos/fediway/docker-compose.integration.yaml)"]
    #[sqlx::test]
    async fn detail_first_view_auto_resolves_and_surfaces_viewer_favourited(pool: PgPool) {
        let token = load_token();
        let http = http_client();

        seed_local_auth(&pool, &token).await;
        let created = create_status(&http, &token, "detail auto-resolve first view").await;

        let fav = http
            .post(format!(
                "{MASTODON_BASE}/api/v1/statuses/{}/favourite",
                created.id
            ))
            .bearer_auth(token.as_str())
            .send()
            .await
            .unwrap();
        assert!(fav.status().is_success());

        let app =
            common::TestApp::from_pool_with_mastodon(pool.clone(), Some(MASTODON_BASE.into()))
                .await;
        let snowflake = seed_commonfeed(&pool, &created.uri).await;

        let pre = state::statuses::find_by_id(&pool, snowflake)
            .await
            .unwrap()
            .unwrap();
        assert!(
            pre.mastodon_local_id.is_none(),
            "precondition: cached row must start unresolved"
        );

        let resp = app
            .raw_request(
                Request::get(format!("/api/v1/statuses/{snowflake}"))
                    .header("authorization", format!("Bearer {}", token.as_str()))
                    .header("x-forwarded-proto", "https")
                    .body(Body::empty())
                    .unwrap(),
            )
            .await;

        assert_eq!(resp.status, StatusCode::OK);
        let body = resp.json();
        assert_eq!(body["id"], snowflake.to_string());
        assert_eq!(
            body["favourited"], true,
            "authenticated first-view of an unresolved recommendation must auto-resolve so Mastodon's fresh per-user state can surface"
        );
        assert_eq!(body["favourites_count"], 1);

        let post = state::statuses::find_by_id(&pool, snowflake)
            .await
            .unwrap()
            .unwrap();
        assert!(
            post.mastodon_local_id.is_some(),
            "the auto-resolve side effect must persist the mapping for subsequent views"
        );
    }

    #[ignore = "requires running Mastodon (repos/fediway/docker-compose.integration.yaml)"]
    #[sqlx::test]
    async fn detail_post_resolve_returns_fresh_mastodon_counters(pool: PgPool) {
        let token = load_token();
        let http = http_client();

        seed_local_auth(&pool, &token).await;
        let created = create_status(&http, &token, "integration detail freshness").await;

        let app =
            common::TestApp::from_pool_with_mastodon(pool.clone(), Some(MASTODON_BASE.into()))
                .await;
        let snowflake = seed_commonfeed(&pool, &created.uri).await;

        let fav = app
            .raw_request(
                Request::post(format!("/api/v1/statuses/{snowflake}/favourite"))
                    .header("authorization", format!("Bearer {}", token.as_str()))
                    .header("x-forwarded-proto", "https")
                    .body(Body::empty())
                    .unwrap(),
            )
            .await;
        assert_eq!(fav.status, StatusCode::OK);

        let detail = app
            .raw_request(
                Request::get(format!("/api/v1/statuses/{snowflake}"))
                    .header("authorization", format!("Bearer {}", token.as_str()))
                    .header("x-forwarded-proto", "https")
                    .body(Body::empty())
                    .unwrap(),
            )
            .await;

        assert_eq!(detail.status, StatusCode::OK);
        let body = detail.json();
        assert_eq!(
            body["id"],
            snowflake.to_string(),
            "detail route must rewrite Mastodon's id back to our snowflake"
        );
        assert_eq!(
            body["favourites_count"], 1,
            "post-resolve detail proxy must surface the fresh counter from Mastodon, not the 0 from cached post_data"
        );
        assert_eq!(
            body["favourited"], true,
            "per-user flags come from Mastodon and must reach the client"
        );
    }
}

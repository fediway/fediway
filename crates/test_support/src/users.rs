use sqlx::PgPool;

/// A test user with a valid OAuth bearer token. Construct via [`TestUser::builder`].
pub struct TestUser {
    pub user_id: i64,
    pub account_id: i64,
    pub username: String,
    pub token: String,
}

impl TestUser {
    #[must_use]
    pub fn builder() -> TestUserBuilder {
        TestUserBuilder::default()
    }
}

/// Builder for a Mastodon-shaped test user. Defaults to a fully-functional user
/// (confirmed, approved, not disabled) with a valid, non-revoked token. Override
/// any field to test the corresponding rejection path.
// Each bool is an independent toggle, not state — a state machine would make
// the test API strictly worse, so we opt out of the pedantic lint here.
#[allow(clippy::struct_excessive_bools)]
pub struct TestUserBuilder {
    confirmed: bool,
    approved: bool,
    disabled: bool,
    suspended: bool,
    memorial: bool,
    moved: bool,
    revoked: bool,
}

impl Default for TestUserBuilder {
    fn default() -> Self {
        Self {
            confirmed: true,
            approved: true,
            disabled: false,
            suspended: false,
            memorial: false,
            moved: false,
            revoked: false,
        }
    }
}

impl TestUserBuilder {
    #[must_use]
    pub fn unconfirmed(mut self) -> Self {
        self.confirmed = false;
        self
    }

    #[must_use]
    pub fn unapproved(mut self) -> Self {
        self.approved = false;
        self
    }

    #[must_use]
    pub fn disabled(mut self) -> Self {
        self.disabled = true;
        self
    }

    #[must_use]
    pub fn suspended(mut self) -> Self {
        self.suspended = true;
        self
    }

    #[must_use]
    pub fn memorial(mut self) -> Self {
        self.memorial = true;
        self
    }

    #[must_use]
    pub fn moved(mut self) -> Self {
        self.moved = true;
        self
    }

    #[must_use]
    pub fn revoked(mut self) -> Self {
        self.revoked = true;
        self
    }

    pub async fn insert(self, pool: &PgPool) -> TestUser {
        // Process-nanos suffix keeps usernames + tokens unique within a single test.
        let nanos = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .expect("system time before epoch")
            .as_nanos();
        let username = format!("u{nanos:x}");
        let token = format!("tok_{nanos:x}");
        // Sentinel value for the "moved" case — auth only cares NULL vs non-NULL.
        let moved_to: Option<i64> = if self.moved { Some(999_999) } else { None };

        let account_id: i64 = sqlx::query_scalar(
            "INSERT INTO accounts (username, suspended_at, memorial, moved_to_account_id)
             VALUES ($1, CASE WHEN $2 THEN NOW() END, $3, $4)
             RETURNING id",
        )
        .bind(&username)
        .bind(self.suspended)
        .bind(self.memorial)
        .bind(moved_to)
        .fetch_one(pool)
        .await
        .expect("insert account");

        let user_id: i64 = sqlx::query_scalar(
            "INSERT INTO users (account_id, confirmed_at, approved, disabled)
             VALUES ($1, CASE WHEN $2 THEN NOW() END, $3, $4)
             RETURNING id",
        )
        .bind(account_id)
        .bind(self.confirmed)
        .bind(self.approved)
        .bind(self.disabled)
        .fetch_one(pool)
        .await
        .expect("insert user");

        sqlx::query(
            "INSERT INTO oauth_access_tokens (token, resource_owner_id, revoked_at, created_at, scopes)
             VALUES ($1, $2, CASE WHEN $3 THEN NOW() END, NOW(), 'read write follow')",
        )
        .bind(&token)
        .bind(user_id)
        .bind(self.revoked)
        .execute(pool)
        .await
        .expect("insert oauth token");

        TestUser {
            user_id,
            account_id,
            username,
            token,
        }
    }
}

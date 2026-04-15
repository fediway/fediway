#!/bin/bash
set -euo pipefail

USERNAME="test"
EMAIL="test@localhost"
APP_NAME="fediway-test"
TOKEN_PATH="/token/mastodon_token"

bin/tootctl accounts create "$USERNAME" \
    --email "$EMAIL" \
    --confirmed \
    --role Owner 2>/dev/null || true

bin/tootctl accounts approve "$USERNAME" 2>/dev/null || true

bin/rails runner - <<RUBY
user = User.find_by!(email: '$EMAIL')
user.update!(approved: true) unless user.approved?
user.confirm! unless user.confirmed?

app = Doorkeeper::Application.find_by(name: '$APP_NAME') ||
  Doorkeeper::Application.create!(
    name: '$APP_NAME',
    redirect_uri: 'urn:ietf:wg:oauth:2.0:oob',
    scopes: 'read write follow push'
  )

token = Doorkeeper::AccessToken.where(
  resource_owner_id: user.id,
  application_id: app.id,
  revoked_at: nil
).first || Doorkeeper::AccessToken.create!(
  resource_owner_id: user.id,
  application_id: app.id,
  scopes: 'read write follow push',
  expires_in: nil
)

File.write('$TOKEN_PATH', token.token)
File.chmod(0o644, '$TOKEN_PATH')
puts "fediway-test token written"
RUBY

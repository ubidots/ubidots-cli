# Authentication

The CLI supports two authentication methods:

- **Static token** — legacy `X-Auth-Token` header, suitable for automation scripts.
- **OAuth2 (OIDC)** — interactive browser-based login with automatic token refresh.
  Recommended for interactive use and for tools that need scoped, revocable access.

---

## OAuth2 Login

### Prerequisites

DevOps must register an OAuth2 Application in the Ubidots core before users can log in:

```bash
# Run on the core server (or via manage.py shell)
python manage.py create_oauth_application \
  --name ubidots-cli \
  --client-type public \
  --authorization-grant-type authorization-code \
  --redirect-uris "http://127.0.0.1:53682/callback" \
  --algorithm RS256
```

The `client_id` printed by this command is what users pass to `--client-id`.

> The default port `53682` is pre-registered. If your firewall blocks loopback
> connections on that port, register an additional redirect URI for the
> alternate port and pass `--port <alt-port>` at login time.

---

### Logging in

```bash
ubidots login --client-id <client-id>
```

This opens your browser to the Ubidots consent screen. After approval the CLI
exchanges the auth code for tokens and writes them to your profile.

#### Key flags

| Flag                  | Description                                                                                |
|-----------------------|--------------------------------------------------------------------------------------------|
| `--client-id <id>`    | OAuth2 `client_id`. Can also be set via `UBIDOTS_OAUTH_CLIENT_ID`.                         |
| `--profile <name>`    | Write tokens to a named profile instead of the active one.                                 |
| `--no-browser`        | Print the authorization URL instead of opening a browser. Useful in headless environments. |
| `--api-domain <url>`  | Override the Ubidots API domain (e.g. `https://cs.ubidots.site`).                          |
| `--scope <scopes>`    | Space-separated list of scopes. Default: `read write offline_access`.                      |
| `--port <port>`       | Loopback port for the OAuth callback. Default: `53682`.                                    |
| `--timeout <seconds>` | How long to wait for the browser callback. Default: `60`.                                  |

**Example — headless environment:**

```bash
# <!-- not-tested: requires manual browser step -->
ubidots login --client-id ubidots-cli --no-browser
# Prints: https://industrial.api.ubidots.com/o/authorize/?...
# Open that URL in a browser on another machine, approve, then paste the
# resulting http://127.0.0.1:53682/callback?code=... URL back into the CLI.
```

---

### Checking who you are logged in as

```bash
ubidots whoami
```

Decodes the JWT access token and prints the authenticated user's email address,
expiry, and scopes. Does not make a network call if the token is still valid.

---

### Logging out

```bash
ubidots logout
```

Revokes the refresh token on the server and clears all OAuth fields from the
active profile. Subsequent API calls will fail with a session-expired error
until you log in again.

---

### Token expiry and automatic refresh

Access tokens expire (default: 15 minutes). The CLI refreshes them
transparently before they expire — no manual intervention needed. The new
tokens are written to your profile automatically.

If the refresh token itself is revoked or has expired, the next command will
fail with:

Session expired — the CLI exits with a non-zero status and reports that the
session has expired, prompting you to re-authenticate with `ubidots login`.

---

## Troubleshooting

### Firewall blocking loopback port

The OAuth callback lands on `http://127.0.0.1:53682/callback`. If your
firewall blocks this port:

1. Choose a free port: `lsof -nP -iTCP:53682 -sTCP:LISTEN`
2. Ask DevOps to add `http://127.0.0.1:<alt-port>/callback` as an allowed
   redirect URI on the OAuth Application.
3. Login with: `ubidots login --client-id <id> --port <alt-port>`

### Browser does not open

Use `--no-browser` and open the printed URL manually:

```bash
ubidots login --client-id ubidots-cli --no-browser
```

### "client_id invalid" or "Unknown client" errors

- Confirm the `client_id` matches the one registered by DevOps exactly.
- Confirm `--api-domain` points to the correct Ubidots instance.
- Check that the OAuth Application has `Active` status in the admin.

### Session expired immediately after login

The clock on your machine or the server may be skewed. The CLI applies a
30-second leeway, but larger skews cause token validation to fail.

---

## Migrating from static tokens to OAuth2

If you previously configured a profile with a static token:

```bash
# Check current auth method
ubidots config show

# Log in with OAuth2 (overwrites the static token in the active profile)
ubidots login --client-id ubidots-cli

# Verify
ubidots whoami
```

Your static token remains stored under `access_token` in the profile YAML
until overwritten; the `auth_method` field switches to `OAUTH2` after login.

To revert to a static token:

```bash
ubidots config set auth_method TOKEN access_token <your-token>
```

---

## Profile YAML reference

OAuth2-authenticated profiles contain the following fields:

| Field             | Description                                                |
|-------------------|------------------------------------------------------------|
| `auth_method`     | `OAUTH2` when logged in via `ubidots login`.               |
| `access_token`    | JWT access token (RS256).                                  |
| `refresh_token`   | Opaque refresh token used to obtain new access tokens.     |
| `expires_at`      | Unix timestamp (int) when the access token expires.        |
| `oauth_client_id` | The `client_id` used at login.                             |
| `scope`           | Space-separated scopes granted.                            |
| `token_type`      | Always `Bearer`.                                           |
| `api_domain`      | The Ubidots API domain this profile authenticates against. |

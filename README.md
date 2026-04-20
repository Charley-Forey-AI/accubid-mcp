# Accubid MCP Server

MCP server for Accubid Anywhere APIs with Trimble Identity authentication.

## Features

- Trimble Identity auth: **server** (`client_credentials` / `authorization_code`), **delegated** (Agent Studio actor JWT + Trimble **token exchange** so outbound calls use your subscribed app), or **hybrid** (exchange when an actor token is present, else server OAuth)
- Domain tools for:
  - database
  - project
  - estimate
  - closeout
  - changeorder
  - insights
  - context
  - workflows
- Tool metadata and server capabilities in YAML
- Shared API client with retries/timeouts
- Built-in resilience with circuit breaker and optional rate limiting
- MCP resources and prompts for common Accubid workflows
- Insights and context tools for analytics and one-call data gathering
- Workflow packet tools for project and estimate readiness
- Optional namespaced tool aliases for multi-server environments
- Structured response envelope with stable error codes and request IDs
- Runtime-enriched tool discovery metadata (`required_params`, `optional_params`, alias info)

## Unblock successful Accubid calls

If Accubid returns **401 / fault `900909`** while **Postman authorization-code** tokens work against the same API paths, Trimble is rejecting the **token-exchange** bearer—the MCP HTTP stack is rarely the cause.

### Path A — Server OAuth + authorization code (recommended first)

Use the **same grant as working Postman** (direct access token for your app, no On-Behalf-Of):

1. Set **`ACCUBID_AUTH_MODE=server`** (not `delegated`).
2. Set **`ACCUBID_OAUTH_GRANT=authorization_code`**, **`CLIENT_ID`**, **`CLIENT_SECRET`**, and **`ACCUBID_SCOPE`** to match your working Postman app—include API scopes required for each area (e.g. **`anywhere-database`** for Database tools).
3. Register **`OAUTH_REDIRECT_URI`** on the Trimble app and mirror it in `.env`; run **`accubid-mcp-oauth-login`** once on the MCP host; restart the service.
4. Use MCP clients that do **not** force Agent Studio actor tokens as the Accubid bearer (or accept that Studio’s actor is not used for Accubid auth in this mode).

Outbound calls use [`auth.get_access_token()`](src/auth.py), i.e. the **stored OAuth user token**, not token exchange.

**Trade-off:** No per-request **On-Behalf-Of** identity from Agent Studio for Accubid.

### Path B — Hybrid + skip token exchange (`ACCUBID_HYBRID_ACCUBID_USE_SERVER_OAUTH`)

When Agent Studio must connect over HTTP **but** OBO tokens get **900909** while **authorization-code** tokens succeed:

1. Configure **`ACCUBID_AUTH_MODE=hybrid`** with server OAuth (`authorization_code` or `client_credentials`) as for Path A.
2. Set **`ACCUBID_HYBRID_ACCUBID_USE_SERVER_OAUTH=true`** in `.env` and restart.

The actor JWT is **still validated** so errors can include **`actor_azp`** / **`actor_sub`**; Accubid HTTP uses the **server OAuth** token only.

**Trade-off:** Accubid sees the **server** identity, not an OBO-exchanged token for the Studio actor.

### Path C — Fix delegated / OBO with Trimble

Follow [Trimble 900909 troubleshooting](#trimble-900909-subscription-inactive-troubleshooting): same **`CLIENT_ID`** as Postman, scopes, Developer Console subscription and token-exchange settings, optional **`ACCUBID_TOKEN_EXCHANGE_RESOURCE`** only if Trimble specifies it, and escalation to Trimble support with both token profiles if needed.

## Setup

1. Copy `.env.example` to `.env`.
2. Set **`ACCUBID_AUTH_MODE`** (`server`, `delegated`, or `hybrid`) and the variables below that match your deployment.
3. **Server OAuth** (`ACCUBID_AUTH_MODE=server` or for fallback in `hybrid`): set `CLIENT_ID`, `CLIENT_SECRET`, and `ACCUBID_SCOPE` (e.g. `anywhere-database` … `anywhere-changeorder`). Set **`ACCUBID_OAUTH_GRANT`** to **`client_credentials`** or **`authorization_code`** (user token file + `accubid-mcp-oauth-login`; see `.env.example`).
4. **Delegated / Agent Studio** (`ACCUBID_AUTH_MODE=delegated` or `hybrid` with actor): use **streamable HTTP** from Studio so each request carries the **On behalf of actor** JWT. Set **`CLIENT_ID`**, **`CLIENT_SECRET`**, and **`ACCUBID_SCOPE`** (same as server OAuth): the server validates the actor JWT, then calls Trimble Identity **RFC 8693 token exchange** so Accubid Anywhere receives an access token issued for **your** app (the one subscribed to the Accubid Anywhere API in the Developer Portal)—not Agent Studio’s `azp`. In the [Trimble Developer Console](https://console.trimble.com/), enable the **token exchange (On-Behalf-Of)** grant for that application. Configure **`ACCUBID_DELEGATED_ISSUER`**, optional **`ACCUBID_DELEGATED_JWKS_URL`**, **`ACCUBID_DELEGATED_AUDIENCE`**, and **`ACCUBID_DELEGATED_REQUIRED_SCOPES`**. The **`scope`** claim often lists only `accubid_agentic_ai` while Studio still shows `openid`; you may include **`openid`** in required scopes anyway—the server treats **`openid`** as satisfied when the JWT has OIDC identity claims **`iss`** and **`sub`** even if `openid` is not a token in **`scope`**.
5. Install dependencies:

```bash
pip install -e .
```

If you use **`authorization_code`** on the server, run `accubid-mcp-oauth-login` once (browser) after saving `.env`.

For local development (tests, lint, typing):

```bash
pip install -e ".[dev]"
```

### Authorization code vs token exchange (delegated)

These are **different OAuth grants**, so access tokens are **not** interchangeable by default:

| Flow | What happens | Typical use |
|------|----------------|-------------|
| **Authorization code** (e.g. Postman `/oauth/authorize` → `/oauth/token`) | User consents; Trimble issues an access token **directly** for your `client_id` and requested scopes. | Interactive login, tools like Postman. |
| **Token exchange / On-Behalf-Of** (`ACCUBID_AUTH_MODE=delegated` or `hybrid` with actor) | MCP sends the **Agent Studio actor JWT** as `subject_token` to `/oauth/token` with `grant_type=...token-exchange`; Trimble returns a **new** access token for **`CLIENT_ID`** with scopes from **`ACCUBID_SCOPE`**. | Agent Studio passes the actor token; MCP exchanges it so Accubid sees **your** subscribed app. |

**Verify before blaming “MCP vs Postman”:**

1. **`client_id` must match** — The `client_id` in your Postman authorize URL must equal **`CLIENT_ID`** in `.env`. On HTTP startup the server logs which `CLIENT_ID` is used for OBO. If Postman uses App A and MCP uses App B, one token can work at Accubid while the other returns `900909`.
2. **Decode JWTs locally** — Compare **`azp`**, **`scope`** (string claim), and **`aud`** between a **working** authorization-code access token and the **outbound** token from MCP (enable `ACCUBID_DEBUG_LOG_OUTBOUND_TOKEN` briefly). They should reflect the **same** app (`azp`) when configured correctly; differences in `scope` mean **`ACCUBID_SCOPE`** should be aligned with the authorize URL’s `scope=` plus API scopes Trimble requires (e.g. `anywhere-database`).
3. **`ACCUBID_SCOPE`** — The OBO request sends exactly the joined list from `ACCUBID_SCOPE`. Match what you request in Postman’s authorize step for overlapping scopes.

If auth-code tokens work against Accubid but OBO tokens still return **`900909`** after matching `client_id` and scopes, entitlement for **token-exchange**-issued tokens may differ from authorization-code tokens at Trimble—open a support case with both token profiles (grant type, `azp`, `scope`), not only MCP logs.

**Optional:** If Trimble Identity documentation or support specifies a **resource indicator** for token exchange (RFC 8707), set **`ACCUBID_TOKEN_EXCHANGE_RESOURCE`** (see `.env.example`). Do not guess the value; confirm with Trimble first.

**Prove the MCP stack without Studio:** Run **`ACCUBID_AUTH_MODE=server`** with **`ACCUBID_OAUTH_GRANT=authorization_code`** (same flow as Postman; token file via `accubid-mcp-oauth-login`). If that works to Accubid but delegated does not, focus on OBO configuration and Trimble portal settings for token exchange.

## Run

- STDIO:

```bash
python -m src.main
```

- HTTP:

```bash
python -m src.main --http
```

HTTP script entrypoint:

```bash
accubid-mcp-http
```

## MCP resources

The server exposes read-only resources:

- `accubid://databases`
- `accubid://databases/{database_token}/folders`
- `accubid://databases/{database_token}/folders/{parent_folder_id}`
- `accubid://databases/{database_token}/projects`
- `accubid://databases/{database_token}/projects/{project_id}`
- `accubid://databases/{database_token}/projects/{project_id}/estimates`
- `accubid://databases/{database_token}/estimates/{estimate_id}`
- `accubid://databases/{database_token}/projects/{project_id}/contracts`
- `accubid://databases/{database_token}/contracts/{contract_id}/pcos`
- `accubid://databases/{database_token}/contracts/{contract_id}/statuses`
- `accubid://databases/{database_token}/estimates/{estimate_id}/bid-breakdown-views`
- `accubid://databases/{database_token}/bid-summaries/{bid_summary_id}/final-price`
- `accubid://context/project/{database_token}/{project_id}`
- `accubid://insights/pipeline/{database_token}/{start_date}/{end_date}`

These resources are useful for lightweight cacheable reads and context hydration.

## MCP prompts

Reusable prompts are available for guided workflows:

- `bid_discovery`
- `closeout_for_estimate`
- `changeorder_flow`
- `pipeline_report`
- `full_closeout_report`
- `changeorder_summary_by_project`

## Workflows and analytics

Additional tools provide analytics and context aggregation without requiring new
Accubid endpoints:

- Insights:
  - `get_pipeline_summary`
  - `get_closeout_summary`
  - `get_changeorder_summary`
- Context:
  - `get_project_context`
  - `get_estimate_context`
- Workflows:
  - `get_project_health_packet`
  - `get_estimate_readiness_packet`

Recommended workflow chains:

1. Pipeline report:
   - `list_databases` -> `get_pipeline_summary`
2. Closeout report:
   - `get_estimate` -> `get_closeout_summary` -> `get_bid_breakdown` (optional)
3. Changeorder summary:
   - `list_contracts` -> `get_changeorder_summary`
4. Project health packet:
   - `list_databases` -> `list_projects` -> `get_project_health_packet`
5. Estimate readiness packet:
   - `get_estimate` -> `get_estimate_readiness_packet`

## Tool usage flow

Call tools in this order for most tasks:

1. `list_databases` -> get `databaseToken`
2. `list_projects` -> get `projectID`
3. `list_estimates` -> get `estimateID`
4. Use closeout/changeorder tools with IDs from previous steps

Database token and project IDs are stable and can be cached.

Many list-style tools support optional client-side pagination:

- `page_index` (0-based)
- `page_size`

List responses include a `pagination` object with `page_index`, `page_size`,
`total_count`, `total_pages`, and `has_next_page`.

High-volume list tools now also support optional query shaping:

- `search` (text search)
- `sort_by` (field alias per tool)
- `sort_direction` (`asc` or `desc`)
- `status` (for changeorder list tools where relevant)

Examples:

```bash
list_projects(database_token="...", search="tower", sort_by="name", sort_direction="asc")
list_estimates(database_token="...", project_id="...", search="phase", sort_by="due_date", sort_direction="desc")
list_pcos(database_token="...", contract_id="...", status="Open", sort_by="number", sort_direction="asc")
```

Date inputs for estimate due-date workflows accept either `yyyymmdd`,
`YYYY-MM-DD`, or `MM/DD/YYYY` and are normalized internally.

## Response contract

All tools return a consistent envelope:

```json
{
  "ok": true,
  "request_id": "uuid",
  "data": {}
}
```

Errors:

```json
{
  "ok": false,
  "request_id": "uuid",
  "error": {
    "code": "validation_error",
    "message": "..."
  }
}
```

Common error codes include `validation_error`, `auth_failed`, `api_error`, `dependency_unhealthy`, and `internal_error`.
When the API circuit breaker is open, error code `circuit_open` is returned.

## Operations runbook

- Accubid **401 / 900909** or “subscription inactive”: start with [Unblock successful Accubid calls](#unblock-successful-accubid-calls) (Path A–C).
- Verify base health:
  - `GET /health` in HTTP mode.
- Verify dependency readiness:
  - `GET /ready` in HTTP mode.
- Optional dependency validation:
  - Set `HEALTHCHECK_VERIFY_DEPENDENCIES=true` to have `/health` verify Trimble Identity.
- Startup fail-fast checks:
  - Set `STARTUP_VALIDATE_DEPENDENCIES=true` to validate identity connectivity before serving.
  - Set `STARTUP_VALIDATE_ACCUBID=true` to additionally validate Accubid API connectivity at startup/health-check.
- JSON logs:
  - Set `LOG_FORMAT=json`.
- Retry tuning:
  - `ACCUBID_CLIENT_RETRY_COUNT`
  - `ACCUBID_CLIENT_RETRY_BASE_SECONDS`
  - `ACCUBID_CLIENT_RETRY_MAX_SECONDS`
  - `ACCUBID_CLIENT_RETRYABLE_STATUS_CODES`
- Circuit breaker:
  - `ACCUBID_CIRCUIT_BREAKER_FAILURES`
  - `ACCUBID_CIRCUIT_BREAKER_COOLDOWN_SECONDS`
- Optional API rate limiting:
  - `ACCUBID_RATE_LIMIT_RPS` (0 disables)
- Standard list pagination defaults:
  - `ACCUBID_LIST_DEFAULT_PAGE_SIZE`
  - `ACCUBID_LIST_MAX_PAGE_SIZE`
- Optional short-lived cache for discovery endpoints:
  - `ACCUBID_CACHE_ENABLED`
  - `ACCUBID_CACHE_TTL_SECONDS`
  - `ACCUBID_CACHE_STATE_FILE` (optional persisted cache state file path)
- Optional tool namespacing:
  - set `ACCUBID_TOOL_NAMESPACE=accubid` to expose aliases like `accubid/list_projects`.
- Optional response key normalization:
  - set `ACCUBID_RESPONSE_SNAKE_CASE=true` to convert tool response keys to snake_case.
- Request correlation:
  - set request header `X-Request-Id` (or configure `REQUEST_ID_HEADER`) so logs and envelopes share correlation IDs.
- Metrics:
  - set `ENABLE_METRICS=true` and scrape `GET /metrics` (or `METRICS_ROUTE`).
- Domain feature flags:
  - `ACCUBID_TOOLS_DISABLE_DATABASE`
  - `ACCUBID_TOOLS_DISABLE_PROJECT`
  - `ACCUBID_TOOLS_DISABLE_ESTIMATE`
  - `ACCUBID_TOOLS_DISABLE_CLOSEOUT`
  - `ACCUBID_TOOLS_DISABLE_CHANGEORDER`
- Composed-tool performance tuning:
  - `ACCUBID_COMPOSED_TOOL_CONCURRENCY` (default `4`)
- Optional persisted circuit state file path:
  - `ACCUBID_CIRCUIT_STATE_FILE`
- Accubid Anywhere HTTP base and per-module paths: requests use `ACCUBID_API_BASE_URL` (default `https://cloud.api.trimble.com/anywhere`) plus **`/{area}/{version}`** and the documented path segment—for example `GET .../database/v1/databases`, `.../project/v2/Folders/{databaseToken}`, `.../estimate/v1/Estimate/...`, `.../closeout/v1/BidBreakdownView/...` (defaults in `ACCUBID_API_VERSION_*`; override if Trimble changes a module).
- Production safety:
  - set `ENV=production` to enforce HTTPS for `ACCUBID_API_BASE_URL`.

## Trimble 900909 (“subscription inactive”) troubleshooting

Accubid Anywhere ties **401** / fault **`900909`** (“The subscription to the API is inactive”) to the **OAuth client** on the **outbound** access token (JWT claim **`azp`** on that token), not to URL typos alone.

**Escalation checklist (Path C)**

1. **`client_id` parity** — The **`client_id`** in your Postman `/oauth/authorize` URL must equal **`CLIENT_ID`** in MCP `.env`. Different apps → different **`azp`** → different subscription.
2. **Scopes** — **`ACCUBID_SCOPE`** (used in token exchange) must include every scope you need for the APIs you call; align with your successful Postman authorize **`scope=`** plus API scopes (e.g. **`anywhere-database`**).
3. **Developer Console** — For that **`CLIENT_ID`**: Accubid Anywhere product subscribed, **token exchange (On-Behalf-Of)** enabled, scopes granted for the app.
4. **Prove it is grant-specific** — If the **same** **`CLIENT_ID`** works with **authorization-code** tokens but **token-exchange** tokens fail with **900909** after steps 1–3, contact **Trimble support** with: timestamp, **`900909`**, outbound JWT **`azp`** / **`scope`** from error details, grant type (`authorization_code` vs `token-exchange`), and **`actor_account_id`** when applicable.
5. **`ACCUBID_TOKEN_EXCHANGE_RESOURCE`** — Set **only** if Trimble Identity documentation or support gives the exact resource URI (RFC 8707); see `.env.example`.

**Delegated / hybrid with actor (default behavior)**

The MCP **exchanges** the Agent Studio actor token for a new access token using **`CLIENT_ID`** / **`CLIENT_SECRET`** (see [Trimble Identity](https://developer.trimble.com/docs/authentication/) token exchange). The Accubid API should see **`azp`** = your MCP app. If you still get **900909**:

1. In the [Trimble Developer Console](https://console.trimble.com/), open the app matching **`CLIENT_ID`** in `.env` (not Agent Studio’s client).
2. Confirm that app is **subscribed** to the **Accubid Anywhere** API products you call, and that **token exchange (On-Behalf-Of)** is allowed for the app.
3. Tool errors still include **`actor_azp`** / **`actor_sub`** from the **inbound** actor JWT for support correlation.
4. Consider **Path B** (`ACCUBID_HYBRID_ACCUBID_USE_SERVER_OAUTH`) under [Unblock successful Accubid calls](#unblock-successful-accubid-calls) if you must keep Studio HTTP but Accubid should use the server OAuth bearer like Postman.

**If you forwarded the raw actor token (older builds)**

If **`azp`** in diagnostics is Agent Studio’s app, that token was sent unchanged to Accubid; subscribe that client in the portal or upgrade to the token-exchange flow above.

Postman can succeed with a different **`client_id`** than Studio’s actor token—same user, different **`azp`** → different product entitlement until exchange is used.

## Security notes

- Never commit `.env`, `CLIENT_ID`, or `CLIENT_SECRET`.
- Prefer injecting secrets via a secure secret manager in production.
- For HTTP mode, deploy behind a reverse proxy/load balancer that terminates TLS and enforces access control and rate limiting.
- If browser-facing traffic is introduced, configure CORS policy at the reverse proxy/application edge.
- Rotate `CLIENT_SECRET` regularly and monitor token refresh behavior (`ACCUBID_TOKEN_REFRESH_BUFFER_SECONDS` and `ACCUBID_TOKEN_TTL_SECONDS`).

## Quality gates

Run before merging:

```bash
python -m ruff check .
python -m mypy src
python -m pytest
python -m pip_audit
```

Optional live integration check:

```bash
ACCUBID_INTEGRATION=1 pytest -m integration
```

## Troubleshooting

- `auth_failed`: verify `CLIENT_ID`, `CLIENT_SECRET`, `ACCUBID_SCOPE`, and `OPENID_CONFIGURATION_URL`.
- `api_error` with 429/503: tune retry/circuit-breaker settings and check upstream API health.
- `api_error` payload body missing details: long upstream payloads are intentionally truncated for safety.
- `circuit_open`: wait for cooldown or reduce failure conditions; inspect API/network status.
- timeouts: increase `ACCUBID_REQUEST_TIMEOUT_SECONDS` and verify network reachability.
- SignalR tools failing: ensure `connection_id` is valid and from an existing SignalR session (MCP does not create SignalR sessions).

## Migration notes

If you are upgrading from an earlier build:

- Reinstall with dev extras to pick up new quality tools:
  - `pip install -e ".[dev]"`
- Review new optional environment variables:
  - `ACCUBID_CACHE_STATE_FILE`
  - `ACCUBID_CIRCUIT_STATE_FILE`
  - `ACCUBID_COMPOSED_TOOL_CONCURRENCY`
- If you maintain external tool metadata snapshots, refresh them:
  - `list_available_tools` now returns runtime-enriched metadata fields.

## Notes

- Accubid requires API Data Access permissions in Accubid Anywhere Manager.
- SignalR-based extension endpoints are exposed as trigger tools and require a valid `connection_id`.

# Accubid MCP Server

MCP server for Accubid Anywhere APIs with Trimble Identity authentication.

## Features

- Trimble Identity **on-behalf-of** auth: each MCP HTTP request carries `Authorization: Bearer <actor JWT>` (e.g. from Agent Studio); the server **exchanges** it at `id.trimble.com/oauth/token` (RFC 8693) so Accubid Anywhere receives a token for **your** `CLIENT_ID`
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

## Authentication (Trimble Agent Studio)

1. **Register one OAuth application** in [Trimble Developer Console](https://console.trimble.com/) with **token exchange (On-Behalf-Of)** enabled and **Accubid Anywhere** subscribed for that app.
2. Copy `.env.example` to `.env` and set **`CLIENT_ID`**, **`CLIENT_SECRET`**, and **`ACCUBID_SCOPE`** (default `openid accubid_agentic_ai` — align with your Postman authorize `scope=` when debugging).
3. Run the MCP with **streamable HTTP** (`python -m src.main --http` or `accubid-mcp-http`). **STDIO** has no per-request HTTP headers; tools will fail without an actor Bearer.
4. Connect from **Agent Studio** so each MCP request includes **`Authorization: Bearer &lt;actor JWT&gt;`** (On behalf of actor). The server exchanges that token at **`POST {issuer}/oauth/token`** with `grant_type=urn:ietf:params:oauth:grant-type:token-exchange` and uses the returned access token for Accubid API calls.

Postman **authorization-code** tokens are issued directly to your app; the MCP path uses **token exchange** instead. Both should target the **same `CLIENT_ID`** and compatible **scopes** for Accubid to accept the outbound bearer.

## Setup

1. Copy `.env.example` to `.env` and set **`CLIENT_ID`**, **`CLIENT_SECRET`**, **`ACCUBID_SCOPE`**.
2. Install dependencies:

```bash
pip install -e .
```

For local development (tests, lint, typing):

```bash
pip install -e ".[dev]"
```

### Authorization code (Postman) vs token exchange (MCP)

| Flow | What happens |
|------|----------------|
| **Authorization code** (Postman) | User consents; Trimble issues an access token **directly** for your `client_id`. |
| **Token exchange** (this MCP) | MCP sends the **actor JWT** as `subject_token`; Trimble returns a **new** access token for **`CLIENT_ID`** with scopes from **`ACCUBID_SCOPE`**. |

**Debug:** Set **`ACCUBID_DEBUG_LOG_OUTBOUND_TOKEN=true`** briefly; compare outbound JWT **`azp`** to your Postman token. Both should be your subscribed app when **`CLIENT_ID`** matches.

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
- Optional dependency metadata:
  - Set `HEALTHCHECK_VERIFY_DEPENDENCIES=true` to have `/health` include structured checks (env is validated at import; live Accubid calls still need an actor Bearer per request).
- Startup checks:
  - Set `STARTUP_VALIDATE_DEPENDENCIES=true` to run dependency checks at startup.
  - Set `STARTUP_VALIDATE_ACCUBID=true` to note that Accubid API validation requires streamable HTTP with an actor token (see checks payload).
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

Accubid Anywhere ties **401** / fault **`900909`** to the **OAuth client** on the **outbound** access token (JWT claim **`azp`**), not to URL typos alone.

**Checklist**

1. **`client_id` parity** — Postman’s `client_id` must equal **`CLIENT_ID`** in `.env`.
2. **Scopes (most common fix)** — Token exchange sends **`ACCUBID_SCOPE`** to Trimble. If **`outbound_scope_claim`** in errors is only `accubid_agentic_ai` but Postman’s token works, your Postman **authorize URL** almost certainly includes extra scopes (e.g. **`anywhere-database`**, **`anywhere-project`**, …). Copy the **`scope=`** query value from Postman into **`ACCUBID_SCOPE`** (space-separated, same as Postman). REST endpoints such as `GET .../database/v1/databases` typically require **`anywhere-database`** in the access token, not only `accubid_agentic_ai`.
3. **Developer Console** — For **`CLIENT_ID`**: enable the same **Accubid Anywhere API products** / scopes as in Postman, and **token exchange (On-Behalf-Of)**. Restart the MCP after changing **`ACCUBID_SCOPE`** (cache keys include scope).
4. **Still failing?** — Contact **Trimble support** with outbound JWT **`azp`** / **`scope`** from tool error details.

**If `outbound_azp` already equals your `CLIENT_ID`** (token exchange succeeded) but you still get 900909, this is **not** an MCP wiring bug — it is scope or product subscription for that client vs. the API route.

**If `outbound_scope_claim` already includes `anywhere-database` and you still get 900909:** the MCP is exchanging and requesting the right scopes. Postman uses **authorization-code**; Agent Studio uses **token-exchange**. Trimble’s Accubid gateway may apply **different subscription rules** for those two grant types.

**Do not set `ACCUBID_TOKEN_EXCHANGE_RESOURCE`.** Trimble Identity returns HTTP 400: `resource parameter explicitly rejected by this IDP` — RFC 8707 resource indicators are not supported on Trimble token exchange.

**Optional:** try **`ACCUBID_TOKEN_EXCHANGE_AUDIENCE=<GUID>`** only (restart MCP). Use one value from your outbound JWT’s `aud` claim (often a second GUID beside your `client_id`), visible in tool error details as `outbound_aud`.

If Postman still works with the same `CLIENT_ID` but audience does not help, open a **Trimble support** case: compare decoded JWT from **authorization_code** vs **token_exchange** (claims `aud`, `azp`, `scope`) and the 900909 timestamp.

The MCP **exchanges** the Agent Studio actor token using **`CLIENT_ID`** / **`CLIENT_SECRET`**. Accubid should see **`azp`** = your MCP app after exchange. Tool errors include **`actor_azp`** / **`actor_sub`** (unverified decode of the inbound JWT) for diagnostics.

## Security notes

- Never commit `.env`, `CLIENT_ID`, or `CLIENT_SECRET`.
- Prefer injecting secrets via a secure secret manager in production.
- For HTTP mode, deploy behind a reverse proxy/load balancer that terminates TLS and enforces access control and rate limiting.
- If browser-facing traffic is introduced, configure CORS policy at the reverse proxy/application edge.
- Rotate `CLIENT_SECRET` regularly.

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

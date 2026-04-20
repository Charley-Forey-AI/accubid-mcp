# Changelog

## 0.3.0 - 2026-04-20

- **Breaking:** Authentication is **on-behalf-of only** (RFC 8693 token exchange). Removed `ACCUBID_AUTH_MODE`, server/hybrid OAuth, PKCE `accubid-mcp-oauth-login`, JWKS delegated validation, and `trimble-id` / `PyJWT` dependencies.
- Agent Studio must send `Authorization: Bearer` on each streamable HTTP request; `CLIENT_ID` / `CLIENT_SECRET` / `ACCUBID_SCOPE` are required in `.env`.
- Optional **`ACCUBID_TOKEN_EXCHANGE_RESOURCE`** and **`ACCUBID_TOKEN_EXCHANGE_AUDIENCE`** for Trimble token exchange when 900909 persists with correct scopes.
- HTTP shutdown: close aiohttp client in a background thread to avoid `asyncio.run()` during uvicorn’s loop (fixes “coroutine was never awaited” on SIGTERM).

## 0.2.0 - 2026-03-16

- Added structured response envelope with stable error codes and request IDs.
- Added centralized tool runtime wrapper with consistent logging and exception mapping.
- Added input validation helpers for IDs and date values.
- Added configurable retry backoff and retryable status codes.
- Added optional startup and health dependency validation checks.
- Added development quality gates (pytest, ruff, mypy) and initial test suite.
- Added CI workflow and Dockerfile for deployment readiness.
- Expanded runbook/security documentation and workspace root README.

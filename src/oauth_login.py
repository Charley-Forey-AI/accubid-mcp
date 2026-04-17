"""CLI: open browser for Trimble authorization code + PKCE and save tokens for the MCP server."""

from __future__ import annotations

import asyncio
import secrets
import webbrowser

import aiohttp
from aiohttp import web

from .config import Config
from .errors import AuthError
from .log_config import get_logger
from .oauth_flow import (
    build_authorization_url,
    exchange_authorization_code,
    fetch_openid_metadata,
    generate_pkce_pair,
    parse_redirect_binding,
    write_token_file,
)

logger = get_logger()


async def run_oauth_login() -> None:
    """Start local callback server, open authorize URL, exchange code, write token file."""
    if Config.ACCUBID_OAUTH_GRANT != "authorization_code":
        raise AuthError(
            "Set ACCUBID_OAUTH_GRANT=authorization_code in .env before running this command.",
            details={"current": Config.ACCUBID_OAUTH_GRANT},
        )

    scopes = Config.accubid_scopes()
    scope_str = " ".join(scopes)
    redirect_uri = Config.OAUTH_REDIRECT_URI
    host, port, path = parse_redirect_binding(redirect_uri)
    code_verifier, code_challenge = generate_pkce_pair()
    state = secrets.token_urlsafe(24)

    loop = asyncio.get_running_loop()
    result_future: asyncio.Future[dict[str, str]] = loop.create_future()

    async def handle_callback(request: web.Request) -> web.StreamResponse:
        if request.path != path:
            return web.Response(status=404, text="Not found")
        err = request.query.get("error")
        if err:
            if not result_future.done():
                result_future.set_exception(
                    AuthError(
                        "OAuth error from provider",
                        details={"error": err, "description": request.query.get("error_description", "")},
                    )
                )
            return web.Response(
                status=400,
                content_type="text/html",
                text=f"<html><body><p>Authorization failed: {err}</p></body></html>",
            )
        code = request.query.get("code", "")
        got_state = request.query.get("state", "")
        if got_state != state:
            if not result_future.done():
                result_future.set_exception(AuthError("OAuth state mismatch"))
            return web.Response(
                status=400,
                content_type="text/html",
                text="<html><body><p>Invalid state</p></body></html>",
            )
        if not code:
            if not result_future.done():
                result_future.set_exception(AuthError("Missing authorization code"))
            return web.Response(status=400, text="Missing code")
        if not result_future.done():
            result_future.set_result({"code": code})
        return web.Response(
            status=200,
            content_type="text/html",
            text="<html><body><p>Login successful. You can close this window.</p></body></html>",
        )

    app = web.Application()
    app.router.add_get(path, handle_callback)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    logger.info("Listening for OAuth callback on %s:%s%s", host, port, path)

    try:
        async with aiohttp.ClientSession() as session:
            meta = await fetch_openid_metadata(session, Config.OPENID_CONFIGURATION_URL)
            auth_endpoint = meta.get("authorization_endpoint")
            token_endpoint = meta.get("token_endpoint")
            if not auth_endpoint or not token_endpoint:
                raise AuthError("OpenID metadata missing authorization_endpoint or token_endpoint")

            auth_url = build_authorization_url(
                authorization_endpoint=auth_endpoint,
                client_id=Config.CLIENT_ID,
                redirect_uri=redirect_uri,
                scope=scope_str,
                state=state,
                code_challenge=code_challenge,
            )
            webbrowser.open(auth_url)
            data = await asyncio.wait_for(result_future, timeout=300.0)
            token_payload = await exchange_authorization_code(
                session,
                token_endpoint=token_endpoint,
                client_id=Config.CLIENT_ID,
                client_secret=Config.CLIENT_SECRET,
                code=data["code"],
                redirect_uri=redirect_uri,
                code_verifier=code_verifier,
            )
    finally:
        await runner.cleanup()

    access = str(token_payload.get("access_token", "")).strip()
    if not access:
        raise AuthError("Token response missing access_token", details={"keys": list(token_payload.keys())})
    refresh = token_payload.get("refresh_token")
    refresh_s = str(refresh).strip() if refresh else None
    expires_in = token_payload.get("expires_in")
    ei = int(expires_in) if isinstance(expires_in, (int, float)) else None

    out_path = Config.oauth_token_path_resolved()
    write_token_file(
        out_path,
        access_token=access,
        refresh_token=refresh_s,
        expires_in=ei,
        fallback_ttl_seconds=Config.ACCUBID_TOKEN_TTL_SECONDS,
    )
    logger.info("Saved tokens to %s", out_path)


def main() -> None:
    asyncio.run(run_oauth_login())


if __name__ == "__main__":
    main()

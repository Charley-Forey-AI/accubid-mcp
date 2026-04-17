"""Main entry point for Accubid MCP server."""

import asyncio
import atexit
import contextlib
import importlib.metadata
import os
import signal
import sys
from dataclasses import dataclass
from typing import Any, Callable, Coroutine

from fastmcp import FastMCP
from fastmcp.server.dependencies import get_http_request
from fastmcp.server.middleware.middleware import CallNext, Middleware, MiddlewareContext

from .auth import AccubidAuth
from .client import AccubidClient
from .config import Config
from .errors import AuthError, DependencyCheckError
from .log_config import get_logger, setup_logging
from .metrics import render_metrics
from .observability import clear_request_id, error_response, success_response
from .prompts import register_prompts
from .registry import load_capabilities, search_tools
from .resources import register_resources
from .tool_runtime import execute_tool
from .tools import register_tools

setup_logging()
logger = get_logger()

class RequestIdMiddleware(Middleware):
    """Propagate request ID from HTTP headers when present."""

    async def on_message(self, context: MiddlewareContext[object], call_next: CallNext) -> object:
        from .observability import set_request_id

        header_name = Config.REQUEST_ID_HEADER
        try:
            with contextlib.suppress(Exception):
                request = get_http_request()
                request_id = (
                    request.headers.get(header_name) or request.headers.get("x-correlation-id") or ""
                ).strip()
                if request_id:
                    set_request_id(request_id)
            return await call_next(context)
        finally:
            clear_request_id()


def _app_version() -> str:
    if Config.APP_VERSION:
        return Config.APP_VERSION
    with contextlib.suppress(Exception):
        return importlib.metadata.version("accubid-mcp")
    return "unknown"


@dataclass
class AppContainer:
    mcp: FastMCP
    auth: AccubidAuth
    client: AccubidClient
    list_available_tools: Any
    run_dependency_checks: Callable[[], Coroutine[Any, Any, dict]]


def create_app() -> AppContainer:
    """Create a fully wired MCP app container."""
    mcp = FastMCP("accubid-mcp")
    auth = AccubidAuth()
    client = AccubidClient(auth)
    register_tools(mcp, client)
    register_resources(mcp, client)
    register_prompts(mcp)
    mcp.add_middleware(RequestIdMiddleware())

    @mcp.tool()
    async def list_available_tools(domain: str = "", query: str = "") -> dict:
        """Discover available tools by domain and keyword search."""
        return await execute_tool(
            "list_available_tools",
            lambda: _list_available_tools(domain=domain, query=query),
            context={"domain": domain, "query": query},
        )

    async def _list_available_tools(domain: str = "", query: str = "") -> dict:
        tools = search_tools(query=query or None, domain=domain or None)
        namespace = Config.ACCUBID_TOOL_NAMESPACE
        if namespace:
            namespace_prefix = f"{namespace}/"
            namespaced_tools = [tool for tool in tools if str(tool.get("name", "")).startswith(namespace_prefix)]
            if namespaced_tools:
                tools = namespaced_tools
            else:
                prefixed: list[dict[str, Any]] = []
                for tool in tools:
                    tool_copy = dict(tool)
                    name = str(tool_copy.get("name", ""))
                    if "/" not in name:
                        tool_copy["name"] = f"{namespace}/{name}"
                    prefixed.append(tool_copy)
                tools = prefixed
        return {"tools": tools}

    async def _run_dependency_checks() -> dict:
        try:
            await auth.get_access_token()
            checks: dict[str, str] = {"trimble_identity": "ok"}
            if Config.STARTUP_VALIDATE_ACCUBID:
                await client.get_databases()
                checks["accubid_api"] = "ok"
            return checks
        except Exception as exc:
            raise DependencyCheckError(
                "Dependency health check failed",
                details={"cause": str(exc)},
            ) from exc

    @mcp.custom_route("/health", methods=["GET"])
    async def health_check(_request):
        """Return service health and server capabilities."""
        from starlette.responses import JSONResponse

        base_payload = {
            "capabilities": load_capabilities(),
            "api_base_url": Config.ACCUBID_API_BASE_URL,
            "version": _app_version(),
        }
        try:
            if not Config.HEALTHCHECK_VERIFY_DEPENDENCIES:
                payload = success_response({"status": "ok", **base_payload})
                return JSONResponse(payload)

            try:
                checks = await _run_dependency_checks()
                payload = success_response({"status": "ok", "checks": checks, **base_payload})
                return JSONResponse(payload)
            except DependencyCheckError as exc:
                payload = error_response(exc)
                payload["data"] = {"status": "degraded", **base_payload}
                return JSONResponse(payload, status_code=503)
        finally:
            clear_request_id()

    @mcp.custom_route("/ready", methods=["GET"])
    async def readiness_check(_request):
        """Readiness probe that validates external dependencies."""
        from starlette.responses import JSONResponse

        try:
            checks = await _run_dependency_checks()
            payload = success_response({"status": "ready", "checks": checks, "version": _app_version()})
            return JSONResponse(payload)
        except DependencyCheckError as exc:
            payload = error_response(exc)
            payload["data"] = {"status": "not_ready", "version": _app_version()}
            return JSONResponse(payload, status_code=503)
        finally:
            clear_request_id()

    @mcp.custom_route(Config.METRICS_ROUTE, methods=["GET"])
    async def metrics(_request):
        """Prometheus metrics endpoint."""
        from starlette.responses import Response

        if not Config.ENABLE_METRICS:
            return Response(status_code=404, content="metrics disabled")
        body, content_type = render_metrics()
        return Response(content=body, media_type=content_type)

    return AppContainer(
        mcp=mcp,
        auth=auth,
        client=client,
        list_available_tools=list_available_tools,
        run_dependency_checks=_run_dependency_checks,
    )


app = create_app()
mcp = app.mcp
auth = app.auth
client = app.client
list_available_tools = app.list_available_tools


def _mcp_http_kwargs() -> dict:
    host = os.getenv("MCP_HOST", "0.0.0.0").strip()
    port = int(os.getenv("MCP_PORT", "8000"))
    path = os.getenv("MCP_HTTP_PATH", "mcp").strip().strip("/")
    return {"transport": "streamable-http", "host": host, "port": port, "path": f"/{path}"}


def _close_client_sync() -> None:
    with contextlib.suppress(Exception):
        asyncio.run(app.client.close())


def run() -> None:
    """Run in STDIO mode."""
    app.mcp.run()


def run_http() -> None:
    """Run in streamable HTTP mode."""
    kwargs = _mcp_http_kwargs()
    atexit.register(_close_client_sync)
    signal.signal(signal.SIGTERM, lambda *_args: _close_client_sync())
    signal.signal(signal.SIGINT, lambda *_args: _close_client_sync())
    logger.info("Starting HTTP server on %s:%s%s", kwargs["host"], kwargs["port"], kwargs["path"])
    http_app = app.mcp.http_app(path=kwargs["path"], transport="streamable-http")
    if Config.MCP_CORS_ORIGINS:
        from starlette.middleware.cors import CORSMiddleware

        origins = [origin.strip() for origin in Config.MCP_CORS_ORIGINS.split(",") if origin.strip()]
        http_app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    import uvicorn

    uvicorn.run(http_app, host=kwargs["host"], port=kwargs["port"])


def main() -> None:
    """CLI dispatch. Default STDIO; pass --http for HTTP transport."""
    if Config.STARTUP_VALIDATE_DEPENDENCIES:
        try:
            asyncio.run(app.run_dependency_checks())
        except DependencyCheckError as exc:
            # Authorization-code mode: missing token file / failed refresh raises AuthError and would
            # exit before uvicorn binds (nginx 502). Allow the server to start so /health and MCP work
            # once tokens exist at OAUTH_TOKEN_PATH.
            if Config.ACCUBID_OAUTH_GRANT == "authorization_code" and isinstance(exc.__cause__, AuthError):
                cause = str((exc.details or {}).get("cause", exc))
                logger.warning(
                    "Startup dependency check skipped (authorization_code / AuthError): %s. "
                    "Server starting; set tokens at %s or run accubid-mcp-oauth-login.",
                    cause,
                    Config.oauth_token_path_resolved(),
                )
            else:
                raise
        else:
            logger.info("Startup dependency checks passed.")
    if "--http" in sys.argv:
        run_http()
    else:
        run()


if __name__ == "__main__":
    try:
        main()
    finally:
        try:
            asyncio.run(app.client.close())
        except RuntimeError:
            pass

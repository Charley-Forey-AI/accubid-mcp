"""Trimble Identity OAuth2 authorization-code + PKCE helpers and token persistence."""

from __future__ import annotations

import base64
import contextlib
import hashlib
import json
import os
import secrets
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlencode, urlparse

from aiohttp import ClientSession

from .errors import AuthError


def generate_pkce_pair() -> tuple[str, str]:
    """Return (code_verifier, code_challenge) for S256 PKCE."""
    verifier = secrets.token_urlsafe(64).rstrip("=")[:128]
    if len(verifier) < 43:
        verifier = secrets.token_urlsafe(48).rstrip("=")
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return verifier, challenge


async def fetch_openid_metadata(session: ClientSession, openid_configuration_url: str) -> dict[str, Any]:
    async with session.get(openid_configuration_url) as response:
        if response.status != 200:
            text = await response.text()
            raise AuthError(
                "Failed to load OpenID configuration",
                details={"status": response.status, "body": text[:512]},
            )
        return await response.json()


def build_authorization_url(
    *,
    authorization_endpoint: str,
    client_id: str,
    redirect_uri: str,
    scope: str,
    state: str,
    code_challenge: str,
) -> str:
    q = urlencode(
        {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": scope,
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
    )
    return f"{authorization_endpoint}?{q}"


async def post_token_form(session: ClientSession, token_endpoint: str, form: dict[str, str]) -> dict[str, Any]:
    body = urlencode(form)
    headers = {"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"}
    async with session.post(token_endpoint, data=body, headers=headers) as response:
        text = await response.text()
        if response.status != 200:
            raise AuthError(
                "Token endpoint request failed",
                details={"status": response.status, "body": text[:2048]},
            )
        return json.loads(text)


async def exchange_authorization_code(
    session: ClientSession,
    *,
    token_endpoint: str,
    client_id: str,
    client_secret: str,
    code: str,
    redirect_uri: str,
    code_verifier: str,
) -> dict[str, Any]:
    form = {
        "grant_type": "authorization_code",
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
        "redirect_uri": redirect_uri,
        "code_verifier": code_verifier,
    }
    return await post_token_form(session, token_endpoint, form)


async def refresh_access_token(
    session: ClientSession,
    *,
    token_endpoint: str,
    client_id: str,
    client_secret: str,
    refresh_token: str,
    scope: str,
) -> dict[str, Any]:
    form = {
        "grant_type": "refresh_token",
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
    }
    if scope:
        form["scope"] = scope
    return await post_token_form(session, token_endpoint, form)


def parse_redirect_binding(redirect_uri: str) -> tuple[str, int, str]:
    """Return (host, port, path) for the local callback server."""
    parsed = urlparse(redirect_uri)
    host = parsed.hostname or "127.0.0.1"
    if parsed.port:
        port = parsed.port
    elif parsed.scheme == "https":
        port = 443
    else:
        port = 80
    path = parsed.path or "/"
    if not path.startswith("/"):
        path = "/" + path
    return host, port, path


def read_token_file(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def write_token_file(
    path: Path,
    *,
    access_token: str,
    refresh_token: str | None,
    expires_in: int | None,
    fallback_ttl_seconds: int,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    now = time.time()
    if expires_in and expires_in > 0:
        expires_at = now + float(expires_in)
    else:
        expires_at = now + float(fallback_ttl_seconds)
    payload = {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_at": expires_at,
    }
    text = json.dumps(payload)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)
    with contextlib.suppress(OSError):
        os.chmod(path, 0o600)

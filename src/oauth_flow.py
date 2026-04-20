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


def looks_like_jwt(token: str) -> bool:
    """True if token looks like a JWT (three base64url segments, header has alg).

    Trimble Identity often expects ``subject_token_type`` JWT for token exchange;
    opaque access tokens use ``access_token`` type instead.
    """
    if not token or not isinstance(token, str):
        return False
    parts = token.strip().split(".")
    if len(parts) != 3:
        return False
    try:
        segment = parts[0].strip()
        pad = 4 - (len(segment) % 4)
        if pad != 4:
            segment += "=" * pad
        decoded = base64.urlsafe_b64decode(segment)
        header = json.loads(decoded.decode("utf-8"))
        return isinstance(header, dict) and "alg" in header
    except Exception:
        return False


async def exchange_on_behalf_of(
    session: ClientSession,
    *,
    token_endpoint: str,
    client_id: str,
    client_secret: str,
    subject_token: str,
    scope: str,
    resource: str | None = None,
) -> dict[str, Any]:
    """RFC 8693-style token exchange at Trimble ``/oauth/token`` (On-Behalf-Of).

    Uses HTTP Basic ``client_id:client_secret``. Tries JWT ``subject_token_type`` when the
    subject looks like a JWT; otherwise ``access_token``. Retries once with JWT type on
    ``400`` + ``not supported`` when the first attempt used ``access_token`` type.

    If ``resource`` is set (RFC 8707 resource indicator), it is included in the token request.

    Returns the parsed JSON object (must include ``access_token``). Raises :class:`AuthError`
    on failure (no fallback).
    """
    credentials = f"{client_id}:{client_secret}"
    encoded = base64.b64encode(credentials.encode()).decode()
    auth_header = f"Basic {encoded}"
    headers = {
        "Authorization": auth_header,
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
    }

    use_jwt_type = looks_like_jwt(subject_token)
    subject_token_type = (
        "urn:ietf:params:oauth:token-type:jwt"
        if use_jwt_type
        else "urn:ietf:params:oauth:token-type:access_token"
    )

    async def do_exchange(stype: str) -> tuple[int, str]:
        form: dict[str, str] = {
            "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
            "subject_token": subject_token,
            "subject_token_type": stype,
            "scope": scope,
        }
        if resource:
            form["resource"] = resource
        body = urlencode(form)
        async with session.post(token_endpoint, data=body, headers=headers) as response:
            return response.status, await response.text()

    def _parse_success(response_text: str) -> dict[str, Any]:
        try:
            token_data: dict[str, Any] = json.loads(response_text)
        except json.JSONDecodeError as exc:
            raise AuthError(
                "Token exchange response was not valid JSON",
                details={"body": response_text[:2048]},
            ) from exc
        if "error" in token_data:
            desc = str(
                token_data.get("error_description") or token_data.get("error") or "Unknown error"
            )
            raise AuthError(
                "Token exchange error",
                details={"error": token_data.get("error"), "error_description": desc[:2048]},
            )
        access = token_data.get("access_token") or token_data.get("AccessToken")
        if not access or not str(access).strip():
            raise AuthError(
                "Token exchange response missing access_token",
                details={"keys": list(token_data.keys())},
            )
        return token_data

    status, response_text = await do_exchange(subject_token_type)
    if status == 200:
        return _parse_success(response_text)

    if (
        status == 400
        and "not supported" in response_text.lower()
        and not use_jwt_type
        and looks_like_jwt(subject_token)
    ):
        status, response_text = await do_exchange("urn:ietf:params:oauth:token-type:jwt")
        if status == 200:
            return _parse_success(response_text)

    msg_lower = response_text.lower()
    if "signature verification failed" in msg_lower:
        raise AuthError(
            "On-behalf-of token exchange failed: JWT signature verification failed. "
            "The subject token was not issued or cannot be verified by this Trimble Identity environment. "
            "Ensure OPENID_CONFIGURATION_URL matches the environment that issued the token.",
            details={"status": status, "body": response_text[:2048]},
        )
    if "intended audience" in msg_lower or "not the intended audience" in msg_lower:
        raise AuthError(
            "On-behalf-of token exchange failed: caller is not the intended audience of the subject token. "
            "Ensure CLIENT_ID matches the MCP application registered for token exchange in Trimble Developer Console.",
            details={"status": status, "body": response_text[:2048]},
        )
    if status == 400 and ("unsupported_grant_type" in msg_lower or "invalid_grant" in msg_lower):
        raise AuthError(
            "On-behalf-of token exchange rejected by Trimble Identity. "
            "Enable the token exchange (On-Behalf-Of) grant for this application in the Trimble Developer Console "
            "and ensure ACCUBID_SCOPE includes the scopes your app is allowed to request.",
            details={"status": status, "body": response_text[:2048]},
        )
    raise AuthError(
        f"On-behalf-of token exchange failed with HTTP {status}",
        details={"status": status, "body": response_text[:2048]},
    )


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

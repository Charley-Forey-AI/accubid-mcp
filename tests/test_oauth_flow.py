"""Tests for OAuth PKCE helpers."""

from pathlib import Path

import pytest

from src.oauth_flow import (
    generate_pkce_pair,
    oauth_login_listen_target,
    parse_redirect_binding,
    read_token_file,
    write_token_file,
)


def test_pkce_verifier_and_challenge_differ_and_length() -> None:
    v, c = generate_pkce_pair()
    assert v != c
    assert len(v) >= 43
    assert len(c) >= 43


def test_parse_redirect_binding() -> None:
    host, port, path = parse_redirect_binding("http://127.0.0.1:8765/oauth/callback")
    assert host == "127.0.0.1"
    assert port == 8765
    assert path == "/oauth/callback"


def test_oauth_login_listen_target_loopback() -> None:
    bind, port, path = oauth_login_listen_target("http://127.0.0.1:8765/oauth/callback")
    assert bind == "127.0.0.1"
    assert port == 8765
    assert path == "/oauth/callback"
    bind2, _, _ = oauth_login_listen_target("http://localhost:9999/cb")
    assert bind2 == "127.0.0.1"


def test_oauth_login_listen_target_rejects_external_host() -> None:
    with pytest.raises(ValueError, match="loopback"):
        oauth_login_listen_target("https://flows.ai.trimble.com/rest/oauth2-credential/callback")


def test_write_and_read_token_file(tmp_path: Path) -> None:
    p = tmp_path / "t.json"
    write_token_file(
        p,
        access_token="a",
        refresh_token="r",
        expires_in=3600,
        fallback_ttl_seconds=60,
    )
    data = read_token_file(p)
    assert data is not None
    assert data["access_token"] == "a"
    assert data["refresh_token"] == "r"
    assert data["expires_at"] > 0

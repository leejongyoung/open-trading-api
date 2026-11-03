import os
import sys

import pytest
from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import server  # noqa: E402


def test_default_host_is_loopback(monkeypatch):
    monkeypatch.delenv("MCP_HOST", raising=False)
    assert server.get_bind_host() == "127.0.0.1"


def test_host_env_override(monkeypatch):
    monkeypatch.setenv("MCP_HOST", "0.0.0.0")
    assert server.get_bind_host() == "0.0.0.0"


def test_cors_defaults_not_wildcard(monkeypatch):
    monkeypatch.delenv("MCP_CORS_ORIGINS", raising=False)
    assert "*" not in server.get_cors_origins()


def test_cors_env_list(monkeypatch):
    monkeypatch.setenv("MCP_CORS_ORIGINS", "https://a.example, https://b.example")
    assert server.get_cors_origins() == ["https://a.example", "https://b.example"]


def _app(token):
    async def ok(request):
        return JSONResponse({"ok": True})

    app = Starlette(routes=[Route("/mcp", ok, methods=["GET", "POST"]), Route("/health", ok)])
    app.add_middleware(server.BearerAuthMiddleware, token=token)
    app.add_middleware(
        CORSMiddleware, allow_origins=["http://localhost"], allow_methods=["GET", "POST", "OPTIONS"], allow_headers=["*"]
    )
    return TestClient(app)


def test_auth_rejects_missing_and_wrong_token():
    c = _app("s3cret")
    assert c.get("/mcp").status_code == 401
    assert c.get("/mcp", headers={"Authorization": "Bearer nope"}).status_code == 401


def test_auth_accepts_token_and_health_exempt():
    c = _app("s3cret")
    assert c.get("/mcp", headers={"Authorization": "Bearer s3cret"}).status_code == 200
    assert c.get("/health").status_code == 200


def test_preflight_bypasses_auth_and_cors_restricted():
    c = _app("s3cret")
    r = c.options("/mcp", headers={"Origin": "http://localhost", "Access-Control-Request-Method": "POST"})
    assert r.status_code == 200
    assert r.headers["access-control-allow-origin"] == "http://localhost"
    r = c.options("/mcp", headers={"Origin": "http://evil.example", "Access-Control-Request-Method": "POST"})
    assert "access-control-allow-origin" not in r.headers


def test_path_segment_allows_plain_names():
    assert server._is_safe_segment("domestic_stock") is True
    assert server._is_safe_segment("order_cash") is True


def test_path_segment_rejects_traversal_and_query():
    assert server._is_safe_segment("../secret") is False
    assert server._is_safe_segment("a?b") is False
    assert server._is_safe_segment("a/b") is False
    assert server._is_safe_segment("") is False
    assert server._is_safe_segment("a b") is False


def test_resource_rejects_unsafe_segments():
    assert server._kis_api_main_file.fn("../x", "order_cash") == "❌ 잘못된 파라미터"
    assert server._kis_api_check_file.fn("domestic_stock", "a/b") == "❌ 잘못된 파라미터"

"""이슈 #22 회귀 테스트: GET 자동 로그인 금지, Host/Origin 검증, 실전 주문 게이트.

KIS API를 호출하지 않는다. kis_auth는 import 시점에 설정 파일을 읽으므로
가짜 모듈로 대체한다. 인증이 필요한 경로는 라우터 모듈의 가드를 monkeypatch한다.
"""

import sys
import types

import pytest
from fastapi.testclient import TestClient


def _install_kis_auth_stub():
    stub = types.ModuleType("kis_auth")
    stub.__getattr__ = lambda name: None  # noqa: B023
    sys.modules["kis_auth"] = stub


_install_kis_auth_stub()

from backend import security  # noqa: E402
from backend.security import (  # noqa: E402
    check_real_order_limits,
    is_allowed_origin,
    is_valid_stock_code,
    real_orders_allowed,
)


def test_stock_code_format():
    assert is_valid_stock_code("005930") is True
    assert is_valid_stock_code("00593") is False
    assert is_valid_stock_code("../../etc") is False
    assert is_valid_stock_code("005930 ") is False
    assert is_valid_stock_code("") is False
    assert is_valid_stock_code(None) is False


def test_origin_policy():
    assert is_allowed_origin(None) is True  # 비브라우저 클라이언트
    assert is_allowed_origin("http://localhost:3000") is True
    assert is_allowed_origin("http://127.0.0.1:8000") is True
    assert is_allowed_origin("https://evil.example") is False
    assert is_allowed_origin("http://localhost.evil.example") is False


def test_real_order_opt_in(monkeypatch):
    monkeypatch.setenv("STRATEGY_ALLOW_REAL_ORDERS", "1")
    assert real_orders_allowed() is True
    monkeypatch.setenv("STRATEGY_ALLOW_REAL_ORDERS", "0")
    assert real_orders_allowed() is False


def test_real_order_limits():
    assert check_real_order_limits(1, 1000) is None
    assert "상한" in check_real_order_limits(security.MAX_REAL_ORDER_QTY + 1, 1000)
    assert "상한" in check_real_order_limits(1, security.MAX_REAL_ORDER_AMOUNT + 1)
    # 시장가(가격 미상)는 수량만 검사
    assert check_real_order_limits(security.MAX_REAL_ORDER_QTY, None) is None


@pytest.fixture()
def client():
    from backend.main import app

    with TestClient(app) as c:
        yield c


def test_untrusted_host_rejected(client):
    r = client.get("/api/health", headers={"host": "evil.example"})
    assert r.status_code == 400


def test_health_ok_from_testserver(client):
    assert client.get("/api/health").status_code == 200


def test_price_does_not_auto_login(client):
    import backend as backend_pkg

    assert backend_pkg.is_authenticated() is False
    r = client.get("/api/market/price/005930?env_dv=prod")
    assert r.json()["status"] == "error"
    # GET 한 번으로 로그인 상태가 되면 안 된다
    assert backend_pkg.is_authenticated() is False


def test_price_rejects_bad_stock_code(client):
    r = client.get("/api/market/price/abc")
    assert r.json()["message"] == "종목코드는 6자리 숫자여야 합니다"
    # 경로 구분자가 든 값은 라우팅 단계에서 404로 거부된다
    assert client.get("/api/market/price/..%2F..%2Fx").status_code == 404


def test_websocket_rejects_bad_stock_code(client):
    with pytest.raises(Exception):
        with client.websocket_connect("/api/market/ws/abc"):
            pass


def test_websocket_rejects_evil_origin(client):
    with pytest.raises(Exception):
        with client.websocket_connect(
            "/api/market/ws/005930", headers={"origin": "https://evil.example"}
        ):
            pass


def test_execute_real_mode_requires_opt_in(client, monkeypatch):
    import backend.routers.orders as orders

    monkeypatch.setattr(orders, "is_authenticated", lambda: True)
    monkeypatch.setattr(orders, "get_current_mode", lambda: "prod")
    monkeypatch.delenv("STRATEGY_ALLOW_REAL_ORDERS", raising=False)
    r = client.post(
        "/api/orders/execute",
        json={
            "stock_code": "005930",
            "stock_name": "삼성전자",
            "action": "BUY",
            "order_type": "limit",
            "price": 70000,
            "quantity": 1,
            "signal_reason": "test",
        },
    )
    assert "STRATEGY_ALLOW_REAL_ORDERS" in r.json()["message"]

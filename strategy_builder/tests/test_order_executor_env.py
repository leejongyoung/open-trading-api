"""이슈 #20 회귀 테스트: prod 모드가 실전 TR ID를 쓰는지, 허용 밖 환경은 거부하는지.

KIS API를 호출하지 않는다. kis_auth는 import 시점에 설정 파일을 읽으므로
가짜 모듈로 대체하고, pandas 등 나머지 의존성은 실제 것을 쓴다.
"""

import sys
import types

import pytest


def _install_kis_auth_stub():
    stub = types.ModuleType("kis_auth")
    stub.__getattr__ = lambda name: None  # noqa: B023
    sys.modules["kis_auth"] = stub


_install_kis_auth_stub()

from core.order_executor import OrderExecutor, is_real_env, resolve_order_tr_id  # noqa: E402
from core.signal import Action  # noqa: E402


@pytest.mark.parametrize(
    ("env_dv", "expected"),
    [("real", True), ("prod", True), ("demo", False), ("vps", False)],
)
def test_is_real_env_normalizes_router_modes(env_dv, expected):
    assert is_real_env(env_dv) is expected


@pytest.mark.parametrize("env_dv", ["", "paper", "REAL", "test", None])
def test_is_real_env_rejects_unknown(env_dv):
    with pytest.raises(ValueError):
        is_real_env(env_dv)


@pytest.mark.parametrize(
    ("env_dv", "action", "expected"),
    [
        ("real", Action.BUY, "TTTC0012U"),
        ("real", Action.SELL, "TTTC0011U"),
        ("prod", Action.BUY, "TTTC0012U"),  # 라우터가 넘기는 값. 과거에는 VTTC가 선택됨
        ("prod", Action.SELL, "TTTC0011U"),
        ("demo", Action.BUY, "VTTC0012U"),
        ("demo", Action.SELL, "VTTC0011U"),
        ("vps", Action.BUY, "VTTC0012U"),
        ("vps", Action.SELL, "VTTC0011U"),
    ],
)
def test_resolve_order_tr_id_matches_reference(env_dv, action, expected):
    assert resolve_order_tr_id(env_dv, action) == expected


def test_executor_normalizes_prod_to_real():
    ex = OrderExecutor(env_dv="prod")
    assert ex.is_real is True
    ex = OrderExecutor(env_dv="vps")
    assert ex.is_real is False


def test_executor_rejects_unknown_env():
    with pytest.raises(ValueError):
        OrderExecutor(env_dv="paper")

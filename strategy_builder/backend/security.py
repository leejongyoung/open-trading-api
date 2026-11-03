"""로컬 API 서버 측 보안 가드 (이슈 #22).

- 브라우저가 아닌 호출자는 Origin을 보내지 않으므로 None은 허용하고,
  브라우저 Origin은 localhost 계열만 허용한다 (DNS rebinding 완화).
- 실전(prod) 주문·취소는 명시 옵트인(STRATEGY_ALLOW_REAL_ORDERS=1)이 있을 때만
  실행하고, 수량·금액 상한을 둔다. 모의(vps) 주문에는 상한을 적용하지 않는다.
"""

import os
import re
import threading

_STOCK_CODE_RE = re.compile(r"\d{6}")

_LOCAL_ORIGIN_RE = re.compile(
    r"https?://(localhost|127\.0\.0\.1|\[::1\])(:\d+)?/?$"
)

# 실전 주문 상한 (환경변수로 조정 가능)
MAX_REAL_ORDER_QTY = int(os.getenv("STRATEGY_MAX_ORDER_QTY", "100"))
MAX_REAL_ORDER_AMOUNT = int(os.getenv("STRATEGY_MAX_ORDER_AMOUNT", "10000000"))


def is_valid_stock_code(stock_code: str) -> bool:
    """종목코드는 6자리 숫자만 허용한다."""
    return isinstance(stock_code, str) and _STOCK_CODE_RE.fullmatch(stock_code) is not None


def get_trusted_hosts() -> list:
    """TrustedHostMiddleware 허용 호스트. testserver는 FastAPI TestClient용."""
    extra = [
        h.strip() for h in os.getenv("STRATEGY_TRUSTED_HOSTS", "").split(",") if h.strip()
    ]
    return ["127.0.0.1", "localhost", "testserver"] + extra


def is_allowed_origin(origin: str | None) -> bool:
    """WS/브라우저 Origin 검사. Origin이 없으면(비브라우저 클라이언트) 허용."""
    if not origin:
        return True
    return _LOCAL_ORIGIN_RE.match(origin.strip()) is not None


def real_orders_allowed() -> bool:
    """실전 주문 명시 옵트인 여부."""
    return os.getenv("STRATEGY_ALLOW_REAL_ORDERS", "0") == "1"


def is_real_mode(env_dv: str) -> bool:
    return env_dv in ("real", "prod")


def check_real_order_limits(quantity: int, price: int | None) -> str | None:
    """실전 주문 상한 검사. 위반 시 사유 문자열, 통과 시 None."""
    if quantity > MAX_REAL_ORDER_QTY:
        return (
            f"실전 주문 수량 상한({MAX_REAL_ORDER_QTY}주)을 초과했습니다: {quantity}주"
        )
    if price is not None and price * quantity > MAX_REAL_ORDER_AMOUNT:
        return (
            "실전 주문 금액 상한"
            f"({MAX_REAL_ORDER_AMOUNT:,}원)을 초과했습니다: {price * quantity:,}원"
        )
    return None


class WebSocketSubscriptionGuard:
    """WS 구독 수 상한 (무제한 폴링 태스크 생성 방지)."""

    def __init__(self, limit: int = 20):
        self._limit = limit
        self._count = 0
        self._lock = threading.Lock()

    def acquire(self) -> bool:
        with self._lock:
            if self._count >= self._limit:
                return False
            self._count += 1
            return True

    def release(self) -> None:
        with self._lock:
            self._count = max(0, self._count - 1)


ws_subscription_guard = WebSocketSubscriptionGuard()

import time
import os
import threading
from typing import Callable, Dict, List
from collections import defaultdict
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse

from backend.app.config import settings


class RateLimiter(BaseHTTPMiddleware):
    def __init__(self, app, requests_per_minute: int = None):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute or settings.rate_limit.per_minute
        self.window_size: int = 60
        self._requests: Dict[str, List[float]] = defaultdict(list)
        self._lock = threading.Lock()

    def _get_client_ip(self, request: Request) -> str:
        x_forwarded_for = request.headers.get("x-forwarded-for")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()

        x_real_ip = request.headers.get("x-real-ip")
        if x_real_ip:
            return x_real_ip

        if request.client:
            return request.client.host

        return "unknown"

    def _is_rate_limited(self, client_ip: str) -> bool:
        current_time = time.time()
        window_start = current_time - self.window_size

        with self._lock:
            request_times = self._requests[client_ip]

            request_times = [t for t in request_times if t > window_start]
            self._requests[client_ip] = request_times

            if len(request_times) >= self.requests_per_minute:
                return True

            request_times.append(current_time)
            return False

    def _get_retry_after(self, client_ip: str) -> int:
        current_time = time.time()
        window_start = current_time - self.window_size

        with self._lock:
            request_times = self._requests[client_ip]
            valid_times = [t for t in request_times if t > window_start]

            if not valid_times:
                return 0

            oldest_request = min(valid_times)
            retry_after = int(oldest_request + self.window_size - current_time)
            return max(1, retry_after)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 在测试环境中禁用限流
        if os.environ.get('PYTEST_RUNNING') == '1' or not settings.rate_limit.enabled:
            return await call_next(request)

        client_ip = self._get_client_ip(request)

        if self._is_rate_limited(client_ip):
            retry_after = self._get_retry_after(client_ip)
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "请求过于频繁，请稍后再试",
                    "retry_after": retry_after
                },
                headers={"Retry-After": str(retry_after)}
            )

        return await call_next(request)

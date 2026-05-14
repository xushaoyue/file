import time
import logging
from typing import Callable
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("audit.middleware")


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()

        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent", "unknown")

        logger.info(
            "请求开始 | method=%s | path=%s | client_ip=%s | user_agent=%s",
            request.method,
            request.url.path,
            client_ip,
            user_agent
        )

        try:
            response = await call_next(request)
        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                "请求异常 | method=%s | path=%s | client_ip=%s | duration=%.3fs | error=%s",
                request.method,
                request.url.path,
                client_ip,
                duration,
                str(e)
            )
            raise

        duration = time.time() - start_time

        logger.info(
            "请求完成 | method=%s | path=%s | client_ip=%s | status=%d | duration=%.3fs",
            request.method,
            request.url.path,
            client_ip,
            response.status_code,
            duration
        )

        return response

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

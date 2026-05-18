import logging

from starlette.requests import Request

logger = logging.getLogger("audit.middleware")


def get_client_ip(request: Request) -> str:
    x_forwarded_for = request.headers.get("x-forwarded-for")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()

    x_real_ip = request.headers.get("x-real-ip")
    if x_real_ip:
        return x_real_ip

    if request.client:
        return request.client.host

    return "unknown"

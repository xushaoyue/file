from datetime import datetime, timedelta
try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

from backend.app.config import settings


def get_timezone_offset(dt: datetime) -> timedelta:
    """获取配置时区相对于 UTC 的偏移量"""
    try:
        tz = ZoneInfo(settings.app.timezone)
        return tz.utcoffset(dt)
    except Exception:
        offset_str = settings.app.timezone
        if offset_str == "Asia/Shanghai":
            return timedelta(hours=8)
        elif offset_str == "Asia/Tokyo":
            return timedelta(hours=9)
        elif offset_str == "America/New_York":
            return timedelta(hours=-5)
        elif offset_str == "America/Chicago":
            return timedelta(hours=-6)
        elif offset_str == "America/Los_Angeles":
            return timedelta(hours=-8)
        elif offset_str == "Europe/London":
            return timedelta(hours=0)
        elif offset_str == "Europe/Berlin":
            return timedelta(hours=1)
        elif offset_str == "Europe/Paris":
            return timedelta(hours=1)
        elif offset_str == "UTC":
            return timedelta(hours=0)
        else:
            return timedelta(hours=0)

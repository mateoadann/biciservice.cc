from datetime import datetime, timezone
from zoneinfo import ZoneInfo


CORDOBA_TZ = ZoneInfo("America/Argentina/Cordoba")


def now_cordoba_naive() -> datetime:
    return datetime.now(CORDOBA_TZ).replace(tzinfo=None)


def to_cordoba_local(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value
    return value.astimezone(CORDOBA_TZ).replace(tzinfo=None)


def utc_to_cordoba_naive(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(CORDOBA_TZ).replace(tzinfo=None)


def format_cordoba_datetime(value: datetime | None, fmt: str = "%d/%m/%Y %H:%M") -> str:
    local_value = to_cordoba_local(value)
    if local_value is None:
        return "-"
    return local_value.strftime(fmt)

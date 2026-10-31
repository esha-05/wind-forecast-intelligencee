"""Elexon BMRS client. Endpoint paths/params follow the public v1 stream API but
were NOT verified against live responses in the build sandbox (no network access)."""
import logging
import time
from datetime import date, datetime, timedelta, timezone

import httpx

from app.core.config import settings

log = logging.getLogger(__name__)


class ElexonError(RuntimeError):
    pass


def _get(client: httpx.Client, path: str, params: dict) -> list:
    url = f"{settings.elexon_base}{path}"
    for attempt in range(4):
        try:
            r = client.get(url, params=params, timeout=settings.timeout)
            if r.status_code == 429 or r.status_code >= 500:
                log.warning("Elexon %s -> %s (attempt %d)", path, r.status_code, attempt + 1)
                time.sleep(2 ** attempt)
                continue
            r.raise_for_status()
            data = r.json()
            if not isinstance(data, list):
                raise ElexonError(f"Unexpected response shape from {path}")
            return data
        except (httpx.HTTPError, ValueError) as e:
            if attempt == 3:
                raise ElexonError(f"{path} failed: {e}") from e
            time.sleep(2 ** attempt)
    raise ElexonError(f"{path} failed after retries")


def _windows(start: date, end: date):
    cur = datetime(start.year, start.month, start.day, tzinfo=timezone.utc)
    stop = datetime(end.year, end.month, end.day, tzinfo=timezone.utc) + timedelta(days=1)
    while cur < stop:
        nxt = min(cur + timedelta(days=settings.chunk_days), stop)
        yield cur, nxt
        cur = nxt


def fetch_actual(start: date, end: date) -> list:
    out: list = []
    with httpx.Client() as c:
        for a, b in _windows(start, end):
            out += _get(c, "/datasets/FUELHH/stream", {
                "settlementDateFrom": a.date().isoformat(),
                "settlementDateTo": (b - timedelta(days=1)).date().isoformat(),
                "fuelType": "WIND",
            })
    return out


def fetch_forecast(pub_start: date, pub_end: date) -> list:
    out: list = []
    fmt = "%Y-%m-%dT%H:%M:%SZ"
    with httpx.Client() as c:
        for a, b in _windows(pub_start, pub_end):
            out += _get(c, "/datasets/WINDFOR/stream", {
                "publishDateTimeFrom": a.strftime(fmt), "publishDateTimeTo": b.strftime(fmt)})
    return out

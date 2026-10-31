import logging
import time
from datetime import date

from app.clients import elexon
from app.core.config import settings
from app.services.processing import clean_actual, clean_forecast

log = logging.getLogger(__name__)
PERIOD_START, PERIOD_END = date(2026, 1, 1), date(2026, 1, 31)
_cache: dict = {}


def get_frames(force: bool = False):
    """Returns (actual_df, forecast_df, fetched_at_epoch). Cached; raises ElexonError on failure."""
    if not force and _cache and time.time() - _cache["t"] < settings.cache_ttl:
        return _cache["a"], _cache["f"], _cache["t"]
    log.info("Fetching Elexon data")
    a = clean_actual(elexon.fetch_actual(PERIOD_START, PERIOD_END))
    f = clean_forecast(elexon.fetch_forecast(date(2025, 12, 15), date(2026, 2, 1)))
    _cache.update(a=a, f=f, t=time.time())
    return a, f, _cache["t"]

import re
from datetime import date as Date, datetime, timezone

import pandas as pd
from fastapi import APIRouter, HTTPException, Query

from app.clients.elexon import ElexonError
from app.core.config import settings
from app.services import store
from app.services.processing import build_intervals, metrics

router = APIRouter(prefix="/api")
RULE = "Latest forecast with publishTime <= cutoff time (UTC) on the day before delivery. Assumption, not an official Elexon rule."


def _d(v: str) -> Date:
    try:
        d = Date.fromisoformat(v)
    except ValueError:
        raise HTTPException(422, f"Invalid date '{v}', expected YYYY-MM-DD")
    if not (store.PERIOD_START <= d <= store.PERIOD_END):
        raise HTTPException(422, "Date must be within January 2026")
    return d


def _c(v: str) -> str:
    if not re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", v):
        raise HTTPException(422, f"Invalid cutoff '{v}', expected HH:MM")
    return v


def _rows(df: pd.DataFrame) -> list:
    d = df.drop(columns=["cutoff"]).copy()
    for c in ("startTime", "publishTime"):
        d[c] = d[c].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    return d.astype(object).where(d.notna(), None).to_dict("records")


def _load(start: Date, end: Date, cutoff: str):
    try:
        a, f, t = store.get_frames()
    except ElexonError as e:
        raise HTTPException(502, f"Elexon data unavailable: {e}")
    return build_intervals(a, f, start, end, cutoff), datetime.fromtimestamp(t, timezone.utc).isoformat()


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/forecast")
def forecast(date: str, cutoff: str = Query(settings.default_cutoff)):
    d, c = _d(date), _c(cutoff)
    df, t = _load(d, d, c)
    return {"date": date, "cutoff": c, "cutoff_rule": RULE, "fetched_at": t,
            "rows": _rows(df.drop(columns=["actual", "error", "abs_error"]))}


@router.get("/accuracy")
def accuracy(date: str, cutoff: str = Query(settings.default_cutoff)):
    d, c = _d(date), _c(cutoff)
    df, t = _load(d, d, c)
    return {"date": date, "cutoff": c, "cutoff_rule": RULE, "fetched_at": t, "error_convention": "error = forecast - actual",
            "metrics": metrics(df), "rows": _rows(df)}


@router.get("/accuracy/summary")
def summary(start_date: str, end_date: str, cutoff: str = Query(settings.default_cutoff)):
    s, e, c = _d(start_date), _d(end_date), _c(cutoff)
    if s > e:
        raise HTTPException(422, "start_date must be <= end_date")
    df, t = _load(s, e, c)
    return {"start_date": start_date, "end_date": end_date, "cutoff": c, "fetched_at": t, "metrics": metrics(df)}


@router.post("/refresh")
def refresh():
    try:
        _, _, t = store.get_frames(force=True)
    except ElexonError as e:
        raise HTTPException(502, f"Elexon data unavailable: {e}")
    return {"fetched_at": datetime.fromtimestamp(t, timezone.utc).isoformat()}

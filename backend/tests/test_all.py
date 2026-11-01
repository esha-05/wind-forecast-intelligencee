
"""All fixtures here are SYNTHETIC and deterministic; they are not Elexon data."""

from datetime import date

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import store
from app.services.processing import (
    build_intervals,
    clean_actual,
    clean_forecast,
    metrics,
)

T = "2026-01-15T12:00:00Z"

ACT = [
    {"startTime": T, "fuelType": "WIND", "generation": 100},
    {"startTime": T, "fuelType": "CCGT", "generation": 999},
    {
        "startTime": "2026-01-15T12:30:00Z",
        "fuelType": "WIND",
        "generation": 100,
    },
]

FC = [
    {
        "startTime": T,
        "publishTime": publish_time,
        "generation": generation,
    }
    for publish_time, generation in [
        ("2026-01-13T08:00:00Z", 50),
        ("2026-01-14T07:59:00Z", 110),
        ("2026-01-14T08:00:00Z", 120),
        ("2026-01-14T08:01:00Z", 999),
    ]
]

FC += FC[-1:]  # Duplicate row


def frames():
    return clean_actual(ACT), clean_forecast(FC)


def test_filters_wind_and_keeps_missing_as_nan():
    a = clean_actual(ACT)

    assert len(a) == 2
    assert a["actual"].tolist() == [100, 100]


def test_selects_latest_eligible_and_excludes_after_cutoff():
    df = build_intervals(
        *frames(),
        date(2026, 1, 15),
        date(2026, 1, 15),
        "08:00",
    )

    r = df[df.startTime == pd.Timestamp(T)].iloc[0]

    assert r.forecast == 120
    assert str(r.publishTime) == "2026-01-14 08:00:00+00:00"
    assert r.error == 20
    assert r.status == "matched"
    assert len(df) == 24


def test_cutoff_selects_only_eligible_forecasts():
    # At 06:00, only the Jan 13 forecast is eligible.
    df = build_intervals(
        *frames(),
        date(2026, 1, 15),
        date(2026, 1, 15),
        "06:00",
    )

    r = df[df.startTime == pd.Timestamp(T)].iloc[0]

    assert r.forecast == 50
    assert r.status == "matched"

    # At 08:00, the 12:00 interval is matched.
    df = build_intervals(
        *frames(),
        date(2026, 1, 15),
        date(2026, 1, 15),
        "08:00",
    )

    assert (df.status == "missing_both").sum() == 23


def test_metrics_and_mape_policy():
    df = pd.DataFrame({
        "forecast": [110, 90, 5, 1],
        "actual": [100, 100, 0, 1.0],
        "status": ["matched"] * 4,
        "startTime": range(4),
    })

    df["error"] = df.forecast - df.actual
    df["abs_error"] = df.error.abs()

    m = metrics(df)

    assert m["mae"] == pytest.approx(6.25)
    assert m["bias"] == pytest.approx(1.25)
    assert m["rmse"] == pytest.approx(
        ((100 + 100 + 25 + 0) / 4) ** 0.5
    )
    assert m["mape_excluded"] == 1
    assert m["coverage_pct"] == 100


def test_coverage_counts_expected_month():
    a, f = frames()

    df = build_intervals(
        a,
        f,
        date(2026, 1, 1),
        date(2026, 1, 31),
        "08:00",
    )

    m = metrics(df)

    assert m["expected"] == 744
    assert m["matched"] == 1


def test_api_pipeline_and_errors(monkeypatch):
    monkeypatch.setattr(
        store,
        "get_frames",
        lambda force=False: (*frames(), 0.0),
    )

    c = TestClient(app)

    response = c.get(
        "/api/accuracy?date=2026-01-15&cutoff=08:00"
    )

    assert response.status_code == 200

    j = response.json()

    assert j["metrics"]["matched"] == 1
    assert len(j["rows"]) == 24
    assert j["rows"][12]["forecast"] == 120

    assert c.get(
        "/api/accuracy?date=2026-02-01"
    ).status_code == 422

    assert c.get(
        "/api/forecast?date=2026-01-15&cutoff=25:00"
    ).status_code == 422

    assert c.get("/api/health").json() == {"status": "ok"}


def test_upstream_failure_returns_502():
    from app.clients.elexon import ElexonError

    def boom(force=False):
        raise ElexonError("down")

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(store, "get_frames", boom)

    try:
        response = TestClient(app).get(
            "/api/forecast?date=2026-01-15"
        )
        assert response.status_code == 502
    finally:
        monkeypatch.undo()

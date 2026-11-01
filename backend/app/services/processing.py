
from datetime import date

import numpy as np
import pandas as pd

MAPE_MIN_ACTUAL = 1.0  # Exclude |actual| < 1 from MAPE


def _frame(records: list) -> pd.DataFrame:
    df = pd.DataFrame(records)

    for c in ("startTime", "publishTime"):
        if c in df:
            df[c] = pd.to_datetime(df[c], utc=True, errors="coerce")

    if "generation" in df:
        df["generation"] = pd.to_numeric(
            df["generation"], errors="coerce"
        )

    return df


def clean_actual(records: list) -> pd.DataFrame:
    cols = ["startTime", "actual"]

    if not records:
        return pd.DataFrame(columns=cols)

    df = _frame(records)

    if "fuelType" in df:
        df = df[df["fuelType"].astype(str).str.upper() == "WIND"]

    df = (
        df.dropna(subset=["startTime", "generation"])
        .drop_duplicates("startTime", keep="last")
    )

    return df.rename(columns={"generation": "actual"})[cols]


def clean_forecast(records: list) -> pd.DataFrame:
    cols = ["startTime", "publishTime", "forecast"]

    if not records:
        return pd.DataFrame(columns=cols)

    df = _frame(records).dropna(
        subset=["startTime", "publishTime", "generation"]
    )

    df = df.drop_duplicates(
        ["startTime", "publishTime"], keep="last"
    )

    return df.rename(columns={"generation": "forecast"})[cols]


def cutoff_for(start_times: pd.Series, cutoff: str) -> pd.Series:
    """Decision cutoff = HH:MM UTC on the day before delivery."""
    h, m = map(int, cutoff.split(":"))

    return (
        start_times.dt.normalize()
        - pd.Timedelta(days=1, unit="D")
        + pd.Timedelta(hours=h, minutes=m)
    )


def build_intervals(
    actual,
    fc,
    start: date,
    end: date,
    cutoff: str
):
    # WINDFOR forecast delivery timestamps are hourly.
    grid = pd.DataFrame({
        "startTime": pd.date_range(
            pd.Timestamp(start, tz="UTC"),
            pd.Timestamp(end, tz="UTC") + pd.Timedelta(days=1),
            freq="1h",
            inclusive="left"
        )
    })

    grid["cutoff"] = cutoff_for(grid["startTime"], cutoff)

    # Select the latest eligible forecast for each delivery hour.
    f = fc.merge(grid, on="startTime", how="inner")
    f = f[f["publishTime"] <= f["cutoff"]]

    selected = (
        f.sort_values("publishTime")
        .groupby("startTime", as_index=False)
        .tail(1)
    )

    # Aggregate only complete pairs of half-hourly actual readings.
    if not actual.empty:
        hourly_actual = actual.copy()

        hourly_actual["hour"] = (
            hourly_actual["startTime"].dt.floor("h")
        )

        hourly_actual["expected_second"] = (
            hourly_actual["hour"] + pd.Timedelta(minutes=30)
        )

        hourly_actual = (
    hourly_actual.groupby("hour")
    .agg(
        actual=("actual", "mean"),
        actual_periods=("startTime", "nunique"),
        first_time=("startTime", "min"),
        last_time=("startTime", "max"),
        expected_second=("expected_second", "first"),
    )
    .reset_index()
)
        hourly_actual["expected_first"] = hourly_actual["hour"]

        valid = (
            (hourly_actual["actual_periods"] == 2)
            & (
                hourly_actual["first_time"]
                == hourly_actual["expected_first"]
            )
            & (
                hourly_actual["last_time"]
                == hourly_actual["expected_second"]
            )
        )

        hourly_actual.loc[~valid, "actual"] = np.nan

        hourly_actual = hourly_actual.rename(
            columns={"hour": "startTime"}
        )[["startTime", "actual"]]

    else:
        hourly_actual = pd.DataFrame(
            columns=["startTime", "actual"]
        )

    # Merge hourly forecasts and hourly actuals.
    df = grid.merge(
        selected[["startTime", "publishTime", "forecast"]],
        on="startTime",
        how="left"
    )

    df = df.merge(
        hourly_actual[["startTime", "actual"]],
        on="startTime",
        how="left"
    )

    df["error"] = df["forecast"] - df["actual"]
    df["abs_error"] = df["error"].abs()

    hf = df["forecast"].notna()
    ha = df["actual"].notna()

    df["status"] = np.select(
        [hf & ha, ~hf & ha, hf & ~ha],
        ["matched", "missing_forecast", "missing_actual"],
        "missing_both"
    )

    return df


def metrics(df: pd.DataFrame) -> dict:
    m = df[df["status"] == "matched"]

    expected, n = len(df), len(m)

    out = {
        "matched": n,
        "expected": expected,
        "coverage_pct": (
            round(100 * n / expected, 2) if expected else None
        ),
        "mae": None,
        "rmse": None,
        "bias": None,
        "mape_pct": None,
        "mape_excluded": 0,
    }

    if n:
        out.update(
            mae=float(m["abs_error"].mean()),
            rmse=float(np.sqrt((m["error"] ** 2).mean())),
            bias=float(m["error"].mean()),
        )

        ok = m[m["actual"].abs() >= MAPE_MIN_ACTUAL]

        out["mape_excluded"] = n - len(ok)

        if len(ok):
            out["mape_pct"] = float(
                (ok["abs_error"] / ok["actual"].abs()).mean() * 100
            )

    return out

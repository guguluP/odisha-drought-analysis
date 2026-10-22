"""Data loading and calculations for the dashboard.

Reads ONLY files in data/clean/ (Odisha CSV tables and the small district GeoJSON made by make_geojson.py).
All functions are plain pandas so they can be explained (and tested) without running the app.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
CLEAN = ROOT / "data" / "clean"

DROUGHT_THRESHOLD = -1.0          # a month is a drought month if SPEI <= -1
NORMAL_SHARE = 15.87              # % of months <= -1 expected for a standard normal variable
# Expected % of months in each class for a standard normal variable (used as a reference in the severity chart)
NORMAL_CLASS_SHARE = {"Moderate": 9.19, "Severe": 4.41, "Extreme": 2.28}
SCALES = {"1": "spei_1", "4": "spei_4", "12": "spei_12"}     # radio value -> column name
STATE_NAME = "Odisha (whole state)"      # the statewide series (Odisha as a state in the atlas)
DEFAULT_REGION = STATE_NAME
YEAR_MIN, YEAR_MAX = 1901, 2025


def _load_monthly():
    # One monthly table: region (statewide series + 30 districts), date, year, decade, spei_1, spei_4, spei_12
    cols = ["date", "year", "decade", "spei_1", "spei_4", "spei_12"]
    state = pd.read_csv(CLEAN / "odisha_month.csv", usecols=cols, parse_dates=["date"])
    state.insert(0, "region", STATE_NAME)
    districts = pd.read_csv(CLEAN / "odisha_district_month.csv", usecols=["district"] + cols, parse_dates=["date"])
    districts = districts.rename(columns={"district": "region"})
    return pd.concat([state, districts], ignore_index=True).sort_values(["region", "date"]).reset_index(drop=True)


MONTHLY = _load_monthly()
DISTRICTS = sorted(r for r in MONTHLY["region"].unique() if r != STATE_NAME)
REGIONS = [STATE_NAME] + DISTRICTS                    # dropdown order: whole state first, then 30 districts A-Z
GEOJSON = json.loads((CLEAN / "geo" / "odisha_districts.geojson").read_text())


def select(region, y0, y1, scale):
    """Monthly rows of one region for years y0..y1, with the chosen SPEI column renamed to 'spei'."""
    df = MONTHLY
    part = df[(df["region"] == region) & (df["year"] >= y0) & (df["year"] <= y1)]
    return part[["date", "year", "decade", SCALES[scale]]].rename(columns={SCALES[scale]: "spei"}).reset_index(drop=True)


def severity_class(spei):
    """Moderate (-1.5 < x <= -1), Severe (-2 < x <= -1.5), Extreme (x <= -2), otherwise No drought (NaN stays NaN)."""
    classes = pd.cut(spei, bins=[-np.inf, -2, -1.5, -1, np.inf], labels=["Extreme", "Severe", "Moderate", "No drought"])
    return classes


def drought_events(sel):
    """Run theory: an event = consecutive months with SPEI <= -1 (a missing month ends a run).

    Events are counted inside the selected period only (an event that started before the period starts at the first month shown).
    Returns a DataFrame with start, end, duration (months), severity (sum of -SPEI) and peak (lowest SPEI).
    """
    is_dry = (sel["spei"] <= DROUGHT_THRESHOLD)                      # False for NaN
    run_id = (is_dry != is_dry.shift()).cumsum()                      # new id each time dry/not-dry changes
    dry = sel[is_dry].assign(run=run_id[is_dry])
    if dry.empty:
        return pd.DataFrame(columns=["start", "end", "duration", "severity", "peak"])
    return dry.groupby("run").agg(start=("date", "first"), end=("date", "last"), duration=("date", "size"),
                                  severity=("spei", lambda s: -s.sum()), peak=("spei", "min")).reset_index(drop=True)


def kpis(sel):
    """Numbers for the four KPI cards."""
    valid = sel["spei"].notna()
    out = {"valid_months": int(valid.sum())}
    if out["valid_months"] == 0:
        return None
    out["share"] = 100 * (sel.loc[valid, "spei"] <= DROUGHT_THRESHOLD).mean()
    out["drought_months"] = int((sel["spei"] <= DROUGHT_THRESHOLD).sum())
    ev = drought_events(sel)
    out["events"] = len(ev)
    if len(ev):
        longest = ev.loc[ev["duration"].idxmax()]          # first one if there is a tie
        out["longest"], out["longest_start"] = int(longest["duration"]), longest["start"]
    else:
        out["longest"], out["longest_start"] = 0, None
    # Worst year = lowest yearly mean SPEI (only years with at least 6 valid months, so 1901 SPEI-12 is skipped)
    yearly = sel.groupby("year")["spei"].agg(["mean", "count"])
    yearly = yearly[yearly["count"] >= 6]
    if len(yearly):
        out["worst_year"], out["worst_value"] = int(yearly["mean"].idxmin()), yearly["mean"].min()
    else:
        out["worst_year"], out["worst_value"] = None, None
    return out


def shares_all(y0, y1, scale):
    """Drought share (%) of every region (statewide series + 30 districts) for the period -> Series sorted high to low."""
    df = MONTHLY
    part = df[(df["year"] >= y0) & (df["year"] <= y1)]
    col = part[SCALES[scale]]
    dry = (col <= DROUGHT_THRESHOLD).groupby(part["region"]).sum()
    n = col.notna().groupby(part["region"]).sum()
    return (100 * dry / n.replace(0, np.nan)).sort_values(ascending=False)


def decade_table(sel):
    """% of valid months in drought for each decade in the selection (and how many months the decade has)."""
    valid = sel[sel["spei"].notna()]
    t = valid.groupby("decade").agg(months=("spei", "size"), dry=("spei", lambda s: (s <= DROUGHT_THRESHOLD).sum()))
    t["share"] = 100 * t["dry"] / t["months"]
    return t.reset_index()


def severity_table(sel):
    """% of valid months in each drought class, next to the normal-distribution expectation."""
    classes = severity_class(sel["spei"].dropna())
    share = classes.value_counts(normalize=True) * 100
    rows = [{"class": c, "share": share.get(c, 0.0), "normal": NORMAL_CLASS_SHARE[c],
             "months": int((classes == c).sum())} for c in ["Moderate", "Severe", "Extreme"]]
    return pd.DataFrame(rows)

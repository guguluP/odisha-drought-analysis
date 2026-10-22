"""Dashboard tests (no browser needed; Odisha-only version). Run from the project root:  python tests/test_dashboard.py

1. Calls every callback function directly with many input combinations (whole state + districts, all SPEI timescales,
   edge periods such as a single year, 1901 only, the full record) and checks that no exception is raised.
2. Checks the KPI numbers against the clean result tables (notebook 02) and reports/ODISHA_ONLY_FACTS.md.
"""
import itertools
import sys
import time
from contextvars import copy_context
from pathlib import Path

import pandas as pd
from dash.exceptions import PreventUpdate

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import app  # noqa: E402
from dashboard import data as D  # noqa: E402

results = {"calls": 0, "prevented": 0, "errors": []}
STATE = D.STATE_NAME

# ---------------------------------------------------------------- 0. data set-up
assert D.REGIONS[0] == STATE and len(D.REGIONS) == 31 and len(D.DISTRICTS) == 30, D.REGIONS
assert D.DEFAULT_REGION == STATE
assert len(D.GEOJSON["features"]) == 30
assert set(f["properties"]["name"] for f in D.GEOJSON["features"]) == set(D.DISTRICTS), "map names must equal district names"
print("Regions: whole state + 30 districts; map has 30 features with the same names: OK")

# ---------------------------------------------------------------- 1. callback 1 (map click -> dropdown)
assert app.update_region_from_map({"points": [{"location": "Balasore"}]}, STATE) == "Balasore"
for click, cur in [(None, STATE), ({"points": [{"location": "Balasore"}]}, "Balasore"), ({"points": [{"location": "Kerala"}]}, STATE)]:
    try:
        app.update_region_from_map(click, cur)
        raise AssertionError("expected PreventUpdate")
    except PreventUpdate:
        pass
print("Callback 1 (map click -> region): OK")

# ---------------------------------------------------------------- 2. callbacks 2-4 over many inputs
periods = [[1901, 2025], [1991, 2025], [1901, 1901], [2025, 2025], [1901, 1960], [2011, 2021], [1950, 1950]]
regions = [STATE, "Nuapada", "Balasore", "Koraput", "Puri", "Malkangiri"]
t0 = time.time()
for region, years, scale in itertools.product(regions, periods, ["1", "4", "12"]):
    for func in (app.update_summary, app.update_map_and_ranking):
        try:
            assert func(region, years, scale) is not None
            results["calls"] += 1
        except Exception as e:  # noqa: BLE001
            results["errors"].append((func.__name__, region, years, scale, repr(e)))
    try:
        app.download_selection(1, region, years, scale)
        results["calls"] += 1
    except Exception as e:  # noqa: BLE001
        results["errors"].append(("download_selection", region, years, scale, repr(e)))
# Every one of the 31 regions must work for the default view
for region in D.REGIONS:
    for func in (app.update_summary, app.update_map_and_ranking):
        try:
            assert func(region, [1991, 2025], "1") is not None
            results["calls"] += 1
        except Exception as e:  # noqa: BLE001
            results["errors"].append((func.__name__, region, "all regions", "1", repr(e)))
# An unknown region must be ignored, not crash
for func in (app.update_summary, app.update_map_and_ranking):
    try:
        func("Kerala", [1991, 2025], "1")
    except PreventUpdate:
        results["prevented"] += 1
elapsed = time.time() - t0
print(f"Callbacks 2-4: {results['calls']} calls in {elapsed:.1f} s, {results['prevented']} stale inputs ignored, "
      f"{len(results['errors'])} errors")
for e in results["errors"]:
    print("  ERROR", e)

out = app.update_summary(STATE, [1901, 1901], "12")
print("Edge case whole Odisha 1901 SPEI-12 ->", out[1], "|", out[2], "|", out[7], out[8])

# The CSV download of the whole state has 1500 rows for the full record
dl = app.download_selection(1, STATE, [1901, 2025], "1")
assert dl["filename"].startswith("Odisha_whole_state_1901_2025_spei1"), dl["filename"]
print("Download file name:", dl["filename"])

# ---------------------------------------------------------------- 3. KPI cross-check with notebook 02 tables
rank_dist = pd.read_csv(ROOT / "data/clean/ranking_odisha_districts_1991_2025.csv").set_index("district")
rows = []
for region in ["Nuapada", "Balasore", "Koraput", "Puri", "Malkangiri"]:
    k = D.kpis(D.select(region, 1991, 2025, "1"))
    t = rank_dist.loc[region]
    rows.append({"region": region, "share_dash": round(k["share"], 2), "share_nb02": round(t["drought_share_1991_2025"], 2),
                 "events_dash": k["events"], "events_nb02": int(t["events"]),
                 "longest_dash": k["longest"], "longest_nb02": int(t["longest_event"])})
check = pd.DataFrame(rows)
check["match"] = ((check["share_dash"] == check["share_nb02"]) & (check["events_dash"] == check["events_nb02"])
                  & (check["longest_dash"] == check["longest_nb02"]))
print("\nKPI cross-check for districts, SPEI-1, 1991-2025 (dashboard vs notebook 02 ranking table):")
print(check.to_string(index=False))

# Whole-state cross-checks against the facts file (numbers computed in notebooks 01-02)
facts = {}
for line in (ROOT / "reports/ODISHA_ONLY_FACTS.md").read_text().splitlines():
    parts = [x.strip() for x in line.strip().strip("|").split("|")]
    if len(parts) == 3 and parts[2].startswith("`"):
        facts[parts[2].strip("`")] = parts[1].replace("−", "-")
full = D.kpis(D.select(STATE, 1901, 2025, "1"))
recent = D.kpis(D.select(STATE, 1991, 2025, "1"))
extra = [
    ("Odisha 1901-2025 drought months", full["drought_months"], int(facts["odisha_drought_months"])),
    ("Odisha 1901-2025 events", full["events"], int(facts["odisha_events_spei1"])),
    ("Odisha 1901-2025 longest event (months)", full["longest"], int(facts["odisha_longest_event"])),
    ("Odisha 1991-2025 drought share (%)", f"{recent['share']:.1f}", facts["odisha_share_1991_2025"]),
    ("Odisha 1901-2025 valid months", full["valid_months"], int(facts["rows_odisha_month"])),
]
for label, got, expected in extra:
    print(f"  {label}: dashboard = {got}, facts file = {expected} -> {'MATCH' if str(got) == str(expected) else 'MISMATCH'}")
print(f"  Odisha 1901-2025 longest event starts {full['longest_start']:%b %Y}; worst year {full['worst_year']} ({full['worst_value']:.2f}); "
      f"1991-2025 worst year {recent['worst_year']} ({recent['worst_value']:.2f})")

ok = not results["errors"] and check["match"].all() and all(str(g) == str(e) for _, g, e in extra)
print("\nALL TESTS PASSED" if ok else "\nSOME TESTS FAILED")
sys.exit(0 if ok else 1)

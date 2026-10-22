"""HTTP smoke test (Odisha-only dashboard) + real browser screenshots (headless Chromium via Playwright).

Start the app first (in another terminal):   gunicorn app:server -b 127.0.0.1:8050
Then run from the project root:               python tests/http_and_screenshots.py
"""
import json
import sys
from pathlib import Path

import requests
from playwright.sync_api import sync_playwright

URL = "http://127.0.0.1:8050"
FIG = Path(__file__).resolve().parent.parent / "reports" / "figures"

# ---------------------------------------------------------------- 1. HTTP: page, layout, callback list, two real callback requests
for path in ["/", "/_dash-layout", "/_dash-dependencies", "/assets/style.css"]:
    r = requests.get(URL + path, timeout=30)
    print(f"GET {path:22s} -> {r.status_code} ({len(r.content)} bytes)")
    assert r.status_code == 200
deps = requests.get(URL + "/_dash-dependencies", timeout=30).json()
print("Callbacks registered:", len(deps))
for d in deps:
    print("  inputs:", [i["id"] + "." + i["property"] for i in d["inputs"]], "->", d["output"][:90])


def post_callback(dep, inputs, state=None, changed=None):
    # Same request the browser sends when an input changes
    # "..a.children...b.figure.." (several outputs) -> [{"id": "a", "property": "children"}, ...]
    parts = dep["output"].strip(".").split("...") if dep["output"].startswith("..") else [dep["output"]]
    outputs = [dict(zip(["id", "property"], part.rsplit(".", 1))) for part in parts]
    body = {"output": dep["output"], "outputs": outputs if len(outputs) > 1 else outputs[0], "inputs": inputs, "state": state or [],
            "changedPropIds": changed or [inputs[0]["id"] + "." + inputs[0]["property"]]}
    r = requests.post(URL + "/_dash-update-component", json=body, timeout=60)
    return r.status_code, (r.json() if r.status_code == 200 else r.text[:200])


summary_dep = next(d for d in deps if "selection-title" in d["output"])
inputs = [{"id": "region", "property": "value", "value": "Nuapada"},
          {"id": "years", "property": "value", "value": [1991, 2025]}, {"id": "scale", "property": "value", "value": "4"}]
code, resp = post_callback(summary_dep, inputs, changed=["region.value"])
print("POST summary callback (Nuapada, SPEI-4) ->", code, "| title:", resp["response"]["selection-title"]["children"],
      "| share:", resp["response"]["kpi-share-value"]["children"])
assert code == 200

region_dep = next(d for d in deps if d["output"] == "region.value")
code, resp = post_callback(region_dep,
                           [{"id": "map", "property": "clickData", "value": {"points": [{"location": "Balasore"}]}}],
                           state=[{"id": "region", "property": "value", "value": "Odisha (whole state)"}], changed=["map.clickData"])
print("POST region callback (map click on Balasore) ->", code, "| new region:", resp["response"]["region"]["value"])
assert resp["response"]["region"]["value"] == "Balasore"

# ---------------------------------------------------------------- 2. Screenshots in a real (headless) browser
def wait_ready(page, expect_title):
    # Wait until the header shows the expected selection and all 5 graphs have drawn
    page.wait_for_function("t => document.querySelector('#selection-title')?.innerText.startsWith(t)", arg=expect_title,
                           timeout=60000)
    page.wait_for_function("() => document.querySelectorAll('.js-plotly-plot .main-svg').length >= 5", timeout=60000)
    page.wait_for_timeout(1500)   # let the map finish drawing


def kpis(page):
    return {k: page.inner_text(f"#kpi-{k}-value") + " | " + page.inner_text(f"#kpi-{k}-note")
            for k in ["share", "events", "longest", "worst"]}


errors = []
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)

    def pick(name):
        page.click("#region")                                                    # open the dropdown
        page.click(f"label.dash-dropdown-option:has-text('{name}')")             # pick the option

    # (a) default view: whole Odisha, 1991-2025, SPEI-1
    page.goto(URL)
    wait_ready(page, "Odisha (whole state) · 1991–2025 · SPEI-1")
    print("\nDefault view KPIs:", json.dumps(kpis(page), ensure_ascii=False))
    page.screenshot(path=str(FIG / "dashboard_default_odisha_whole_state.png"), full_page=True)

    # (b) Nuapada from the dropdown
    pick("Nuapada")
    wait_ready(page, "Nuapada · 1991–2025 · SPEI-1")
    print("Nuapada KPIs:", json.dumps(kpis(page), ensure_ascii=False))
    page.screenshot(path=str(FIG / "dashboard_district_nuapada.png"), full_page=True)

    # (c) Balasore (coastal) by clicking on the dropdown, then SPEI-12 timescale
    pick("Balasore")
    wait_ready(page, "Balasore · 1991–2025 · SPEI-1")
    page.get_by_text("SPEI-12 (12 months)", exact=True).click()
    wait_ready(page, "Balasore · 1991–2025 · SPEI-12")
    print("Balasore SPEI-12 KPIs:", json.dumps(kpis(page), ensure_ascii=False))
    page.screenshot(path=str(FIG / "dashboard_district_balasore_spei12.png"), full_page=True)
    browser.close()

print("\nBrowser errors:", errors if errors else "none")
for f in sorted(FIG.glob("dashboard_*.png")):
    print("saved", f.relative_to(FIG.parent.parent))
sys.exit(1 if errors else 0)

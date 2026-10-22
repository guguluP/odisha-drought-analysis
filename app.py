"""India Drought Analysis (State: Odisha) – Plotly Dash dashboard (Odisha only since the 2026-10-09 scope change).

Run locally:   python app.py            -> open http://127.0.0.1:8050
Live:          https://piyushpatnaik.pythonanywhere.com/  (free PythonAnywhere hosting; see DEPLOY_PYTHONANYWHERE.md)
Other hosts:   gunicorn app:server      (e.g. Render / Hugging Face Spaces)

The app reads only data/clean/ (Odisha CSV tables + one small district GeoJSON made by dashboard/make_geojson.py).

Callbacks (see the Week 6 report for a diagram):
  1. update_region_from_map: a map click on a district    -> region dropdown value             (chained: feeds 2, 3 and 4)
  2. update_summary        : region, years, SPEI           -> header text, 4 KPI cards, time series, decade bar, severity chart
  3. update_map_and_ranking: region, years, SPEI           -> district map and district ranking bar
  4. download_selection    : "Download CSV" button         -> CSV of the monthly values shown
"""
import os

from dash import Dash, Input, Output, State, ctx, dcc, html, no_update
from dash.exceptions import PreventUpdate

from dashboard import data as D
from dashboard import figures as F

app = Dash(__name__, title="Odisha Drought Dashboard")
server = app.server          # the Flask server object, needed by gunicorn for deployment


# ----------------------------------------------------------------------------------------------- layout helpers
def kpi_card(card_id, label):
    # One KPI card: a big number (filled by a callback) and a small note under it
    return html.Div(className="kpi", children=[
        html.Div(label, className="kpi-label"),
        html.Div("–", id=f"{card_id}-value", className="kpi-value"),
        html.Div("", id=f"{card_id}-note", className="kpi-note"),
    ])


controls = html.Div(className="card controls", children=[
    html.Div(className="control", children=[
        html.Label("Region"),
        dcc.Dropdown(id="region", options=D.REGIONS, value=D.DEFAULT_REGION, clearable=False),
    ]),
    html.Div(className="control", children=[
        html.Label("SPEI timescale"),
        dcc.RadioItems(id="scale", value="1", inline=True, className="radio",
                       options=[{"label": " SPEI-1 (1 month)", "value": "1"},
                                {"label": " SPEI-4 (4 months)", "value": "4"},
                                {"label": " SPEI-12 (12 months)", "value": "12"}]),
    ]),
    html.Div(className="control wide", children=[
        html.Label("Period (years)"),
        dcc.RangeSlider(id="years", min=D.YEAR_MIN, max=D.YEAR_MAX, step=1, value=[1991, 2025], allowCross=False,
                        marks={y: str(y) for y in [1901, 1920, 1940, 1960, 1980, 2000, 2025]},
                        tooltip={"placement": "bottom", "always_visible": False}),
    ]),
])

app.layout = html.Div(className="page", children=[
    html.Header(className="header", children=[
        html.H1("Odisha Drought Dashboard"),
        html.P("Monthly SPEI for Odisha and its 30 districts (Drought Atlas of India, 1901–2025). A drought month has SPEI ≤ −1. "
               "Pick the whole state or a district, a period and an SPEI timescale – or click a district on the map."),
    ]),
    controls,
    html.H2(id="selection-title", className="selection-title"),
    html.Div(className="kpi-row", children=[
        kpi_card("kpi-share", "Drought share"),
        kpi_card("kpi-events", "Drought events"),
        kpi_card("kpi-longest", "Longest event"),
        kpi_card("kpi-worst", "Worst year"),
    ]),
    html.Div(className="card", children=[dcc.Graph(id="timeseries", config={"displaylogo": False})]),
    html.Div(className="row", children=[
        html.Div(className="card half", children=[dcc.Graph(id="map", config={"displaylogo": False})]),
        html.Div(className="card half", children=[dcc.Graph(id="ranking", config={"displaylogo": False})]),
    ]),
    html.Div(className="row", children=[
        html.Div(className="card half", children=[dcc.Graph(id="decades", config={"displaylogo": False})]),
        html.Div(className="card half", children=[dcc.Graph(id="severity", config={"displaylogo": False})]),
    ]),
    html.Div(className="card download", children=[
        html.Button("Download CSV of the selected series", id="download-btn", n_clicks=0),
        dcc.Download(id="download"),
        html.Span(" Monthly values of the region, period and timescale shown above.", className="kpi-note"),
    ]),
    html.Footer(className="footer", children=[
        html.P(["Data: Chuphal, D. S., Kushwaha, A. P., Aadhar, S. & Mishra, V. ",
                html.I("Drought Atlas of India, 1901–2025 (v2)"), ". Zenodo. ",
                html.A("https://zenodo.org/records/20368514", href="https://zenodo.org/records/20368514", target="_blank"),
                ". Boundaries: shapefiles distributed with the atlas."]),
        html.P("CUTM1018 Data Analysis and Visualization with Python · Piyush Patnaik (250301370280), "
               "Vegulla Virendra Kaushik (250301370267) · Faculty: Chandra Sekhar Jena"),
        html.P("Note: each SPEI series is standardised over 1901–2025, so over the full period every region has about 16% "
               "drought months; compare periods (e.g. 1991–2025) to see change. Scope: Odisha only (statewide series + 30 districts)."),
    ]),
])


# ----------------------------------------------------------------------------------------------- callbacks
@app.callback(
    Output("region", "value"),
    Input("map", "clickData"),
    State("region", "value"),
)
def update_region_from_map(click_data, current):
    """Callback 1 (chained): a click on a district in the map selects it in the dropdown."""
    if not click_data:
        raise PreventUpdate
    clicked = click_data["points"][0].get("location")
    if clicked in D.DISTRICTS and clicked != current:
        return clicked
    raise PreventUpdate                        # click on the district already selected


def _period_text(years):
    y0, y1 = years
    return f"{y0}" if y0 == y1 else f"{y0}–{y1}"


@app.callback(
    Output("selection-title", "children"),
    Output("kpi-share-value", "children"), Output("kpi-share-note", "children"),
    Output("kpi-events-value", "children"), Output("kpi-events-note", "children"),
    Output("kpi-longest-value", "children"), Output("kpi-longest-note", "children"),
    Output("kpi-worst-value", "children"), Output("kpi-worst-note", "children"),
    Output("timeseries", "figure"), Output("decades", "figure"), Output("severity", "figure"),
    Input("region", "value"), Input("years", "value"), Input("scale", "value"),
)
def update_summary(region, years, scale):
    """Callback 2: header, KPI cards and the three region charts."""
    if region not in D.REGIONS:
        raise PreventUpdate
    y0, y1 = years
    period = _period_text(years)
    title = f"{region} · {period} · SPEI-{scale}"
    sel = D.select(region, y0, y1, scale)
    k = D.kpis(sel)
    if k is None:                              # e.g. SPEI-12 for 1901 only: no valid months
        msg = f"No SPEI-{scale} values for {period} (SPEI-4/12 start in Apr/Dec 1901)."
        blank = F.empty_figure(msg)
        return (title, "n/a", msg, "n/a", "", "n/a", "", "n/a", "", F.empty_figure(msg, 380), blank, blank)

    share_note = f"{k['drought_months']} of {k['valid_months']} months · normal ≈ 15.9%"
    events_note = "runs of consecutive drought months"
    if k["longest"]:
        longest_value = f"{k['longest']} month" + ("s" if k["longest"] > 1 else "")
        longest_note = f"starting {k['longest_start']:%b %Y}"
    else:
        longest_value, longest_note = "none", "no drought month in this period"
    if k["worst_year"] is not None:
        worst_value, worst_note = str(k["worst_year"]), f"lowest yearly mean SPEI-{scale}: {k['worst_value']:.2f}"
    else:
        worst_value, worst_note = "n/a", "needs a year with at least 6 valid months"

    return (title,
            f"{k['share']:.1f}%", share_note,
            f"{k['events']}", events_note,
            longest_value, longest_note,
            worst_value, worst_note,
            F.timeseries_figure(sel, region, scale),
            F.decade_figure(D.decade_table(sel), region),
            F.severity_figure(D.severity_table(sel), region))


@app.callback(
    Output("map", "figure"), Output("ranking", "figure"),
    Input("region", "value"), Input("years", "value"), Input("scale", "value"),
)
def update_map_and_ranking(region, years, scale):
    """Callback 3: drought share of every region for the period -> map (selected region outlined) and ranking."""
    if region not in D.REGIONS:
        raise PreventUpdate
    shares = D.shares_all(years[0], years[1], scale).dropna()
    if shares.empty:
        msg = f"No SPEI-{scale} values for {_period_text(years)}."
        return F.empty_figure(msg, 520), F.empty_figure(msg, 520)
    period = _period_text(years)
    return (F.map_figure(shares, region, period, scale),
            F.ranking_figure(shares, region, period, scale))


@app.callback(
    Output("download", "data"),
    Input("download-btn", "n_clicks"),
    State("region", "value"), State("years", "value"), State("scale", "value"),
    prevent_initial_call=True,
)
def download_selection(n_clicks, region, years, scale):
    """Callback 4: send the monthly values currently shown as a CSV file."""
    sel = D.select(region, years[0], years[1], scale).rename(columns={"spei": f"spei_{scale}"})
    sel["drought"] = (sel[f"spei_{scale}"] <= D.DROUGHT_THRESHOLD).astype(int)
    name = f"{region.replace(' ', '_').replace('(', '').replace(')', '')}_{years[0]}_{years[1]}_spei{scale}.csv"
    return dcc.send_data_frame(sel.to_csv, name, index=False)


if __name__ == "__main__":
    # debug=False so the page looks the same as a deployed app; set debug=True while developing
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", 8050)), debug=False)   # PORT=8060 python app.py to use another port

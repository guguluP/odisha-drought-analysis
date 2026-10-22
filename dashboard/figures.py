"""Plotly figure builders for the dashboard. Each function takes plain data and returns a go.Figure."""
import plotly.graph_objects as go

from dashboard.data import DROUGHT_THRESHOLD, NORMAL_SHARE, GEOJSON, STATE_NAME

# One colour theme (same idea as the Week 4 notebook): red = dry, blue = wet
COL = {"dry": "#b2182b", "wet": "#2166ac", "line": "#4d4d4d", "neutral": "#bdbdbd", "highlight": "#e66101",
       "Moderate": "#fdae61", "Severe": "#f46d43", "Extreme": "#a50026", "normal": "#9e9e9e"}
FONT = {"family": "Segoe UI, Roboto, Arial, sans-serif", "size": 12}


def _layout(fig, title, height=360):
    fig.update_layout(title={"text": title, "x": 0.01, "font": {"size": 15}}, height=height, font=FONT,
                      margin={"l": 55, "r": 20, "t": 50, "b": 45}, plot_bgcolor="white", paper_bgcolor="white",
                      legend={"orientation": "h", "y": -0.18, "x": 0})
    fig.update_xaxes(showgrid=True, gridcolor="#eeeeee", zeroline=False)
    fig.update_yaxes(showgrid=True, gridcolor="#eeeeee", zeroline=False)
    return fig


def empty_figure(message, height=360):
    fig = go.Figure()
    fig.add_annotation(text=message, x=0.5, y=0.5, xref="paper", yref="paper", showarrow=False, font={"size": 14})
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    return _layout(fig, "", height)


def timeseries_figure(sel, region, scale):
    """Monthly SPEI line, a dashed drought threshold at -1, and red shading where SPEI <= -1."""
    fig = go.Figure()
    # Shading: an invisible line at -1, then the SPEI clipped at -1 filled down to it ("tonexty")
    fig.add_trace(go.Scatter(x=sel["date"], y=[DROUGHT_THRESHOLD] * len(sel), mode="lines",
                             line={"width": 0}, hoverinfo="skip", showlegend=False))
    fig.add_trace(go.Scatter(x=sel["date"], y=sel["spei"].clip(upper=DROUGHT_THRESHOLD), mode="lines",
                             line={"width": 0}, fill="tonexty", fillcolor="rgba(178,24,43,0.45)",
                             name="Drought month (SPEI ≤ −1)", hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=sel["date"], y=sel["spei"], mode="lines", line={"width": 1, "color": COL["line"]},
                             name=f"Monthly SPEI-{scale}", hovertemplate="%{x|%b %Y}: %{y:.2f}<extra></extra>"))
    # Threshold as a line trace (shown in the legend instead of a text label that would cover the data)
    fig.add_trace(go.Scatter(x=[sel["date"].min(), sel["date"].max()], y=[DROUGHT_THRESHOLD] * 2, mode="lines",
                             line={"dash": "dash", "color": COL["dry"], "width": 1.5}, name="Drought threshold (−1)",
                             hoverinfo="skip"))
    fig.add_hline(y=0, line={"color": "#999999", "width": 1})
    fig.update_yaxes(title=f"SPEI-{scale}")
    fig.update_xaxes(title="Month")
    return _layout(fig, f"{region}: monthly SPEI-{scale} with drought months shaded", 380)


def decade_figure(table, region):
    """Bar: % of months in drought for each decade; dotted line = 15.9% normal expectation."""
    labels = [f"{d}s" for d in table["decade"]]
    colours = [COL["dry"] if s > NORMAL_SHARE else COL["wet"] for s in table["share"]]
    fig = go.Figure(go.Bar(x=labels, y=table["share"], marker_color=colours, name="Drought months (%)",
                           customdata=table[["dry", "months"]],
                           hovertemplate="%{x}: %{y:.1f}% (%{customdata[0]} of %{customdata[1]} months)<extra></extra>"))
    # Normal expectation: a full-width dotted line, named in the legend (a text label would cover the bars)
    fig.add_hline(y=NORMAL_SHARE, line={"dash": "dot", "color": "black"})
    fig.add_trace(go.Scatter(x=[None], y=[None], mode="lines", line={"dash": "dot", "color": "black"},
                             name="Normal expectation (15.9%)"))
    fig.update_yaxes(title="Drought months (% of months)", rangemode="tozero")
    fig.update_xaxes(title="Decade (partial decades use the months selected)")
    return _layout(fig, f"{region}: drought months per decade (red = above normal)")


def severity_figure(table, region):
    """Grouped bars: % of months in each drought class vs what a normal distribution would give."""
    fig = go.Figure()
    fig.add_trace(go.Bar(x=table["class"], y=table["share"], name=region,
                         marker_color=[COL[c] for c in table["class"]], customdata=table["months"],
                         hovertemplate="%{x}: %{y:.1f}% (%{customdata} months)<extra></extra>",
                         text=[f"{v:.1f}%" for v in table["share"]], textposition="outside"))
    fig.add_trace(go.Bar(x=table["class"], y=table["normal"], name="Normal expectation", marker_color=COL["normal"],
                         opacity=0.6, hovertemplate="%{x}: %{y:.1f}% expected<extra></extra>"))
    fig.update_layout(barmode="group")
    fig.update_yaxes(title="% of months", rangemode="tozero")
    fig.update_xaxes(title="Severity class (Moderate −1.5 < x ≤ −1, Severe −2 < x ≤ −1.5, Extreme ≤ −2)")
    return _layout(fig, f"{region}: severity classes vs normal expectation")


def map_figure(shares, selected, period_text, scale):
    """Choropleth of the drought share of the 30 Odisha districts; a selected district gets a thick black outline."""
    districts = shares.drop(STATE_NAME, errors="ignore")
    fig = go.Figure()
    fig.add_trace(go.Choropleth(geojson=GEOJSON, featureidkey="properties.name", locations=districts.index, z=districts.values,
                                colorscale="YlOrRd", marker_line_color="white", marker_line_width=0.6,
                                colorbar={"title": {"text": "Drought<br>months (%)"}, "thickness": 12, "len": 0.75},
                                hovertemplate="%{location}: %{z:.1f}%<extra></extra>"))
    if selected != STATE_NAME:      # highlight: transparent fill, thick outline (nothing to outline for the whole state)
        fig.add_trace(go.Choropleth(geojson=GEOJSON, featureidkey="properties.name", locations=[selected], z=[1],
                                    colorscale=[[0, "rgba(0,0,0,0)"], [1, "rgba(0,0,0,0)"]], showscale=False,
                                    marker_line_color="black", marker_line_width=3, hoverinfo="skip"))
    fig.update_geos(fitbounds="locations", visible=False, projection_type="mercator")
    _layout(fig, f"Odisha districts: drought months (SPEI-{scale} ≤ −1), {period_text} — click a district to select it", 520)
    fig.update_layout(margin={"l": 0, "r": 0, "t": 50, "b": 0})
    return fig


def ranking_figure(shares, selected, period_text, scale):
    """Horizontal bar ranking of the 30 districts; the selected district in orange; dashed line = whole-state share."""
    districts = shares.drop(STATE_NAME, errors="ignore")
    s = districts.sort_values()        # lowest at the bottom, highest at the top
    colours = [COL["highlight"] if r == selected else COL["neutral"] for r in s.index]
    fig = go.Figure(go.Bar(x=s.values, y=s.index, orientation="h", marker_color=colours,
                           hovertemplate="%{y}: %{x:.1f}%<extra></extra>"))
    fig.add_vline(x=NORMAL_SHARE, line={"dash": "dot", "color": "black"})
    state_share = shares.get(STATE_NAME)
    if state_share is not None:
        fig.add_vline(x=state_share, line={"dash": "dash", "color": COL["highlight"]})
    fig.update_xaxes(title=f"Drought months (%); dotted = 15.9% normal, dashed = Odisha")
    fig.update_yaxes(tickfont={"size": 10})
    title = f"Ranking of {len(s)} Odisha districts, {period_text}"
    if selected != STATE_NAME and selected in districts.index:
        rank = int(districts.rank(ascending=False, method="min")[selected])     # ties share a rank
        title += f" — {selected} is #{rank}"
    elif state_share is not None:
        title += f" — whole Odisha: {state_share:.1f}%"
    _layout(fig, title, 520)
    fig.update_layout(showlegend=False, margin={"l": 140, "r": 20, "t": 50, "b": 45})
    return fig

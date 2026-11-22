"""Plotly chart builders with one consistent look.

Conventions
* Proportions are dots with 95% CI whiskers; a HOLLOW dot means the group has
  fewer than 40 respondents (descriptive only).
* Population groups keep the same colour on every page (colour follows the group).
* Ordered answer scales use a single-hue light-to-dark ramp.
* Every chart is paired with a table in the app (the table view).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from . import config as C

TEXT = "#0b0b0b"
TEXT_2 = "#52514e"
MUTED = "#8a8984"
GRID = "#e7e6e2"
SURFACE = "#ffffff"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
ALL_COLOR = "#3d3c39"
ORDINAL = {2: ["#86b6ef", "#1c5cab"], 3: ["#86b6ef", "#2a78d6", "#104281"],
           4: ["#86b6ef", "#3987e5", "#1c5cab", "#0d366b"],
           5: ["#86b6ef", "#5598e7", "#2a78d6", "#1c5cab", "#104281"],
           6: ["#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"],
           7: ["#9ec5f4", "#6da7ec", "#3987e5", "#2a78d6", "#1c5cab", "#104281", "#0d366b"],
           8: ["#b7d3f6", "#86b6ef", "#5598e7", "#3987e5", "#256abf", "#1c5cab", "#104281", "#0d366b"]}
FIXED = {C.GRP_DX: SERIES[0], C.GRP_SUSP: SERIES[1], C.GRP_NONE: SERIES[2], "All": ALL_COLOR}
FONT = "Inter, system-ui, -apple-system, Segoe UI, Roboto, sans-serif"


def color_map(groups: list[str]) -> dict[str, str]:
    if len(groups) == 1:  # a single series is the primary blue
        return {groups[0]: SERIES[0]}
    out, i = {}, 0
    for g in groups:
        if g in FIXED:
            out[g] = FIXED[g]
        else:
            out[g] = SERIES[i % len(SERIES)]
            i += 1
    return out


def _wrap(s: str, width: int = 42) -> str:
    words, lines, cur = str(s).split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 > width and cur:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    lines.append(cur)
    return "<br>".join(lines)


def _layout(fig: go.Figure, height: int, xtitle: str = "", pct: bool = True, legend: bool = True):
    fig.update_layout(
        height=height, margin=dict(l=8, r=24, t=36 if legend else 12, b=40),
        font=dict(family=FONT, size=13, color=TEXT_2), paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)", hoverlabel=dict(font=dict(family=FONT, size=13), bgcolor="white"),
        showlegend=legend,
        legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="left", x=0,
                    font=dict(size=12, color=TEXT_2), title=None, itemclick="toggle"),
    )
    fig.update_xaxes(showgrid=True, gridcolor=GRID, gridwidth=1, zeroline=False, linecolor=GRID,
                     ticks="", title=dict(text=xtitle, font=dict(size=12, color=TEXT_2)),
                     tickfont=dict(color=TEXT_2))
    if pct:
        fig.update_xaxes(range=[0, 1.0], tickformat=".0%", dtick=0.2)
    fig.update_yaxes(showgrid=False, linecolor=GRID, ticks="", tickfont=dict(color=TEXT, size=12.5),
                     automargin=True)
    return fig


def dot_ci(t: pd.DataFrame, label_col: str = "Indicator", group_order: list[str] | None = None,
           title_x: str = "% of respondents (95% CI)", show_all: bool = True) -> go.Figure:
    """Dot + CI whisker per (label, group). t has p, lo, hi, n, k, small, Group."""
    if t.empty:
        return go.Figure()
    groups = group_order or list(dict.fromkeys(t["Group"]))
    if not show_all:
        groups = [g for g in groups if g != "All"]
    groups = [g for g in groups if g in set(t["Group"])]
    labels = list(dict.fromkeys(t[label_col]))
    cmap = color_map(groups)
    ng = len(groups)
    band = 0.7
    offs = np.linspace(-band / 2, band / 2, ng) if ng > 1 else [0.0]
    fig = go.Figure()
    for gi, g in enumerate(groups):
        sub = t[t["Group"] == g].set_index(label_col).reindex(labels)
        y = [len(labels) - 1 - i + offs[gi] * -1 for i in range(len(labels))]
        small = sub["small"].fillna(True).astype(bool).to_numpy()
        col = cmap[g]
        fig.add_trace(go.Scatter(
            x=sub["p"], y=y, mode="markers", name=g, legendgroup=g,
            marker=dict(size=10, color=[SURFACE if s else col for s in small],
                        line=dict(color=[col if s else SURFACE for s in small], width=2), symbol="circle"),
            error_x=dict(type="data", symmetric=False, array=(sub["hi"] - sub["p"]),
                         arrayminus=(sub["p"] - sub["lo"]), color=col, thickness=2, width=0),
            customdata=np.stack([sub["k"].fillna(0), sub["n"].fillna(0), sub["lo"], sub["hi"],
                                 [lab for lab in labels]], axis=-1),
            hovertemplate=f"<b>{g}</b><br>%{{customdata[4]}}<br>%{{x:.0%}} "
                          "(95% CI %{customdata[2]:.0%}–%{customdata[3]:.0%})<br>"
                          "%{customdata[0]:.0f} of %{customdata[1]:.0f}<extra></extra>",
        ))
    fig.update_yaxes(tickvals=list(range(len(labels))), ticktext=[_wrap(l) for l in labels[::-1]],
                     range=[-0.6, len(labels) - 0.4])
    for i in range(len(labels) - 1):
        fig.add_hline(y=i + 0.5, line=dict(color=GRID, width=1))
    fig = _layout(fig, max(200, 90 + len(labels) * (26 + 14 * ng)), title_x, legend=ng > 1)
    fig.update_layout(legend=dict(y=1.02, yanchor="bottom"), margin=dict(t=48 if ng > 1 else 12))
    return fig


def bars(t: pd.DataFrame, label_col: str = "Option", group_order: list[str] | None = None,
         sort: bool = True, title_x: str = "% of respondents") -> go.Figure:
    """Horizontal bars of p per option; grouped when more than one group."""
    if t.empty:
        return go.Figure()
    groups = group_order or list(dict.fromkeys(t["Group"]))
    groups = [g for g in groups if g in set(t["Group"])]
    labels = list(dict.fromkeys(t[label_col]))
    if sort:
        tot = t[t["Group"] == groups[0]].set_index(label_col)["p"].reindex(labels)
        labels = list(tot.sort_values(ascending=True, na_position="first").index)
    else:
        labels = labels[::-1]
    cmap = color_map(groups)
    fig = go.Figure()
    for g in groups[::-1]:
        sub = t[t["Group"] == g].set_index(label_col).reindex(labels)
        fig.add_trace(go.Bar(
            y=[_wrap(l, 46) for l in labels], x=sub["p"], orientation="h", name=g,
            marker=dict(color=cmap[g], line=dict(color=SURFACE, width=2),
                        cornerradius=4),
            text=[f"{p:.0%}" if pd.notna(p) else "" for p in sub["p"]] if len(groups) <= 2 else None,
            textposition="outside", textfont=dict(color=TEXT_2, size=12), cliponaxis=False,
            customdata=np.stack([sub["k"].fillna(0), sub["n"].fillna(0), sub["lo"], sub["hi"]], axis=-1),
            hovertemplate=f"<b>{g}</b><br>%{{y}}<br>%{{x:.0%}} (95% CI %{{customdata[2]:.0%}}–"
                          "%{customdata[3]:.0%})<br>%{customdata[0]:.0f} of %{customdata[1]:.0f}<extra></extra>",
        ))
    fig.update_layout(barmode="group", bargap=0.35, bargroupgap=0.08)
    n_bars = len(labels) * len(groups)
    fig = _layout(fig, max(160, 50 + n_bars * 22 + len(labels) * 10), title_x, legend=len(groups) > 1)
    fig.update_layout(legend=dict(traceorder="reversed"))
    pmax = np.nanmax(t["p"].to_numpy(dtype=float)) if len(t) else 1
    fig.update_xaxes(range=[0, min(1.0, max(0.25, pmax * 1.18))])
    return fig


def stacked(t: pd.DataFrame, order: list[str], labels: dict[str, str] | None = None,
            group_order: list[str] | None = None, title_x: str = "% of respondents") -> go.Figure:
    """100% stacked horizontal bar per group for an ordered answer scale."""
    if t.empty:
        return go.Figure()
    groups = group_order or list(dict.fromkeys(t["Group"]))
    groups = [g for g in groups if g in set(t["Group"])]
    ramp = ORDINAL.get(len(order), ORDINAL[8])
    fig = go.Figure()
    ns = t.groupby("Group")["n"].first()
    ylab = [f"{g}  (n={int(ns.get(g, 0))})" for g in groups][::-1]
    for i, val in enumerate(order):
        sub = t[t["value"] == val].set_index("Group").reindex(groups[::-1])
        name = (labels or {}).get(val, val)
        fig.add_trace(go.Bar(
            y=ylab, x=sub["p"], orientation="h", name=_wrap(name, 34),
            marker=dict(color=ramp[i], line=dict(color=SURFACE, width=2)),
            hovertemplate=f"<b>{name}</b><br>%{{y}}<br>%{{x:.0%}}<extra></extra>",
        ))
    fig.update_layout(barmode="stack", bargap=0.45, legend=dict(traceorder="normal"))
    fig = _layout(fig, max(150, 90 + 40 * len(groups)), title_x)
    return fig


def flow(steps: list[tuple[str, int]]) -> go.Figure:
    labels = [s for s, _ in steps][::-1]
    vals = [v for _, v in steps][::-1]
    fig = go.Figure(go.Bar(
        y=[_wrap(l, 40) for l in labels], x=vals, orientation="h",
        marker=dict(color=SERIES[0], cornerradius=4), text=[f"{v:,}" for v in vals],
        textposition="outside", textfont=dict(color=TEXT_2), cliponaxis=False,
        hovertemplate="%{y}: %{x:,}<extra></extra>"))
    fig = _layout(fig, 60 + 44 * len(steps), "Respondents", pct=False, legend=False)
    fig.update_xaxes(range=[0, max(vals) * 1.15 if vals else 1])
    fig.update_layout(bargap=0.45)
    return fig


def effect_forest(df: pd.DataFrame, measure: str = "Difference (pp)") -> go.Figure:
    d = df[df["Effect measure"] == measure].dropna(subset=["Effect"])
    if d.empty:
        return go.Figure()
    labels = list(d["Outcome"])[::-1]
    d = d.iloc[::-1]
    scale = 100 if measure.startswith("Difference") else 1
    col = [SERIES[0]] * len(d)
    fig = go.Figure(go.Scatter(
        x=d["Effect"] * scale, y=[_wrap(l, 48) for l in labels], mode="markers",
        marker=dict(size=10, color=[SURFACE if s else c for s, c in zip(d["small"], col)],
                    line=dict(color=col, width=2)),
        error_x=dict(type="data", symmetric=False, array=(d["Effect high"] - d["Effect"]) * scale,
                     arrayminus=(d["Effect"] - d["Effect low"]) * scale, color=SERIES[0], thickness=2, width=0),
        customdata=np.stack([d["Effect low"] * scale, d["Effect high"] * scale, d["p"]], axis=-1),
        hovertemplate="%{y}<br>%{x:.1f} (95% CI %{customdata[0]:.1f} to %{customdata[1]:.1f})"
                      "<br>p = %{customdata[2]:.3f}<extra></extra>"))
    fig.add_vline(x=0, line=dict(color=MUTED, width=1))
    title = "Difference in percentage points (95% CI)" if scale == 100 else "Rank-biserial r (95% CI)"
    fig = _layout(fig, 70 + 36 * len(d), title, pct=False, legend=False)
    return fig


def or_forest(tab: pd.DataFrame) -> go.Figure:
    d = tab[tab["Term"] != "Intercept"].iloc[::-1]
    if d.empty:
        return go.Figure()
    fig = go.Figure(go.Scatter(
        x=d["OR"], y=list(d["Term"]), mode="markers",
        marker=dict(size=10, color=SERIES[0], line=dict(color=SURFACE, width=2)),
        error_x=dict(type="data", symmetric=False, array=d["OR high"] - d["OR"],
                     arrayminus=d["OR"] - d["OR low"], color=SERIES[0], thickness=2, width=0),
        hovertemplate="%{y}<br>OR %{x:.2f}<extra></extra>"))
    fig.add_vline(x=1, line=dict(color=MUTED, width=1))
    fig = _layout(fig, 80 + 40 * len(d), "Odds ratio (95% profile-likelihood CI, log scale)", pct=False,
                  legend=False)
    ticks = [0.1, 0.2, 0.25, 0.5, 1, 2, 4, 5, 10]
    lo = float(np.nanmin(d["OR low"])) if d["OR low"].notna().any() else 0.5
    hi = float(np.nanmax(d["OR high"])) if d["OR high"].notna().any() else 2
    tv = [t for t in ticks if lo / 1.3 <= t <= hi * 1.3] or [0.5, 1, 2]
    fig.update_xaxes(type="log", tickvals=tv, ticktext=[f"{t:g}" for t in tv])
    return fig


def missing_bars(m: pd.DataFrame) -> go.Figure:
    d = m.iloc[::-1]
    fig = go.Figure(go.Bar(
        y=d["Section"], x=d["% missing"], orientation="h",
        marker=dict(color=SERIES[0], cornerradius=4),
        text=[f"{p:.1%}" for p in d["% missing"]], textposition="outside", cliponaxis=False,
        textfont=dict(color=TEXT_2), hovertemplate="%{y}: %{x:.1%}<extra></extra>"))
    fig.add_vline(x=C.MISSING_FLAG, line=dict(color="#d03b3b", width=1))
    fig = _layout(fig, 60 + 30 * len(d), "Item non-response among women shown the items", pct=False,
                  legend=False)
    fig.update_xaxes(tickformat=".0%", range=[0, max(0.15, float(np.nanmax(d["% missing"])) * 1.3 if len(d) else 0.15)])
    return fig

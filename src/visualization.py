"""Plotly bubble-chart builder shared by the Sectoral and Micro pages.

The chart is a configurable "market map": X/Y position, bubble size and color
are all driven by `config` keys resolved through metrics.py. Quadrant
boundaries always come from the FULL universe passed in as `df_universe`.
"""
import math

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from src.analytics import QUADRANT_COLORS, assign_quadrants, scale_bubble_sizes, universe_medians
from src.metrics import COLOR_OPTIONS, DEFAULT_CHART_CONFIG, METRICS, SIZE_OPTIONS, TOOLTIP_FIELDS

POS_COLOR = "#16A34A"
NEG_COLOR = "#DC2626"
NEUTRAL_COLOR = "#9CA3AF"
SELECTED_RING = "#0F172A"
GUIDE_COLOR = "#2563EB"


def _fmt_num(value) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "N/A"
    return f"{value:,.2f}"


def _hover_text(row: pd.Series, fields, quadrant) -> str:
    parts = []
    for label, column, fmt in fields:
        value = row.get(column)
        if value is None or (isinstance(value, float) and (math.isnan(value) or pd.isna(value))):
            continue  # skip unavailable fields entirely
        rendered = fmt.format(value) if fmt else str(value)
        parts.append(f"<b>{label}:</b> {rendered}")
    if quadrant is not None and not (isinstance(quadrant, float) and math.isnan(quadrant)):
        parts.append(f"<b>Quadrant:</b> {quadrant}")
    return "<br>".join(parts)


def build_bubble_figure(
    df_plot: pd.DataFrame,
    df_universe: pd.DataFrame,
    config: dict | None = None,
    *,
    name_col: str = "Company",
    symbol_col: str = "NSE Symbol",
    hover_fields=None,
    selected_label: str | None = None,
    log_x: bool = True,
    title: str = "",
    height: int = 680,
) -> go.Figure:
    cfg = {**DEFAULT_CHART_CONFIG, **(config or {})}
    x_m, y_m = METRICS[cfg["x"]], METRICS[cfg["y"]]
    size_col, size_label, size_abs = SIZE_OPTIONS[cfg["size"]]
    color_col, color_label = COLOR_OPTIONS[cfg["color"]]

    x_col, y_col = x_m.column, y_m.column
    med_x, med_y = universe_medians(df_universe, x_col, y_col)

    plot = df_plot.copy()
    plot["Quadrant"] = assign_quadrants(plot, x_col, y_col, med_x, med_y)
    plotted = plot.dropna(subset=[x_col, y_col]).copy()
    if plotted.empty:
        fig = go.Figure()
        fig.update_layout(
            template="plotly_white",
            height=height,
            title=title or "No companies can be positioned on this chart",
            annotations=[dict(text="No valid data for the selected axes", showarrow=False, font=dict(size=16))],
        )
        return fig

    # --- encodings -------------------------------------------------------
    sizes = scale_bubble_sizes(plotted[size_col])
    raw_color = plotted[color_col]
    colors = np.where(raw_color.isna(), NEUTRAL_COLOR, np.where(raw_color > 0, POS_COLOR, NEG_COLOR))

    fields = hover_fields if hover_fields is not None else TOOLTIP_FIELDS
    hover_texts = [
        _hover_text(row, fields, row["Quadrant"])
        for _, row in plotted.iterrows()
    ]

    dimmed = selected_label is not None
    base_opacity = 0.12 if dimmed else 0.62

    fig = go.Figure(
        go.Scatter(
            x=plotted[x_col],
            y=plotted[y_col],
            mode="markers",
            marker=dict(
                size=sizes,
                color=colors,
                opacity=base_opacity,
                line=dict(width=1, color="rgba(15,23,42,0.25)"),
            ),
            text=hover_texts,
            hoverinfo="text",
            hoverlabel=dict(bgcolor="#FFFFFF", bordercolor="#CBD5E1", font=dict(color="#0F172A")),
            customdata=plotted[symbol_col] if symbol_col in plotted.columns else None,
            showlegend=False,
        )
    )

    # --- selected stock highlight ----------------------------------------
    if dimmed:
        sel_mask = plotted[symbol_col] == selected_label if symbol_col in plotted.columns else None
        if sel_mask is not None and sel_mask.any():
            sel = plotted[sel_mask].iloc[0]
            sel_size = float(sizes[sel_mask].iloc[0])
            sel_color = (
                NEUTRAL_COLOR
                if pd.isna(sel[color_col])
                else (POS_COLOR if sel[color_col] > 0 else NEG_COLOR)
            )
            fig.add_trace(
                go.Scatter(
                    x=[sel[x_col]],
                    y=[sel[y_col]],
                    mode="markers",
                    marker=dict(
                        size=sel_size * 1.2,
                        color=sel_color,
                        opacity=0.95,
                        line=dict(width=3, color=SELECTED_RING),
                    ),
                    hoverinfo="skip",
                    showlegend=False,
                )
            )
            fig.add_vline(x=sel[x_col], line_width=1.2, line_dash="dot", line_color=GUIDE_COLOR)
            fig.add_hline(y=sel[y_col], line_width=1.2, line_dash="dot", line_color=GUIDE_COLOR)

    # --- quadrant boundaries (FULL-universe medians) ----------------------
    fig.add_vline(x=med_x, line_width=1.4, line_dash="dash", line_color="#94A3B8")
    fig.add_hline(y=med_y, line_width=1.4, line_dash="dash", line_color="#94A3B8")

    # --- quadrant labels (paper coords; robust across log/linear axes) ----
    label_style = dict(showarrow=False, font=dict(size=13, color="#64748B"), opacity=0.85)
    fig.add_annotation(xref="paper", yref="paper", x=0.03, y=0.97, text="<b>Growth + Value</b>",
                       xanchor="left", yanchor="top", **label_style)
    fig.add_annotation(xref="paper", yref="paper", x=0.97, y=0.97, text="<b>Growth + Premium</b>",
                       xanchor="right", yanchor="top", **label_style)
    fig.add_annotation(xref="paper", yref="paper", x=0.03, y=0.03, text="<b>Value + Low Growth</b>",
                       xanchor="left", yanchor="bottom", **label_style)
    fig.add_annotation(xref="paper", yref="paper", x=0.97, y=0.03, text="<b>Expensive + Low Growth</b>",
                       xanchor="right", yanchor="bottom", **label_style)

    fig.update_layout(
        template="plotly_white",
        title=title,
        height=height,
        margin=dict(l=10, r=10, t=60, b=10),
        xaxis=dict(
            title=f"{x_m.label} {'(log)' if log_x else ''}",
            type="log" if log_x else "linear",
            gridcolor="#F1F5F9",
            zeroline=False,
        ),
        yaxis=dict(title=y_m.label, gridcolor="#F1F5F9", zeroline=False),
        clickmode="event+select",
    )

    # Keep genuine outliers: no range clipping is applied anywhere above.
    return fig

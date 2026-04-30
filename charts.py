"""
charts.py — Plotly chart builders for FDA Device Recall Explorer.
Clinical white SaaS palette: white/gray backgrounds, Inter font,
minimal chrome, Class I in red.
"""

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

# ── Palette ───────────────────────────────────────────────────────────────────
C = {
    "bg":       "#ffffff",
    "page":     "#f9fafb",
    "border":   "#e5e7eb",
    "ink":      "#111827",
    "muted":    "#6b7280",
    "subtle":   "#9ca3af",
    "surface":  "#f3f4f6",

    # Classification — semantically correct colours
    "cls1":     "#dc2626",   # Class I   — red    (most serious)
    "cls1_bg":  "#fef2f2",
    "cls2":     "#2563eb",   # Class II  — blue
    "cls2_bg":  "#eff6ff",
    "cls3":     "#059669",   # Class III — green  (least serious)
    "cls3_bg":  "#f0fdf4",
    "unk":      "#9ca3af",
}

CLASS_COLORS = {
    "Class I":   C["cls1"],
    "Class II":  C["cls2"],
    "Class III": C["cls3"],
    "Unknown":   C["unk"],
}

_FONT = "'Inter', -apple-system, sans-serif"

_BASE = dict(
    paper_bgcolor=C["bg"],
    plot_bgcolor =C["bg"],
    font=dict(family=_FONT, color=C["muted"], size=11),
    margin=dict(l=12, r=12, t=40, b=12),
    legend=dict(
        bgcolor=C["bg"],
        bordercolor=C["border"],
        borderwidth=1,
        font=dict(size=10),
    ),
    xaxis=dict(
        gridcolor=C["border"],
        linecolor=C["border"],
        tickfont=dict(size=10, color=C["muted"]),
        title_font=dict(size=10, color=C["muted"]),
        showgrid=True,
        zeroline=False,
    ),
    yaxis=dict(
        gridcolor=C["border"],
        linecolor=C["border"],
        tickfont=dict(size=10, color=C["muted"]),
        title_font=dict(size=10, color=C["muted"]),
        showgrid=True,
        zeroline=False,
    ),
)


def _apply(fig: go.Figure, title="", height=340) -> go.Figure:
    fig.update_layout(
        **_BASE,
        height=height,
        title=dict(
            text=title,
            font=dict(size=11, color=C["muted"], family=_FONT),
            x=0, xanchor="left",
        ),
    )
    return fig


# ── Chart 1: Trend ────────────────────────────────────────────────────────────

def chart_trend_over_time(df: pd.DataFrame, freq: str = "M") -> go.Figure:
    if df.empty or "initiated_date" not in df.columns:
        return _empty("No data available.")

    df2 = df.dropna(subset=["initiated_date"]).copy()
    if df2.empty:
        return _empty("No dated records to plot.")

    df2["period"] = df2["initiated_date"].dt.to_period(freq).dt.to_timestamp()
    grouped = (
        df2.groupby(["period", "classification"])
        .size()
        .reset_index(name="count")
        .sort_values("period")
    )

    fig = go.Figure()
    for cls in ["Class I", "Class II", "Class III", "Unknown"]:
        if cls not in grouped["classification"].unique():
            continue
        sub   = grouped[grouped["classification"] == cls]
        color = CLASS_COLORS[cls]
        fig.add_trace(go.Scatter(
            x=sub["period"],
            y=sub["count"],
            name=cls,
            mode="lines+markers",
            line=dict(color=color, width=2),
            marker=dict(size=4, color=color),
            hovertemplate=f"<b>{cls}</b><br>%{{x|%b %Y}}: %{{y}} recalls<extra></extra>",
        ))

    label = "Monthly" if freq == "M" else "Quarterly"
    _apply(fig, title=f"Recall Trend — {label}", height=320)
    fig.update_layout(hovermode="x unified")
    fig.update_xaxes(title_text="")
    fig.update_yaxes(title_text="Recalls")
    return fig


# ── Chart 2: Top manufacturers ────────────────────────────────────────────────

def chart_top_manufacturers(df: pd.DataFrame, top_n: int = 15) -> go.Figure:
    if df.empty:
        return _empty("No data available.")

    counts = (
        df["recalling_firm"].value_counts()
        .head(top_n).reset_index()
    )
    counts.columns = ["firm", "count"]
    counts = counts.sort_values("count")

    fig = go.Figure(go.Bar(
        x=counts["count"],
        y=counts["firm"],
        orientation="h",
        marker=dict(color=C["ink"], opacity=0.8, line_width=0),
        text=counts["count"],
        textposition="outside",
        textfont=dict(size=10, color=C["muted"]),
        hovertemplate="<b>%{y}</b><br>%{x} recalls<extra></extra>",
    ))

    _apply(fig, title=f"Top {top_n} Recalling Manufacturers",
           height=max(320, top_n * 28))
    fig.update_xaxes(title_text="Recall Count")
    fig.update_yaxes(tickfont=dict(size=10))
    return fig


# ── Chart 3: Class distribution ───────────────────────────────────────────────

def chart_class_distribution(df: pd.DataFrame) -> go.Figure:
    if df.empty:
        return _empty("No data.")

    counts = df["classification"].value_counts().reset_index()
    counts.columns = ["cls", "count"]

    fig = go.Figure(go.Pie(
        labels=counts["cls"],
        values=counts["count"],
        hole=0.6,
        marker=dict(
            colors=[CLASS_COLORS.get(c, C["unk"]) for c in counts["cls"]],
            line=dict(color=C["bg"], width=3),
        ),
        textinfo="label+percent",
        textfont=dict(size=10, family=_FONT),
        hovertemplate="%{label}<br>%{value:,} recalls (%{percent})<extra></extra>",
    ))

    _apply(fig, title="By Classification", height=290)
    fig.update_layout(showlegend=False, margin=dict(l=8, r=8, t=40, b=0))
    return fig


# ── Chart 4: Recall reason keywords ──────────────────────────────────────────

REASON_KEYWORDS = [
    "sterility", "labeling", "software", "contamination", "mislabeled",
    "packaging", "failure", "malfunction", "leakage", "breakage",
    "biocompatibility", "incorrect", "missing", "design", "manufacturing",
    "specification", "corrosion", "fracture", "electrical", "software defect",
]

def chart_recall_reasons(df: pd.DataFrame, top_n: int = 14) -> go.Figure:
    if df.empty:
        return _empty("No recall reason data.")

    combined = (
        df["reason_for_recall"].fillna("") + " " +
        df.get("root_cause", pd.Series("", index=df.index)).fillna("")
    ).str.lower()

    counts = {}
    for kw in REASON_KEYWORDS:
        n = combined.str.contains(kw, regex=False).sum()
        if n > 0:
            counts[kw.title()] = int(n)

    if not counts:
        return _empty("No keyword matches found.")

    kw_df = (
        pd.Series(counts).sort_values(ascending=True)
        .tail(top_n).reset_index()
    )
    kw_df.columns = ["keyword", "count"]

    fig = go.Figure(go.Bar(
        x=kw_df["count"],
        y=kw_df["keyword"],
        orientation="h",
        marker=dict(color=C["ink"], opacity=0.75, line_width=0),
        text=kw_df["count"],
        textposition="outside",
        textfont=dict(size=10, color=C["muted"]),
        hovertemplate="<b>%{y}</b><br>%{x} records<extra></extra>",
    ))

    _apply(fig, title=f"Recall Reason Keywords — {len(df):,} records",
           height=max(260, len(kw_df) * 30))
    fig.update_xaxes(title_text="Count")
    return fig


# ── Chart 5: Recall status ────────────────────────────────────────────────────

def chart_recall_status(df: pd.DataFrame) -> go.Figure:
    if df.empty or "recall_status" not in df.columns:
        return _empty("No recall status data.")

    df2 = df[df["recall_status"].notna() & (df["recall_status"] != "")].copy()
    if df2.empty:
        return _empty("No status values in current results.")

    grouped = (
        df2.groupby(["classification", "recall_status"])
        .size().reset_index(name="count")
    )

    status_colors = {
        "Ongoing":    "#f59e0b",
        "Completed":  "#059669",
        "Terminated": "#9ca3af",
        "Open":       "#dc2626",
    }

    fig = go.Figure()
    for status in grouped["recall_status"].unique():
        sub = grouped[grouped["recall_status"] == status]
        fig.add_trace(go.Bar(
            x=sub["classification"],
            y=sub["count"],
            name=status,
            marker_color=status_colors.get(status, C["muted"]),
            marker_opacity=0.85,
            marker_line_width=0,
            hovertemplate=f"<b>{status}</b><br>%{{x}}: %{{y}} recalls<extra></extra>",
        ))

    _apply(fig, title="Recall Status by Classification", height=280)
    fig.update_layout(barmode="group", xaxis_title="")
    return fig


# ── Chart 6: State map ────────────────────────────────────────────────────────

def chart_state_map(df: pd.DataFrame) -> go.Figure:
    if df.empty or "state" not in df.columns:
        return _empty("No state data available.")

    state_counts = df["state"].value_counts().reset_index()
    state_counts.columns = ["state", "count"]
    state_counts = state_counts[state_counts["state"].str.match(r"^[A-Z]{2}$")]
    if state_counts.empty:
        return _empty("No valid US state data.")

    fig = go.Figure(go.Choropleth(
        locations=state_counts["state"],
        z=state_counts["count"],
        locationmode="USA-states",
        colorscale=[
            [0,   "#f3f4f6"],
            [0.25, "#d1d5db"],
            [0.6,  "#6b7280"],
            [1,    "#111827"],
        ],
        showscale=True,
        colorbar=dict(
            title=dict(text="Recalls", font=dict(size=10, color=C["muted"], family=_FONT)),
            tickfont=dict(size=9, color=C["muted"], family=_FONT),
            bgcolor=C["bg"],
            outlinewidth=0,
            len=0.65,
        ),
        hovertemplate="<b>%{location}</b><br>%{z} recalls<extra></extra>",
        marker_line_color=C["border"],
        marker_line_width=0.5,
    ))

    _apply(fig, title="Recalls by State (Firm Location)", height=360)
    fig.update_layout(
        geo=dict(
            scope="usa",
            bgcolor=C["bg"],
            lakecolor=C["page"],
            landcolor=C["surface"],
            showlakes=True,
            showframe=False,
            coastlinecolor=C["border"],
        ),
    )
    return fig


# ── Empty placeholder ─────────────────────────────────────────────────────────

def _empty(message: str, height: int = 240) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(
        text=message,
        xref="paper", yref="paper",
        x=0.5, y=0.5, showarrow=False,
        font=dict(color=C["muted"], size=12, family=_FONT),
    )
    _apply(fig, height=height)
    return fig

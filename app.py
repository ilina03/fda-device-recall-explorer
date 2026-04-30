"""
app.py — FDA Device Recall Explorer
Clean clinical white SaaS aesthetic
"""

import streamlit as st
import pandas as pd
from datetime import date

from api import fetch_recalls, get_date_range_default, CLASSIFICATION_VALUES
from charts import (
    chart_trend_over_time,
    chart_top_manufacturers,
    chart_class_distribution,
    chart_recall_reasons,
    chart_recall_status,
    chart_state_map,
)

st.set_page_config(
    page_title="FDA Device Recall Explorer",
    page_icon="⚕",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, sans-serif;
    background-color: #f9fafb;
    color: #111827;
    font-size: 14px;
}

/* ── sidebar ── */
[data-testid="stSidebar"] {
    background-color: #ffffff;
    border-right: 1px solid #e5e7eb;
}
[data-testid="stSidebar"] * { color: #111827 !important; }
[data-testid="stSidebar"] .stMarkdown p {
    font-size: 0.68rem;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    color: #6b7280 !important;
}

/* ── main ── */
.main .block-container {
    padding-top: 1.5rem;
    padding-bottom: 3rem;
    max-width: 1400px;
    background: #f9fafb;
}

/* ── page header ── */
.page-title {
    font-size: 1.2rem;
    font-weight: 600;
    color: #111827;
    letter-spacing: -0.02em;
    margin: 0;
}
.page-meta {
    font-size: 0.78rem;
    color: #6b7280;
    margin: 0.2rem 0 1.25rem;
}
.page-meta a { color: #2563eb; text-decoration: none; }

/* ── metric cards ── */
[data-testid="metric-container"] {
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    padding: 1rem 1.1rem;
}
[data-testid="stMetricValue"] {
    font-size: 1.75rem !important;
    font-weight: 600 !important;
    color: #111827 !important;
    line-height: 1.1;
    font-family: 'Inter', sans-serif !important;
}
[data-testid="stMetricLabel"] {
    font-size: 0.68rem !important;
    font-weight: 500 !important;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    color: #9ca3af !important;
}
[data-testid="stMetricDelta"] svg { display: none; }

/* ── tabs ── */
[data-baseweb="tab-list"] {
    background: transparent !important;
    border-bottom: 1px solid #e5e7eb !important;
    gap: 0;
    padding: 0;
}
[data-baseweb="tab"] {
    background: transparent !important;
    color: #6b7280 !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.82rem !important;
    font-weight: 500 !important;
    padding: 0.6rem 1rem !important;
    border-radius: 0 !important;
    border-bottom: 2px solid transparent !important;
}
[aria-selected="true"][data-baseweb="tab"] {
    color: #111827 !important;
    border-bottom: 2px solid #111827 !important;
    background: transparent !important;
}

/* ── dataframes ── */
[data-testid="stDataFrame"] {
    border: 1px solid #e5e7eb !important;
    border-radius: 8px;
}

/* ── inputs ── */
[data-testid="stTextInput"] input {
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 6px;
    font-size: 0.85rem;
    color: #111827;
}
[data-testid="stTextInput"] input:focus {
    border-color: #2563eb;
    box-shadow: 0 0 0 3px rgba(37,99,235,0.1);
}

/* ── buttons ── */
[data-testid="stButton"] > button,
[data-testid="stDownloadButton"] > button {
    background: #ffffff;
    border: 1px solid #e5e7eb;
    color: #374151;
    font-family: 'Inter', sans-serif;
    font-size: 0.8rem;
    font-weight: 500;
    border-radius: 6px;
    padding: 0.4rem 1rem;
    transition: all 0.12s;
}
[data-testid="stButton"] > button:hover,
[data-testid="stDownloadButton"] > button:hover {
    background: #f3f4f6;
    border-color: #d1d5db;
    color: #111827;
}

/* ── callout ── */
.callout {
    background: #eff6ff;
    border: 1px solid #bfdbfe;
    border-radius: 6px;
    padding: 0.65rem 1rem;
    font-size: 0.8rem;
    color: #1e40af;
    margin-bottom: 0.8rem;
    line-height: 1.55;
}
.callout code {
    font-size: 0.75rem;
    background: #dbeafe;
    padding: 1px 4px;
    border-radius: 3px;
}

/* ── section labels ── */
.section-label {
    font-size: 0.68rem;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    color: #6b7280;
    margin: 0.6rem 0 0.35rem;
}

/* ── hr ── */
hr { border: none; border-top: 1px solid #e5e7eb; margin: 0.75rem 0; }

footer { visibility: hidden; }
#MainMenu { visibility: hidden; }
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("**Filters**")
    st.markdown("<hr>", unsafe_allow_html=True)

    st.markdown('<p class="section-label">Device Classification</p>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    selected_classes = []
    for col, cls, short in zip(
        [c1, c2, c3],
        ["Class I", "Class II", "Class III"],
        ["I", "II", "III"],
    ):
        with col:
            if st.checkbox(short, value=True, key=f"cls_{cls}"):
                selected_classes.append(cls)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<p class="section-label">Date Range</p>', unsafe_allow_html=True)
    default_start_str, default_end_str = get_date_range_default()
    date_start = st.date_input(
        "From", value=date.fromisoformat(default_start_str),
        min_value=date(2004, 1, 1), max_value=date.today(),
        label_visibility="collapsed",
    )
    date_end = st.date_input(
        "To", value=date.fromisoformat(default_end_str),
        min_value=date(2004, 1, 1), max_value=date.today(),
        label_visibility="collapsed",
    )

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<p class="section-label">Reason Keyword</p>', unsafe_allow_html=True)
    keyword = st.text_input(
        "keyword", placeholder="e.g. sterility, software, labeling",
        label_visibility="collapsed",
    )

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<p class="section-label">Max Records</p>', unsafe_allow_html=True)
    max_records = st.selectbox(
        "max", options=[100, 250, 500, 1000, 2000], index=2,
        label_visibility="collapsed",
        help="Results cached for 1 hour per filter combination.",
    )

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<p class="section-label">Trend Granularity</p>', unsafe_allow_html=True)
    freq = "M" if st.radio(
        "freq", ["Monthly", "Quarterly"], horizontal=True,
        label_visibility="collapsed",
    ) == "Monthly" else "Q"

    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown(
        '<p style="font-size:0.7rem;color:#9ca3af;line-height:1.6;">'
        'Source: <a href="https://open.fda.gov/apis/device/recall/" '
        'style="color:#2563eb;text-decoration:none;">openFDA /device/recall</a><br>'
        'Medical devices only · Not for clinical use<br>'
        'FDA data updated weekly</p>',
        unsafe_allow_html=True,
    )


# ══════════════════════════════════════════════════════════════════
# FETCH
# ══════════════════════════════════════════════════════════════════
if not selected_classes:
    st.warning("Select at least one device classification in the sidebar.")
    st.stop()

with st.spinner("Loading from openFDA..."):
    try:
        df = fetch_recalls(
            classifications=tuple(selected_classes),
            start_date=date_start.strftime("%Y-%m-%d"),
            end_date=date_end.strftime("%Y-%m-%d"),
            keyword=keyword.strip() or None,
            max_records=max_records,
        )
    except RuntimeError as e:
        st.error(f"API Error: {e}")
        st.stop()


# ══════════════════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════════════════
st.markdown(
    '<p class="page-title">FDA Device Recall Explorer</p>'
    '<p class="page-meta">'
    'Data from <a href="https://open.fda.gov/apis/device/recall/">openFDA</a> · '
    'Updated weekly by the FDA · For research use only</p>',
    unsafe_allow_html=True,
)

if df.empty:
    st.info("No records match the current filters. Try widening the date range or removing the keyword.")
    st.stop()


# ══════════════════════════════════════════════════════════════════
# KPI ROW
# ══════════════════════════════════════════════════════════════════
m1, m2, m3, m4, m5, m6 = st.columns(6)

total  = len(df)
n1     = (df["classification"] == "Class I").sum()
n2     = (df["classification"] == "Class II").sum()
n3     = (df["classification"] == "Class III").sum()
nfirms = df["recalling_firm"].nunique()
span   = (
    f"{df['initiated_date'].min().strftime('%b \'%y')} – "
    f"{df['initiated_date'].max().strftime('%b \'%y')}"
    if df["initiated_date"].notna().any() else "N/A"
)

m1.metric("Total Recalls", f"{total:,}")
m2.metric("Class I",       f"{n1:,}",   help="Most serious — may cause death or serious injury")
m3.metric("Class II",      f"{n2:,}",   help="May cause temporary or reversible consequences")
m4.metric("Class III",     f"{n3:,}",   help="Least likely to cause adverse health consequences")
m5.metric("Manufacturers", f"{nfirms:,}")
m6.metric("Span",          span)

st.markdown("<hr>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════
# TABS
# ══════════════════════════════════════════════════════════════════
tab_trend, tab_mfr, tab_reasons, tab_geo, tab_data = st.tabs([
    "Trend",
    "Manufacturers",
    "Recall Reasons",
    "Geography",
    "Raw Data",
])


# ── Trend ─────────────────────────────────────────────────────────
with tab_trend:
    col_left, col_right = st.columns([3, 1], gap="large")
    with col_left:
        st.plotly_chart(
            chart_trend_over_time(df, freq=freq),
            use_container_width=True, config={"displayModeBar": False},
        )
    with col_right:
        st.plotly_chart(
            chart_class_distribution(df),
            use_container_width=True, config={"displayModeBar": False},
        )
    st.plotly_chart(
        chart_recall_status(df),
        use_container_width=True, config={"displayModeBar": False},
    )


# ── Manufacturers ─────────────────────────────────────────────────
with tab_mfr:
    top_n = st.slider("Top N manufacturers", 5, 30, 15, step=5)
    st.plotly_chart(
        chart_top_manufacturers(df, top_n=top_n),
        use_container_width=True, config={"displayModeBar": False},
    )

    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown('<p class="section-label">Manufacturer Detail</p>', unsafe_allow_html=True)

    mfr_table = (
        df.groupby("recalling_firm")
        .agg(
            Recalls  =("recall_number",  "count"),
            Class_I  =("classification", lambda x: (x == "Class I").sum()),
            Class_II =("classification", lambda x: (x == "Class II").sum()),
            Class_III=("classification", lambda x: (x == "Class III").sum()),
            States   =("state",          lambda x: ", ".join(sorted(x.dropna().unique())[:4])),
            Earliest =("initiated_date", lambda x: x.dropna().min().strftime("%Y-%m-%d") if len(x.dropna()) > 0 else ""),
            Latest   =("initiated_date", lambda x: x.dropna().max().strftime("%Y-%m-%d") if len(x.dropna()) > 0 else ""),
        )
        .sort_values("Recalls", ascending=False)
        .reset_index()
        .rename(columns={"recalling_firm": "Manufacturer"})
    )
    st.dataframe(mfr_table, use_container_width=True, hide_index=True)


# ── Recall Reasons ────────────────────────────────────────────────
with tab_reasons:
    st.markdown(
        '<div class="callout">Keywords matched against <code>reason_for_recall</code> and '
        '<code>root_cause_description</code> free-text fields. A single record may match '
        'multiple keywords. Use the sidebar keyword filter to drill into a specific failure mode.</div>',
        unsafe_allow_html=True,
    )
    st.plotly_chart(
        chart_recall_reasons(df, top_n=14),
        use_container_width=True, config={"displayModeBar": False},
    )

    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown('<p class="section-label">Sample Recall Reasons — 50 Most Recent</p>',
                unsafe_allow_html=True)

    reasons_df = (
        df[["recall_number", "classification", "recalling_firm",
            "reason_for_recall", "root_cause", "initiated_date"]]
        .dropna(subset=["reason_for_recall"])
        .sort_values("initiated_date", ascending=False)
        .head(50)
    )
    reasons_df["initiated_date"] = reasons_df["initiated_date"].dt.strftime("%Y-%m-%d")
    reasons_df.columns = ["Recall #", "Class", "Firm", "Reason for Recall", "Root Cause", "Date"]
    st.dataframe(reasons_df, use_container_width=True, hide_index=True)


# ── Geography ─────────────────────────────────────────────────────
with tab_geo:
    col_map, col_tbl = st.columns([3, 1], gap="large")
    with col_map:
        st.plotly_chart(
            chart_state_map(df),
            use_container_width=True, config={"displayModeBar": False},
        )
    with col_tbl:
        st.markdown('<p class="section-label">Recalls by State</p>', unsafe_allow_html=True)
        state_df = df["state"].value_counts().reset_index()
        state_df.columns = ["State", "Recalls"]
        st.dataframe(state_df, use_container_width=True, hide_index=True, height=340)


# ── Raw Data ──────────────────────────────────────────────────────
with tab_data:
    row = st.columns([3, 1])
    with row[0]:
        search = st.text_input(
            "Search", placeholder="Filter by any text across all columns...",
            label_visibility="collapsed",
        )

    display_df = df.copy()
    display_df["initiated_date"] = display_df["initiated_date"].dt.strftime("%Y-%m-%d")

    if search:
        mask = display_df.apply(
            lambda r: r.astype(str).str.contains(search, case=False).any(), axis=1,
        )
        display_df = display_df[mask]

    cols = [c for c in [
        "recall_number", "classification", "recall_status", "recalling_firm",
        "product_description", "reason_for_recall", "root_cause",
        "initiated_date", "state", "product_code", "device_name",
    ] if c in display_df.columns]

    st.markdown(f'<p class="section-label">{len(display_df):,} records</p>',
                unsafe_allow_html=True)
    st.dataframe(display_df[cols], use_container_width=True, hide_index=True)

    with row[1]:
        st.download_button(
            label="Export CSV",
            data=display_df[cols].to_csv(index=False).encode(),
            file_name=f"fda_device_recalls_{date.today().isoformat()}.csv",
            mime="text/csv",
        )

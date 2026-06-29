import streamlit as st
import feedparser
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import urllib.parse
import html
import re

# ── Page config ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="India Auto Competitor Intelligence Dashboard",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Theme / CSS ──────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    /* Base background */
    .stApp { background-color: #F7FAFD; }

    /* Sidebar */
    section[data-testid="stSidebar"] { background-color: #002C5F; }
    section[data-testid="stSidebar"] * { color: #FFFFFF !important; }
    section[data-testid="stSidebar"] .stSelectbox label,
    section[data-testid="stSidebar"] .stMultiselect label { color: #BFD9F0 !important; }

    /* Header banner */
    .dashboard-header {
        background: linear-gradient(135deg, #002C5F 0%, #007FA8 100%);
        padding: 2rem 2.5rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        color: #FFFFFF;
    }
    .dashboard-header h1 { margin: 0; font-size: 2rem; font-weight: 700; letter-spacing: 0.02em; }
    .dashboard-header p  { margin: 0.4rem 0 0; font-size: 0.95rem; opacity: 0.85; }

    /* KPI cards */
    .kpi-card {
        background: #FFFFFF;
        border-radius: 10px;
        padding: 1.25rem 1.5rem;
        border-left: 5px solid #007FA8;
        box-shadow: 0 2px 8px rgba(0,44,95,0.08);
        height: 100%;
    }
    .kpi-label { font-size: 0.78rem; color: #5A7290; font-weight: 600; text-transform: uppercase; letter-spacing: 0.06em; }
    .kpi-value { font-size: 2rem; color: #002C5F; font-weight: 800; margin-top: 0.25rem; line-height: 1; }
    .kpi-sub   { font-size: 0.82rem; color: #007FA8; margin-top: 0.35rem; font-weight: 500; }

    /* Section headings */
    .section-heading {
        font-size: 1.05rem;
        font-weight: 700;
        color: #002C5F;
        border-bottom: 2px solid #007FA8;
        padding-bottom: 0.35rem;
        margin-bottom: 1rem;
    }

    /* Article table links */
    a { color: #007FA8 !important; text-decoration: none; }
    a:hover { text-decoration: underline; }

    /* Disclaimer banner */
    .disclaimer {
        background: #E8F1FA;
        border-left: 4px solid #007FA8;
        border-radius: 6px;
        padding: 0.75rem 1.25rem;
        font-size: 0.82rem;
        color: #5A7290;
        margin-top: 1rem;
    }

    /* Hide Streamlit default top padding */
    .block-container { padding-top: 1rem !important; }

    /* DataFrame styling */
    .stDataFrame { border-radius: 8px; overflow: hidden; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Constants ────────────────────────────────────────────────────────────────
COMPETITORS = {
    "Tata Motors":       "Tata Motors India car",
    "Mahindra":          "Mahindra car India",
    "Maruti Suzuki":     "Maruti Suzuki India",
    "Kia India":         "Kia India car",
    "Toyota India":      "Toyota India car",
    "MG Motor India":    "MG Motor India",
    "Honda Cars India":  "Honda Cars India",
    "Skoda India":       "Skoda India",
    "Volkswagen India":  "Volkswagen India",
    "Renault India":     "Renault India",
}

CATEGORIES = {
    "EV":         ["ev", "electric", "battery", "charging", "bev"],
    "Hybrid":     ["hybrid", "hev"],
    "Investment": ["investment", "invest", "plant", "factory", "capacity", "expansion", "manufacturing"],
    "Launch":     ["launch", "unveil", "facelift", "booking", "debut", "introduced", "variant"],
    "Price":      ["price", "discount", "hike", "increase", "cut", "offer"],
    "Export":     ["export", "shipment", "overseas", "global market"],
    "Policy":     ["policy", "regulation", "gst", "emission", "cafe", "subsidy", "tax"],
}

BRAND_COLORS = [
    "#002C5F", "#007FA8", "#1E6B9A", "#2E86C1", "#3498DB",
    "#5DADE2", "#7FB3D3", "#A9CCE3", "#6A89A7", "#4A7FA5",
]

PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, sans-serif", color="#002C5F"),
    margin=dict(l=20, r=20, t=40, b=20),
)


# ── Helpers ──────────────────────────────────────────────────────────────────
def categorize(text: str) -> str:
    t = text.lower()
    for cat, kws in CATEGORIES.items():
        if any(re.search(r"\b" + re.escape(kw) + r"\b", t) for kw in kws):
            return cat
    return "Other"


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_all_news(selected_brands: tuple) -> pd.DataFrame:
    rows = []
    for brand in selected_brands:
        query = COMPETITORS[brand]
        url = (
            f"https://news.google.com/rss/search?"
            f"q={urllib.parse.quote(query)}&hl=en-IN&gl=IN&ceid=IN:en"
        )
        feed = feedparser.parse(url)
        for entry in feed.entries[:30]:
            title   = entry.get("title", "").strip()
            link    = entry.get("link", "")
            pub     = entry.get("published", "")
            summary = re.sub(r"<[^>]+>", "", entry.get("summary", ""))
            if not title:
                continue
            rows.append({
                "Brand":     brand,
                "Title":     title,
                "Link":      link,
                "Published": pub,
                "Summary":   summary[:220] + "…" if len(summary) > 220 else summary,
                "Category":  categorize(title + " " + summary),
            })

    if not rows:
        return pd.DataFrame(columns=["Brand", "Title", "Link", "Published", "Summary", "Category"])

    df = pd.DataFrame(rows)
    df = df.drop_duplicates(subset=["Title", "Brand"])
    return df


# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ Filters")
    st.markdown("---")

    selected_brands = st.multiselect(
        "Select Competitors",
        options=list(COMPETITORS.keys()),
        default=list(COMPETITORS.keys()),
    )

    all_cats = ["All"] + list(CATEGORIES.keys()) + ["Other"]
    selected_cat = st.selectbox("Filter by Category", all_cats)

    st.markdown("---")
    refresh = st.button("🔄 Refresh Data", use_container_width=True)
    if refresh:
        st.cache_data.clear()
        st.rerun()

    st.markdown("---")
    st.markdown(
        "<small style='opacity:0.6;'>Data refreshes automatically every hour.<br>"
        "Click Refresh to fetch latest news immediately.</small>",
        unsafe_allow_html=True,
    )


# ── Header ───────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class="dashboard-header">
        <h1>🚗 India Auto Competitor Intelligence Dashboard</h1>
        <p>Real-time media signal monitoring for India's automotive market</p>
    </div>
    """,
    unsafe_allow_html=True,
)

if not selected_brands:
    st.warning("Please select at least one competitor from the sidebar.")
    st.stop()

# ── Data load ────────────────────────────────────────────────────────────────
with st.spinner("Fetching latest news from Google News RSS…"):
    df_raw = fetch_all_news(tuple(selected_brands))

if df_raw.empty:
    st.error("No articles found. This may be a temporary network issue. Try refreshing.")
    st.stop()

# Apply category filter
df = df_raw.copy()
if selected_cat != "All":
    df = df[df["Category"] == selected_cat]

# ── KPI Cards ────────────────────────────────────────────────────────────────
total_articles  = len(df)
brands_tracked  = df["Brand"].nunique()
top_brand       = df["Brand"].value_counts().idxmax() if total_articles else "—"
top_signal      = df["Category"].value_counts().idxmax() if total_articles else "—"

c1, c2, c3, c4 = st.columns(4)

with c1:
    st.markdown(
        f'<div class="kpi-card">'
        f'<div class="kpi-label">Total Articles</div>'
        f'<div class="kpi-value">{total_articles}</div>'
        f'<div class="kpi-sub">in filtered view</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

with c2:
    st.markdown(
        f'<div class="kpi-card">'
        f'<div class="kpi-label">Competitors Tracked</div>'
        f'<div class="kpi-value">{brands_tracked}</div>'
        f'<div class="kpi-sub">brands monitored</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

with c3:
    st.markdown(
        f'<div class="kpi-card">'
        f'<div class="kpi-label">Top Mentioned Brand</div>'
        f'<div class="kpi-value" style="font-size:1.3rem;">{top_brand}</div>'
        f'<div class="kpi-sub">most news coverage</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

with c4:
    st.markdown(
        f'<div class="kpi-card">'
        f'<div class="kpi-label">Top Signal</div>'
        f'<div class="kpi-value" style="font-size:1.5rem;">{top_signal}</div>'
        f'<div class="kpi-sub">dominant category</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

st.markdown("<br>", unsafe_allow_html=True)

# ── Charts Row 1 ─────────────────────────────────────────────────────────────
col_left, col_right = st.columns([3, 2])

with col_left:
    st.markdown('<div class="section-heading">📊 News Mentions by Brand</div>', unsafe_allow_html=True)
    brand_counts = df["Brand"].value_counts().reset_index()
    brand_counts.columns = ["Brand", "Articles"]

    fig_bar = px.bar(
        brand_counts,
        x="Articles",
        y="Brand",
        orientation="h",
        color="Articles",
        color_continuous_scale=["#BFD9F0", "#007FA8", "#002C5F"],
        text="Articles",
    )
    fig_bar.update_traces(textposition="outside", marker_line_width=0)
    fig_bar.update_layout(
        **PLOTLY_LAYOUT,
        height=360,
        yaxis=dict(categoryorder="total ascending", title=""),
        xaxis_title="Number of Articles",
        coloraxis_showscale=False,
    )
    st.plotly_chart(fig_bar, use_container_width=True)

with col_right:
    st.markdown('<div class="section-heading">🥧 Share of Voice</div>', unsafe_allow_html=True)
    fig_pie = px.pie(
        brand_counts,
        values="Articles",
        names="Brand",
        color_discrete_sequence=BRAND_COLORS,
        hole=0.45,
    )
    fig_pie.update_traces(textposition="outside", textinfo="label+percent")
    fig_pie.update_layout(
        **PLOTLY_LAYOUT,
        height=360,
        showlegend=False,
    )
    st.plotly_chart(fig_pie, use_container_width=True)

# ── Charts Row 2 ─────────────────────────────────────────────────────────────
st.markdown('<div class="section-heading">🎯 Strategic Signals by Brand</div>', unsafe_allow_html=True)

signal_df = (
    df.groupby(["Brand", "Category"])
    .size()
    .reset_index(name="Count")
)

cat_order = list(CATEGORIES.keys()) + ["Other"]
fig_signal = px.bar(
    signal_df,
    x="Brand",
    y="Count",
    color="Category",
    barmode="stack",
    color_discrete_sequence=px.colors.qualitative.Set2,
    category_orders={"Category": cat_order},
)
fig_signal.update_layout(
    **PLOTLY_LAYOUT,
    height=360,
    xaxis_title="",
    yaxis_title="Articles",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
)
st.plotly_chart(fig_signal, use_container_width=True)

# ── Recent Articles Table ─────────────────────────────────────────────────────
st.markdown('<div class="section-heading">📰 Recent Articles</div>', unsafe_allow_html=True)

display_df = df[["Brand", "Category", "Title", "Published", "Link"]].copy()

def safe_link(row) -> str:
    """Return a sanitized HTML anchor only for http/https URLs."""
    raw_url = str(row["Link"]).strip()
    safe_url = raw_url if re.match(r"^https?://", raw_url) else "#"
    safe_title = html.escape(str(row["Title"]))
    safe_href  = html.escape(safe_url, quote=True)
    return f'<a href="{safe_href}" target="_blank" rel="noopener noreferrer">{safe_title}</a>'

display_df["Article"] = display_df.apply(safe_link, axis=1)
display_df = display_df[["Brand", "Category", "Published", "Article"]].reset_index(drop=True)

st.markdown(
    display_df.to_html(escape=False, index=False),
    unsafe_allow_html=True,
)

# ── CSV Download ──────────────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
csv_data = df[["Brand", "Category", "Title", "Published", "Link", "Summary"]].to_csv(index=False)
st.download_button(
    label="⬇️ Download Articles as CSV",
    data=csv_data,
    file_name="india_auto_competitor_news.csv",
    mime="text/csv",
    use_container_width=False,
)

# ── Disclaimer ────────────────────────────────────────────────────────────────
st.markdown(
    '<div class="disclaimer">'
    "⚠️ <strong>Note:</strong> This dashboard measures media and search signals derived from Google News RSS feeds. "
    "It does not reflect actual sales volume, market share, or financial performance of any brand."
    "</div>",
    unsafe_allow_html=True,
)

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
    .stApp { background-color: #F7FAFD; }

    section[data-testid="stSidebar"] { background-color: #002C5F; }
    section[data-testid="stSidebar"] * { color: #FFFFFF !important; }
    section[data-testid="stSidebar"] .stSelectbox label,
    section[data-testid="stSidebar"] .stMultiselect label { color: #BFD9F0 !important; }

    .dashboard-header {
        background: linear-gradient(135deg, #002C5F 0%, #007FA8 100%);
        padding: 1.25rem 2rem;
        border-radius: 10px;
        margin-bottom: 1rem;
        color: #FFFFFF;
    }
    .dashboard-header h1 { margin: 0; font-size: 1.6rem; font-weight: 700; letter-spacing: 0.02em; }
    .dashboard-header p  { margin: 0.25rem 0 0; font-size: 0.88rem; opacity: 0.8; }

    /* All KPI cards share a fixed height so the row is perfectly uniform */
    .kpi-row { display: flex; gap: 0; }
    .kpi-card {
        background: #FFFFFF;
        border-radius: 10px;
        padding: 1.1rem 1.4rem;
        border-left: 4px solid #007FA8;
        box-shadow: 0 1px 6px rgba(0,44,95,0.07);
        /* Fixed height forces uniformity regardless of value length */
        min-height: 110px;
        display: flex;
        flex-direction: column;
        justify-content: flex-start;
    }
    .kpi-label { font-size: 0.72rem; color: #7A90A8; font-weight: 600; text-transform: uppercase; letter-spacing: 0.07em; margin-bottom: 0.3rem; }
    .kpi-value { font-size: 1.9rem; color: #002C5F; font-weight: 800; line-height: 1.1; }
    .kpi-value-md { font-size: 1.35rem; color: #002C5F; font-weight: 800; line-height: 1.2; margin-top: 0.05rem; }
    .kpi-sub   { font-size: 0.75rem; color: #8AAABE; margin-top: 0.3rem; font-weight: 400; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

    .section-heading {
        font-size: 1.05rem;
        font-weight: 700;
        color: #002C5F;
        border-bottom: 2px solid #007FA8;
        padding-bottom: 0.35rem;
        margin-bottom: 1rem;
    }

    .methodology-note {
        background: #E8F4FA;
        border-left: 4px solid #007FA8;
        border-radius: 6px;
        padding: 0.65rem 1.1rem;
        font-size: 0.81rem;
        color: #2C5282;
        margin-bottom: 1rem;
        line-height: 1.5;
    }

    /* Subtle explanatory captions under section headings */
    .section-caption {
        font-size: 0.78rem;
        color: #8A9BB0;
        margin-top: -0.6rem;
        margin-bottom: 0.9rem;
        line-height: 1.45;
    }

    /* KPI tooltip line */
    .kpi-tip {
        font-size: 0.74rem;
        color: #9BAFC4;
        margin-top: 0.4rem;
        line-height: 1.4;
        font-style: italic;
    }

    /* Data quality check box */
    .dq-box {
        background: #FAFCFF;
        border: 1px solid #D4E4F0;
        border-radius: 8px;
        padding: 1rem 1.25rem;
        margin-bottom: 0.5rem;
    }
    .dq-ok   { color: #276749; font-weight: 600; }
    .dq-warn { color: #B7791F; font-weight: 600; }
    .dq-bad  { color: #C53030; font-weight: 600; }

    a { color: #007FA8 !important; text-decoration: none; }
    a:hover { text-decoration: underline; }

    .disclaimer {
        background: #E8F1FA;
        border-left: 4px solid #007FA8;
        border-radius: 6px;
        padding: 0.75rem 1.25rem;
        font-size: 0.82rem;
        color: #5A7290;
        margin-top: 1rem;
    }

    .block-container { padding-top: 1rem !important; }
    .stDataFrame { border-radius: 8px; overflow: hidden; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Constants ────────────────────────────────────────────────────────────────

# Brand-specific RSS query strings (for the Brand News Feed)
BRAND_QUERIES = {
    "Tata Motors":      "Tata Motors India car",
    "Mahindra":         "Mahindra car India",
    "Maruti Suzuki":    "Maruti Suzuki India",
    "Kia India":        "Kia India car",
    "Toyota India":     "Toyota India car",
    "MG Motor India":   "MG Motor India",
    "Honda Cars India": "Honda Cars India",
    "Skoda India":      "Skoda India",
    "Volkswagen India": "Volkswagen India",
    "Renault India":    "Renault India",
}

# Keyword sets for detecting brand mentions in free text.
# Patterns are matched case-insensitively against (title + summary).
# Prefer compound model names over bare single-word tokens to reduce false positives.
BRAND_KEYWORDS = {
    "Tata Motors":      [
        "tata motors", "tata nexon", "tata harrier", "tata safari",
        "tata punch", "tata altroz", "tata curvv", "tata tigor",
        "tata tiago", "tata ev", r"\btata\.ev\b",
        # bare "tata" only after compound patterns fail; keep as fallback
        r"\btata\b",
    ],
    "Mahindra":         [
        "mahindra", r"\bm&m\b",
        # XUV prefix without closing boundary catches XUV700/XUV400/XUV3XO/XUV9e
        r"\bxuv\d*\b", r"\bxuv3xo\b", r"\bxev\b",
        r"\bscorpio\b", r"\bthar\b", r"\bbolero\b",
        r"\bbe\.6\b", r"\bbe6\b",
    ],
    "Maruti Suzuki":    [
        "maruti suzuki", r"\bmaruti\b",
        # avoid bare "suzuki" — matches Suzuki motorcycles (not India cars)
        "suzuki india", "suzuki cars",
        "grand vitara", r"\bbrezza\b", r"\bswift\b",
        r"\bbaleno\b", r"\bdzire\b", r"\bfronx\b",
        r"\bjimny\b", r"\bertiga\b",
    ],
    "Kia India":        [
        r"\bkia\b", r"\bseltos\b", r"\bsonet\b",
        r"\bcarens\b", r"\bsyros\b",
        # EV model numbers are Kia-specific enough in India auto context
        r"\bev6\b", r"\bev9\b",
    ],
    "Toyota India":     [
        r"\btoyota\b", "innova crysta", "innova hycross",
        r"\bfortuner\b", "urban cruiser hyryder", r"\bhyryder\b",
        r"\bcamry\b", r"\bglanza\b",
    ],
    "MG Motor India":   [
        # Always anchor as "mg motor" or "mg <model>" — bare "mg" too short/ambiguous
        "mg motor", r"\bmg hector\b", r"\bmg astor\b",
        r"\bmg windsor\b", r"\bmg comet\b", r"\bmg zs\b",
        r"\bmg gloster\b", r"\bmg india\b",
    ],
    "Honda Cars India": [
        # bare "honda" is reasonably brand-specific in India auto context
        r"\bhonda\b", "honda city", "honda amaze",
        "honda elevate", r"\bwr-v\b",
    ],
    "Skoda India":      [
        r"\bskoda\b", r"\bkushaq\b", r"\bslavia\b",
        r"\bkodiaq\b",
    ],
    "Volkswagen India": [
        r"\bvolkswagen\b",
        # bare "vw" is fine in India auto news; add explicit India context as fallback
        r"\bvw\b", r"\btaigun\b", r"\bvirtus\b", r"\btiguan\b",
    ],
    "Renault India":    [
        r"\brenault\b", r"\bkiger\b", r"\btriber\b",
        r"\bkwid\b", r"\bduster\b",
    ],
}

# Broad market pool queries (for Share of Voice)
MARKET_POOL_QUERIES = [
    "India auto industry passenger vehicle EV launch investment",
    "India car market Tata Mahindra Maruti Kia Toyota MG",
    "India SUV EV hybrid car launch market",
]

CATEGORIES = {
    "EV":         ["ev", "electric", "battery", "charging", "bev"],
    "Hybrid":     ["hybrid", "hev"],
    "Investment": ["investment", "invest", "plant", "factory", "capacity",
                   "expansion", "manufacturing"],
    "Launch":     ["launch", "unveil", "facelift", "booking", "debut",
                   "introduced", "variant"],
    "Price":      ["price", "discount", "hike", "increase", "cut", "offer"],
    "Export":     ["export", "shipment", "overseas", "global market"],
    "Policy":     ["policy", "regulation", "gst", "emission", "cafe",
                   "subsidy", "tax"],
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


def _parse_feed(query: str, limit: int) -> list[dict]:
    """Fetch and parse a Google News RSS feed for the given query string."""
    url = (
        "https://news.google.com/rss/search?"
        f"q={urllib.parse.quote(query)}&hl=en-IN&gl=IN&ceid=IN:en"
    )
    feed = feedparser.parse(url)
    rows = []
    for entry in feed.entries[:limit]:
        title   = entry.get("title", "").strip()
        link    = entry.get("link", "")
        pub     = entry.get("published", "")
        summary = re.sub(r"<[^>]+>", "", entry.get("summary", ""))
        if not title:
            continue
        rows.append({
            "Title":     title,
            "Link":      link,
            "Published": pub,
            "Summary":   summary[:300],
        })
    return rows


def _mentions_brand(text: str, brand: str) -> bool:
    """Return True if any keyword for the brand matches in the given text."""
    t = text.lower()
    for kw in BRAND_KEYWORDS[brand]:
        if re.search(kw, t):
            return True
    return False


# ── Data fetchers (separately cached) ────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_brand_feed(selected_brands: tuple) -> pd.DataFrame:
    """
    A. Brand News Feed — brand-specific RSS queries.
    Used for Recent Articles and Strategic Signals charts.
    Limits 15 articles per brand to keep the table manageable.
    """
    rows = []
    for brand in selected_brands:
        query = BRAND_QUERIES[brand]
        for item in _parse_feed(query, limit=15):
            summary_short = (
                item["Summary"][:220] + "…"
                if len(item["Summary"]) > 220 else item["Summary"]
            )
            rows.append({
                "Brand":     brand,
                "Title":     item["Title"],
                "Link":      item["Link"],
                "Published": item["Published"],
                "Summary":   summary_short,
                "Category":  categorize(item["Title"] + " " + item["Summary"]),
            })

    if not rows:
        return pd.DataFrame(
            columns=["Brand", "Title", "Link", "Published", "Summary", "Category"]
        )

    df = pd.DataFrame(rows)
    df = df.drop_duplicates(subset=["Title", "Brand"])
    return df


@st.cache_data(ttl=3600, show_spinner=False)
def _fetch_raw_pool() -> list[dict]:
    """
    Fetch and deduplicate the broad market news pool.
    Cached independently of brand selection so re-filtering brands
    doesn't trigger a fresh network fetch.
    """
    all_items: list[dict] = []
    for query in MARKET_POOL_QUERIES:
        all_items.extend(_parse_feed(query, limit=50))

    seen: set[tuple] = set()
    unique_items: list[dict] = []
    for item in all_items:
        key = (item["Title"].lower().strip(), item["Link"].strip())
        if key not in seen:
            seen.add(key)
            unique_items.append(item)
    return unique_items


def fetch_market_pool(selected_brands: tuple) -> pd.DataFrame:
    """
    B. Market News Pool — count brand mentions in the deduplicated pool.
    Uses _fetch_raw_pool() for network fetching (cached); mention counting
    is a fast in-memory step that naturally adapts to brand selection.
    """
    unique_items = _fetch_raw_pool()

    if not unique_items:
        return pd.DataFrame(columns=["Brand", "Mentions"])

    mention_counts: dict[str, int] = {b: 0 for b in selected_brands}
    for item in unique_items:
        text = (item["Title"] + " " + item["Summary"]).lower()
        for brand in selected_brands:
            if _mentions_brand(text, brand):
                mention_counts[brand] += 1

    rows = [
        {"Brand": brand, "Mentions": count}
        for brand, count in mention_counts.items()
        if count > 0
    ]

    if not rows:
        return pd.DataFrame(columns=["Brand", "Mentions"])

    return pd.DataFrame(rows).sort_values("Mentions", ascending=False)


# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ Filters")
    st.markdown("---")

    selected_brands = st.multiselect(
        "Select Competitors",
        options=list(BRAND_QUERIES.keys()),
        default=list(BRAND_QUERIES.keys()),
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
brands_tuple = tuple(selected_brands)

with st.spinner("Fetching brand news feeds and market pool…"):
    df_brand = fetch_brand_feed(brands_tuple)
    df_pool  = fetch_market_pool(brands_tuple)

if df_brand.empty and df_pool.empty:
    st.error("No articles found. This may be a temporary network issue. Try refreshing.")
    st.stop()

# Apply category filter to brand feed (used for articles table + signals chart)
df_filtered = df_brand.copy()
if selected_cat != "All":
    df_filtered = df_filtered[df_filtered["Category"] == selected_cat]

# ── KPI Cards ────────────────────────────────────────────────────────────────
total_brand_articles = len(df_brand)
brands_tracked       = len(selected_brands)
top_sov_brand        = (
    df_pool.iloc[0]["Brand"] if not df_pool.empty else "—"
)
top_signal = (
    df_filtered["Category"].value_counts().idxmax()
    if not df_filtered.empty else "—"
)

c1, c2, c3, c4 = st.columns(4)

with c1:
    st.markdown(
        f'<div class="kpi-card">'
        f'<div class="kpi-label">Brand Articles Collected</div>'
        f'<div class="kpi-value">{total_brand_articles}</div>'
        f'<div class="kpi-sub">from brand-specific feeds</div>'
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
        f'<div class="kpi-value-md">{html.escape(str(top_sov_brand))}</div>'
        f'<div class="kpi-sub">highest mentions in market pool</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

with c4:
    st.markdown(
        f'<div class="kpi-card">'
        f'<div class="kpi-label">Top Signal Type</div>'
        f'<div class="kpi-value-md">{html.escape(str(top_signal))}</div>'
        f'<div class="kpi-sub">dominant category</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

# ── How to read this dashboard ───────────────────────────────────────────────
with st.expander("ℹ️ How to read this dashboard", expanded=False):
    st.markdown(
        """
| Metric | What it shows |
|---|---|
| **Brand Articles Collected** | Total articles fetched from brand-specific Google News RSS feeds (up to 15 per brand). Drives the Recent Articles table and Strategic Signals chart. |
| **Competitors Tracked** | Number of brands currently selected in the sidebar filter. |
| **Top Mentioned Brand** | The competitor with the highest number of mentions in the common market news pool — not from brand-specific feeds. Indicates strongest media visibility during the period. |
| **Top Signal Type** | The most frequent strategic category (EV, Launch, Investment, Price, etc.) found across the brand-specific articles in the current filter. |
| **News Mentions by Brand** | How often each competitor appears in the broader India auto market news pool. Based on keyword detection across deduplicated articles from 3 broad market queries. Reflects relative media presence, not sales or market share. |
| **Share of Voice** | Each brand's percentage of total mentions in the market news pool. Calculated from news mentions only — not vehicle sales or revenue. |
| **Strategic Signals by Brand** | Brand-specific articles classified by theme (EV, Hybrid, Investment, Launch, Price, Export, Policy). Shows what each competitor is publicly communicating about. |
| **Recent Articles** | Original articles from brand-specific RSS feeds. Click any title to read the source. Use this to verify whether a signal is genuine. |
| **Data Quality Check** | Flags potential reliability issues: a high "Other" ratio means keyword coverage may be incomplete; identical brand counts may indicate artificial sampling; low market pool coverage means few brands were detected in the broader news pool. |
        """,
        unsafe_allow_html=False,
    )

# ── Charts Row 1: Market pool-based ─────────────────────────────────────────
col_left, col_right = st.columns([3, 2])

with col_left:
    st.markdown(
        '<div class="section-heading">📊 News Mentions by Brand</div>'
        '<div class="section-caption">Shows how often each competitor is mentioned '
        'in the collected India auto market news pool. This indicates relative media '
        'visibility, not actual sales performance or market share.</div>',
        unsafe_allow_html=True,
    )
    if df_pool.empty:
        st.info("No brand mentions detected in the market news pool.")
    else:
        pool_sorted = df_pool.sort_values("Mentions", ascending=True)
        fig_bar = px.bar(
            pool_sorted,
            x="Mentions",
            y="Brand",
            orientation="h",
            color="Mentions",
            color_continuous_scale=["#BFD9F0", "#007FA8", "#002C5F"],
            text="Mentions",
        )
        fig_bar.update_traces(textposition="outside", marker_line_width=0)
        fig_bar.update_layout(
            **PLOTLY_LAYOUT,
            height=360,
            yaxis=dict(title=""),
            xaxis_title="Mentions in market news pool",
            coloraxis_showscale=False,
        )
        st.plotly_chart(fig_bar, use_container_width=True)  # noqa: STC-deprecated

with col_right:
    st.markdown(
        '<div class="section-heading">📢 Share of Voice</div>'
        '<div class="section-caption">Each brand\'s percentage of total competitor '
        'mentions in the collected news pool. A higher share means more media '
        'attention during the selected period. '
        '<em>Note: calculated from news mentions, not vehicle sales.</em></div>',
        unsafe_allow_html=True,
    )
    if df_pool.empty:
        st.info("No data available for Share of Voice.")
    else:
        sov_total = df_pool["Mentions"].sum()
        df_sov = df_pool.copy()
        df_sov["Share (%)"] = (df_sov["Mentions"] / sov_total * 100).round(1)
        df_sov = df_sov.sort_values("Share (%)", ascending=True)

        fig_sov = px.bar(
            df_sov,
            x="Share (%)",
            y="Brand",
            orientation="h",
            color="Share (%)",
            color_continuous_scale=["#BFD9F0", "#007FA8", "#002C5F"],
            text=df_sov["Share (%)"].apply(lambda v: f"{v:.1f}%"),
        )
        fig_sov.update_traces(textposition="outside", marker_line_width=0)
        fig_sov.update_layout(
            **PLOTLY_LAYOUT,
            height=360,
            yaxis=dict(title=""),
            xaxis_title="Share of Voice (%)",
            coloraxis_showscale=False,
        )
        st.plotly_chart(fig_sov, use_container_width=True)

# ── Charts Row 2: Brand feed-based ──────────────────────────────────────────
st.markdown(
    '<div class="section-heading">🎯 Strategic Signals by Brand</div>'
    '<div class="section-caption">Classifies competitor news into strategic themes '
    'such as EV, Hybrid, Investment, Launch, Price, Export, and Policy. '
    'Helps identify what each competitor is currently focusing on.</div>',
    unsafe_allow_html=True,
)

if df_filtered.empty:
    st.info("No articles match the selected category filter.")
else:
    signal_df = (
        df_filtered.groupby(["Brand", "Category"])
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
st.markdown(
    '<div class="section-heading">📰 Recent Articles</div>'
    '<div class="section-caption">Lists recent articles collected from brand-specific '
    'RSS feeds. Use this section to check the original source behind each signal '
    'and verify whether the article is relevant.</div>',
    unsafe_allow_html=True,
)

if df_filtered.empty:
    st.info("No articles to display for the current filter selection.")
else:
    display_df = df_filtered[["Brand", "Category", "Title", "Published", "Link"]].copy()

    def safe_link(row) -> str:
        raw_url  = str(row["Link"]).strip()
        safe_url = raw_url if re.match(r"^https?://", raw_url) else "#"
        safe_title = html.escape(str(row["Title"]))
        safe_href  = html.escape(safe_url, quote=True)
        return f'<a href="{safe_href}" target="_blank" rel="noopener noreferrer">{safe_title}</a>'

    display_df["Article"] = display_df.apply(safe_link, axis=1)
    display_df = display_df[["Brand", "Category", "Published", "Article"]].reset_index(drop=True)

    # Escape all plain-text columns so untrusted RSS content cannot inject HTML.
    # The "Article" column is already sanitised by safe_link(); leave it as-is.
    for col in ("Brand", "Category", "Published"):
        display_df[col] = display_df[col].apply(lambda v: html.escape(str(v)))

    st.markdown(
        display_df.to_html(escape=False, index=False),
        unsafe_allow_html=True,
    )

# ── Data Quality Check ───────────────────────────────────────────────────────
with st.expander("🔍 Data Quality Check", expanded=False):
    st.markdown(
        '<div class="section-caption" style="margin-top:0;">'
        'Checks whether the collected data is reliable enough for interpretation. '
        'A high "Other" ratio or identical article counts across brands may indicate '
        'that the keyword logic or collection method needs improvement.'
        '</div>',
        unsafe_allow_html=True,
    )

    if not df_brand.empty:
        dq_cols = st.columns(3)

        # 1. Other-category ratio
        other_count  = (df_brand["Category"] == "Other").sum()
        other_ratio  = other_count / len(df_brand) * 100
        if other_ratio >= 60:
            dq_class, dq_icon = "dq-bad",  "🔴"
        elif other_ratio >= 35:
            dq_class, dq_icon = "dq-warn", "🟡"
        else:
            dq_class, dq_icon = "dq-ok",   "🟢"

        with dq_cols[0]:
            st.markdown(
                f'<div class="dq-box">'
                f'<div class="kpi-label">"Other" Category Ratio</div>'
                f'<div class="kpi-value" style="font-size:1.6rem;">'
                f'{dq_icon} {other_ratio:.0f}%</div>'
                f'<div class="{dq_class}" style="font-size:0.78rem;margin-top:0.3rem;">'
                f'{"High — keyword coverage may be incomplete" if other_ratio >= 60 else "Moderate — some articles uncategorised" if other_ratio >= 35 else "Good — most articles are categorised"}'
                f'</div></div>',
                unsafe_allow_html=True,
            )

        # 2. Uniform brand counts check
        brand_counts_dq = df_brand["Brand"].value_counts()
        is_uniform      = brand_counts_dq.nunique() == 1 and len(brand_counts_dq) > 1
        uniq_counts     = brand_counts_dq.nunique()

        with dq_cols[1]:
            u_icon  = "🟡" if is_uniform else "🟢"
            u_class = "dq-warn" if is_uniform else "dq-ok"
            u_label = "All brands identical — may indicate equal sampling cap" \
                      if is_uniform else f"{uniq_counts} different count values — looks natural"
            st.markdown(
                f'<div class="dq-box">'
                f'<div class="kpi-label">Brand Count Distribution</div>'
                f'<div class="kpi-value" style="font-size:1.6rem;">'
                f'{u_icon} {"Uniform" if is_uniform else "Varied"}</div>'
                f'<div class="{u_class}" style="font-size:0.78rem;margin-top:0.3rem;">'
                f'{u_label}'
                f'</div></div>',
                unsafe_allow_html=True,
            )

        # 3. Market pool size
        pool_size      = len(_fetch_raw_pool())
        pool_brands    = int(df_pool["Mentions"].gt(0).sum()) if not df_pool.empty else 0
        coverage_ratio = pool_brands / max(len(selected_brands), 1)
        if pool_size == 0 or coverage_ratio < 0.3:
            p_icon, p_class = "🔴", "dq-bad"
        elif coverage_ratio < 0.6:
            p_icon, p_class = "🟡", "dq-warn"
        else:
            p_icon, p_class = "🟢", "dq-ok"

        with dq_cols[2]:
            st.markdown(
                f'<div class="dq-box">'
                f'<div class="kpi-label">Market Pool Coverage</div>'
                f'<div class="kpi-value" style="font-size:1.6rem;">'
                f'{p_icon} {pool_brands}/{len(selected_brands)} brands</div>'
                f'<div class="{p_class}" style="font-size:0.78rem;margin-top:0.3rem;">'
                f'{pool_size} unique articles in pool'
                f'</div></div>',
                unsafe_allow_html=True,
            )
    else:
        st.info("No data available for quality check.")

# ── CSV Download ──────────────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
if not df_brand.empty:
    csv_data = df_brand[["Brand", "Category", "Title", "Published", "Link", "Summary"]].to_csv(
        index=False
    )
    st.download_button(
        label="⬇️ Download Brand Articles as CSV",
        data=csv_data,
        file_name="india_auto_brand_news.csv",
        mime="text/csv",
        use_container_width=False,
    )

# ── Disclaimer ────────────────────────────────────────────────────────────────
st.markdown(
    '<div class="disclaimer">'
    "⚠️ <strong>Note:</strong> This dashboard measures media and search signals derived "
    "from Google News RSS feeds. It does not reflect actual sales volume, market share, "
    "or financial performance of any brand."
    "</div>",
    unsafe_allow_html=True,
)

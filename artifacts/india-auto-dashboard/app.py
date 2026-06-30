import streamlit as st
import feedparser
import pandas as pd
import plotly.express as px
import urllib.parse
import html
import re
from datetime import datetime, timezone, timedelta

IST = timezone(timedelta(hours=5, minutes=30))

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="인도 자동차 경쟁사 동향 대시보드",
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
        padding: 1.1rem 2rem;
        border-radius: 10px;
        margin-bottom: 0.75rem;
        color: #FFFFFF;
    }
    .dashboard-header h1 { margin: 0; font-size: 1.5rem; font-weight: 700; letter-spacing: 0.01em; }
    .dashboard-header p  { margin: 0.2rem 0 0; font-size: 0.85rem; opacity: 0.8; }

    /* Freshness info bar */
    .freshness-bar {
        background: #FFFFFF;
        border: 1px solid #D8E8F4;
        border-radius: 8px;
        padding: 0.55rem 1.25rem;
        margin-bottom: 0.85rem;
        display: flex;
        gap: 2.5rem;
        align-items: center;
        flex-wrap: wrap;
    }
    .freshness-item { display: flex; flex-direction: column; }
    .freshness-label { font-size: 0.68rem; color: #8AAABE; font-weight: 600;
                       text-transform: uppercase; letter-spacing: 0.06em; }
    .freshness-value { font-size: 0.88rem; color: #002C5F; font-weight: 600; margin-top: 0.1rem; }
    .freshness-stale  { color: #C53030; }

    /* KPI cards — uniform height via flexbox */
    .kpi-card {
        background: #FFFFFF;
        border-radius: 10px;
        padding: 1.05rem 1.3rem;
        border-left: 4px solid #007FA8;
        box-shadow: 0 1px 6px rgba(0,44,95,0.07);
        min-height: 108px;
        display: flex;
        flex-direction: column;
        justify-content: flex-start;
    }
    .kpi-label   { font-size: 0.69rem; color: #7A90A8; font-weight: 600;
                   text-transform: uppercase; letter-spacing: 0.07em; margin-bottom: 0.25rem; }
    .kpi-value   { font-size: 1.85rem; color: #002C5F; font-weight: 800; line-height: 1.1; }
    .kpi-value-md{ font-size: 1.25rem; color: #002C5F; font-weight: 800;
                   line-height: 1.2; margin-top: 0.05rem; }
    .kpi-sub     { font-size: 0.72rem; color: #8AAABE; margin-top: 0.28rem;
                   font-weight: 400; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

    /* Section headings + captions */
    .section-heading {
        font-size: 1rem;
        font-weight: 700;
        color: #002C5F;
        border-bottom: 2px solid #007FA8;
        padding-bottom: 0.3rem;
        margin-bottom: 0.5rem;
    }
    .section-caption {
        font-size: 0.76rem;
        color: #8A9BB0;
        margin-top: -0.3rem;
        margin-bottom: 0.85rem;
        line-height: 1.45;
    }

    /* Data quality boxes */
    .dq-box {
        background: #FAFCFF;
        border: 1px solid #D4E4F0;
        border-radius: 8px;
        padding: 0.85rem 1.1rem;
        margin-bottom: 0.5rem;
    }
    .dq-ok   { color: #276749; font-weight: 600; }
    .dq-warn { color: #B7791F; font-weight: 600; }
    .dq-bad  { color: #C53030; font-weight: 600; }

    /* Stale data warning banner */
    .stale-banner {
        background: #FFF5F5;
        border-left: 4px solid #C53030;
        border-radius: 6px;
        padding: 0.6rem 1rem;
        font-size: 0.82rem;
        color: #C53030;
        font-weight: 500;
        margin-top: 0.5rem;
    }

    a { color: #007FA8 !important; text-decoration: none; }
    a:hover { text-decoration: underline; }

    .disclaimer {
        background: #E8F1FA;
        border-left: 4px solid #007FA8;
        border-radius: 6px;
        padding: 0.65rem 1.1rem;
        font-size: 0.8rem;
        color: #5A7290;
        margin-top: 1rem;
    }

    .block-container { padding-top: 0.75rem !important; }
    .stDataFrame { border-radius: 8px; overflow: hidden; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Constants ────────────────────────────────────────────────────────────────

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

BRAND_KEYWORDS = {
    "Tata Motors":      [
        "tata motors", "tata nexon", "tata harrier", "tata safari",
        "tata punch", "tata altroz", "tata curvv", "tata tigor",
        "tata tiago", "tata ev", r"\btata\b",
    ],
    "Mahindra":         [
        "mahindra", r"\bm&m\b",
        r"\bxuv\d*\b", r"\bxuv3xo\b", r"\bxev\b",
        r"\bscorpio\b", r"\bthar\b", r"\bbolero\b",
        r"\bbe\.6\b", r"\bbe6\b",
    ],
    "Maruti Suzuki":    [
        "maruti suzuki", r"\bmaruti\b",
        "suzuki india", "suzuki cars",
        "grand vitara", r"\bbrezza\b", r"\bswift\b",
        r"\bbaleno\b", r"\bdzire\b", r"\bfronx\b",
        r"\bjimny\b", r"\bertiga\b",
    ],
    "Kia India":        [
        r"\bkia\b", r"\bseltos\b", r"\bsonet\b",
        r"\bcarens\b", r"\bsyros\b", r"\bev6\b", r"\bev9\b",
    ],
    "Toyota India":     [
        r"\btoyota\b", "innova crysta", "innova hycross",
        r"\bfortuner\b", "urban cruiser hyryder", r"\bhyryder\b",
        r"\bcamry\b", r"\bglanza\b",
    ],
    "MG Motor India":   [
        "mg motor", r"\bmg hector\b", r"\bmg astor\b",
        r"\bmg windsor\b", r"\bmg comet\b", r"\bmg zs\b",
        r"\bmg gloster\b", r"\bmg india\b",
    ],
    "Honda Cars India": [
        r"\bhonda\b", "honda city", "honda amaze",
        "honda elevate", r"\bwr-v\b",
    ],
    "Skoda India":      [
        r"\bskoda\b", r"\bkushaq\b", r"\bslavia\b", r"\bkodiaq\b",
    ],
    "Volkswagen India": [
        r"\bvolkswagen\b", r"\bvw\b", r"\btaigun\b",
        r"\bvirtus\b", r"\btiguan\b",
    ],
    "Renault India":    [
        r"\brenault\b", r"\bkiger\b", r"\btriber\b",
        r"\bkwid\b", r"\bduster\b",
    ],
}

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
    """Fetch and parse a Google News RSS feed. Returns items with PublishedDt (UTC datetime)."""
    url = (
        "https://news.google.com/rss/search?"
        f"q={urllib.parse.quote(query)}&hl=en-IN&gl=IN&ceid=IN:en"
    )
    feed = feedparser.parse(url)
    rows = []
    for entry in feed.entries[:limit]:
        title   = entry.get("title", "").strip()
        link    = entry.get("link", "")
        pub_str = entry.get("published", "")
        summary = re.sub(r"<[^>]+>", "", entry.get("summary", ""))
        if not title:
            continue
        # Parse publish date → UTC datetime
        pub_parsed = entry.get("published_parsed")
        try:
            pub_dt = datetime(*pub_parsed[:6], tzinfo=timezone.utc) if pub_parsed else None
        except Exception:
            pub_dt = None
        rows.append({
            "Title":       title,
            "Link":        link,
            "Published":   pub_str,
            "PublishedDt": pub_dt,
            "Summary":     summary[:300],
        })
    return rows


def _mentions_brand(text: str, brand: str) -> bool:
    t = text.lower()
    for kw in BRAND_KEYWORDS[brand]:
        if re.search(kw, t):
            return True
    return False


def _now_ist_str() -> str:
    return datetime.now(tz=timezone.utc).astimezone(IST).strftime("%Y-%m-%d %H:%M IST")


# ── Data fetchers (separately cached) ────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_brand_feed(selected_brands: tuple, date_range_days: int) -> tuple:
    """
    A. Brand News Feed — brand-specific RSS queries with when:Xd date filter.
    Returns (df, fetched_at_ist_str).
    """
    when_suffix = f" when:{date_range_days}d"
    rows = []
    for brand in selected_brands:
        query = BRAND_QUERIES[brand] + when_suffix
        for item in _parse_feed(query, limit=15):
            summary_short = (
                item["Summary"][:220] + "…"
                if len(item["Summary"]) > 220 else item["Summary"]
            )
            rows.append({
                "Brand":       brand,
                "Title":       item["Title"],
                "Link":        item["Link"],
                "Published":   item["Published"],
                "PublishedDt": item["PublishedDt"],
                "Summary":     summary_short,
                "Category":    categorize(item["Title"] + " " + item["Summary"]),
            })

    fetched_at = _now_ist_str()

    if not rows:
        return (
            pd.DataFrame(columns=["Brand", "Title", "Link", "Published",
                                   "PublishedDt", "Summary", "Category"]),
            fetched_at,
        )

    df = pd.DataFrame(rows)
    df = df.drop_duplicates(subset=["Title", "Brand"])
    return (df, fetched_at)


@st.cache_data(ttl=3600, show_spinner=False)
def _fetch_raw_pool(date_range_days: int) -> tuple:
    """
    Fetch and deduplicate the broad market news pool with when:Xd filter.
    Returns (unique_items, raw_count, fetched_at_ist_str).
    """
    when_suffix = f" when:{date_range_days}d"
    all_items: list[dict] = []
    for query in MARKET_POOL_QUERIES:
        all_items.extend(_parse_feed(query + when_suffix, limit=50))

    raw_count = len(all_items)
    seen: set[tuple] = set()
    unique_items: list[dict] = []
    for item in all_items:
        key = (item["Title"].lower().strip(), item["Link"].strip())
        if key not in seen:
            seen.add(key)
            unique_items.append(item)

    return (unique_items, raw_count, _now_ist_str())


def fetch_market_pool(selected_brands: tuple, date_range_days: int) -> pd.DataFrame:
    """
    B. Count brand mentions in the deduplicated market pool.
    """
    unique_items, _, _ = _fetch_raw_pool(date_range_days)

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
    st.markdown("## ⚙️ 필터")
    st.markdown("---")

    date_range_options = {"최근 1일": 1, "최근 7일": 7, "최근 30일": 30}
    selected_range_label = st.selectbox(
        "수집 기간",
        options=list(date_range_options.keys()),
        index=1,          # default: 최근 7일
    )
    date_range_days = date_range_options[selected_range_label]

    st.markdown("---")

    selected_brands = st.multiselect(
        "경쟁사 선택",
        options=list(BRAND_QUERIES.keys()),
        default=list(BRAND_QUERIES.keys()),
    )

    all_cats = ["전체"] + list(CATEGORIES.keys()) + ["Other"]
    selected_cat = st.selectbox("신호 유형 필터", all_cats)

    st.markdown("---")
    refresh = st.button("🔄 데이터 새로고침", use_container_width=True)
    if refresh:
        st.cache_data.clear()
        st.rerun()

    st.markdown("---")
    st.markdown(
        "<small style='opacity:0.6;'>데이터는 1시간마다 자동 갱신됩니다.<br>"
        "즉시 갱신하려면 위 버튼을 누르세요.</small>",
        unsafe_allow_html=True,
    )


# ── Header ───────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class="dashboard-header">
        <h1>🚗 인도 자동차 경쟁사 동향 대시보드</h1>
        <p>인도 자동차 시장의 경쟁사 뉴스, 미디어 노출, 전략 신호를 모니터링하는 대시보드</p>
    </div>
    """,
    unsafe_allow_html=True,
)

if not selected_brands:
    st.warning("최소 1개 이상의 경쟁사를 선택하세요.")
    st.stop()

# ── Data load ────────────────────────────────────────────────────────────────
brands_tuple = tuple(selected_brands)

with st.spinner("브랜드 뉴스 피드와 시장 풀을 수집하는 중…"):
    df_brand, fetched_at_str = fetch_brand_feed(brands_tuple, date_range_days)
    pool_items, pool_raw_count, _ = _fetch_raw_pool(date_range_days)
    df_pool = fetch_market_pool(brands_tuple, date_range_days)

if df_brand.empty and df_pool.empty:
    st.error("기사를 찾을 수 없습니다. 일시적인 네트워크 오류일 수 있습니다. 새로고침을 시도하세요.")
    st.stop()

# Category filter
df_filtered = df_brand.copy()
if selected_cat != "전체":
    df_filtered = df_filtered[df_filtered["Category"] == selected_cat]

# Latest article datetime
pub_dates = df_brand["PublishedDt"].dropna().tolist() if not df_brand.empty else []
latest_dt = max(pub_dates) if pub_dates else None
now_utc   = datetime.now(tz=timezone.utc)

if latest_dt:
    latest_ist_str = latest_dt.astimezone(IST).strftime("%Y-%m-%d %H:%M IST")
    days_stale     = (now_utc - latest_dt).total_seconds() / 86400
else:
    latest_ist_str = "—"
    days_stale     = None

# ── Freshness bar ────────────────────────────────────────────────────────────
stale_flag = days_stale is not None and days_stale > 3
stale_class = "freshness-stale" if stale_flag else ""
st.markdown(
    f'<div class="freshness-bar">'
    f'  <div class="freshness-item">'
    f'    <span class="freshness-label">최종 업데이트 시각</span>'
    f'    <span class="freshness-value">{html.escape(fetched_at_str)}</span>'
    f'  </div>'
    f'  <div class="freshness-item">'
    f'    <span class="freshness-label">최신 기사 날짜</span>'
    f'    <span class="freshness-value {stale_class}">{html.escape(latest_ist_str)}</span>'
    f'  </div>'
    f'  <div class="freshness-item">'
    f'    <span class="freshness-label">데이터 수집 기준</span>'
    f'    <span class="freshness-value">{html.escape(selected_range_label)}</span>'
    f'  </div>'
    f'</div>',
    unsafe_allow_html=True,
)

# ── KPI Cards ────────────────────────────────────────────────────────────────
total_brand_articles = len(df_brand)
brands_tracked       = len(selected_brands)
top_sov_brand        = df_pool.iloc[0]["Brand"] if not df_pool.empty else "—"
top_signal = (
    df_filtered["Category"].value_counts().idxmax()
    if not df_filtered.empty else "—"
)

c1, c2, c3, c4 = st.columns(4)

with c1:
    st.markdown(
        f'<div class="kpi-card">'
        f'<div class="kpi-label">수집 기사 수</div>'
        f'<div class="kpi-value">{total_brand_articles}</div>'
        f'<div class="kpi-sub">브랜드별 RSS 피드 기준</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

with c2:
    st.markdown(
        f'<div class="kpi-card">'
        f'<div class="kpi-label">추적 브랜드 수</div>'
        f'<div class="kpi-value">{brands_tracked}</div>'
        f'<div class="kpi-sub">선택된 경쟁사 수</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

with c3:
    st.markdown(
        f'<div class="kpi-card">'
        f'<div class="kpi-label">최다 언급 브랜드</div>'
        f'<div class="kpi-value-md">{html.escape(str(top_sov_brand))}</div>'
        f'<div class="kpi-sub">시장 풀 기준 언급량</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

with c4:
    st.markdown(
        f'<div class="kpi-card">'
        f'<div class="kpi-label">주요 전략 신호</div>'
        f'<div class="kpi-value-md">{html.escape(str(top_signal))}</div>'
        f'<div class="kpi-sub">가장 많이 나타난 신호 유형</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

# ── 대시보드 해석 가이드 ─────────────────────────────────────────────────────
with st.expander("ℹ️ 대시보드 해석 가이드", expanded=False):
    st.markdown(
        """
| 항목 | 설명 |
|---|---|
| **수집 기사 수** | 브랜드별 Google News RSS 피드에서 수집한 기사 수 (브랜드당 최대 15건). 최근 기사 목록 및 전략 신호 차트의 기반 데이터입니다. |
| **추적 브랜드 수** | 사이드바에서 현재 선택된 경쟁사 수입니다. |
| **최다 언급 브랜드** | 브랜드별 피드가 아닌 공통 시장 뉴스 풀에서 가장 많이 언급된 경쟁사입니다. 해당 기간 미디어 노출이 가장 높은 브랜드를 나타냅니다. |
| **주요 전략 신호** | 수집된 기사에서 가장 많이 분류된 전략 테마입니다 (EV, Launch, Investment, Price 등). |
| **브랜드별 뉴스 언급량** | 인도 자동차 시장 관련 3개의 광범위 쿼리로 수집된 기사 풀에서 각 브랜드가 언급된 횟수입니다. 판매량이나 시장 점유율과는 무관합니다. |
| **뉴스 언급 점유율** | 시장 뉴스 풀 내 전체 브랜드 언급량 대비 각 브랜드의 비율입니다. 차량 판매 기준이 아닌 미디어 노출 기준입니다. |
| **브랜드별 전략 신호** | 브랜드별 기사를 EV, 하이브리드, 투자, 출시, 가격, 수출, 정책 등 전략 테마로 분류한 누적 막대 차트입니다. |
| **최근 기사 목록** | 브랜드별 RSS 피드에서 수집한 기사 목록입니다. 제목을 클릭하면 원문을 확인할 수 있습니다. |
| **데이터 품질 점검** | 수집 데이터의 신뢰성을 점검합니다. '기타' 비율이 높거나 최신 기사 날짜가 오래된 경우 수집 품질 이슈를 의심해보세요. |
        """,
        unsafe_allow_html=False,
    )

# ── Charts Row 1: Market pool ────────────────────────────────────────────────
col_left, col_right = st.columns([3, 2])

with col_left:
    st.markdown(
        '<div class="section-heading">📊 브랜드별 뉴스 언급량</div>'
        '<div class="section-caption">인도 자동차 시장 광역 쿼리 풀에서 각 브랜드가 언급된 횟수입니다. '
        '판매량·시장 점유율이 아닌 미디어 노출 지표입니다.</div>',
        unsafe_allow_html=True,
    )
    if df_pool.empty:
        st.info("시장 뉴스 풀에서 브랜드 언급이 감지되지 않았습니다.")
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
            xaxis_title="언급 횟수 (시장 뉴스 풀 기준)",
            coloraxis_showscale=False,
        )
        st.plotly_chart(fig_bar, use_container_width=True)

with col_right:
    st.markdown(
        '<div class="section-heading">📢 뉴스 언급 점유율</div>'
        '<div class="section-caption">시장 뉴스 풀 내 전체 언급량 대비 각 브랜드 비율입니다. '
        '<em>차량 판매 기준이 아닌 미디어 언급 기준입니다.</em></div>',
        unsafe_allow_html=True,
    )
    if df_pool.empty:
        st.info("점유율 데이터를 사용할 수 없습니다.")
    else:
        sov_total = df_pool["Mentions"].sum()
        df_sov = df_pool.copy()
        df_sov["점유율 (%)"] = (df_sov["Mentions"] / sov_total * 100).round(1)
        df_sov = df_sov.sort_values("점유율 (%)", ascending=True)

        fig_sov = px.bar(
            df_sov,
            x="점유율 (%)",
            y="Brand",
            orientation="h",
            color="점유율 (%)",
            color_continuous_scale=["#BFD9F0", "#007FA8", "#002C5F"],
            text=df_sov["점유율 (%)"].apply(lambda v: f"{v:.1f}%"),
        )
        fig_sov.update_traces(textposition="outside", marker_line_width=0)
        fig_sov.update_layout(
            **PLOTLY_LAYOUT,
            height=360,
            yaxis=dict(title=""),
            xaxis_title="뉴스 언급 점유율 (%)",
            coloraxis_showscale=False,
        )
        st.plotly_chart(fig_sov, use_container_width=True)

# ── Charts Row 2: Strategic signals ─────────────────────────────────────────
st.markdown(
    '<div class="section-heading">🎯 브랜드별 전략 신호</div>'
    '<div class="section-caption">경쟁사 기사를 EV, 하이브리드, 투자, 출시, 가격, 수출, 정책 등 '
    '전략 테마로 분류합니다. 각 브랜드가 현재 어디에 집중하고 있는지 파악하는 데 활용하세요.</div>',
    unsafe_allow_html=True,
)

if df_filtered.empty:
    st.info("선택한 필터 조건에 맞는 기사가 없습니다.")
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
        yaxis_title="기사 수",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    st.plotly_chart(fig_signal, use_container_width=True)

# ── Recent Articles Table ─────────────────────────────────────────────────────
st.markdown(
    '<div class="section-heading">📰 최근 기사 목록</div>'
    '<div class="section-caption">브랜드별 RSS 피드에서 수집한 최근 기사입니다. '
    '제목을 클릭하면 원문을 확인할 수 있습니다. 기사 제목은 영어 원문 그대로 표시됩니다.</div>',
    unsafe_allow_html=True,
)

if df_filtered.empty:
    st.info("현재 필터 조건에 표시할 기사가 없습니다.")
else:
    display_df = df_filtered[["Brand", "Category", "Title", "Published", "Link"]].copy()

    def safe_link(row) -> str:
        raw_url    = str(row["Link"]).strip()
        safe_url   = raw_url if re.match(r"^https?://", raw_url) else "#"
        safe_title = html.escape(str(row["Title"]))
        safe_href  = html.escape(safe_url, quote=True)
        return f'<a href="{safe_href}" target="_blank" rel="noopener noreferrer">{safe_title}</a>'

    display_df["기사"] = display_df.apply(safe_link, axis=1)
    display_df = display_df[["Brand", "Category", "Published", "기사"]].rename(
        columns={"Brand": "브랜드", "Category": "유형", "Published": "날짜"}
    ).reset_index(drop=True)

    for col in ("브랜드", "유형", "날짜"):
        display_df[col] = display_df[col].apply(lambda v: html.escape(str(v)))

    st.markdown(display_df.to_html(escape=False, index=False), unsafe_allow_html=True)

# ── Data Quality Check ───────────────────────────────────────────────────────
with st.expander("🔍 데이터 품질 점검", expanded=False):
    pool_dedup_count = len(pool_items)

    # Stale article warning
    if stale_flag:
        st.markdown(
            '<div class="stale-banner">⚠️ 최신 기사 날짜가 3일 이상 오래되었습니다. '
            'RSS 수집 상태를 확인하세요.</div>',
            unsafe_allow_html=True,
        )

    if not df_brand.empty:
        dq_r1, dq_r2, dq_r3 = st.columns(3)

        # 1. Raw collected vs dedup (pool)
        with dq_r1:
            st.markdown(
                f'<div class="dq-box">'
                f'<div class="kpi-label">수집 기사 (브랜드 피드)</div>'
                f'<div class="kpi-value" style="font-size:1.5rem;">{total_brand_articles}</div>'
                f'<div style="font-size:0.76rem;color:#5A7290;margin-top:0.2rem;">'
                f'시장 풀 원본: {pool_raw_count}건 → 중복 제거 후: {pool_dedup_count}건</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

        # 2. Other ratio
        other_count = (df_brand["Category"] == "Other").sum()
        other_ratio = other_count / len(df_brand) * 100
        if other_ratio >= 60:
            r_icon, r_class, r_msg = "🔴", "dq-bad",  "키워드 커버리지 부족 가능성"
        elif other_ratio >= 35:
            r_icon, r_class, r_msg = "🟡", "dq-warn", "일부 기사 미분류"
        else:
            r_icon, r_class, r_msg = "🟢", "dq-ok",   "분류 상태 양호"

        with dq_r2:
            st.markdown(
                f'<div class="dq-box">'
                f'<div class="kpi-label">기타 비율 (Other ratio)</div>'
                f'<div class="kpi-value" style="font-size:1.5rem;">'
                f'{r_icon} {other_ratio:.0f}%</div>'
                f'<div class="{r_class}" style="font-size:0.76rem;margin-top:0.2rem;">'
                f'{r_msg}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

        # 3. Latest article date + last fetched
        if days_stale is None:
            stale_label_class = "dq-warn"
            stale_label_msg   = "게시일 정보 없음 — 신선도 판단 불가"
        elif stale_flag:
            stale_label_class = "dq-bad"
            stale_label_msg   = f"{days_stale:.0f}일 경과 — 수집 상태 확인 필요"
        else:
            stale_label_class = "dq-ok"
            stale_label_msg   = "최신 상태 양호"

        with dq_r3:
            st.markdown(
                f'<div class="dq-box">'
                f'<div class="kpi-label">최신 기사 날짜 / 마지막 수집</div>'
                f'<div class="kpi-value" style="font-size:1.05rem;margin-top:0.1rem;">'
                f'{html.escape(latest_ist_str)}</div>'
                f'<div style="font-size:0.73rem;color:#8AAABE;margin-top:0.15rem;">'
                f'수집 시각: {html.escape(fetched_at_str)}</div>'
                f'<div class="{stale_label_class}" style="font-size:0.76rem;margin-top:0.2rem;">'
                f'{stale_label_msg}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
    else:
        st.info("품질 점검에 사용할 데이터가 없습니다.")

# ── CSV Download ──────────────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
if not df_brand.empty:
    csv_data = df_brand[
        ["Brand", "Category", "Title", "Published", "Link", "Summary"]
    ].to_csv(index=False)
    st.download_button(
        label="⬇️ 기사 CSV 다운로드",
        data=csv_data,
        file_name="india_auto_competitor_news.csv",
        mime="text/csv",
        use_container_width=False,
    )

# ── Disclaimer ────────────────────────────────────────────────────────────────
st.markdown(
    '<div class="disclaimer">'
    "⚠️ <strong>주의:</strong> 이 대시보드는 Google News RSS 피드에서 수집한 미디어 및 검색 신호를 측정합니다. "
    "실제 판매량, 시장 점유율, 또는 각 브랜드의 재무 성과를 반영하지 않습니다."
    "</div>",
    unsafe_allow_html=True,
)

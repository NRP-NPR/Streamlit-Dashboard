import streamlit as st
import feedparser
import pandas as pd
import plotly.express as px
import urllib.parse
import html
import re
from datetime import datetime, timezone, timedelta

IST = timezone(timedelta(hours=5, minutes=30))

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="India Auto Competitor Dashboard",
    page_icon=":car:",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Language & persistent state ───────────────────────────────────────────────
if "lang" not in st.session_state:
    st.session_state["lang"] = "ko"
if "date_range_days" not in st.session_state:
    st.session_state["date_range_days"] = 7

lang = st.session_state["lang"]

# ── Bilingual UI strings ──────────────────────────────────────────────────────
STRINGS: dict[str, dict[str, str]] = {
    "ko": {
        "eyebrow": "COMPETITOR INTELLIGENCE · INDIA AUTO MARKET",
        "built_by": "Built by Naaryn Park · Corporate Planning Intern· MVP v1.0",
        "page_title": "인도 자동차 경쟁사 동향 대시보드",
        "page_sub": "인도 자동차 시장의 경쟁사 뉴스, 미디어 노출, 전략 신호를 모니터링합니다.",
        "lang_label": "언어",
        "sidebar_title": "필터",
        "date_label": "수집 기간",
        "d_1": "최근 1일",
        "d_7": "최근 7일",
        "d_30": "최근 30일",
        "brand_label": "경쟁사 선택",
        "signal_label": "신호 유형",
        "all": "전체",
        "refresh": "데이터 새로고침",
        "refresh_note": "데이터는 1시간마다 자동 갱신됩니다. 즉시 갱신하려면 위 버튼을 누르세요.",
        "last_updated": "최종 업데이트",
        "latest_article": "최신 기사 날짜",
        "period": "수집 기간",
        "warn_select": "최소 1개 이상의 경쟁사를 선택하세요.",
        "loading": "뉴스 데이터를 수집하는 중입니다...",
        "no_data": "기사를 찾을 수 없습니다. 일시적인 네트워크 오류일 수 있습니다.",
        "kpi_articles": "수집 기사 수",
        "kpi_articles_sub": "브랜드별 RSS 기준",
        "kpi_brands": "추적 브랜드",
        "kpi_brands_sub": "선택된 경쟁사",
        "kpi_top_brand": "최다 언급 브랜드",
        "kpi_top_brand_sub": "시장 뉴스 풀 기준",
        "kpi_top_signal": "주요 전략 신호",
        "kpi_top_signal_sub": "가장 많이 나타난 유형",
        "guide_title": "대시보드 해석 가이드",
        "guide_table": (
            "| 항목 | 설명 |\n|---|---|\n"
            "| **수집 기사 수** | 브랜드별 Google News RSS에서 수집한 기사 수 (브랜드당 최대 15건). |\n"
            "| **추적 브랜드** | 현재 선택된 경쟁사 수. |\n"
            "| **최다 언급 브랜드** | 공통 시장 뉴스 풀에서 가장 많이 언급된 경쟁사. 판매량 기준이 아님. |\n"
            "| **주요 전략 신호** | 수집 기사에서 가장 많이 분류된 전략 테마 (EV, Launch, Investment 등). |\n"
            "| **브랜드별 뉴스 언급량** | 광역 쿼리 풀에서 각 브랜드가 언급된 횟수. 미디어 노출 지표. |\n"
            "| **뉴스 언급 점유율** | 시장 풀 내 전체 언급량 대비 각 브랜드 비율. |\n"
            "| **브랜드별 전략 신호** | 브랜드별 기사를 전략 테마로 분류한 누적 막대 차트. |\n"
            "| **최근 기사 목록** | 브랜드별 RSS에서 수집한 기사 목록. 제목 클릭 시 원문 확인 가능. |\n"
            "| **데이터 품질 점검** | 수집 데이터의 신뢰성 점검. 기타 비율과 기사 신선도를 확인합니다. |"
        ),
        "mentions_title": "브랜드별 뉴스 언급량",
        "mentions_cap": "인도 자동차 시장 광역 쿼리 풀에서 각 브랜드가 언급된 횟수입니다. 판매량·시장 점유율 지표가 아닙니다.",
        "mentions_xaxis": "언급 횟수",
        "mentions_empty": "시장 뉴스 풀에서 브랜드 언급이 감지되지 않았습니다.",
        "sov_title": "뉴스 언급 점유율",
        "sov_cap": "시장 뉴스 풀 내 전체 언급량 대비 각 브랜드 비율입니다. 차량 판매 기준이 아닙니다.",
        "sov_xaxis": "점유율 (%)",
        "sov_empty": "점유율 데이터를 사용할 수 없습니다.",
        "signal_title": "브랜드별 전략 신호",
        "signal_cap": "경쟁사 기사를 EV, 하이브리드, 투자, 출시, 가격, 수출, 정책 등 전략 테마로 분류합니다.",
        "signal_yaxis": "기사 수",
        "signal_empty": "선택한 필터 조건에 맞는 기사가 없습니다.",
        "articles_title": "최근 기사 목록",
        "articles_cap": "브랜드별 RSS 피드에서 수집한 최근 기사입니다. 기사 제목은 영어 원문으로 표시됩니다.",
        "articles_empty": "현재 필터 조건에 표시할 기사가 없습니다.",
        "col_brand": "브랜드",
        "col_type": "유형",
        "col_date": "날짜",
        "col_article": "기사",
        "dq_title": "데이터 품질 점검",
        "dq_stale_banner": "최신 기사 날짜가 3일 이상 경과했습니다. RSS 수집 상태를 확인하세요.",
        "dq_feed": "브랜드 피드 수집",
        "dq_pool": "시장 풀 {raw}건 수집 → {dedup}건 (중복 제거)",
        "dq_other": "기타 비율 (Other)",
        "dq_freshness": "기사 신선도",
        "dq_latest": "최신 기사",
        "dq_fetched": "수집 시각",
        "dq_fresh": "최신 상태 양호",
        "dq_stale_msg": "{days:.0f}일 경과 — 확인 필요",
        "dq_unknown": "게시일 정보 없음 — 신선도 판단 불가",
        "dq_ok": "분류 상태 양호",
        "dq_warn": "일부 기사 미분류",
        "dq_bad": "키워드 커버리지 부족 가능성",
        "dq_empty": "품질 점검에 사용할 데이터가 없습니다.",
        "download": "기사 CSV 다운로드",
        "disclaimer": "이 대시보드는 Google News RSS에서 수집한 미디어 노출 신호를 측정합니다. 실제 판매량, 시장 점유율, 재무 성과를 반영하지 않습니다.",
    },
    "en": {
        "eyebrow": "COMPETITOR INTELLIGENCE · INDIA AUTO MARKET",
        "built_by": "Built by Naaryn Park · Corporate Planning Intern· MVP v1.0",
        "page_title": "India Auto Competitor Intelligence Dashboard",
        "page_sub": "Monitor competitor news, media exposure, and strategic signals in the Indian auto market.",
        "lang_label": "Language",
        "sidebar_title": "Filters",
        "date_label": "Date Range",
        "d_1": "Last 1 Day",
        "d_7": "Last 7 Days",
        "d_30": "Last 30 Days",
        "brand_label": "Competitors",
        "signal_label": "Signal Type",
        "all": "All",
        "refresh": "Refresh Data",
        "refresh_note": "Data refreshes automatically every hour. Click above to refresh immediately.",
        "last_updated": "Last Updated",
        "latest_article": "Latest Article",
        "period": "Date Range",
        "warn_select": "Please select at least one competitor.",
        "loading": "Fetching news data...",
        "no_data": "No articles found. This may be a temporary network error.",
        "kpi_articles": "Articles Collected",
        "kpi_articles_sub": "From brand RSS feeds",
        "kpi_brands": "Brands Tracked",
        "kpi_brands_sub": "Selected competitors",
        "kpi_top_brand": "Top Mentioned Brand",
        "kpi_top_brand_sub": "By market news pool",
        "kpi_top_signal": "Top Strategic Signal",
        "kpi_top_signal_sub": "Most frequent theme",
        "guide_title": "How to Read This Dashboard",
        "guide_table": (
            "| Metric | Description |\n|---|---|\n"
            "| **Articles Collected** | Articles from brand-specific Google News RSS feeds (up to 15 per brand). |\n"
            "| **Brands Tracked** | Number of currently selected competitors. |\n"
            "| **Top Mentioned Brand** | Most mentioned competitor in the broad market news pool. Not a sales metric. |\n"
            "| **Top Strategic Signal** | Most frequent strategic theme in collected articles (EV, Launch, Investment, etc.). |\n"
            "| **News Mentions by Brand** | Times each brand was mentioned in the broad market news pool. Media exposure metric. |\n"
            "| **Share of Voice** | Each brand's share of total mentions in the market news pool. |\n"
            "| **Strategic Signals by Brand** | Articles classified into strategic themes per brand, shown as a stacked bar. |\n"
            "| **Recent Articles** | Latest articles from brand RSS feeds. Click titles to read originals. |\n"
            "| **Data Quality Check** | Reliability check: Other ratio and article freshness. |"
        ),
        "mentions_title": "News Mentions by Brand",
        "mentions_cap": "Times each brand was mentioned in the broad India auto market news pool. Not a sales or market share metric.",
        "mentions_xaxis": "Mention Count",
        "mentions_empty": "No brand mentions detected in the market news pool.",
        "sov_title": "Share of Voice",
        "sov_cap": "Each brand's share of total mentions in the market news pool. Media exposure, not vehicle sales.",
        "sov_xaxis": "Share of Voice (%)",
        "sov_empty": "Share of voice data unavailable.",
        "signal_title": "Strategic Signals by Brand",
        "signal_cap": "Competitor articles classified into strategic themes: EV, Hybrid, Investment, Launch, Price, Export, Policy.",
        "signal_yaxis": "Article Count",
        "signal_empty": "No articles match the selected filter.",
        "articles_title": "Recent Articles",
        "articles_cap": "Latest articles from brand-specific RSS feeds. Titles are shown in English as published.",
        "articles_empty": "No articles to display for the current filter.",
        "col_brand": "Brand",
        "col_type": "Type",
        "col_date": "Date",
        "col_article": "Article",
        "dq_title": "Data Quality Check",
        "dq_stale_banner": "Latest article date is more than 3 days old. Please check RSS collection status.",
        "dq_feed": "Brand Feed Articles",
        "dq_pool": "Market pool: {raw} fetched → {dedup} after dedup",
        "dq_other": "Other Category Ratio",
        "dq_freshness": "Article Freshness",
        "dq_latest": "Latest Article",
        "dq_fetched": "Last Fetched",
        "dq_fresh": "Data is fresh",
        "dq_stale_msg": "{days:.0f} days old — check collection",
        "dq_unknown": "No publish dates — freshness unknown",
        "dq_ok": "Classification healthy",
        "dq_warn": "Some articles unclassified",
        "dq_bad": "Possible keyword coverage gap",
        "dq_empty": "No data available for quality check.",
        "download": "Download Articles CSV",
        "disclaimer": "This dashboard measures media exposure signals from Google News RSS. It does not reflect actual sales volumes, market share, or financial performance.",
    },
}

S = STRINGS[lang]

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    html, body, .stApp {
        background-color: #F5F8FB !important;
        font-family: Inter, system-ui, -apple-system, sans-serif;
    }
    .block-container {
    width: 100% !important;
    max-width: 1120px !important;
    padding-top: 1.25rem !important;
    padding-bottom: 2.5rem !important;
    padding-left: 1.25rem !important;
    padding-right: 1.25rem !important;
    margin: 0 auto !important;
    box-sizing: border-box !important;
}

html, body, .stApp, [data-testid="stAppViewContainer"] {
    overflow-x: hidden !important;
}

[data-testid="stHorizontalBlock"] {
    width: 100% !important;
    box-sizing: border-box !important;
}

.js-plotly-plot, .plot-container, .plotly {
    max-width: 100% !important;
    overflow-x: hidden !important;
}

@media (max-width: 768px) {
    .block-container {
        max-width: 100% !important;
        padding-left: 0.85rem !important;
        padding-right: 0.85rem !important;
        padding-top: 0.75rem !important;
    }
}

    /* ── Sidebar ── */
    section[data-testid="stSidebar"] {
        background-color: #001E3C !important;
        border-right: none;
    }
    section[data-testid="stSidebar"] * { color: #FFFFFF !important; }
    section[data-testid="stSidebar"] .stSelectbox label,
    section[data-testid="stSidebar"] .stMultiselect label {
        color: #7AAFD4 !important;
        font-size: 0.68rem !important;
        font-weight: 600 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.08em !important;
    }
    section[data-testid="stSidebar"] hr {
        border-color: #0D3A63 !important;
        margin: 0.75rem 0 !important;
    }
    .sb-section {
        font-size: 0.62rem;
        color: #3A6A94 !important;
        text-transform: uppercase;
        letter-spacing: 0.12em;
        font-weight: 700;
        margin: 1.1rem 0 0.6rem 0;
    }
    .sb-note {
        font-size: 0.72rem;
        color: #3A6A94 !important;
        line-height: 1.5;
        margin-top: 0.5rem;
    }

    /* ── Page header card ── */
    .page-header {
        background: #FFFFFF;
        width: 100%;
        box-sizing: border-box;
        overflow: visible;
        border: 1px solid #D8E6F0;
        border-top: 3px solid #002C5F;
        border-radius: 10px;
        padding: 0.95rem 1.5rem 0.85rem;
        margin-bottom: 0.75rem;
    }
    .ph-title {
    font-size: clamp(1.45rem, 2vw, 1.85rem);
    font-weight: 750;
    color: #001A38;
    letter-spacing: -0.02em;
    margin: 0 0 0.35rem 0;
    line-height: 1.25;
    word-break: keep-all;
    overflow-wrap: break-word;
}
    .ph-sub {
        font-size: 0.78rem;
        color: #7A90A8;
        margin: 0;
        font-weight: 400;
        line-height: 1.4;
    }
    .ph-eyebrow {
        display: inline-block;
        font-size: 0.62rem;
        color: #007FA8;
        font-weight: 700;
        letter-spacing: 0.14em;
        text-transform: uppercase;
        margin-bottom: 0.55rem;
    }

    .ph-eyebrow {
        display: inline-block;
        font-size: 0.62rem;
        color: #007FA8;
        font-weight: 700;
        letter-spacing: 0.14em;
        text-transform: uppercase;
        margin-bottom: 0.55rem;
    }

    .ph-built {
        display: inline-block;
        font-size: 0.72rem;
        color: #6F86A0;
        margin-top: 0.75rem;
        font-weight: 600;
        background: #F1F7FC;
        border: 1px solid #D8E6F0;
        border-radius: 999px;
        padding: 0.28rem 0.65rem;
    }
    .page-header {
        background: #FFFFFF;
        width: 100%;
        box-sizing: border-box;
        overflow: visible;
        border: 1px solid #D8E6F0;
        border-top: 3px solid #002C5F;
        border-radius: 10px;
        padding: 1.35rem 1.75rem 1.2rem;
        margin-bottom: 0.9rem;
        display: block;
    }

    .ph-meta-mini {
        display: flex;
        flex-direction: column;
        gap: 0.15rem;
    }

    .ph-meta-label {
        font-size: 0.58rem;
        color: #8EA7BC;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }

    .ph-meta-value {
        font-size: 0.78rem;
        color: #001A38;
        font-weight: 700;
        line-height: 1.25;
    }

    .ph-stale {
        color: #C53030 !important;
    }

    @media (max-width: 700px) {
    }
    /* ── KPI cards ── */
    .kpi-card {
        background: #FFFFFF;
        border: 1px solid #D8E6F0;
        border-radius: 12px;
        padding: 1.05rem 1.25rem;
        border-left: 3px solid #007FA8;
        box-shadow: 0 1px 4px rgba(0,30,60,0.05);
        min-height: 100px;
        display: flex;
        flex-direction: column;
        justify-content: flex-start;
    }
    .kpi-label {
        font-size: 0.63rem;
        color: #8A9BB0;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.09em;
        margin-bottom: 0.3rem;
    }
    .kpi-value {
        font-size: 1.85rem;
        color: #001A38;
        font-weight: 700;
        line-height: 1.05;
        letter-spacing: -0.02em;
    }
    .kpi-value-md {
        font-size: 1.15rem;
        color: #001A38;
        font-weight: 700;
        line-height: 1.25;
        margin-top: 0.05rem;
    }
    .kpi-sub {
        font-size: 0.68rem;
        color: #A0B4C8;
        margin-top: 0.3rem;
        font-weight: 400;
    }

    /* ── Section card headers ── */
    .section-card {
        background: #FFFFFF;
        border: 1px solid #D8E6F0;
        border-radius: 12px;
        padding: 1rem 1.35rem 0.85rem;
        margin-top: 1.5rem;
        margin-bottom: 0.6rem;
        box-shadow: 0 1px 3px rgba(0,30,60,0.04);
    }
    .sc-title {
        font-size: 0.9rem;
        font-weight: 700;
        color: #001A38;
        letter-spacing: 0.005em;
        border-left: 3px solid #007FA8;
        padding-left: 0.65rem;
        margin: 0 0 0.3rem 0;
        line-height: 1.3;
    }
    .sc-cap {
        font-size: 0.73rem;
        color: #8A9BB0;
        line-height: 1.5;
        margin: 0;
        padding-left: 1rem;
    }

    /* ── Article table ── */
    .at-wrap {
        overflow-x: auto;
        margin-top: 0.5rem;
        border-radius: 8px;
        border: 1px solid #D8E6F0;
    }
    .at-wrap table {
        width: 100%;
        border-collapse: collapse;
        font-size: 0.81rem;
        font-family: Inter, system-ui, sans-serif;
    }
    .at-wrap th {
        background: #F5F8FB;
        color: #6A82A0;
        font-weight: 600;
        font-size: 0.65rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        padding: 0.6rem 0.9rem;
        border-bottom: 1px solid #D8E6F0;
        text-align: left;
        white-space: nowrap;
    }
    .at-wrap td {
        padding: 0.52rem 0.9rem;
        border-bottom: 1px solid #EEF4FA;
        color: #1A2A3A;
        vertical-align: top;
        line-height: 1.45;
    }
    .at-wrap tr:last-child td { border-bottom: none; }
    .at-wrap tr:hover td { background: #F8FBFE; }

    /* ── DQ boxes ── */
    .dq-box {
        background: #FAFCFF;
        border: 1px solid #D8E6F0;
        border-radius: 10px;
        padding: 0.9rem 1.1rem;
        height: 100%;
    }
    .dq-lbl {
        font-size: 0.62rem;
        color: #8A9BB0;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.09em;
        margin-bottom: 0.4rem;
    }
    .dq-val {
        font-size: 1.4rem;
        color: #001A38;
        font-weight: 700;
        line-height: 1.1;
    }
    .dq-note { font-size: 0.7rem; color: #6A82A0; margin-top: 0.25rem; line-height: 1.4; }
    .st-ok   { color: #1E6B41; font-weight: 600; font-size: 0.76rem; margin-top: 0.3rem; }
    .st-warn { color: #92600A; font-weight: 600; font-size: 0.76rem; margin-top: 0.3rem; }
    .st-bad  { color: #C53030; font-weight: 600; font-size: 0.76rem; margin-top: 0.3rem; }

    /* ── Stale banner ── */
    .stale-banner {
        background: #FFF5F5;
        border-left: 3px solid #C53030;
        border-radius: 6px;
        padding: 0.55rem 0.9rem;
        font-size: 0.79rem;
        color: #C53030;
        font-weight: 500;
        margin-bottom: 0.75rem;
    }

    /* ── Expander ── */
    details summary {
        font-size: 0.84rem !important;
        font-weight: 600 !important;
        color: #001A38 !important;
    }

    /* ── Links ── */
    a { color: #007FA8 !important; text-decoration: none; }
    a:hover { text-decoration: underline; }

    /* ── Disclaimer ── */
    .disclaimer {
        background: #EEF5FA;
        border-left: 3px solid #007FA8;
        border-radius: 6px;
        padding: 0.65rem 1rem;
        font-size: 0.74rem;
        color: #4A6A88;
        margin-top: 1.5rem;
        line-height: 1.5;
    }

    @media (max-width: 700px) {
    }
    .meta-strip {
        background: #FFFFFF;
        border: 1px solid #D8E6F0;
        border-radius: 10px;
        padding: 0.85rem 1.15rem;
        margin: -0.25rem 0 0.9rem 0;
        display: flex;
        gap: 1.5rem;
        flex-wrap: wrap;
        font-size: 0.78rem;
        color: #001A38;
        box-shadow: 0 1px 3px rgba(0,30,60,0.04);
    }

    .meta-strip b {
        color: #8EA7BC;
        font-size: 0.68rem;
        font-weight: 700;
    }

    @media (max-width: 700px) {
        .meta-strip {
            flex-direction: column;
            gap: 0.35rem;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)
# ── Top language toggle ───────────────────────────────────────────────────────
# ── Constants ─────────────────────────────────────────────────────────────────
BRAND_QUERIES = {
    "Tata Motors": "Tata Motors India car",
    "Mahindra": "Mahindra car India",
    "Maruti Suzuki": "Maruti Suzuki India",
    "Kia India": "Kia India car",
    "Toyota India": "Toyota India car",
    "MG Motor India": "MG Motor India",
    "Honda Cars India": "Honda Cars India",
    "Skoda India": "Skoda India",
    "Volkswagen India": "Volkswagen India",
    "Renault India": "Renault India",
}

BRAND_KEYWORDS = {
    "Tata Motors": [
        "tata motors",
        "tata nexon",
        "tata harrier",
        "tata safari",
        "tata punch",
        "tata altroz",
        "tata curvv",
        "tata tigor",
        "tata tiago",
        "tata ev",
        r"\btata\b",
    ],
    "Mahindra": [
        "mahindra",
        r"\bm&m\b",
        r"\bxuv\d*\b",
        r"\bxuv3xo\b",
        r"\bxev\b",
        r"\bscorpio\b",
        r"\bthar\b",
        r"\bbolero\b",
        r"\bbe\.6\b",
        r"\bbe6\b",
    ],
    "Maruti Suzuki": [
        "maruti suzuki",
        r"\bmaruti\b",
        "suzuki india",
        "suzuki cars",
        "grand vitara",
        r"\bbrezza\b",
        r"\bswift\b",
        r"\bbaleno\b",
        r"\bdzire\b",
        r"\bfronx\b",
        r"\bjimny\b",
        r"\bertiga\b",
    ],
    "Kia India": [
        r"\bkia\b",
        r"\bseltos\b",
        r"\bsonet\b",
        r"\bcarens\b",
        r"\bsyros\b",
        r"\bev6\b",
        r"\bev9\b",
    ],
    "Toyota India": [
        r"\btoyota\b",
        "innova crysta",
        "innova hycross",
        r"\bfortuner\b",
        "urban cruiser hyryder",
        r"\bhyryder\b",
        r"\bcamry\b",
        r"\bglanza\b",
    ],
    "MG Motor India": [
        "mg motor",
        r"\bmg hector\b",
        r"\bmg astor\b",
        r"\bmg windsor\b",
        r"\bmg comet\b",
        r"\bmg zs\b",
        r"\bmg gloster\b",
        r"\bmg india\b",
    ],
    "Honda Cars India": [
        r"\bhonda\b",
        "honda city",
        "honda amaze",
        "honda elevate",
        r"\bwr-v\b",
    ],
    "Skoda India": [
        r"\bskoda\b",
        r"\bkushaq\b",
        r"\bslavia\b",
        r"\bkodiaq\b",
    ],
    "Volkswagen India": [
        r"\bvolkswagen\b",
        r"\bvw\b",
        r"\btaigun\b",
        r"\bvirtus\b",
        r"\btiguan\b",
    ],
    "Renault India": [
        r"\brenault\b",
        r"\bkiger\b",
        r"\btriber\b",
        r"\bkwid\b",
        r"\bduster\b",
    ],
}

MARKET_POOL_QUERIES = [
    "India auto industry passenger vehicle EV launch investment",
    "India car market Tata Mahindra Maruti Kia Toyota MG",
    "India SUV EV hybrid car launch market",
]

CATEGORIES = {
    "EV": ["ev", "electric", "battery", "charging", "bev"],
    "Hybrid": ["hybrid", "hev"],
    "Investment": [
        "investment",
        "invest",
        "plant",
        "factory",
        "capacity",
        "expansion",
        "manufacturing",
    ],
    "Launch": [
        "launch",
        "unveil",
        "facelift",
        "booking",
        "debut",
        "introduced",
        "variant",
    ],
    "Price": ["price", "discount", "hike", "increase", "cut", "offer"],
    "Export": ["export", "shipment", "overseas", "global market"],
    "Policy": ["policy", "regulation", "gst", "emission", "cafe", "subsidy", "tax"],
}

# Corporate colour palette for strategic signals (no Set2)
SIGNAL_COLORS = {
    "EV": "#007FA8",
    "Hybrid": "#2E9E77",
    "Investment": "#5B7EB8",
    "Launch": "#D9873A",
    "Price": "#8E6DB8",
    "Export": "#4A96CA",
    "Policy": "#B05050",
    "Other": "#9AAFC0",
}

PLOTLY_LAYOUT = dict(
    paper_bgcolor="#FFFFFF",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, system-ui, sans-serif", color="#001A38", size=12),
    margin=dict(l=10, r=65, t=30, b=10),
)


# ── Helpers ───────────────────────────────────────────────────────────────────
def categorize(text: str) -> str:
    t = text.lower()
    for cat, kws in CATEGORIES.items():
        if any(re.search(r"\b" + re.escape(kw) + r"\b", t) for kw in kws):
            return cat
    return "Other"


def _parse_feed(query: str, limit: int) -> list[dict]:
    """Fetch and parse one Google News RSS feed."""
    url = (
        "https://news.google.com/rss/search?"
        f"q={urllib.parse.quote(query)}&hl=en-IN&gl=IN&ceid=IN:en"
    )
    feed = feedparser.parse(url)
    rows = []
    for entry in feed.entries[:limit]:
        title = entry.get("title", "").strip()
        link = entry.get("link", "")
        pub_str = entry.get("published", "")
        summary = re.sub(r"<[^>]+>", "", entry.get("summary", ""))
        if not title:
            continue
        pub_parsed = entry.get("published_parsed")
        try:
            pub_dt = (
                datetime(*pub_parsed[:6], tzinfo=timezone.utc) if pub_parsed else None
            )
        except Exception:
            pub_dt = None
        rows.append(
            {
                "Title": title,
                "Link": link,
                "Published": pub_str,
                "PublishedDt": pub_dt,
                "Summary": summary[:300],
            }
        )
    return rows


def _mentions_brand(text: str, brand: str) -> bool:
    t = text.lower()
    for kw in BRAND_KEYWORDS[brand]:
        if re.search(kw, t):
            return True
    return False


def _now_ist_str() -> str:
    return datetime.now(tz=timezone.utc).astimezone(IST).strftime("%Y-%m-%d %H:%M IST")


# ── Data fetchers ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_brand_feed(selected_brands: tuple, date_range_days: int) -> tuple:
    """Brand-specific RSS queries. Returns (df, fetched_at_ist_str)."""
    when_suffix = f" when:{date_range_days}d"
    rows = []
    for brand in selected_brands:
        query = BRAND_QUERIES[brand] + when_suffix
        for item in _parse_feed(query, limit=15):
            summary_short = (
                item["Summary"][:220] + "…"
                if len(item["Summary"]) > 220
                else item["Summary"]
            )
            rows.append(
                {
                    "Brand": brand,
                    "Title": item["Title"],
                    "Link": item["Link"],
                    "Published": item["Published"],
                    "PublishedDt": item["PublishedDt"],
                    "Summary": summary_short,
                    "Category": categorize(item["Title"] + " " + item["Summary"]),
                }
            )
    fetched_at = _now_ist_str()
    if not rows:
        return (
            pd.DataFrame(
                columns=[
                    "Brand",
                    "Title",
                    "Link",
                    "Published",
                    "PublishedDt",
                    "Summary",
                    "Category",
                ]
            ),
            fetched_at,
        )
    df = pd.DataFrame(rows)
    df = df.drop_duplicates(subset=["Title", "Brand"])
    return (df, fetched_at)


@st.cache_data(ttl=3600, show_spinner=False)
def _fetch_raw_pool(date_range_days: int) -> tuple:
    """Broad market pool. Returns (unique_items, raw_count, fetched_at_ist_str)."""
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
    """Count brand mentions in deduplicated market pool."""
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


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    # Date range — persist across reruns
    st.markdown(
        f'<div class="sb-section">{S["date_label"]}</div>',
        unsafe_allow_html=True,
    )

    date_opts = {S["d_1"]: 1, S["d_7"]: 7, S["d_30"]: 30}
    _days_to_label = {v: k for k, v in date_opts.items()}
    _cur_label = _days_to_label.get(st.session_state["date_range_days"], S["d_7"])
    _cur_idx = list(date_opts.keys()).index(_cur_label)

    selected_range_label = st.selectbox(
        label="date_range",
        options=list(date_opts.keys()),
        index=_cur_idx,
        label_visibility="collapsed",
        key="_date_range",
    )

    date_range_days = date_opts[selected_range_label]
    st.session_state["date_range_days"] = date_range_days

    st.markdown("---")

    # Competitor selection
    st.markdown(
        f'<div class="sb-section">{S["brand_label"]}</div>',
        unsafe_allow_html=True,
    )

    selected_brands = st.multiselect(
        label="brands",
        options=list(BRAND_QUERIES.keys()),
        default=list(BRAND_QUERIES.keys()),
        label_visibility="collapsed",
        key="_brands",
    )

    st.markdown("---")

    # Signal type filter
    st.markdown(
        f'<div class="sb-section">{S["signal_label"]}</div>',
        unsafe_allow_html=True,
    )

    all_cats = [S["all"]] + list(CATEGORIES.keys()) + ["Other"]

    selected_cat = st.selectbox(
        label="signal_type",
        options=all_cats,
        label_visibility="collapsed",
        key="_signal",
    )

    st.markdown("---")

    if st.button(S["refresh"], use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.markdown(
        f'<div class="sb-note">{html.escape(S["refresh_note"])}</div>',
        unsafe_allow_html=True,
    )


# Emergency fallback: make sure filter variables exist
if "selected_brands" not in locals():
    selected_brands = list(BRAND_QUERIES.keys())

if "date_range_days" not in locals():
    date_range_days = st.session_state.get("date_range_days", 7)

if "selected_range_label" not in locals():
    selected_range_label = S["d_7"]

if "selected_cat" not in locals():
    selected_cat = S["all"]
# ── Validate selection ────────────────────────────────────────────────────────
if not selected_brands:
    st.warning(S["warn_select"])
    st.stop()

brands_tuple = tuple(selected_brands)

# ── Header placeholder — filled after data loads ──────────────────────────────
header_ph = st.empty()

# ── Data load ─────────────────────────────────────────────────────────────────
with st.spinner(S["loading"]):
    df_brand, fetched_at_str = fetch_brand_feed(brands_tuple, date_range_days)
    pool_items, pool_raw_count, _ = _fetch_raw_pool(date_range_days)
    df_pool = fetch_market_pool(brands_tuple, date_range_days)

if df_brand.empty and df_pool.empty:
    st.error(S["no_data"])
    st.stop()

# Category filter
df_filtered = df_brand.copy()
is_all_cats = selected_cat == S["all"]
if not is_all_cats:
    df_filtered = df_filtered[df_filtered["Category"] == selected_cat]

# Latest article freshness
pub_dates = df_brand["PublishedDt"].dropna().tolist() if not df_brand.empty else []
latest_dt = max(pub_dates) if pub_dates else None
now_utc = datetime.now(tz=timezone.utc)

if latest_dt:
    latest_ist_str = latest_dt.astimezone(IST).strftime("%Y-%m-%d %H:%M IST")
    days_stale = (now_utc - latest_dt).total_seconds() / 86400
else:
    latest_ist_str = "—"
    days_stale = None

stale_flag = days_stale is not None and days_stale > 3
stale_class = "ph-stale" if stale_flag else ""
# ── Render header (now data is loaded) ───────────────────────────────────────
header_html = f"""
<div class="page-header">
    <div class="ph-eyebrow">{html.escape(S["eyebrow"])}</div>
    <div class="ph-title">{html.escape(S["page_title"])}</div>
    <div class="ph-sub">{html.escape(S["page_sub"])}</div>
    <div class="ph-built">{html.escape(S["built_by"])}</div>
</div>
"""

header_ph.markdown(header_html, unsafe_allow_html=True)
# ── Language selector below header ────────────────────────────────────────────
_, lang_col = st.columns([4, 1.4])

with lang_col:
    lang_options = ["KR · 한국어", "EN · English"]
    lang_index = 0 if st.session_state["lang"] == "ko" else 1

    lang_choice = st.selectbox(
        label="Language",
        options=lang_options,
        index=lang_index,
        key="_lang_select_main",
    )

new_lang = "ko" if "한국어" in lang_choice else "en"
if new_lang != st.session_state["lang"]:
    st.session_state["lang"] = new_lang
    st.rerun()
st.markdown(
    f"""
    <div class="meta-strip">
        <span><b>{html.escape(S["last_updated"])}</b> · {html.escape(fetched_at_str)}</span>
        <span><b>{html.escape(S["latest_article"])}</b> · {html.escape(latest_ist_str)}</span>
        <span><b>{html.escape(S["period"])}</b> · {html.escape(selected_range_label)}</span>
    </div>
    """,
    unsafe_allow_html=True,
)
# ── KPI Cards ─────────────────────────────────────────────────────────────────
total_articles = len(df_brand)
brands_tracked = len(selected_brands)
top_sov_brand = df_pool.iloc[0]["Brand"] if not df_pool.empty else "—"
top_signal = (
    df_filtered["Category"].value_counts().idxmax() if not df_filtered.empty else "—"
)

c1, c2, c3, c4 = st.columns(4)

with c1:
    st.markdown(
        f'<div class="kpi-card">'
        f'<div class="kpi-label">{S["kpi_articles"]}</div>'
        f'<div class="kpi-value">{total_articles}</div>'
        f'<div class="kpi-sub">{html.escape(S["kpi_articles_sub"])}</div>'
        f"</div>",
        unsafe_allow_html=True,
    )

with c2:
    st.markdown(
        f'<div class="kpi-card">'
        f'<div class="kpi-label">{S["kpi_brands"]}</div>'
        f'<div class="kpi-value">{brands_tracked}</div>'
        f'<div class="kpi-sub">{html.escape(S["kpi_brands_sub"])}</div>'
        f"</div>",
        unsafe_allow_html=True,
    )

with c3:
    st.markdown(
        f'<div class="kpi-card">'
        f'<div class="kpi-label">{S["kpi_top_brand"]}</div>'
        f'<div class="kpi-value-md">{html.escape(str(top_sov_brand))}</div>'
        f'<div class="kpi-sub">{html.escape(S["kpi_top_brand_sub"])}</div>'
        f"</div>",
        unsafe_allow_html=True,
    )

with c4:
    st.markdown(
        f'<div class="kpi-card">'
        f'<div class="kpi-label">{S["kpi_top_signal"]}</div>'
        f'<div class="kpi-value-md">{html.escape(str(top_signal))}</div>'
        f'<div class="kpi-sub">{html.escape(S["kpi_top_signal_sub"])}</div>'
        f"</div>",
        unsafe_allow_html=True,
    )

# ── Dashboard guide ───────────────────────────────────────────────────────────
with st.expander(S["guide_title"], expanded=False):
    st.markdown(S["guide_table"])

# ── Charts row 1: Mentions + Share of Voice ───────────────────────────────────
col_l, col_r = st.columns([3, 2])

with col_l:
    st.markdown(
        f'<div class="section-card">'
        f'<div class="sc-title">{html.escape(S["mentions_title"])}</div>'
        f'<div class="sc-cap">{html.escape(S["mentions_cap"])}</div>'
        f"</div>",
        unsafe_allow_html=True,
    )
    if df_pool.empty:
        st.info(S["mentions_empty"])
    else:
        pool_sorted = df_pool.sort_values("Mentions", ascending=True)
        fig_bar = px.bar(
            pool_sorted,
            x="Mentions",
            y="Brand",
            orientation="h",
            color="Mentions",
            color_continuous_scale=["#C8DFF0", "#007FA8", "#002C5F"],
            text="Mentions",
        )
        fig_bar.update_traces(textposition="outside", marker_line_width=0)
        fig_bar.update_layout(
            **PLOTLY_LAYOUT,
            height=360,
            yaxis=dict(title="", tickfont=dict(size=11)),
            xaxis=dict(
                title=S["mentions_xaxis"],
                showgrid=True,
                gridcolor="#EEF4FA",
                zeroline=False,
            ),
            coloraxis_showscale=False,
        )
        st.plotly_chart(fig_bar, use_container_width=True)

with col_r:
    st.markdown(
        f'<div class="section-card">'
        f'<div class="sc-title">{html.escape(S["sov_title"])}</div>'
        f'<div class="sc-cap">{html.escape(S["sov_cap"])}</div>'
        f"</div>",
        unsafe_allow_html=True,
    )
    if df_pool.empty:
        st.info(S["sov_empty"])
    else:
        sov_total = df_pool["Mentions"].sum()
        df_sov = df_pool.copy()
        df_sov["pct"] = (df_sov["Mentions"] / sov_total * 100).round(1)
        df_sov = df_sov.sort_values("pct", ascending=True)

        fig_sov = px.bar(
            df_sov,
            x="pct",
            y="Brand",
            orientation="h",
            color="pct",
            color_continuous_scale=["#C8DFF0", "#007FA8", "#002C5F"],
            text=df_sov["pct"].apply(lambda v: f"{v:.1f}%"),
        )
        fig_sov.update_traces(textposition="outside", marker_line_width=0)
        fig_sov.update_layout(
            **PLOTLY_LAYOUT,
            height=360,
            yaxis=dict(title="", tickfont=dict(size=11)),
            xaxis=dict(
                title=S["sov_xaxis"], showgrid=True, gridcolor="#EEF4FA", zeroline=False
            ),
            coloraxis_showscale=False,
        )
        st.plotly_chart(fig_sov, use_container_width=True)

# ── Chart row 2: Strategic signals ────────────────────────────────────────────
st.markdown(
    f'<div class="section-card">'
    f'<div class="sc-title">{html.escape(S["signal_title"])}</div>'
    f'<div class="sc-cap">{html.escape(S["signal_cap"])}</div>'
    f"</div>",
    unsafe_allow_html=True,
)

if df_filtered.empty:
    st.info(S["signal_empty"])
else:
    signal_df = (
        df_filtered.groupby(["Brand", "Category"]).size().reset_index(name="Count")
    )
    cat_order = list(CATEGORIES.keys()) + ["Other"]

    fig_signal = px.bar(
        signal_df,
        x="Brand",
        y="Count",
        color="Category",
        barmode="stack",
        color_discrete_map=SIGNAL_COLORS,
        category_orders={"Category": cat_order},
    )
    fig_signal.update_layout(
        **PLOTLY_LAYOUT,
        height=340,
        xaxis=dict(title="", tickfont=dict(size=11)),
        yaxis=dict(
            title=S["signal_yaxis"], showgrid=True, gridcolor="#EEF4FA", zeroline=False
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=11),
        ),
        bargap=0.3,
    )
    st.plotly_chart(fig_signal, use_container_width=True)

# ── Recent Articles ───────────────────────────────────────────────────────────
st.markdown(
    f'<div class="section-card">'
    f'<div class="sc-title">{html.escape(S["articles_title"])}</div>'
    f'<div class="sc-cap">{html.escape(S["articles_cap"])}</div>'
    f"</div>",
    unsafe_allow_html=True,
)

if df_filtered.empty:
    st.info(S["articles_empty"])
else:
    disp = df_filtered[["Brand", "Category", "Published", "Title", "Link"]].copy()

    def safe_link(row) -> str:
        raw_url = str(row["Link"]).strip()
        safe_url = raw_url if re.match(r"^https?://", raw_url) else "#"
        safe_title = html.escape(str(row["Title"]))
        safe_href = html.escape(safe_url, quote=True)
        return f'<a href="{safe_href}" target="_blank" rel="noopener noreferrer">{safe_title}</a>'

    disp[S["col_article"]] = disp.apply(safe_link, axis=1)
    disp = (
        disp[[S["col_article"], "Brand", "Category", "Published"]]
        .rename(
            columns={
                "Brand": S["col_brand"],
                "Category": S["col_type"],
                "Published": S["col_date"],
            }
        )
        .reset_index(drop=True)
    )

    for col in (S["col_brand"], S["col_type"], S["col_date"]):
        if col in disp.columns:
            disp[col] = disp[col].apply(lambda v: html.escape(str(v)))

    table_html = disp.to_html(escape=False, index=False)
    st.markdown(
        f'<div class="at-wrap">{table_html}</div>',
        unsafe_allow_html=True,
    )

# ── Data Quality Check ────────────────────────────────────────────────────────
with st.expander(S["dq_title"], expanded=False):
    pool_dedup_count = len(pool_items)

    if stale_flag:
        st.markdown(
            f'<div class="stale-banner">{html.escape(S["dq_stale_banner"])}</div>',
            unsafe_allow_html=True,
        )

    if not df_brand.empty:
        dq1, dq2, dq3 = st.columns(3)

        # 1 — Brand feed + pool counts
        with dq1:
            pool_note = html.escape(
                S["dq_pool"].format(raw=pool_raw_count, dedup=pool_dedup_count)
            )
            st.markdown(
                f'<div class="dq-box">'
                f'<div class="dq-lbl">{S["dq_feed"]}</div>'
                f'<div class="dq-val">{total_articles}</div>'
                f'<div class="dq-note">{pool_note}</div>'
                f"</div>",
                unsafe_allow_html=True,
            )

        # 2 — Other ratio
        other_count = (df_brand["Category"] == "Other").sum()
        other_ratio = other_count / len(df_brand) * 100
        if other_ratio >= 60:
            r_cls, r_dot, r_msg = "st-bad", "●", S["dq_bad"]
        elif other_ratio >= 35:
            r_cls, r_dot, r_msg = "st-warn", "●", S["dq_warn"]
        else:
            r_cls, r_dot, r_msg = "st-ok", "●", S["dq_ok"]

        with dq2:
            st.markdown(
                f'<div class="dq-box">'
                f'<div class="dq-lbl">{S["dq_other"]}</div>'
                f'<div class="dq-val">{other_ratio:.0f}%</div>'
                f'<div class="{r_cls}">{r_dot} {html.escape(r_msg)}</div>'
                f"</div>",
                unsafe_allow_html=True,
            )

        # 3 — Freshness
        if days_stale is None:
            f_cls, f_dot, f_msg = "st-warn", "●", S["dq_unknown"]
        elif stale_flag:
            f_cls, f_dot, f_msg = (
                "st-bad",
                "●",
                S["dq_stale_msg"].format(days=days_stale),
            )
        else:
            f_cls, f_dot, f_msg = "st-ok", "●", S["dq_fresh"]

        with dq3:
            st.markdown(
                f'<div class="dq-box">'
                f'<div class="dq-lbl">{S["dq_freshness"]}</div>'
                f'<div class="dq-val" style="font-size:1rem;margin-top:0.1rem;">'
                f"{html.escape(latest_ist_str)}</div>"
                f'<div class="dq-note">{html.escape(S["dq_fetched"])}: '
                f"{html.escape(fetched_at_str)}</div>"
                f'<div class="{f_cls}">{f_dot} {html.escape(f_msg)}</div>'
                f"</div>",
                unsafe_allow_html=True,
            )
    else:
        st.info(S["dq_empty"])

# ── CSV Download ──────────────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
if not df_brand.empty:
    csv_data = df_brand[
        ["Brand", "Category", "Title", "Published", "Link", "Summary"]
    ].to_csv(index=False)
    st.download_button(
        label=S["download"],
        data=csv_data,
        file_name="india_auto_competitor_news.csv",
        mime="text/csv",
        use_container_width=False,
    )

# ── Disclaimer ────────────────────────────────────────────────────────────────
st.markdown(
    f'<div class="disclaimer">{html.escape(S["disclaimer"])}</div>',
    unsafe_allow_html=True,
)

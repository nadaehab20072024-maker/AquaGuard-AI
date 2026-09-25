"""
AquaGuard AI — UI helpers
============================
Shared styling, translation strings and small rendering helpers used across
every page so the app has one consistent visual system.
"""

import streamlit as st

STATUS_COLORS = {
    "Normal": "#22c55e",
    "Monitoring": "#eab308",
    "Warning": "#f97316",
    "Critical": "#ef4444",
}

STATUS_COLORS_AR = STATUS_COLORS  # colors are language-independent

TXT = {
    "en": {
        "app_title": "AquaGuard AI",
        "app_subtitle": "Smart Water Monitoring & Leak Intelligence",
        "mvp_badge": "MVP • Simulated Data",
        "welcome": "Welcome to AquaGuard AI 💧",
        "choose_lang": "Please choose your preferred language:",
        "nav_overview": "Overview",
        "nav_household": "Household Monitoring",
        "nav_fingerprint": "Consumption Fingerprint",
        "nav_leak": "Leak Detection",
        "nav_building": "Building Water Balance",
        "nav_tank": "Tank & Pump",
        "nav_explorer": "Data Explorer",
        "nav_ai": "AI Insights",
        "nav_assistant": "AI Assistant",
        "select_building": "Building",
        "select_apartment": "Apartment / Household",
        "current_status": "Current Status",
        "current_consumption": "Current Consumption",
        "household_baseline": "Household Baseline",
        "trend": "Trend",
        "idle_flow": "Idle Flow",
        "leak_indicator": "Leak Indicator",
        "household_members": "Household Members",
        "building_id": "Building ID",
        "apartment_id": "Apartment ID",
        "records_analyzed": "Records analyzed",
        "recommended_action": "Recommended Next Action",
    },
    "ar": {
        "app_title": "أكواجارد AI",
        "app_subtitle": "مراقبة ذكية للمياه واكتشاف التسربات",
        "mvp_badge": "نموذج أولي • بيانات محاكاة",
        "welcome": "مرحبًا بك في أكواجارد AI 💧",
        "choose_lang": "الرجاء اختيار لغتك المفضلة:",
        "nav_overview": "نظرة عامة",
        "nav_household": "مراقبة المنزل",
        "nav_fingerprint": "بصمة الاستهلاك",
        "nav_leak": "كشف التسرب",
        "nav_building": "توازن مياه المبنى",
        "nav_tank": "الخزان والمضخة",
        "nav_explorer": "مستكشف البيانات",
        "nav_ai": "رؤى الذكاء الاصطناعي",
        "nav_assistant": "المساعد الذكي",
        "select_building": "المبنى",
        "select_apartment": "الشقة / المنزل",
        "current_status": "الحالة الحالية",
        "current_consumption": "الاستهلاك الحالي",
        "household_baseline": "الخط الأساسي للمنزل",
        "trend": "الاتجاه",
        "idle_flow": "تدفق الخمول",
        "leak_indicator": "مؤشر التسرب",
        "household_members": "أفراد الأسرة",
        "building_id": "رقم المبنى",
        "apartment_id": "رقم الشقة",
        "records_analyzed": "السجلات التي تم تحليلها",
        "recommended_action": "الإجراء الموصى به التالي",
    },
}

STATUS_TRANSLATIONS = {
    "en": {"Normal": "Normal", "Monitoring": "Monitoring", "Warning": "Warning", "Critical": "Critical"},
    "ar": {"Normal": "طبيعي", "Monitoring": "قيد المراقبة", "Warning": "تحذير", "Critical": "حرج"},
}


def t(key: str) -> str:
    lang = st.session_state.get("lang", "en")
    return TXT.get(lang, TXT["en"]).get(key, key)


def status_label(status: str) -> str:
    lang = st.session_state.get("lang", "en")
    return STATUS_TRANSLATIONS.get(lang, STATUS_TRANSLATIONS["en"]).get(status, status)


def inject_css():
    st.markdown(
        """
        <style>
        :root {
            --aq-bg: #0a0e17;
            --aq-panel: #121a2b;
            --aq-panel-border: #1f2c44;
            --aq-cyan: #22d3ee;
            --aq-text: #e6edf7;
            --aq-muted: #93a4bf;
        }
        .stApp {
            background: linear-gradient(180deg, #070b12 0%, #0a0e17 100%);
        }
        section[data-testid="stSidebar"] {
            background: #0b1120;
            border-right: 1px solid var(--aq-panel-border);
        }
        h1, h2, h3, h4 {
            color: var(--aq-text) !important;
            font-family: 'Segoe UI', system-ui, sans-serif;
        }
        .aq-header {
            display: flex;
            align-items: baseline;
            gap: 0.6rem;
            margin-bottom: 0.1rem;
        }
        .aq-title {
            font-size: 2.1rem;
            font-weight: 800;
            background: linear-gradient(90deg, #22d3ee, #60a5fa);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .aq-subtitle {
            color: var(--aq-muted);
            font-size: 1.02rem;
            margin-top: -0.4rem;
        }
        .aq-badge {
            display: inline-block;
            margin-top: 0.4rem;
            padding: 2px 10px;
            border-radius: 999px;
            border: 1px solid var(--aq-panel-border);
            color: var(--aq-cyan);
            font-size: 0.72rem;
            letter-spacing: 0.03em;
        }
        div[data-testid="stMetric"] {
            background: var(--aq-panel);
            border: 1px solid var(--aq-panel-border);
            border-radius: 14px;
            padding: 14px 16px 10px 16px;
        }
        div[data-testid="stMetric"] label {
            color: var(--aq-muted) !important;
        }
        .aq-card {
            background: var(--aq-panel);
            border: 1px solid var(--aq-panel-border);
            border-radius: 14px;
            padding: 18px 20px;
            margin-bottom: 14px;
        }
        .aq-status-pill {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 6px 16px;
            border-radius: 999px;
            font-weight: 700;
            font-size: 0.95rem;
        }
        .aq-dot {
            width: 10px; height: 10px; border-radius: 50%;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_header():
    st.markdown(
        f"""
        <div class="aq-header">
            <span style="font-size:2rem;">💧</span>
            <span class="aq-title">{t('app_title')}</span>
        </div>
        <div class="aq-subtitle">{t('app_subtitle')}</div>
        <div class="aq-badge">{t('mvp_badge')}</div>
        <div style="height:14px"></div>
        """,
        unsafe_allow_html=True,
    )


def status_pill(status: str):
    color = STATUS_COLORS.get(status, "#93a4bf")
    label = status_label(status)
    st.markdown(
        f"""
        <div class="aq-status-pill" style="background:{color}22; color:{color}; border:1px solid {color}55;">
            <span class="aq-dot" style="background:{color};"></span> {label}
        </div>
        """,
        unsafe_allow_html=True,
    )


def card_start():
    st.markdown('<div class="aq-card">', unsafe_allow_html=True)


def card_end():
    st.markdown("</div>", unsafe_allow_html=True)

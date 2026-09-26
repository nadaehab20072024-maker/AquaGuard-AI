"""
AquaGuard AI — UI System
==========================
Shared design system for the whole application: light/dark theme (real
per-component theming, not just a background swap), full bilingual text
table (EN/AR), RTL support for Arabic, and the small rendering helpers used
by every page so the product feels like one coherent, professional app
rather than a stack of separate screens.

Nothing in this file touches the analysis logic — it is purely presentation.
"""

import streamlit as st

# ---------------------------------------------------------------------------
# Status colors (semantic — same meaning in both themes)
# ---------------------------------------------------------------------------
STATUS_COLORS = {
    "Normal": "#22c55e",
    "Monitoring": "#eab308",
    "Warning": "#f97316",
    "Critical": "#ef4444",
}

STATUS_ICONS = {
    "Normal": "🟢",
    "Monitoring": "🟡",
    "Warning": "🟠",
    "Critical": "🔴",
}

NAV_ITEMS = [
    ("overview", "🏠"),
    ("household", "💧"),
    ("fingerprint", "🧬"),
    ("leak", "🚨"),
    ("building", "🏢"),
    ("tank", "🛢️"),
    ("ai", "🤖"),
    ("assistant", "💬"),
    ("profile", "👤"),
]

DEMO_NAV_ITEMS = [
    ("demo", "🎓"),
    ("explorer", "🗂️"),
]

# ---------------------------------------------------------------------------
# Text table
# ---------------------------------------------------------------------------
TXT = {
    "en": {
        "app_title": "AquaGuard AI",
        "app_subtitle": "Smart Water Monitoring & Leak Intelligence",
        "mvp_badge": "MVP • Simulated Data",
        "landing_tagline": "Understand your household's water behavior, detect unusual patterns, "
                            "and act before a small issue becomes a major loss.",
        "choose_lang": "Please choose your preferred language",
        "get_started": "Get started",

        "onboard_title": "Set up your household",
        "onboard_intro": "AquaGuard uses your household profile to learn your normal water-consumption pattern.",
        "onboard_building": "Building / property",
        "onboard_unit": "Apartment / unit",
        "onboard_members": "Number of household members",
        "onboard_submit": "Create my profile",
        "onboard_analyzing": "Analyzing your household…",
        "onboard_note": "This MVP uses simulated data to represent your assigned household.",

        "nav_overview": "Overview",
        "nav_household": "My Water",
        "nav_fingerprint": "Consumption Pattern",
        "nav_leak": "Alerts",
        "nav_building": "Building",
        "nav_tank": "Tank & Pump",
        "nav_ai": "AI Insights",
        "nav_assistant": "Assistant",
        "nav_profile": "Profile",
        "nav_demo": "Jury / Demo Mode",
        "nav_explorer": "Data Explorer",

        "good_morning": "Good morning",
        "good_afternoon": "Good afternoon",
        "good_evening": "Good evening",
        "your_water_status": "Your Water Status",
        "presenter_mode": "Presenter access",
        "presenter_on": "Demo Mode is ON — household switching & raw data are visible.",
        "presenter_toggle": "Enable Jury / Demo Mode",
        "presenter_hint": "For hackathon presentation only — hidden from normal users.",
        "theme_toggle": "Dark mode",

        "status_expl_normal": "Your consumption is currently within your normal household pattern.",
        "status_expl_monitoring": "Your consumption is slightly higher than usual. AquaGuard is keeping an eye on it.",
        "status_expl_warning": "Your consumption is higher than your usual pattern. We are checking whether this may be related to normal household activity.",
        "status_expl_critical": "We found water-use behavior that does not match your normal household pattern.",

        "current_consumption": "Today's Usage",
        "household_baseline": "Normal Range",
        "trend": "Pattern Status",
        "idle_flow": "Idle Flow",
        "leak_indicator": "Leak Indicator",
        "household_members": "Household Members",
        "fingerprint_confidence": "Fingerprint Confidence",
        "building_id": "Building",
        "apartment_id": "Household",
        "records_analyzed": "Records analyzed",
        "recommended_action": "What you can do",
        "why_seeing_this": "Why am I seeing this?",

        "smart_form_title": "A quick question",
        "smart_form_lead": "We noticed that your water use was higher than your usual pattern.",
        "smart_form_question": "Was there any unusual activity during this period?",
        "smart_form_submit": "Submit",
        "smart_form_recorded": "Thanks — re-analyzing your consumption…",
        "smart_form_explained_before": "High usage explained. This has been classified as legitimate household activity.",
        "smart_form_none_needed": "No unusual water activity has been detected recently.",

        "possible_leak": "Possible Hidden Leak",
        "leak_lead": "Unexpected water flow was detected during your usual inactive period.",
        "evidence_title": "Evidence",
        "leak_next_steps": "What you can do",
        "leak_step_1": "Check the visible water fixtures around your home.",
        "leak_step_2": "Use a portable non-invasive moisture detector to inspect suspected areas.",
        "leak_step_3": "If the unusual flow continues, request a technical inspection.",
        "request_inspection": "Request Technical Inspection",
        "inspection_requested": "Request received. A technical inspection has been logged for your household.",

        "fp_intro": "Your Consumption Fingerprint is AquaGuard's understanding of your household's normal water-use behavior.",
        "fp_normal_range": "Normal daily range",
        "fp_avg": "Average daily use",
        "fp_high_days": "Typical high-use days",
        "fp_low_days": "Typical low-use days",
        "fp_idle_period": "Learned idle period",
        "fp_idle_flow": "Expected idle flow",
        "fp_confidence": "Fingerprint confidence",
        "fp_not_ready": "AquaGuard is still learning your household's normal pattern. Check back after a few more days of data.",
        "fp_weekday_pattern": "Weekly pattern",

        "bb_flow_title": "Building Water Balance",
        "bb_main": "Main Meter Water",
        "bb_apts": "Apartment Consumption",
        "bb_ext": "Legitimate External Use",
        "bb_unaccounted": "Unaccounted Water",
        "bb_alert": "This difference may indicate water use outside the monitored apartment meters, or another building-level issue.",
        "bb_balanced": "Your building's water accounts are balanced.",
        "bb_not_available": "Building-level water data is unavailable for this building.",

        "tank_level": "Tank Level",
        "pump_state": "Pump State",
        "tank_normal": "Normal Tank Operation",
        "tank_monitoring": "Monitoring Tank & Pump",
        "tank_issue": "Possible Tank/Pump Issue",
        "tank_not_available": "Tank and pump data is unavailable for this building.",

        "ai_headline": "AquaGuard Insight",
        "ai_meaning": "What this means",
        "ai_action": "Recommended action",

        "assistant_caption": "Ask about your household's AquaGuard data.",
        "assistant_placeholder": "Ask AquaGuard…",
        "assistant_try": "Try",

        "profile_title": "Household Profile",
        "profile_update_note": "Your consumption fingerprint will gradually adapt to your new household pattern.",
        "profile_save": "Save changes",
        "profile_saved": "Your household profile has been updated.",
        "profile_language": "Language",
        "profile_theme": "Appearance",

        "empty_generic": "Nothing to show here yet.",
        "error_generic": "We couldn't load this information right now. Please try again.",

        "demo_title": "Jury / Demo Mode",
        "demo_marked": "Demo Mode",
        "demo_subtitle": "Simulated presentation scenarios — not part of the normal user experience.",
        "demo_scenario": "Demo Scenario",
        "demo_apply": "Apply Scenario",
        "demo_household": "Presenter household selection",
        "demo_switch_note": "This is the only place where switching simulated households is allowed.",
    },
    "ar": {
        "app_title": "أكواجارد AI",
        "app_subtitle": "المراقبة الذكية للمياه واكتشاف التسربات",
        "mvp_badge": "نموذج أولي • بيانات محاكاة",
        "landing_tagline": "افهم سلوك استهلاك المياه في منزلك، واكتشف الأنماط غير المعتادة، "
                            "وتصرّف قبل أن تتحول مشكلة صغيرة إلى خسارة كبيرة.",
        "choose_lang": "الرجاء اختيار لغتك المفضلة",
        "get_started": "ابدأ الآن",

        "onboard_title": "إعداد منزلك",
        "onboard_intro": "يستخدم أكواجارد ملف منزلك لتعلّم نمط استهلاك المياه الطبيعي لديك.",
        "onboard_building": "المبنى / العقار",
        "onboard_unit": "الشقة / الوحدة",
        "onboard_members": "عدد أفراد الأسرة",
        "onboard_submit": "إنشاء ملفي",
        "onboard_analyzing": "جارٍ تحليل بيانات منزلك…",
        "onboard_note": "يستخدم هذا النموذج الأولي بيانات محاكاة لتمثيل المنزل المخصص لك.",

        "nav_overview": "نظرة عامة",
        "nav_household": "مياهي",
        "nav_fingerprint": "نمط الاستهلاك",
        "nav_leak": "التنبيهات",
        "nav_building": "المبنى",
        "nav_tank": "الخزان والمضخة",
        "nav_ai": "رؤى الذكاء الاصطناعي",
        "nav_assistant": "المساعد",
        "nav_profile": "الملف الشخصي",
        "nav_demo": "وضع لجنة التحكيم / العرض",
        "nav_explorer": "مستكشف البيانات",

        "good_morning": "صباح الخير",
        "good_afternoon": "مساء الخير",
        "good_evening": "مساء الخير",
        "your_water_status": "حالة المياه لديك",
        "presenter_mode": "دخول المقدّم",
        "presenter_on": "وضع العرض مفعّل — التبديل بين المنازل والبيانات الخام مرئي الآن.",
        "presenter_toggle": "تفعيل وضع لجنة التحكيم / العرض",
        "presenter_hint": "لعرض الهاكاثون فقط — غير ظاهر للمستخدم العادي.",
        "theme_toggle": "الوضع الداكن",

        "status_expl_normal": "استهلاكك حاليًا ضمن نمط منزلك الطبيعي.",
        "status_expl_monitoring": "استهلاكك أعلى قليلاً من المعتاد. يراقب أكواجارد الوضع.",
        "status_expl_warning": "استهلاكك أعلى من نمطك المعتاد. نتحقق مما إذا كان هذا مرتبطًا بنشاط منزلي طبيعي.",
        "status_expl_critical": "وجدنا سلوك استخدام مياه لا يتطابق مع نمط منزلك الطبيعي.",

        "current_consumption": "استهلاك اليوم",
        "household_baseline": "النطاق الطبيعي",
        "trend": "حالة النمط",
        "idle_flow": "تدفق الخمول",
        "leak_indicator": "مؤشر التسرب",
        "household_members": "أفراد الأسرة",
        "fingerprint_confidence": "ثقة البصمة",
        "building_id": "المبنى",
        "apartment_id": "المنزل",
        "records_analyzed": "السجلات التي تم تحليلها",
        "recommended_action": "ما يمكنك فعله",
        "why_seeing_this": "لماذا أرى هذا؟",

        "smart_form_title": "سؤال سريع",
        "smart_form_lead": "لاحظنا أن استخدام المياه لديك كان أعلى من نمطك المعتاد.",
        "smart_form_question": "هل كان هناك أي نشاط غير معتاد خلال هذه الفترة؟",
        "smart_form_submit": "إرسال",
        "smart_form_recorded": "شكرًا — جارٍ إعادة تحليل استهلاكك…",
        "smart_form_explained_before": "تم تفسير الاستهلاك المرتفع. تم تصنيف هذا كنشاط منزلي مشروع.",
        "smart_form_none_needed": "لم يتم رصد أي نشاط مياه غير معتاد مؤخرًا.",

        "possible_leak": "احتمال وجود تسرب مخفي",
        "leak_lead": "تم رصد تدفق مياه غير متوقع خلال فترة خمولك المعتادة.",
        "evidence_title": "الأدلة",
        "leak_next_steps": "ما يمكنك فعله",
        "leak_step_1": "افحص تجهيزات المياه الظاهرة في منزلك.",
        "leak_step_2": "استخدم كاشف رطوبة محمول غير جراحي لفحص المناطق المشتبه بها.",
        "leak_step_3": "إذا استمر التدفق غير المعتاد، اطلب فحصًا فنيًا.",
        "request_inspection": "طلب فحص فني",
        "inspection_requested": "تم استلام الطلب. تم تسجيل طلب فحص فني لمنزلك.",

        "fp_intro": "بصمة الاستهلاك هي فهم أكواجارد لنمط استخدام المياه الطبيعي في منزلك.",
        "fp_normal_range": "النطاق اليومي الطبيعي",
        "fp_avg": "متوسط الاستخدام اليومي",
        "fp_high_days": "أيام الاستخدام المرتفع المعتادة",
        "fp_low_days": "أيام الاستخدام المنخفض المعتادة",
        "fp_idle_period": "فترة الخمول المتعلَّمة",
        "fp_idle_flow": "تدفق الخمول المتوقع",
        "fp_confidence": "ثقة البصمة",
        "fp_not_ready": "لا يزال أكواجارد يتعلّم نمط منزلك الطبيعي. تحقّق لاحقًا بعد المزيد من البيانات.",
        "fp_weekday_pattern": "النمط الأسبوعي",

        "bb_flow_title": "توازن مياه المبنى",
        "bb_main": "مياه العداد الرئيسي",
        "bb_apts": "استهلاك الشقق",
        "bb_ext": "الاستخدام الخارجي المشروع",
        "bb_unaccounted": "المياه غير المحسوبة",
        "bb_alert": "قد يشير هذا الفرق إلى استخدام مياه خارج عدادات الشقق المراقبة، أو مشكلة أخرى على مستوى المبنى.",
        "bb_balanced": "حسابات مياه مبناك متوازنة.",
        "bb_not_available": "بيانات مياه المبنى غير متوفرة لهذا المبنى.",

        "tank_level": "مستوى الخزان",
        "pump_state": "حالة المضخة",
        "tank_normal": "تشغيل طبيعي للخزان",
        "tank_monitoring": "مراقبة الخزان والمضخة",
        "tank_issue": "احتمال وجود مشكلة في الخزان/المضخة",
        "tank_not_available": "بيانات الخزان والمضخة غير متوفرة لهذا المبنى.",

        "ai_headline": "رؤية أكواجارد",
        "ai_meaning": "ماذا يعني هذا",
        "ai_action": "الإجراء الموصى به",

        "assistant_caption": "اسأل عن بيانات أكواجارد الخاصة بمنزلك.",
        "assistant_placeholder": "اسأل أكواجارد…",
        "assistant_try": "جرّب",

        "profile_title": "الملف الشخصي للمنزل",
        "profile_update_note": "ستتكيف بصمة استهلاكك تدريجيًا مع نمط منزلك الجديد.",
        "profile_save": "حفظ التغييرات",
        "profile_saved": "تم تحديث ملف منزلك.",
        "profile_language": "اللغة",
        "profile_theme": "المظهر",

        "empty_generic": "لا يوجد شيء لعرضه هنا بعد.",
        "error_generic": "تعذّر تحميل هذه المعلومات الآن. يرجى المحاولة مرة أخرى.",

        "demo_title": "وضع لجنة التحكيم / العرض",
        "demo_marked": "وضع العرض التوضيحي",
        "demo_subtitle": "سيناريوهات عرض محاكاة — ليست جزءًا من تجربة المستخدم العادية.",
        "demo_scenario": "سيناريو العرض",
        "demo_apply": "تطبيق السيناريو",
        "demo_household": "اختيار منزل المقدّم",
        "demo_switch_note": "هذا هو المكان الوحيد المسموح فيه بالتبديل بين المنازل المحاكاة.",
    },
}

STATUS_TRANSLATIONS = {
    "en": {"Normal": "Normal", "Monitoring": "Monitoring", "Warning": "Warning", "Critical": "Critical"},
    "ar": {"Normal": "طبيعي", "Monitoring": "قيد المراقبة", "Warning": "تحذير", "Critical": "حرج"},
}

NAV_LABEL_KEYS = {
    "overview": "nav_overview", "household": "nav_household", "fingerprint": "nav_fingerprint",
    "leak": "nav_leak", "building": "nav_building", "tank": "nav_tank", "ai": "nav_ai",
    "assistant": "nav_assistant", "profile": "nav_profile", "demo": "nav_demo", "explorer": "nav_explorer",
}


def t(key: str) -> str:
    lang = st.session_state.get("lang", "en")
    return TXT.get(lang, TXT["en"]).get(key, key)


def is_ar() -> bool:
    return st.session_state.get("lang") == "ar"


def status_label(status: str) -> str:
    lang = st.session_state.get("lang", "en")
    return STATUS_TRANSLATIONS.get(lang, STATUS_TRANSLATIONS["en"]).get(status, status)


def status_explanation_key(status: str) -> str:
    return {
        "Normal": "status_expl_normal", "Monitoring": "status_expl_monitoring",
        "Warning": "status_expl_warning", "Critical": "status_expl_critical",
    }.get(status, "status_expl_normal")


def nav_label(key: str) -> str:
    return t(NAV_LABEL_KEYS.get(key, key))


# ---------------------------------------------------------------------------
# Theme (real light/dark, every component adapts)
# ---------------------------------------------------------------------------
def inject_css():
    dark = st.session_state.get("theme", "dark") == "dark"
    rtl = is_ar()

    root_vars = (
        """
        --aq-bg: #0a0f1a;
        --aq-bg-2: #0d1420;
        --aq-surface: #121a2b;
        --aq-surface-2: #0f1726;
        --aq-border: #23334d;
        --aq-text: #e8eefb;
        --aq-muted: #96a7c4;
        --aq-accent: #22d3ee;
        --aq-accent-2: #38bdf8;
        --aq-teal: #14b8a6;
        --aq-shadow: 0 8px 24px rgba(0,0,0,0.35);
        """
        if dark else
        """
        --aq-bg: #f3f8fb;
        --aq-bg-2: #eaf3f8;
        --aq-surface: #ffffff;
        --aq-surface-2: #f3f8fb;
        --aq-border: #dbe6ef;
        --aq-text: #0c2340;
        --aq-muted: #5b7089;
        --aq-accent: #0891b2;
        --aq-accent-2: #0e7490;
        --aq-teal: #0d9488;
        --aq-shadow: 0 8px 24px rgba(15,60,90,0.08);
        """
    )

    wave_svg = (
        "data:image/svg+xml;utf8,"
        "%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 1440 200'%3E"
        "%3Cpath fill='%2322d3ee' fill-opacity='0.06' "
        "d='M0,80 C240,140 480,20 720,60 C960,100 1200,160 1440,90 L1440,200 L0,200 Z'/%3E%3C/svg%3E"
    )

    direction_css = f"""
        .stApp, section[data-testid="stSidebar"] {{
            direction: {"rtl" if rtl else "ltr"};
        }}
        .aq-card, div[data-testid="stMetric"] {{
            text-align: {"right" if rtl else "left"};
        }}
    """

    st.markdown(
        f"""
        <style>
        :root {{ {root_vars} }}

        .stApp {{
            background:
                linear-gradient(180deg, var(--aq-bg) 0%, var(--aq-bg-2) 100%),
                url("{wave_svg}") bottom / cover no-repeat;
            background-blend-mode: normal;
        }}
        section[data-testid="stSidebar"] {{
            background: var(--aq-surface-2);
            border-right: 1px solid var(--aq-border);
        }}
        {direction_css}

        h1, h2, h3, h4, h5, p, span, label, div {{
            color: var(--aq-text);
        }}
        .stApp, .stApp p, .stApp li {{
            color: var(--aq-text);
        }}
        .stCaption, [data-testid="stCaptionContainer"] {{
            color: var(--aq-muted) !important;
        }}

        .aq-header {{ display:flex; align-items:baseline; gap:0.6rem; margin-bottom:0.1rem; }}
        .aq-title {{
            font-size: 1.9rem; font-weight: 800;
            background: linear-gradient(90deg, var(--aq-accent), var(--aq-accent-2));
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        }}
        .aq-subtitle {{ color: var(--aq-muted); font-size: 0.98rem; margin-top: -0.35rem; }}
        .aq-badge {{
            display:inline-block; margin-top:0.4rem; padding:2px 10px; border-radius:999px;
            border:1px solid var(--aq-border); color: var(--aq-accent); font-size:0.72rem; letter-spacing:0.03em;
        }}

        div[data-testid="stMetric"] {{
            background: var(--aq-surface);
            border: 1px solid var(--aq-border);
            border-radius: 14px;
            padding: 14px 16px 10px 16px;
            box-shadow: var(--aq-shadow);
        }}
        div[data-testid="stMetric"] label {{ color: var(--aq-muted) !important; }}
        div[data-testid="stMetric"] div {{ color: var(--aq-text) !important; }}

        .aq-card {{
            background: var(--aq-surface);
            border: 1px solid var(--aq-border);
            border-radius: 16px;
            padding: 18px 20px;
            margin-bottom: 14px;
            box-shadow: var(--aq-shadow);
        }}
        .aq-card-soft {{
            background: var(--aq-surface-2);
            border: 1px dashed var(--aq-border);
            border-radius: 14px;
            padding: 16px 18px;
            margin-bottom: 14px;
        }}

        .aq-status-pill {{
            display:inline-flex; align-items:center; gap:8px; padding:7px 18px;
            border-radius:999px; font-weight:700; font-size:0.95rem;
        }}
        .aq-dot {{ width:10px; height:10px; border-radius:50%; }}

        .aq-nav-btn button {{
            width: 100%;
            border-radius: 10px !important;
        }}

        .stButton>button, .stDownloadButton>button {{
            border-radius: 10px;
            border: 1px solid var(--aq-border);
        }}
        .stButton>button[kind="primary"] {{
            background: linear-gradient(90deg, var(--aq-accent), var(--aq-accent-2));
            border: none; color: #04222c; font-weight: 700;
        }}

        .aq-lang-card {{
            border: 1px solid var(--aq-border); border-radius: 16px; padding: 22px;
            text-align: center; background: var(--aq-surface); box-shadow: var(--aq-shadow);
        }}

        .aq-demo-banner {{
            border: 1px solid var(--aq-teal); background: color-mix(in srgb, var(--aq-teal) 12%, transparent);
            border-radius: 12px; padding: 10px 16px; margin-bottom: 12px; font-weight: 600;
        }}

        .aq-empty {{
            border: 1px dashed var(--aq-border); border-radius: 14px; padding: 28px;
            text-align:center; color: var(--aq-muted);
        }}

        div[data-testid="stExpander"] {{
            background: var(--aq-surface); border: 1px solid var(--aq-border); border-radius: 12px;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_header():
    st.markdown(
        f"""
        <div class="aq-header">
            <span style="font-size:1.8rem;">💧</span>
            <span class="aq-title">{t('app_title')}</span>
        </div>
        <div class="aq-subtitle">{t('app_subtitle')}</div>
        <div class="aq-badge">{t('mvp_badge')}</div>
        <div style="height:10px"></div>
        """,
        unsafe_allow_html=True,
    )


def status_pill(status: str):
    color = STATUS_COLORS.get(status, "#93a4bf")
    label = status_label(status)
    icon = STATUS_ICONS.get(status, "⚪")
    st.markdown(
        f"""
        <div class="aq-status-pill" style="background:{color}22; color:{color}; border:1px solid {color}55;">
            <span>{icon}</span> {label}
        </div>
        """,
        unsafe_allow_html=True,
    )


def status_explanation(status: str):
    st.write(t(status_explanation_key(status)))


def card_start(soft: bool = False):
    st.markdown(f'<div class="{"aq-card-soft" if soft else "aq-card"}">', unsafe_allow_html=True)


def card_end():
    st.markdown("</div>", unsafe_allow_html=True)


def empty_state(message: str = None):
    st.markdown(f'<div class="aq-empty">🌊 {message or t("empty_generic")}</div>', unsafe_allow_html=True)


def demo_banner(scenario_title: str, scenario_text: str):
    st.markdown(
        f'<div class="aq-demo-banner">🎓 {t("demo_marked")} — <strong>{scenario_title}</strong><br/>'
        f'<span style="font-weight:400;">{scenario_text}</span></div>',
        unsafe_allow_html=True,
    )

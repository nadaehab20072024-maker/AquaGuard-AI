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

import base64
import os

import streamlit as st

_ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")


@st.cache_data(show_spinner=False)
def _logo_data_uri(filename: str) -> str | None:
    """Base64-encode a logo file once and cache it, so the real AquaGuard AI
    logo can be embedded inline in styled HTML (header/sidebar/onboarding)
    instead of falling back to a generic water-drop icon."""
    path = os.path.join(_ASSETS_DIR, filename)
    if not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")
    return f"data:image/jpeg;base64,{b64}"


def logo_uri(size: str = "small") -> str | None:
    """size: 'small' (header/sidebar), 'medium' (onboarding), 'full' (original)."""
    filename = {"small": "logo_small.jpg", "medium": "logo_medium.jpg", "full": "logo.jpg"}.get(size, "logo_small.jpg")
    return _logo_data_uri(filename) or _logo_data_uri("logo.jpg")


# ---------------------------------------------------------------------------
# Status colors (semantic — same meaning in both themes)
# ---------------------------------------------------------------------------
STATUS_COLORS = {
    "Normal": "#22c55e",
    "Monitoring": "#eab308",
    "Warning": "#f97316",
    "Critical": "#ef4444",
    "Pending": "#94a3b8",
}

STATUS_ICONS = {
    "Normal": "🟢",
    "Monitoring": "🟡",
    "Warning": "🟠",
    "Critical": "🔴",
    "Pending": "❔",
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
        "status_expl_pending": "Your usage today is higher than your normal pattern. We're not calling this a problem yet — please answer the quick question below so AquaGuard can confirm.",

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
        "assistant_bill_title": "📎 Attach a water bill",
        "assistant_bill_caption": "Upload a photo or PDF of your actual water bill, and AquaGuard will check it against your normal pattern.",
        "assistant_bill_uploader": "Bill photo or PDF",
        "assistant_bill_analyzing": "Reading your bill…",
        "assistant_bill_not_found": "I couldn't clearly read a consumption figure from this file. You can type it in below instead.",
        "assistant_bill_manual_label": "Billed consumption for this period",
        "assistant_bill_manual_unit": "Unit",
        "assistant_bill_manual_button": "Check this figure",
        "assistant_bill_period_label": "Billing period (days)",
        "assistant_bill_found_prefix": "Found in your bill: ",

        "profile_title": "Household Profile",
        "profile_update_note": "Your consumption fingerprint will gradually adapt to your new household pattern.",
        "profile_save": "Save changes",
        "profile_saved": "Your household profile has been updated.",
        "profile_language": "Language",
        "profile_theme": "Appearance",

        "empty_generic": "Nothing to show here yet.",
        "error_generic": "We couldn't load this information right now. Please try again.",
        "unavailable": "Unavailable",

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
        "status_expl_pending": "استهلاكك اليوم أعلى من نمطك الطبيعي. لسنا نعتبر هذا مشكلة بعد — يرجى الإجابة على السؤال السريع أدناه حتى يتأكد أكواجارد.",

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
        "assistant_bill_title": "📎 أرفقي فاتورة المياه",
        "assistant_bill_caption": "ارفعي صورة أو ملف PDF لفاتورة المياه الفعلية، وسيقارنها أكواجارد بنمط استهلاكك الطبيعي.",
        "assistant_bill_uploader": "صورة الفاتورة أو ملف PDF",
        "assistant_bill_analyzing": "جاري قراءة الفاتورة…",
        "assistant_bill_not_found": "ما قدرت أقرأ رقم الاستهلاك بوضوح من هذا الملف. تقدرين تكتبينه يدويًا بالأسفل بدلاً من ذلك.",
        "assistant_bill_manual_label": "الاستهلاك المفوتَر لهذه الفترة",
        "assistant_bill_manual_unit": "الوحدة",
        "assistant_bill_manual_button": "تحقق من هذا الرقم",
        "assistant_bill_period_label": "مدة الفاتورة (بالأيام)",
        "assistant_bill_found_prefix": "تم العثور عليه بالفاتورة: ",

        "profile_title": "الملف الشخصي للمنزل",
        "profile_update_note": "ستتكيف بصمة استهلاكك تدريجيًا مع نمط منزلك الجديد.",
        "profile_save": "حفظ التغييرات",
        "profile_saved": "تم تحديث ملف منزلك.",
        "profile_language": "اللغة",
        "profile_theme": "المظهر",

        "empty_generic": "لا يوجد شيء لعرضه هنا بعد.",
        "error_generic": "تعذّر تحميل هذه المعلومات الآن. يرجى المحاولة مرة أخرى.",
        "unavailable": "غير متاح",

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
    "en": {"Normal": "Normal", "Monitoring": "Monitoring", "Warning": "Warning", "Critical": "Critical",
           "Pending": "Awaiting Your Answer"},
    "ar": {"Normal": "طبيعي", "Monitoring": "قيد المراقبة", "Warning": "تحذير", "Critical": "حرج",
           "Pending": "بانتظار إجابتك"},
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
        "Pending": "status_expl_pending",
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
        --aq-bg: #2a2550;
        --aq-bg-2: #34306e;
        --aq-surface: #3d3777;
        --aq-surface-2: #352c66;
        --aq-border: #5b4f96;
        --aq-text: #f5f3ff;
        --aq-muted: #c9c2e8;
        --aq-accent: #2dd4bf;
        --aq-accent-2: #60a5fa;
        --aq-accent-3: #a78bfa;
        --aq-teal: #2dd4bf;
        --aq-shadow: 0 10px 30px rgba(20,10,50,0.35);
        --aq-glow: 0 0 0 1px rgba(45,212,191,0.25), 0 8px 24px rgba(96,165,250,0.16);
        """
        if dark else
        """
        --aq-bg: #f4f8fb;
        --aq-bg-2: #eef2fb;
        --aq-surface: #ffffff;
        --aq-surface-2: #f6f9ff;
        --aq-border: #dde5f5;
        --aq-text: #0f2540;
        --aq-muted: #5c6c8a;
        --aq-accent: #0891b2;
        --aq-accent-2: #6366f1;
        --aq-accent-3: #7c3aed;
        --aq-teal: #0d9488;
        --aq-shadow: 0 10px 28px rgba(30,60,110,0.10);
        --aq-glow: 0 0 0 1px rgba(8,145,178,0.12), 0 8px 20px rgba(99,102,241,0.08);
        """
    )
    # Explicit values (not CSS vars) used to force-repaint Streamlit's OWN
    # native widgets (buttons, chat input, dropdown popovers, sidebar collapse
    # control). Those widgets are styled by Streamlit itself from
    # .streamlit/config.toml, which is fixed at server start and can never
    # follow this in-app light/dark toggle — left alone, they stay stuck in
    # the config's dark palette forever, which is what caused invisible
    # text (dark-on-dark navy buttons, a chat box that never changed color).
    native_bg = "#2a2550" if dark else "#ffffff"
    native_surface = "#352c66" if dark else "#f6f9ff"
    native_text = "#f5f3ff" if dark else "#0f2540"
    native_border = "#5b4f96" if dark else "#dde5f5"
    native_placeholder = "#c9c2e8" if dark else "#7c8aa8"

    wave_svg = (
        "data:image/svg+xml;utf8,"
        "%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 1440 320'%3E"
        "%3Cpath fill='%232dd4bf' fill-opacity='0.10' "
        "d='M0,140 C220,200 440,60 720,110 C1000,160 1220,220 1440,130 L1440,320 L0,320 Z'/%3E"
        "%3Cpath fill='%236366f1' fill-opacity='0.08' "
        "d='M0,200 C260,140 520,260 800,190 C1040,130 1260,200 1440,170 L1440,320 L0,320 Z'/%3E%3C/svg%3E"
    )

    align = "right" if rtl else "left"
    # The forced-alignment block below is only needed to correct Arabic (RTL)
    # rendering — Streamlit's own default CSS already left-aligns everything,
    # which is exactly right for English. So in English mode we inject NO
    # forced alignment at all, and any element that explicitly asks to be
    # centered (the language-select screen, empty-state cards, etc.) is left
    # alone. In Arabic mode we still need the broad override (Streamlit's CSS
    # otherwise keeps text left-aligned even inside an RTL container), but we
    # always finish with a higher-priority ".aq-center" escape hatch so any
    # element that wants to stay centered can opt back out.
    forced_align_block = "" if not rtl else f"""
        .stApp p, .stApp li, .stApp label, .stApp span,
        .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6,
        div[data-testid="stMarkdownContainer"],
        div[data-testid="stMarkdownContainer"] > *,
        div[data-testid="stCaptionContainer"],
        div[data-testid="stMetricLabel"],
        div[data-testid="stMetricValue"],
        div[data-testid="stMetricDelta"],
        div[data-testid="stText"],
        .stAlert, .stAlert p, .stException,
        .aq-card, .aq-card-soft,
        div[data-testid="stMetric"] {{
            text-align: {align} !important;
        }}
        .stApp input[type="text"], .stApp input[type="number"], .stApp textarea {{
            text-align: right;
            direction: rtl;
        }}
        div[data-testid="stRadio"] > div, div[data-testid="stCheckbox"] > label {{
            flex-direction: row-reverse;
        }}
    """
    direction_css = f"""
        .stApp, section[data-testid="stSidebar"] {{
            direction: {"rtl" if rtl else "ltr"};
        }}
        /* Full RTL text alignment — not just the sidebar/nav direction, but
           every text-bearing element (Streamlit's own CSS otherwise forces
           left-aligned text even inside an RTL container). Skipped entirely
           in English mode (see comment above). */
        {forced_align_block}
        /* Escape hatch: anything explicitly meant to stay centered (the
           language screen, empty-state cards, language cards) always wins,
           in both English and Arabic. Must come after the block above so it
           takes priority at equal specificity. */
        .aq-center, .aq-center *,
        .aq-empty, .aq-lang-card {{
            text-align: center !important;
        }}
    """

    st.markdown(
        f"""
        <style>
        :root {{ {root_vars} }}

        * {{ transition: background-color 0.25s ease, border-color 0.25s ease, box-shadow 0.2s ease, transform 0.15s ease; }}

        .stApp {{
            background:
                radial-gradient(ellipse 80% 50% at 20% -10%, color-mix(in srgb, var(--aq-accent-3) 18%, transparent), transparent),
                radial-gradient(ellipse 70% 50% at 100% 0%, color-mix(in srgb, var(--aq-accent-2) 14%, transparent), transparent),
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

        .aq-header {{ display:flex; align-items:center; gap:0.7rem; margin-bottom:0.1rem; }}
        .aq-title {{
            font-size: 1.9rem; font-weight: 800;
            background: linear-gradient(90deg, var(--aq-accent), var(--aq-accent-2), var(--aq-accent-3));
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
            background-size: 200% auto;
        }}
        .aq-subtitle {{ color: var(--aq-muted); font-size: 0.98rem; margin-top: -0.35rem; }}
        .aq-badge {{
            display:inline-block; margin-top:0.4rem; padding:2px 10px; border-radius:999px;
            border:1px solid var(--aq-border); color: var(--aq-accent); font-size:0.72rem; letter-spacing:0.03em;
        }}

        div[data-testid="stMetric"] {{
            background: linear-gradient(160deg, var(--aq-surface), var(--aq-surface-2));
            border: 1px solid var(--aq-border);
            border-radius: 14px;
            padding: 14px 16px 10px 16px;
            box-shadow: var(--aq-shadow);
        }}
        div[data-testid="stMetric"]:hover {{
            box-shadow: var(--aq-glow);
            transform: translateY(-2px);
        }}
        div[data-testid="stMetric"] label {{ color: var(--aq-muted) !important; }}
        div[data-testid="stMetric"] div {{ color: var(--aq-text) !important; }}

        .aq-card {{
            background: linear-gradient(160deg, var(--aq-surface), var(--aq-surface-2));
            border: 1px solid var(--aq-border);
            border-radius: 18px;
            padding: 20px 22px;
            margin-bottom: 14px;
            box-shadow: var(--aq-shadow);
        }}
        .aq-card:hover {{ box-shadow: var(--aq-glow); }}
        .aq-card-soft {{
            background: var(--aq-surface-2);
            border: 1px dashed var(--aq-border);
            border-radius: 14px;
            padding: 16px 18px;
            margin-bottom: 14px;
        }}

        .aq-status-pill {{
            display:inline-flex; align-items:center; gap:8px; padding:8px 20px;
            border-radius:999px; font-weight:700; font-size:0.95rem;
            box-shadow: 0 2px 12px rgba(0,0,0,0.12);
        }}
        .aq-dot {{ width:10px; height:10px; border-radius:50%; }}
        .aq-dot-pulse {{ animation: aq-pulse 1.6s ease-in-out infinite; }}
        @keyframes aq-pulse {{
            0% {{ box-shadow: 0 0 0 0 currentColor; opacity: 1; }}
            70% {{ box-shadow: 0 0 0 8px transparent; opacity: 0.7; }}
            100% {{ box-shadow: 0 0 0 0 transparent; opacity: 1; }}
        }}

        /* ---- Horizontal status gauge ---- */
        .aq-gauge-wrap {{
            direction: ltr; /* the green->red gradient reads left-to-right in both languages */
            max-width: 620px;
            margin: 4px 0 16px 0;
        }}
        .aq-gauge-track {{
            position: relative;
            height: 20px;
            border-radius: 999px;
            background: linear-gradient(90deg, #22c55e 0%, #84cc16 22%, #eab308 45%, #f97316 68%, #ef4444 100%);
            box-shadow: inset 0 1px 4px rgba(0,0,0,0.3), var(--aq-shadow);
        }}
        .aq-gauge-pointer {{
            position: absolute;
            top: -11px;
            transform: translateX(-50%);
            transition: left 0.5s ease;
        }}
        .aq-gauge-pointer-tri {{
            width: 0; height: 0; margin: 0 auto;
            border-left: 9px solid transparent;
            border-right: 9px solid transparent;
            border-top: 13px solid var(--aq-text);
            filter: drop-shadow(0 1px 3px rgba(0,0,0,0.35));
        }}
        .aq-gauge-pointer-stem {{
            width: 2px; height: 8px; margin: 0 auto;
            background: var(--aq-text);
            opacity: 0.6;
        }}
        .aq-gauge-labels {{
            display: flex;
            justify-content: space-between;
            margin-top: 6px;
            padding: 0 2px;
        }}
        .aq-gauge-labels span {{
            font-size: 0.68rem;
            color: var(--aq-muted);
            font-weight: 600;
        }}
        .aq-gauge-current {{
            margin-top: 10px;
            font-weight: 800;
            font-size: 1.05rem;
            display: flex;
            align-items: center;
            gap: 8px;
        }}

        .aq-nav-btn button {{
            width: 100%;
            border-radius: 10px !important;
        }}

        /* Buttons — explicit background/color instead of relying on
           Streamlit's native secondary-button colors (which come from
           .streamlit/config.toml and never change with this toggle). This is
           what was making sidebar nav buttons show invisible dark-on-dark
           text after switching to light mode. */
        .stButton>button, .stDownloadButton>button {{
            border-radius: 10px;
            border: 1px solid var(--aq-border);
            background: var(--aq-surface);
            color: var(--aq-text) !important;
        }}
        .stButton>button p, .stButton>button span, .stButton>button div,
        .stDownloadButton>button p, .stDownloadButton>button span {{
            color: var(--aq-text) !important;
        }}
        .stButton>button:hover, .stDownloadButton>button:hover {{
            border-color: var(--aq-accent);
            transform: translateY(-1px);
            box-shadow: var(--aq-glow);
        }}
        .stButton>button[kind="primary"] {{
            background: linear-gradient(90deg, var(--aq-accent), var(--aq-accent-2));
            border: none; color: #04222c !important; font-weight: 700;
            background-size: 150% auto;
        }}
        .stButton>button[kind="primary"] p, .stButton>button[kind="primary"] span,
        .stButton>button[kind="primary"] div {{
            color: #04222c !important;
        }}
        .stButton>button[kind="primary"]:hover {{
            background-position: right center;
            transform: translateY(-1px) scale(1.01);
            box-shadow: 0 6px 20px color-mix(in srgb, var(--aq-accent) 40%, transparent);
        }}

        /* ---- Native Streamlit widgets that config.toml would otherwise
               freeze in one fixed theme forever ---- */
        div[data-testid="stChatInput"],
        div[data-testid="stChatInput"] > div {{
            background: {native_bg} !important;
            border: 1px solid {native_border} !important;
        }}
        div[data-testid="stChatInput"] textarea {{
            background: transparent !important;
            color: {native_text} !important;
            caret-color: {native_text} !important;
        }}
        div[data-testid="stChatInput"] textarea::placeholder {{
            color: {native_placeholder} !important;
            opacity: 1;
        }}
        div[data-testid="stChatMessage"] {{
            background: {native_surface} !important;
            border: 1px solid {native_border} !important;
            border-radius: 14px;
        }}
        div[data-testid="stChatMessage"] p, div[data-testid="stChatMessage"] li,
        div[data-testid="stChatMessage"] span {{
            color: {native_text} !important;
        }}
        /* Selectbox / multiselect closed control */
        div[data-baseweb="select"] > div {{
            background: {native_bg} !important;
            border-color: {native_border} !important;
            color: {native_text} !important;
        }}
        div[data-baseweb="select"] span {{
            color: {native_text} !important;
        }}
        /* Dropdown option lists render in a portal attached to <body>, not
           inside .stApp, so they need their own unscoped rule to pick up the
           current theme instead of Streamlit's fixed native colors. */
        div[data-baseweb="popover"] div[role="listbox"],
        ul[role="listbox"] {{
            background: {native_bg} !important;
        }}
        div[data-baseweb="popover"] li,
        ul[role="listbox"] li {{
            background: {native_bg} !important;
            color: {native_text} !important;
        }}
        div[data-baseweb="popover"] li:hover,
        ul[role="listbox"] li:hover {{
            background: {native_surface} !important;
        }}
        /* Sidebar collapse/expand control (the small arrow shown when the
           sidebar is hidden, especially on mobile) — give it a clean, fixed,
           theme-matched look instead of raw unstyled native content. */
        [data-testid="stSidebarCollapsedControl"],
        [data-testid="stSidebarCollapseButton"] {{
            background: var(--aq-surface) !important;
            border-radius: 8px;
            box-shadow: var(--aq-shadow);
        }}
        [data-testid="stSidebarCollapsedControl"] svg,
        [data-testid="stSidebarCollapseButton"] svg {{
            fill: var(--aq-text) !important;
            color: var(--aq-text) !important;
        }}

        .aq-lang-card {{
            border: 1px solid var(--aq-border); border-radius: 18px; padding: 24px;
            text-align: center; background: linear-gradient(160deg, var(--aq-surface), var(--aq-surface-2));
            box-shadow: var(--aq-shadow); cursor: default;
        }}
        .aq-lang-card:hover {{ box-shadow: var(--aq-glow); transform: translateY(-2px); }}

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

        /* Radio / selectbox options feel more like tappable chips */
        div[data-testid="stRadio"] label {{
            border-radius: 10px; padding: 4px 2px;
        }}

        ::-webkit-scrollbar {{ width: 10px; height: 10px; }}
        ::-webkit-scrollbar-track {{ background: transparent; }}
        ::-webkit-scrollbar-thumb {{ background: var(--aq-border); border-radius: 8px; }}

        /* ---- Mobile: keep the sidebar title on one line instead of letting
               it wrap letter-by-letter down a too-narrow collapsed strip ---- */
        .aq-header, .aq-header * {{
            white-space: nowrap;
        }}
        @media (max-width: 768px) {{
            section[data-testid="stSidebar"] {{
                min-width: 240px;
            }}
            .aq-title {{ font-size: 1.3rem; }}
            .aq-subtitle {{ font-size: 0.8rem; }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_header():
    uri = logo_uri("small")
    logo_html = (
        f'<img src="{uri}" alt="AquaGuard AI" style="height:2.1rem; border-radius:6px;" />'
        if uri else '<span style="font-size:1.8rem;">💧</span>'
    )
    st.markdown(
        f"""
        <div class="aq-header">
            {logo_html}
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
    pulse_class = "aq-dot-pulse" if status == "Critical" else ""
    st.markdown(
        f"""
        <div class="aq-status-pill {pulse_class}" style="background:{color}22; color:{color}; border:1px solid {color}55;">
            <span>{icon}</span> {label}
        </div>
        """,
        unsafe_allow_html=True,
    )


_GAUGE_BAND_ORDER = ["Normal", "Monitoring", "Warning", "Critical"]
_GAUGE_BAND_INDEX = {s: i for i, s in enumerate(_GAUGE_BAND_ORDER)}
# Where each hidden internal level (L1-L8) sits within its public band, so the
# pointer can move with finer resolution than 4 fixed stops without ever
# exposing the L1-L8 codes themselves (per spec, those stay internal-only).
_GAUGE_LEVEL_BAND = {
    "L1": ("Normal", 0), "L2": ("Normal", 1),
    "L3": ("Monitoring", 0), "L4": ("Monitoring", 1),
    "L5": ("Warning", 0), "L6": ("Warning", 1), "L7": ("Warning", 2),
    "L8": ("Critical", 0),
}
_GAUGE_BAND_COUNTS = {"Normal": 2, "Monitoring": 2, "Warning": 3, "Critical": 1}


def status_gauge(status: str, internal_level: str | None = None):
    """Long horizontal gauge (green -> yellow -> orange -> red) with a pointer
    showing where the current status sits, replacing the small status pill.
    'Pending' has no place on a severity gradient (it isn't a verdict yet), so
    it keeps the neutral pill look instead."""
    if status not in _GAUGE_BAND_INDEX:
        status_pill(status)
        return

    band_idx = _GAUGE_BAND_INDEX[status]
    band_width = 100 / len(_GAUGE_BAND_ORDER)
    sub = 0.5
    if internal_level in _GAUGE_LEVEL_BAND:
        lvl_band, lvl_pos = _GAUGE_LEVEL_BAND[internal_level]
        if lvl_band == status:
            count = _GAUGE_BAND_COUNTS[status]
            sub = (lvl_pos + 0.5) / count
    pct = band_idx * band_width + sub * band_width
    pct = max(3.0, min(97.0, pct))

    color = STATUS_COLORS.get(status, "#93a4bf")
    label = status_label(status)
    icon = STATUS_ICONS.get(status, "⚪")
    band_labels = [status_label(s) for s in _GAUGE_BAND_ORDER]

    st.markdown(
        f"""
        <div class="aq-gauge-wrap">
          <div class="aq-gauge-track">
            <div class="aq-gauge-pointer" style="left:{pct}%;">
              <div class="aq-gauge-pointer-tri"></div>
              <div class="aq-gauge-pointer-stem"></div>
            </div>
          </div>
          <div class="aq-gauge-labels">
            <span>{band_labels[0]}</span><span>{band_labels[1]}</span><span>{band_labels[2]}</span><span>{band_labels[3]}</span>
          </div>
          <div class="aq-gauge-current" style="color:{color};">{icon} {label}</div>
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

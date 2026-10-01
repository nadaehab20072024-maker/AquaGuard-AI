"""
AquaGuard AI — Smart Water Monitoring & Leak Intelligence
=============================================================
Hackathon MVP. Runs entirely on simulated Stage-1 data (see /data).
Never claims a live meter / real-time sensor connection.

This file is the presentation layer only: onboarding, navigation, theme,
bilingual UI and page composition. All analysis (fingerprint, anomaly
detection, leak detection, building balance, tank/pump, AI insights,
smart forms, data loading) lives untouched in /modules.

Run with:  streamlit run app.py
"""

import datetime as dt

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from modules import data_loader, fingerprint, anomaly_detection, leak_detection
from modules import building_balance, tank_pump, smart_forms, ai_insights, ui, bill_analysis

st.set_page_config(
    page_title="AquaGuard AI",
    page_icon="💧",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Session defaults
# ---------------------------------------------------------------------------
DEFAULTS = {
    "lang": None,
    "theme": "dark",
    "onboarded": False,
    "page": "overview",
    "demo_mode": False,
    "assigned_building": None,
    "assigned_apartment": None,
    "profile_members": 4,
    "profile_building_label": "",
    "profile_unit_label": "",
    "chat_history": [],
}
for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

ui.inject_css()
t = ui.t

# ---------------------------------------------------------------------------
# Data load (never invents data — see modules/data_loader.py)
# ---------------------------------------------------------------------------
data = data_loader.load_all_data()
ts = data["timeseries"]
profiles = data["profiles"]
building_df = data["building"]
load_warnings = data["warnings"]

apt_daily_all = data_loader.get_apartment_daily(ts) if ts is not None else pd.DataFrame()
pairs = data_loader.apartment_options(profiles, ts)

if not pairs:
    ui.render_header()
    st.error("No household data is available. Please check the /data files." if not ui.is_ar()
              else "لا توجد بيانات منازل متاحة. يرجى التحقق من ملفات البيانات.")
    st.stop()


def assign_household_from_labels(building_label: str, unit_label: str):
    """Deterministically map the household's own entered building/unit labels
    to one real (building, apartment) pair in the simulated dataset, so the
    onboarding experience feels personal without letting a normal user browse
    arbitrary apartment IDs."""
    seed = f"{building_label}-{unit_label}"
    idx = abs(hash(seed)) % len(pairs)
    return pairs[idx]


# ===========================================================================
# STEP 1 — LANGUAGE SELECTION (first-run)
# ===========================================================================
if st.session_state["lang"] is None:
    _logo = ui.logo_uri("medium")
    _logo_html = (
        f'<img src="{_logo}" alt="AquaGuard AI" style="height:96px; border-radius:14px; box-shadow:var(--aq-shadow);" />'
        if _logo else '<div style="font-size:3rem;">💧</div>'
    )
    st.markdown(
        f"""
        <div style="text-align:center; margin-top:6vh;">
            <div>{_logo_html}</div>
            <div class="aq-title" style="font-size:2.3rem;">AquaGuard AI</div>
            <div class="aq-subtitle" style="font-size:1.05rem; margin-top:0.3rem;">
                Smart Water Monitoring &amp; Leak Intelligence
            </div>
            <div style="max-width:560px; margin:1rem auto 0.5rem auto; color:var(--aq-muted);">
                Understand your household's water behavior, detect unusual patterns, and act
                before a small issue becomes a major loss.
            </div>
            <div style="color:var(--aq-muted); margin-top:1.2rem; font-size:1.05rem;">
                Please choose your preferred language / الرجاء اختيار لغتك المفضلة
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.write("")
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        col_en, col_ar = st.columns(2)
        with col_en:
            st.markdown('<div class="aq-lang-card">🇬🇧<br><b>English</b></div>', unsafe_allow_html=True)
            if st.button("Continue in English", use_container_width=True, type="primary"):
                st.session_state["lang"] = "en"
                st.rerun()
        with col_ar:
            st.markdown('<div class="aq-lang-card">🇴🇲<br><b>العربية</b></div>', unsafe_allow_html=True)
            if st.button("المتابعة بالعربية", use_container_width=True, type="primary"):
                st.session_state["lang"] = "ar"
                st.rerun()
    st.stop()

# ===========================================================================
# STEP 2 — HOUSEHOLD PROFILE ONBOARDING (first-run)
# ===========================================================================
if not st.session_state["onboarded"]:
    ui.render_header()
    st.markdown(f"### {t('onboard_title')}")
    st.caption(t("onboard_intro"))
    st.write("")

    with st.form("onboarding_form"):
        c1, c2 = st.columns(2)
        with c1:
            building_label = st.text_input(t("onboard_building"), placeholder="e.g. Al Noor Residence")
        with c2:
            unit_label = st.text_input(t("onboard_unit"), placeholder="e.g. Unit 4B")
        members = st.number_input(t("onboard_members"), min_value=1, max_value=20, value=4)
        submitted = st.form_submit_button(t("onboard_submit"), type="primary", use_container_width=True)

    st.caption(t("onboard_note"))

    if submitted:
        with st.spinner(t("onboard_analyzing")):
            b, a = assign_household_from_labels(building_label or "household", unit_label or str(members))
            st.session_state["assigned_building"] = b
            st.session_state["assigned_apartment"] = a
            st.session_state["profile_members"] = int(members)
            st.session_state["profile_building_label"] = building_label or f"Building {b}"
            st.session_state["profile_unit_label"] = unit_label or f"Unit {a}"
            st.session_state["onboarded"] = True
        st.rerun()
    st.stop()

# ---------------------------------------------------------------------------
# Resolve the household to analyze: demo mode may override the assignment
# ---------------------------------------------------------------------------
sel_building = st.session_state["assigned_building"]
sel_apartment = st.session_state["assigned_apartment"]
if sel_building not in [b for b, a in pairs] or sel_apartment not in [a for b, a in pairs]:
    sel_building, sel_apartment = pairs[0]
    st.session_state["assigned_building"], st.session_state["assigned_apartment"] = pairs[0]


# ---------------------------------------------------------------------------
# Demo/Jury scenario resolution — uses the dataset's own ground-truth labels
# (Household_Scenario / Building_Wide_Case) for exact, reliable lookups.
# These labels are used ONLY to drive the presenter's scenario picker; the
# actual dashboard a normal user sees always runs the real detection engine
# on that household's real data, never a hard-coded "expected" answer.
# ---------------------------------------------------------------------------
_HOUSEHOLD_SCENARIO_COL = "Household_Scenario"
_BUILDING_CASE_COL = "Building_Wide_Case"


def _first_pair_for_household_scenario(profiles_df, scenario_label, pairs):
    if profiles_df is None or profiles_df.empty or _HOUSEHOLD_SCENARIO_COL not in profiles_df.columns:
        return None, None
    matches = profiles_df[profiles_df[_HOUSEHOLD_SCENARIO_COL].astype(str) == scenario_label]
    for _, row in matches.iterrows():
        b, a = str(row["Building_ID"]), str(row["Apartment_ID"])
        if (b, a) in pairs:
            return b, a
    return None, None


def _first_pair_for_building_case(profiles_df, case_label, pairs, prefer_scenario="Normal Household"):
    """Find a representative apartment inside a building carrying the given
    building-wide case, preferring a 'Normal Household' apartment so the
    building-level issue is shown independently of any household-level one."""
    if profiles_df is None or profiles_df.empty or _BUILDING_CASE_COL not in profiles_df.columns:
        return None, None
    matches = profiles_df[profiles_df[_BUILDING_CASE_COL].astype(str) == case_label]
    if matches.empty:
        return None, None
    preferred = matches[matches[_HOUSEHOLD_SCENARIO_COL].astype(str) == prefer_scenario]
    ordered = pd.concat([preferred, matches]).drop_duplicates()
    for _, row in ordered.iterrows():
        b, a = str(row["Building_ID"]), str(row["Apartment_ID"])
        if (b, a) in pairs:
            return b, a
    return None, None


# Scenario key -> ("household" scenario label) or ("building" case label)
_SCENARIO_LOOKUP = {
    "normal": ("household", "Normal Household"),
    "high_usage": ("household", "High Legitimate Usage"),
    "smart_form": ("household", "Smart Form Re-analysis"),
    "hidden_leak": ("household", "Hidden Internal Leak"),
    "profile_change": ("household", "Household Profile Change"),
    "leak_followup": ("household", "Leak Follow-up"),
    "external_pipe_leak": ("building", "External Supply Pipe Leak"),
    "tank_float_valve": ("building", "Tank Float Valve / Overflow Loss"),
    "pump_motor_issue": ("building", "Pump / Motor Issue"),
    "building_wide_loss": ("building", "Building-Wide Water Loss"),
}


def resolve_demo_scenario(choice, apt_daily_all, building_df, pairs, profiles_df=None):
    """Pick a REAL apartment/building from the dataset matching the requested
    demo scenario, using the dataset's own ground-truth scenario labels when
    available. Returns (building, apartment) as strings, or (None, None) if
    the dataset doesn't contain that scenario. Falls back to lightweight
    heuristics if the ground-truth columns aren't present (older dataset)."""
    pairs = [(str(b), str(a)) for b, a in pairs]
    spec = _SCENARIO_LOOKUP.get(choice)
    if spec is not None and profiles_df is not None and not profiles_df.empty:
        kind, label = spec
        if kind == "household":
            b, a = _first_pair_for_household_scenario(profiles_df, label, pairs)
        else:
            b, a = _first_pair_for_building_case(profiles_df, label, pairs)
        if b is not None:
            return b, a
        # fall through to heuristics below if ground-truth lookup found nothing

    # ---- Heuristic fallback (works even without the v2 ground-truth columns) ----
    if choice in ("hidden_leak",):
        for b, a in pairs:
            sub = apt_daily_all[apt_daily_all["Apartment_ID"].astype(str) == a]
            fp_ = fingerprint.build_fingerprint(sub)
            if fp_.get("available") and fp_.get("night_flow_available"):
                nights = sub["Night_Flow_2AM_5AM_Liters"].dropna()
                expected = fp_.get("expected_idle_flow") or 0
                if (nights > max(expected * 5, 10)).tail(7).sum() >= 3:
                    return b, a
        return None, None
    if choice == "high_usage":
        best, best_ratio = None, 0
        for b, a in pairs:
            sub = apt_daily_all[apt_daily_all["Apartment_ID"].astype(str) == a]
            if sub.empty:
                continue
            ratio = sub["Water_Consumption_Liters"].max() / max(sub["Water_Consumption_Liters"].median(), 1)
            if ratio > best_ratio:
                best_ratio, best = ratio, (b, a)
        return best if best else (None, None)
    if choice in ("building_wide_loss", "external_pipe_leak"):
        if building_df is None or building_df.empty or "Unaccounted_Water_Liters" not in building_df.columns:
            return None, None
        row = building_df.loc[building_df["Unaccounted_Water_Liters"].idxmax()]
        b = str(row["Building_ID"])
        apts = sorted(a for bb, a in pairs if bb == b)
        return (b, apts[0]) if apts else (None, None)
    if choice in ("tank_float_valve", "pump_motor_issue"):
        if building_df is None or building_df.empty or "Pump_State" not in building_df.columns:
            return None, None
        cont = building_df[building_df["Pump_State"].astype(str).str.lower() == "continuous"]
        if cont.empty:
            return None, None
        b = str(cont.iloc[0]["Building_ID"])
        apts = sorted(a for bb, a in pairs if bb == b)
        return (b, apts[0]) if apts else (None, None)
    if choice == "normal":
        for b, a in pairs:
            sub = apt_daily_all[apt_daily_all["Apartment_ID"].astype(str) == a]
            fp_ = fingerprint.build_fingerprint(sub)
            if fp_.get("available") and fp_.get("trend") == "Stable":
                return b, a
        return pairs[0] if pairs else (None, None)
    return None, None


DEMO_SCENARIOS = {
    "en": {
        "normal": "Normal Household",
        "high_usage": "High Legitimate Usage",
        "smart_form": "Smart Form Re-analysis",
        "hidden_leak": "Hidden Internal Leak",
        "profile_change": "Household Profile Change",
        "leak_followup": "Leak Follow-up",
        "external_pipe_leak": "External Supply Pipe Leak (Building)",
        "tank_float_valve": "Tank Float Valve / Overflow (Building)",
        "pump_motor_issue": "Pump / Motor Issue (Building)",
        "building_wide_loss": "Building-Wide Water Loss (Building)",
    },
    "ar": {
        "normal": "منزل طبيعي",
        "high_usage": "استخدام مرتفع مشروع",
        "smart_form": "إعادة تحليل عبر النموذج الذكي",
        "hidden_leak": "تسرب داخلي مخفي",
        "profile_change": "تغيير في بيانات الأسرة",
        "leak_followup": "متابعة بعد اكتشاف تسرب",
        "external_pipe_leak": "تسرب في خط الإمداد الخارجي (مبنى)",
        "tank_float_valve": "عطل صمام عوامة الخزان / فيضان (مبنى)",
        "pump_motor_issue": "مشكلة في المضخة / المحرك (مبنى)",
        "building_wide_loss": "فقدان مياه على مستوى المبنى (مبنى)",
    },
}
DEMO_SCENARIO_TEXT = {
    "en": {
        "normal": "This household's consumption is stable and within its own learned normal pattern.",
        "high_usage": "This household is using noticeably more water, but the pattern matches legitimate high usage rather than a leak.",
        "smart_form": "AquaGuard asked the household a quick question about a recent increase, then re-analyzed using their answer.",
        "hidden_leak": "Night-time flow during this household's usual idle hours is well above its learned baseline — a strong signal of a possible internal leak.",
        "profile_change": "The household recently updated its profile (e.g. more members) and the fingerprint is gradually adapting rather than resetting.",
        "leak_followup": "A likely leak was previously flagged; this shows the follow-up path (portable detector, then technical inspection).",
        "external_pipe_leak": "This building's main meter reads well above the sum of apartment meters and known external use — evidence points to a leak in the supply line BEFORE the apartment meters, not inside any single home.",
        "tank_float_valve": "The rooftop tank's level doesn't match its expected level and float-valve behavior looks abnormal — likely overflow or a stuck float valve, a building-level issue.",
        "pump_motor_issue": "The pump's runtime and motor current look abnormal relative to the tank's own behavior — a possible pump/motor issue affecting the whole building.",
        "building_wide_loss": "Unaccounted water at the building level is persistently high without a single clear cause identified yet — a general building-wide water-loss investigation is recommended.",
    },
    "ar": {
        "normal": "استهلاك هذا المنزل مستقر وضمن نمطه الطبيعي المتعلَّم.",
        "high_usage": "يستهلك هذا المنزل كمية أكبر من المعتاد، لكن النمط يطابق استخدامًا مرتفعًا مشروعًا وليس تسربًا.",
        "smart_form": "سأل أكواجارد الأسرة سؤالاً سريعًا عن زيادة حديثة، ثم أعاد التحليل بناءً على إجابتها.",
        "hidden_leak": "تدفق الليل خلال ساعات الخمول المعتادة لهذا المنزل أعلى بكثير من الخط الأساسي المتعلَّم — إشارة قوية لاحتمال وجود تسرب داخلي.",
        "profile_change": "قامت الأسرة مؤخرًا بتحديث بياناتها (مثل زيادة عدد الأفراد)، والبصمة تتكيف تدريجيًا دون إعادة ضبط كاملة.",
        "leak_followup": "تم رصد احتمال تسرب سابقًا؛ يوضح هذا مسار المتابعة (جهاز كشف محمول، ثم فحص فني).",
        "external_pipe_leak": "قراءة العداد الرئيسي للمبنى أعلى بكثير من مجموع عدادات الشقق والاستخدام الخارجي المعروف — الأدلة تشير إلى تسرب في خط الإمداد قبل عدادات الشقق، وليس داخل أي منزل بعينه.",
        "tank_float_valve": "مستوى خزان السطح لا يطابق المستوى المتوقع وسلوك صمام العوامة يبدو غير طبيعي — على الأرجح فيضان أو عطل في صمام العوامة، وهي مشكلة على مستوى المبنى.",
        "pump_motor_issue": "ساعات تشغيل المضخة وتيار المحرك يبدوان غير طبيعيين مقارنة بسلوك الخزان نفسه — احتمال وجود مشكلة في المضخة/المحرك تؤثر على المبنى بأكمله.",
        "building_wide_loss": "المياه غير المحتسبة على مستوى المبنى مرتفعة باستمرار دون سبب واحد واضح حتى الآن — يوصى بالتحقيق العام في فقد المياه على مستوى المبنى.",
    },
}

if st.session_state.get("_demo_jump") and pairs:
    choice = st.session_state.pop("_demo_jump")
    b, a = resolve_demo_scenario(choice, apt_daily_all, building_df, pairs, profiles)
    if b is not None:
        st.session_state["assigned_building"] = b
        st.session_state["assigned_apartment"] = a
        st.session_state["_active_demo_scenario"] = choice
        st.session_state["_demo_toast"] = "Scenario applied." if not ui.is_ar() else "تم تطبيق السيناريو."
    else:
        st.session_state["_demo_toast_warn"] = (
            "That scenario isn't present in the current dataset." if not ui.is_ar()
            else "هذا السيناريو غير موجود في البيانات الحالية."
        )
    sel_building = st.session_state["assigned_building"]
    sel_apartment = st.session_state["assigned_apartment"]

# ---------------------------------------------------------------------------
# Sidebar — theme / language / navigation / presenter access
# ---------------------------------------------------------------------------
with st.sidebar:
    _sidebar_logo = ui.logo_uri("small")
    if _sidebar_logo:
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:2px;">'
            f'<img src="{_sidebar_logo}" style="height:1.6rem;border-radius:5px;" />'
            f'<span class="aq-title" style="font-size:1.25rem;">{t("app_title")}</span></div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(f"### 💧 {t('app_title')}")
    st.caption(t("app_subtitle"))

    lang_toggle = st.radio(
        "🌐", ["English", "العربية"],
        index=0 if st.session_state["lang"] == "en" else 1,
        horizontal=True, label_visibility="collapsed",
    )
    new_lang = "en" if lang_toggle == "English" else "ar"
    if new_lang != st.session_state["lang"]:
        st.session_state["lang"] = new_lang
        st.rerun()

    dark_on = st.toggle(t("theme_toggle"), value=(st.session_state["theme"] == "dark"))
    new_theme = "dark" if dark_on else "light"
    if new_theme != st.session_state["theme"]:
        st.session_state["theme"] = new_theme
        st.rerun()

    st.divider()

    nav_items = list(ui.NAV_ITEMS)
    if st.session_state["demo_mode"]:
        nav_items += ui.DEMO_NAV_ITEMS

    for key, icon in nav_items:
        is_active = st.session_state["page"] == key
        st.markdown('<div class="aq-nav-btn">', unsafe_allow_html=True)
        if st.button(f"{icon}  {ui.nav_label(key)}", key=f"nav_{key}",
                     use_container_width=True, type="primary" if is_active else "secondary"):
            st.session_state["page"] = key
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    st.divider()
    with st.expander(f"🔐 {t('presenter_mode')}"):
        st.caption(t("presenter_hint"))
        presenter_on = st.toggle(t("presenter_toggle"), value=st.session_state["demo_mode"])
        if presenter_on != st.session_state["demo_mode"]:
            st.session_state["demo_mode"] = presenter_on
            if presenter_on:
                st.session_state["page"] = "demo"
            else:
                st.session_state["page"] = "overview"
            st.rerun()

if "_demo_toast" in st.session_state:
    st.toast(st.session_state.pop("_demo_toast"))
if "_demo_toast_warn" in st.session_state:
    st.toast(st.session_state.pop("_demo_toast_warn"), icon="⚠️")

if st.session_state["demo_mode"]:
    ui.demo_banner(
        DEMO_SCENARIOS[st.session_state["lang"]].get(
            st.session_state.get("_active_demo_scenario", "normal"),
            DEMO_SCENARIOS[st.session_state["lang"]]["normal"],
        ) if st.session_state.get("_active_demo_scenario") else t("presenter_on"),
        DEMO_SCENARIO_TEXT[st.session_state["lang"]].get(st.session_state.get("_active_demo_scenario", ""), "")
        if st.session_state.get("_active_demo_scenario") else "",
    )

# ---------------------------------------------------------------------------
# Build the analysis context for the resolved household (single source of truth)
# ---------------------------------------------------------------------------
apt_daily = apt_daily_all[apt_daily_all["Apartment_ID"] == sel_apartment].copy() if not apt_daily_all.empty else pd.DataFrame()

# Demo/Jury Center only: some ground-truth scenarios (e.g. a temporary high-
# usage spike that a household's own Smart Form should still be asked about)
# occurred earlier in the dataset and have since been correctly learned as
# this household's own normal pattern by the most recent date. So the
# presenter can actually SEE the live Smart Form trigger for those specific
# scenarios, we show the household "as of" the real day the event happened —
# still 100% real data, just a different (real) snapshot in time. This never
# affects a normal user, who always sees their true latest data.
if (
    st.session_state.get("demo_mode")
    and st.session_state.get("_active_demo_scenario") in ("high_usage", "smart_form")
    and not apt_daily.empty
    and "Smart_Form_Required" in apt_daily.columns
):
    flagged = apt_daily[apt_daily["Smart_Form_Required"].astype(str) == "Yes"]
    if not flagged.empty:
        cutoff = flagged["Date"].max()
        apt_daily = apt_daily[apt_daily["Date"] <= cutoff].copy()

explained_dates = smart_forms.get_explained_dates(sel_apartment)
fp = fingerprint.build_fingerprint(apt_daily, explained_dates)
analysis = anomaly_detection.analyze_household(apt_daily, fp, explained_dates)

profile_row = None
if profiles is not None and not profiles.empty:
    m = profiles[(profiles["Apartment_ID"] == sel_apartment) & (profiles["Building_ID"] == sel_building)]
    if not m.empty:
        profile_row = m.iloc[0]

household_ctx = {"apartment_id": sel_apartment, "building_id": sel_building, "analysis": analysis, "fingerprint": fp}
if building_df is not None:
    household_ctx["building_balance"] = building_balance.analyze_building(building_df, sel_building, lang=st.session_state["lang"])
    household_ctx["tank_pump"] = tank_pump.analyze_tank_pump(building_df, sel_building, lang=st.session_state["lang"])

CHART_TEMPLATE = "plotly_dark" if st.session_state["theme"] == "dark" else "plotly_white"
ACCENT = "#22d3ee" if st.session_state["theme"] == "dark" else "#0891b2"


def render_consumption_chart(apt_daily, fp, days=30, key_suffix=""):
    if apt_daily.empty:
        ui.empty_state()
        return
    df = apt_daily.tail(days)
    fig = go.Figure()
    if fp.get("available"):
        fig.add_hrect(y0=fp["normal_min"], y1=fp["normal_max"], fillcolor=ACCENT, opacity=0.10, line_width=0)
    fig.add_trace(go.Scatter(
        x=df["Date"], y=df["Water_Consumption_Liters"], mode="lines+markers",
        name="Daily consumption", line=dict(color=ACCENT, width=2),
        marker=dict(size=7, color=["#ef4444" if (fp.get("available") and v > fp["normal_max"]) else ACCENT
                                    for v in df["Water_Consumption_Liters"]]),
    ))
    fig.update_layout(
        template=CHART_TEMPLATE, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        height=340, margin=dict(l=10, r=10, t=30, b=10),
        yaxis_title="Liters / day", legend=dict(orientation="h", y=1.1),
    )
    st.plotly_chart(fig, use_container_width=True, key=f"chart_{key_suffix}")


def render_smart_form():
    lang = st.session_state["lang"]
    ar = ui.is_ar()
    is_night = analysis.get("smart_form_reason") == "night_flow"
    ui.card_start()
    st.markdown(f"### 📝 {t('smart_form_title')}")
    if is_night:
        st.write(
            "We noticed unusually high water flow overnight (2:00–5:00 AM), a time when this "
            "household normally shows little to no activity." if not ar else
            "لاحظنا تدفق مياه مرتفعًا بشكل غير معتاد خلال الليل (٢:٠٠–٥:٠٠ فجرًا)، وهو وقت لا يظهر فيه "
            "هذا المنزل عادةً أي نشاط يُذكر."
        )
        st.write(f"**{'Was there any activity in your home during that time?' if not ar else 'هل كان هناك أي نشاط في منزلك خلال تلك الفترة؟'}**")
    else:
        st.write(t("smart_form_lead"))
        st.write(f"**{'Was this increase expected?' if not ar else 'هل كانت هذه الزيادة متوقعة؟'}**")

    yn_key = f"smart_form_yn_{sel_apartment}_{analysis.get('current_date')}"
    if is_night:
        yes_label = "Yes, there was activity (guests, laundry, cleaning, etc.)" if not ar else "نعم، كان هناك نشاط (ضيوف، غسيل، تنظيف، إلخ)"
        no_label = "No, no one was using water then" if not ar else "لا، ما كان أحد يستخدم المي وقتها"
    else:
        yes_label = "Yes, this was expected" if not ar else "نعم، كانت متوقعة"
        no_label = "No, I don't know why" if not ar else "لا، لا أعرف السبب"
    yn_choice = st.radio("yn", [yes_label, no_label], label_visibility="collapsed", key=yn_key)

    reason = None
    if yn_choice == yes_label:
        st.write(f"**{t('smart_form_question')}**")
        options = smart_forms.EXPLANATION_OPTIONS[:-1]  # exclude "No known explanation" here
        reason = st.radio(
            "explain", options, format_func=lambda o: smart_forms.display_label(o, lang),
            label_visibility="collapsed", key=f"smart_form_{sel_apartment}_{analysis.get('current_date')}",
        )
    else:
        reason = "No known explanation"

    if st.button(t("smart_form_submit"), key=f"submit_{sel_apartment}", type="primary"):
        smart_forms.record_explanation(sel_apartment, analysis["current_date"], reason)
        st.session_state[f"_smart_form_answered_{sel_apartment}_{analysis.get('current_date')}"] = True
        st.success(t("smart_form_recorded"))
        st.rerun()
    ui.card_end()


def render_smart_form_result():
    """Shows the re-analyzed result for TODAY's date, if the household just
    answered the Smart Form for it — independent of whether the question
    itself is still being asked (once answered, the question above
    disappears, but the result must still be visible).

    IMPORTANT: this reflects the REAL, freshly re-computed `analysis` for
    this rerun (built after the answer was recorded and folded into
    explained_dates) — never a hardcoded guess based only on which button
    was clicked. That keeps this message consistent with the status pill
    shown at the top of the page, instead of contradicting it (e.g. never
    says "Possible Water Leak" while the pill still says "Monitoring")."""
    ar = ui.is_ar()
    result_key = f"_smart_form_answered_{sel_apartment}_{analysis.get('current_date')}"
    if not st.session_state.get(result_key):
        return

    if analysis.get("explained_today"):
        if analysis.get("smart_form_reason") == "night_flow":
            st.info(
                f"✅ **{'Explained — Not a Leak' if not ar else 'تم التفسير — ليس تسربًا'}** — "
                + ("You confirmed there was activity at home overnight, so AquaGuard is not treating this "
                   "as a leak today. It will keep learning your household's night-time pattern."
                   if not ar else
                   "أكدت أنه كان هناك نشاط في المنزل خلال الليل، لذا لن يعتبر أكواجارد هذا تسربًا اليوم. "
                   "سيستمر بتعلّم نمط منزلك الليلي.")
            )
        else:
            st.info(
                f"✅ **{'Likely Normal High Usage' if not ar else 'على الأرجح استخدام مرتفع طبيعي'}** — "
                + t("smart_form_explained_before")
            )
    elif analysis.get("leak_indicator") == "Possible hidden leak":
        st.warning(
            f"🚨 **{'Possible Water Leak' if not ar else 'احتمال وجود تسرب مياه'}** — "
            + ("No known reason was given, and night-time flow evidence still points to a possible hidden leak. "
               "AquaGuard recommends checking with a portable moisture detector."
               if not ar else
               "لم يُقدَّم سبب معروف، وأدلة التدفق الليلي ما زالت تشير لاحتمال وجود تسرب مخفي. "
               "يوصي أكواجارد بالفحص باستخدام كاشف رطوبة محمول.")
        )
    elif analysis.get("status") in ("Warning", "Critical"):
        st.warning(
            f"⚠️ **{ui.status_label(analysis['status'])}** — "
            + ("No known reason was given, so AquaGuard will keep this flagged and continue watching closely."
               if not ar else
               "لم يُقدَّم سبب معروف، لذا سيبقي أكواجارد هذا مرصودًا وسيواصل المراقبة عن قرب.")
        )
    else:
        st.info(
            ("No known reason was given yet, but there isn't enough evidence for a leak — AquaGuard will keep monitoring "
             "over the next few days."
             if not ar else
             "لم يُقدَّم سبب معروف بعد، لكن لا توجد أدلة كافية على وجود تسرب — سيواصل أكواجارد المراقبة خلال الأيام القادمة.")
        )


def greeting():
    hour = dt.datetime.now().hour
    if hour < 12:
        return t("good_morning")
    if hour < 18:
        return t("good_afternoon")
    return t("good_evening")


# ===========================================================================
# PAGES
# ===========================================================================
def _render_cross_building_notice(disp_status):
    """If the household's OWN status is Normal but AquaGuard has flagged
    something at the building or tank/pump level, say so explicitly — a
    normal personal reading should never quietly hide a building-wide issue
    the household could still be affected by. Placed right after the status
    gauge (not buried at the bottom) so it's seen right after the status
    itself, and always framed as an extra note beyond the household's own
    (unaffected) status, never as a contradiction of it."""
    if disp_status != "Normal":
        return
    bb = household_ctx.get("building_balance") or {}
    tp = household_ctx.get("tank_pump") or {}
    bb_issue = bb.get("available") and bb.get("status") in ("Warning", "Critical")
    tp_issue = tp.get("available") and tp.get("issue_type") is not None
    if not (bb_issue or tp_issue):
        return
    ar = ui.is_ar()
    if bb_issue and tp_issue:
        where = f"{t('nav_building')} / {t('nav_tank')}"
    elif bb_issue:
        where = t("nav_building")
    else:
        where = t("nav_tank")
    st.warning(
        f"ℹ️ **{'Extra note' if not ar else 'ملاحظة إضافية'}** — "
        + (f"Your own usage is completely normal. But AquaGuard also noticed something worth checking "
           f"at the building level — take a look at the **{where}** page for details."
           if not ar else
           f"استخدامك الشخصي طبيعي تمامًا. لكن أكواجارد لاحظ أيضًا أمرًا يستحق التحقق منه على مستوى المبنى — "
           f"اطّلعي على صفحة **{where}** لمعرفة التفاصيل.")
    )


def page_overview():
    st.markdown(f"#### {greeting()}, {st.session_state['profile_unit_label'] or t('nav_household')}")
    st.caption(f"**{t('your_water_status')}**")
    _disp_status = _effective_display_status(
        analysis["status"], analysis.get("smart_form_needed"), sel_apartment, analysis.get("current_date")
    )
    ui.status_gauge(_disp_status, analysis.get("internal_level"))
    ui.status_explanation(_disp_status)
    _render_cross_building_notice(_disp_status)
    st.write("")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric(t("current_consumption"), f"{analysis['current_consumption']:.0f} L" if analysis['current_consumption'] is not None else "N/A")
    c2.metric(t("household_baseline"), analysis["baseline_text"])
    c3.metric(t("trend"), ai_insights.trend_label(analysis["trend"], st.session_state["lang"]))
    idle_val = analysis.get("night_flow_current")
    c4.metric(t("idle_flow"), f"{idle_val:.1f} L" if idle_val is not None else "N/A")

    st.write("")
    if not apt_daily.empty:
        render_consumption_chart(apt_daily, fp, days=30, key_suffix="overview")
    else:
        ui.empty_state()

    if analysis.get("smart_form_needed"):
        render_smart_form()
    render_smart_form_result()

    facts = ai_insights.build_context_facts(household_ctx)
    insight = ai_insights.deterministic_insight(facts, st.session_state["lang"])
    ui.card_start()
    st.markdown(f"**🤖 {insight['headline']}**")
    st.write(insight["meaning"])
    ui.card_end()


def page_household():
    st.subheader(t("nav_household"))
    ui.status_pill(_effective_display_status(
        analysis["status"], analysis.get("smart_form_needed"), sel_apartment, analysis.get("current_date")
    ))
    st.write("")

    if apt_daily.empty:
        ui.empty_state()
        return

    range_choice = st.radio("range", ["7 days", "30 days", "90 days", "Full history"] if not ui.is_ar()
                             else ["٧ أيام", "٣٠ يومًا", "٩٠ يومًا", "كامل السجل"],
                             horizontal=True, index=1, label_visibility="collapsed")
    days_map = dict(zip(
        ["7 days", "30 days", "90 days", "Full history"] if not ui.is_ar()
        else ["٧ أيام", "٣٠ يومًا", "٩٠ يومًا", "كامل السجل"],
        [7, 30, 90, 10_000],
    ))
    render_consumption_chart(apt_daily, fp, days=days_map[range_choice], key_suffix="household")

    st.markdown("#### " + ("Night / Idle Flow" if not ui.is_ar() else "تدفق الليل / الخمول"))
    if "Night_Flow_2AM_5AM_Liters" in apt_daily.columns and apt_daily["Night_Flow_2AM_5AM_Liters"].notna().any():
        df = apt_daily.tail(days_map[range_choice])
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df["Date"], y=df["Night_Flow_2AM_5AM_Liters"],
                                  name=("Observed" if not ui.is_ar() else "الفعلي"),
                                  line=dict(color="#f97316", width=2)))
        expected = fp.get("expected_idle_flow")
        if expected is not None:
            fig.add_trace(go.Scatter(x=df["Date"], y=[expected] * len(df),
                                      name=("Expected" if not ui.is_ar() else "المتوقع"),
                                      line=dict(color="#22c55e", width=2, dash="dash")))
        fig.update_layout(template=CHART_TEMPLATE, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                           height=300, margin=dict(l=10, r=10, t=20, b=10), yaxis_title="Liters")
        st.plotly_chart(fig, use_container_width=True, key="night_flow_chart")
    else:
        ui.empty_state()

    if analysis.get("smart_form_needed"):
        render_smart_form()
    render_smart_form_result()


def _effective_display_status(status, smart_form_needed, apartment_id, current_date):
    """AquaGuard asks BEFORE judging an ambiguous case — so while a Smart Form
    question is still unanswered for today, the visible status is a neutral
    'Pending' rather than the system's own provisional Monitoring/Warning
    guess. This avoids showing what looks like a verdict before the household
    has had a chance to explain it. Once answered (or if there was never any
    ambiguity — e.g. strong night-flow leak evidence needs no question), the
    real status is shown as normal."""
    if not smart_form_needed:
        return status
    result_key = f"_smart_form_answered_{apartment_id}_{current_date}"
    if st.session_state.get(result_key):
        return status  # already answered — show the re-analyzed real status
    return "Pending"


def _localized_idle_period(value):
    if value is None:
        return t("unavailable")
    ar = ui.is_ar()
    if value == "02:00–05:00 (Night)":
        return "02:00–05:00 (الليل)" if ar else value
    if value == "Not clearly idle (household shows night activity)":
        return "غير واضح الخمول (يظهر نشاط ليلي في المنزل)" if ar else value
    return t("unavailable") if value == "Unavailable" else value


def page_fingerprint():
    st.subheader(t("nav_fingerprint"))
    st.caption(t("fp_intro"))
    if not fp.get("available"):
        ui.empty_state(t("fp_not_ready"))
        return

    ar = ui.is_ar()
    ui.range_gauge(fp["average_daily"], fp["normal_min"], fp["normal_max"], unit="L")
    avg, lo, hi = fp["average_daily"], fp["normal_min"], fp["normal_max"]
    if avg < lo:
        expl = (f"متوسط استهلاكك اليومي ({avg:.0f} لتر) أقل من نطاقك الطبيعي ({lo:.0f}–{hi:.0f} لتر) — "
                f"عادة هذا لا يستدعي القلق، ويعني فقط استخدامًا أخف من المعتاد." if ar else
                f"Your average daily use ({avg:.0f} L) is below your normal range ({lo:.0f}–{hi:.0f} L) — "
                f"this usually isn't a concern, it just means lighter-than-usual use.")
    elif avg > hi:
        expl = (f"متوسط استهلاكك اليومي ({avg:.0f} لتر) أعلى من نطاقك الطبيعي ({lo:.0f}–{hi:.0f} لتر) — "
                f"إذا استمر هذا، قد يستحق التحقق من صفحة 'مياهي' أو 'التنبيهات' لمعرفة السبب." if ar else
                f"Your average daily use ({avg:.0f} L) is above your normal range ({lo:.0f}–{hi:.0f} L) — "
                f"if this continues, it's worth checking the 'My Water' or 'Alerts' page for the reason.")
    else:
        expl = (f"متوسط استهلاكك اليومي ({avg:.0f} لتر) ضمن نطاقك الطبيعي ({lo:.0f}–{hi:.0f} لتر) — لا حاجة للقلق." if ar else
                f"Your average daily use ({avg:.0f} L) is within your normal range ({lo:.0f}–{hi:.0f} L) — nothing to worry about.")
    st.caption(expl)
    st.write("")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric(t("fp_normal_range"), f"{fp['normal_min']:.0f}–{fp['normal_max']:.0f} L")
    c2.metric(t("fp_avg"), f"{fp['average_daily']:.0f} L")
    c3.metric(t("trend"), ai_insights.trend_label(fp["trend"], st.session_state["lang"]))
    c4.metric(t("fp_confidence"), ai_insights.confidence_label(fp["confidence"], st.session_state["lang"]))

    st.write("")
    ui.card_start()
    st.markdown(f"**{t('fp_idle_period')}:** {_localized_idle_period(fp.get('learned_idle_period'))}")
    exp_idle = fp.get("expected_idle_flow")
    st.markdown(f"**{t('fp_idle_flow')}:** " + (f"{exp_idle:.2f} L" if exp_idle is not None else t("unavailable")))
    ui.card_end()

    ui.card_start()
    st.markdown(f"**{t('fp_high_days')}:** " + (", ".join(fp["typical_high_days"]) if fp["typical_high_days"] else "—"))
    st.markdown(f"**{t('fp_low_days')}:** " + (", ".join(fp["typical_low_days"]) if fp["typical_low_days"] else "—"))
    ui.card_end()

    if fp.get("by_weekday"):
        st.markdown(f"#### {t('fp_weekday_pattern')}")
        wd_df = pd.DataFrame(fp["by_weekday"]).T
        wd_df = wd_df.rename(columns={"median": "Median (L)", "mean": "Mean (L)", "count": "Days observed"})
        order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        wd_df = wd_df.reindex([d for d in order if d in wd_df.index])
        st.dataframe(wd_df.round(1), use_container_width=True)


def page_leak():
    st.subheader(t("nav_leak"))
    view = leak_detection.leak_detection_view(apt_daily, fp, explained_dates, lang=st.session_state["lang"])
    _disp_status = _effective_display_status(
        view["status"], view.get("smart_form_needed"), sel_apartment, view.get("current_date")
    )
    ui.status_pill(_disp_status)
    st.write("")

    if _disp_status in ("Warning", "Critical"):
        ui.card_start()
        st.markdown(f"### 🚨 {t('possible_leak')}")
        st.write(t("leak_lead"))
        ui.card_end()

    st.markdown(f"#### {t('evidence_title')}")
    for label, present in view["evidence_checklist"]:
        icon = "🔴" if present else "⚪"
        st.write(f"{icon} {label}")

    if view["night_flow_series"] is not None and not view["night_flow_series"].empty:
        st.markdown("#### " + ("Night flow history" if not ui.is_ar() else "سجل تدفق الليل"))
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=view["night_flow_series"]["Date"], y=view["night_flow_series"]["Night_Flow_2AM_5AM_Liters"],
            marker_color=["#ef4444" if v > max((view.get("expected_idle_flow") or 0) * 5, 10) else ACCENT
                          for v in view["night_flow_series"]["Night_Flow_2AM_5AM_Liters"]],
        ))
        fig.update_layout(template=CHART_TEMPLATE, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                           height=300, margin=dict(l=10, r=10, t=20, b=10), yaxis_title="Liters")
        st.plotly_chart(fig, use_container_width=True, key="leak_night_chart")

    st.markdown(f"#### {t('leak_next_steps')}")
    ui.card_start(soft=True)
    st.write(f"1. {t('leak_step_1')}")
    st.write(f"2. {t('leak_step_2')}")
    st.write(f"3. {t('leak_step_3')}")
    ui.card_end()

    if _disp_status in ("Warning", "Critical"):
        if st.button(f"🔧 {t('request_inspection')}", type="primary"):
            st.success(t("inspection_requested"))

    if view.get("smart_form_needed"):
        render_smart_form()
    elif view["status"] == "Normal":
        ui.empty_state(t("smart_form_none_needed"))
    render_smart_form_result()


def page_building():
    st.subheader(t("nav_building"))
    bb = building_balance.analyze_building(building_df, sel_building, lang=st.session_state["lang"]) if building_df is not None else {"available": False}
    if not bb.get("available"):
        ui.empty_state(t("bb_not_available"))
        return

    ui.status_gauge(bb["status"])
    st.write("")

    ui.card_start()
    st.markdown(f"**💧 {t('bb_main')}**  →  {bb['main_meter']:.0f} L")
    st.markdown(f"**🏠 {t('bb_apts')}**  →  {bb['apartment_total']:.0f} L")
    st.markdown(f"**🚿 {t('bb_ext')}**  →  {bb['legitimate_external']:.0f} L")
    st.markdown(f"**❓ {t('bb_unaccounted')}**  →  {bb['unaccounted']:.0f} L")
    ui.card_end()

    if bb.get("issue_type"):
        st.warning(f"⚠️ **{bb['issue_label']}**")
        ui.card_start(soft=True)
        what_lbl = "What happened?" if not ui.is_ar() else "ماذا حدث؟"
        why_lbl = "Why?" if not ui.is_ar() else "لماذا؟"
        action_lbl = "Recommended action" if not ui.is_ar() else "الإجراء الموصى به"
        st.markdown(f"**{what_lbl}**")
        st.write(bb["issue_what"])
        st.markdown(f"**{why_lbl}**")
        st.write(bb["issue_why"])
        if bb.get("issue_evidence"):
            for ev in bb["issue_evidence"]:
                st.caption("• " + ev)
        st.markdown(f"**{action_lbl}**")
        st.write(bb["issue_action"])
        ui.card_end()
        st.caption(
            "This is a building-level finding, separate from any individual apartment's own status."
            if not ui.is_ar() else
            "هذه ملاحظة على مستوى المبنى، منفصلة عن حالة أي شقة بمفردها."
        )
    else:
        st.success(t("bb_balanced"))

    st.markdown("#### " + ("Historical comparison" if not ui.is_ar() else "مقارنة تاريخية"))
    hist = bb["table"].tail(30)
    fig = go.Figure()
    fig.add_trace(go.Bar(x=hist["Date"], y=hist["Main_Meter_Liters"], name=t("bb_main"), marker_color="#60a5fa"))
    fig.add_trace(go.Bar(x=hist["Date"], y=hist["Apartment_Meters_Total_Liters"], name=t("bb_apts"), marker_color=ACCENT))
    fig.add_trace(go.Scatter(x=hist["Date"], y=hist["Unaccounted_Water_Liters"], name=t("bb_unaccounted"),
                              line=dict(color="#ef4444", width=2), yaxis="y2"))
    fig.update_layout(
        template=CHART_TEMPLATE, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        barmode="group", height=380, margin=dict(l=10, r=10, t=20, b=10),
        yaxis=dict(title="Liters"), yaxis2=dict(title="Unaccounted (L)", overlaying="y", side="right"),
        legend=dict(orientation="h", y=1.15),
    )
    st.plotly_chart(fig, use_container_width=True, key="building_chart")


def page_tank():
    st.subheader(t("nav_tank"))
    tp = tank_pump.analyze_tank_pump(building_df, sel_building, lang=st.session_state["lang"]) if building_df is not None else {"available": False}
    if not tp.get("available"):
        ui.empty_state(t("tank_not_available"))
        return

    status_map = {
        "Normal": ("Normal", t("tank_normal")),
        "Monitoring": ("Monitoring", t("tank_monitoring")),
        "Possible tank/float issue": ("Critical", t("tank_issue")),
        "Possible abnormal pump operation": ("Warning", t("tank_issue")),
    }
    pill_status, label = status_map.get(tp["status"], ("Monitoring", tp["status"]))
    ui.status_pill(pill_status)
    st.write(f"**{label}**")
    st.write("")

    ar = ui.is_ar()
    main_flow_status = "Normal"
    tank_flow_status = "Normal"
    pump_flow_status = "Normal"
    if tp.get("issue_type") == "external_pipe_leak":
        main_flow_status = "Warning"
    elif tp.get("issue_type") == "building_wide_loss":
        main_flow_status = "Monitoring"
    if tp.get("issue_type") == "tank_float_valve":
        tank_flow_status = "Critical"
    elif tp.get("status") == "Monitoring":
        tank_flow_status = "Monitoring"
    if tp.get("issue_type") == "pump_motor_issue":
        pump_flow_status = "Warning"

    ui.flow_diagram([
        {"label": t("bb_main"), "icon": "🚰", "status": main_flow_status},
        {"label": "الخزان" if ar else "Tank",
         "icon": "🛢️",
         "sublabel": f"{tp['tank_level']:.0f}%" if tp.get("tank_level") is not None else None,
         "status": tank_flow_status},
        {"label": "المضخة" if ar else "Pump",
         "icon": "⚙️",
         "sublabel": ui.pump_state_label(tp.get("pump_state")),
         "status": pump_flow_status},
        {"label": t("bb_apts"), "icon": "🏠", "status": "Normal"},
    ])

    c1, c2 = st.columns(2)
    c1.metric(t("tank_level"), f"{tp['tank_level']:.0f} %" if tp.get("tank_level") is not None else t("unavailable"))
    c2.metric(t("pump_state"), ui.pump_state_label(tp.get("pump_state")))

    if tp.get("issue_type") in ("tank_float_valve", "pump_motor_issue"):
        st.write("")
        ui.card_start(soft=True)
        what_lbl = "What happened?" if not ui.is_ar() else "ماذا حدث؟"
        why_lbl = "Why?" if not ui.is_ar() else "لماذا؟"
        action_lbl = "Recommended action" if not ui.is_ar() else "الإجراء الموصى به"
        st.markdown(f"**{tp['issue_label']}**")
        st.markdown(f"**{what_lbl}**")
        st.write(tp["issue_what"])
        st.markdown(f"**{why_lbl}**")
        st.write(tp["issue_why"])
        st.markdown(f"**{action_lbl}**")
        st.write(tp["issue_action"])
        ui.card_end()

    if tp["findings"]:
        st.markdown("#### " + ("Findings" if not ui.is_ar() else "الملاحظات"))
        for f_ in tp["findings"]:
            st.write("• " + f_)

    st.markdown("#### " + ("Recent history" if not ui.is_ar() else "السجل الأخير"))
    hist = tp["table"].tail(30)
    fig = go.Figure()
    if "Tank_Level_Percent" in hist.columns:
        fig.add_trace(go.Scatter(x=hist["Date"], y=hist["Tank_Level_Percent"], name=t("tank_level"),
                                  line=dict(color=ACCENT, width=2)))
    fig.update_layout(template=CHART_TEMPLATE, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                       height=300, margin=dict(l=10, r=10, t=20, b=10), yaxis_title="%")
    st.plotly_chart(fig, use_container_width=True, key="tank_chart")


def page_ai():
    st.subheader(t("nav_ai"))
    facts = ai_insights.build_context_facts(household_ctx)
    insight = ai_insights.deterministic_insight(facts, st.session_state["lang"])

    ui.card_start()
    st.markdown(f"### 🤖 {insight['headline']}")
    st.markdown(f"**{t('why_seeing_this')}**")
    for r in insight["why"]:
        st.write("• " + r)
    st.markdown(f"**{t('ai_meaning')}**")
    st.write(insight["meaning"])
    st.markdown(f"**{t('ai_action')}**")
    st.write(insight["action"])
    ui.card_end()

    if st.session_state["demo_mode"]:
        with st.expander("Facts used for this insight (developer view)"):
            st.json(facts)


def _run_bill_analysis(consumption_liters: float, billing_days: int, found_text: str | None):
    ar = ui.is_ar()
    result = bill_analysis.analyze_bill(consumption_liters, fp, st.session_state["lang"], billing_days)
    lines = []
    if found_text:
        lines.append(f"{t('assistant_bill_found_prefix')}*{found_text.strip()}*")
    if result.get("available"):
        lines.append(result["headline"])
        lines.append(result["note"])
    else:
        lines.append(result.get("message", "—"))
    message = "\n\n".join(lines)
    st.session_state["chat_history"].append(("user", "📎 " + (t("assistant_bill_title"))))
    st.session_state["chat_history"].append(("assistant", message))


def page_assistant():
    st.subheader(t("nav_assistant"))
    st.caption(t("assistant_caption"))

    ui.card_start(soft=True)
    st.markdown(f"**{t('assistant_bill_title')}**")
    st.caption(t("assistant_bill_caption"))
    up_col, days_col = st.columns([2, 1])
    with up_col:
        st.markdown('<div class="aq-compact-uploader">', unsafe_allow_html=True)
        uploaded = st.file_uploader(
            t("assistant_bill_uploader"), type=["png", "jpg", "jpeg", "pdf"],
            key="bill_uploader", label_visibility="collapsed",
        )
        st.markdown('</div>', unsafe_allow_html=True)
    with days_col:
        billing_days = st.number_input(
            t("assistant_bill_period_label"), min_value=1, max_value=120, value=30, key="bill_period_days"
        )

    if uploaded is not None:
        file_sig = f"{uploaded.name}_{uploaded.size}"
        if st.session_state.get("_last_bill_sig") != file_sig:
            with st.spinner(t("assistant_bill_analyzing")):
                text = bill_analysis.extract_text(uploaded)
                parsed = bill_analysis.parse_bill_text(text)
            st.session_state["_last_bill_sig"] = file_sig
            st.session_state["_last_bill_parsed"] = parsed
            if parsed.get("consumption_liters") is not None:
                _run_bill_analysis(parsed["consumption_liters"], int(billing_days), parsed.get("matched_snippet"))
                st.rerun()

        parsed = st.session_state.get("_last_bill_parsed") or {}
        if parsed.get("consumption_liters") is None:
            st.warning(t("assistant_bill_not_found"))
            mc1, mc2, mc3 = st.columns([2, 1, 1])
            with mc1:
                manual_val = st.number_input(t("assistant_bill_manual_label"), min_value=0.0, step=1.0, key="bill_manual_val")
            with mc2:
                unit = st.selectbox(t("assistant_bill_manual_unit"), ["m³", "L"], key="bill_manual_unit")
            with mc3:
                st.write("")
                st.write("")
                if st.button(t("assistant_bill_manual_button"), key="bill_manual_btn", type="primary"):
                    liters = manual_val * 1000.0 if unit == "m³" else manual_val
                    _run_bill_analysis(liters, int(billing_days), None)
                    st.rerun()
    ui.card_end()

    for role, msg in st.session_state["chat_history"]:
        with st.chat_message(role):
            st.write(msg)

    examples = ["Why is my status warning?", "Why did my consumption increase?",
                "Is there a possible hidden leak?", "What is my normal range?"] if not ui.is_ar() else \
        ["لماذا حالتي تحذير؟", "لماذا زاد استهلاكي؟", "هل هناك احتمال تسرب مخفي؟", "ما هو نطاقي الطبيعي؟"]
    st.caption(f"{t('assistant_try')}: " + " · ".join(examples))

    prompt = st.chat_input(t("assistant_placeholder"))
    if prompt:
        st.session_state["chat_history"].append(("user", prompt))
        facts = ai_insights.build_context_facts(household_ctx)
        det_answer = ai_insights.answer_question(prompt, facts, st.session_state["lang"])
        final_answer = ai_insights.llm_rephrase(facts, prompt, st.session_state["lang"], det_answer)
        st.session_state["chat_history"].append(("assistant", final_answer))
        st.rerun()


def page_profile():
    st.subheader(t("profile_title"))
    ui.card_start()
    with st.form("profile_form"):
        c1, c2 = st.columns(2)
        with c1:
            b_label = st.text_input(t("onboard_building"), value=st.session_state["profile_building_label"])
        with c2:
            u_label = st.text_input(t("onboard_unit"), value=st.session_state["profile_unit_label"])
        members = st.number_input(t("onboard_members"), min_value=1, max_value=20,
                                   value=st.session_state["profile_members"])
        saved = st.form_submit_button(t("profile_save"), type="primary")
    ui.card_end()

    if saved:
        st.session_state["profile_building_label"] = b_label
        st.session_state["profile_unit_label"] = u_label
        st.session_state["profile_members"] = int(members)
        st.success(t("profile_saved"))
        st.caption(t("profile_update_note"))

    st.write("")
    st.markdown(f"**{t('household_members')}:** {profile_row['Household_Members'] if profile_row is not None else st.session_state['profile_members']}")
    _conf = fp.get("confidence") if fp.get("available") else None
    st.markdown(f"**{t('fingerprint_confidence')}:** {ai_insights.confidence_label(_conf, st.session_state['lang']) if _conf else t('unavailable')}")

    recurring = smart_forms.get_all_explanations(sel_apartment)
    if recurring:
        st.markdown("#### " + ("Recorded explanations (this session)" if not ui.is_ar() else "التفسيرات المسجلة (هذه الجلسة)"))
        for d, reason in sorted(recurring.items()):
            st.write(f"- {d.date()}: {smart_forms.display_label(reason, st.session_state['lang'])}")


def page_demo():
    st.subheader(t("demo_title"))
    st.caption(t("demo_subtitle"))
    st.write("")

    ui.card_start()
    st.markdown(f"**{t('demo_scenario')}**")
    scenario_keys = [
        "normal", "high_usage", "smart_form", "hidden_leak", "profile_change",
        "leak_followup", "external_pipe_leak", "tank_float_valve",
        "pump_motor_issue", "building_wide_loss",
    ]
    labels = [DEMO_SCENARIOS[st.session_state["lang"]][k] for k in scenario_keys]
    choice_label = st.selectbox("scenario", labels, label_visibility="collapsed")
    choice_key = scenario_keys[labels.index(choice_label)]
    if st.button(t("demo_apply"), type="primary"):
        st.session_state["_demo_jump"] = choice_key
        st.rerun()
    ui.card_end()

    ui.card_start(soft=True)
    st.markdown(f"**{t('demo_household')}**")
    st.caption(t("demo_switch_note"))
    buildings = sorted(set(b for b, a in pairs))
    b_idx = buildings.index(sel_building) if sel_building in buildings else 0
    demo_building = st.selectbox("Building", buildings, index=b_idx, format_func=lambda b: f"Building {b}")
    apts_in_building = sorted(a for b, a in pairs if b == demo_building)
    a_idx = apts_in_building.index(sel_apartment) if sel_apartment in apts_in_building else 0
    demo_apartment = st.selectbox("Apartment", apts_in_building, index=a_idx, format_func=lambda a: f"Apartment {a}")
    if (demo_building, demo_apartment) != (sel_building, sel_apartment):
        if st.button("Switch to this household" if not ui.is_ar() else "التبديل إلى هذا المنزل"):
            st.session_state["assigned_building"] = demo_building
            st.session_state["assigned_apartment"] = demo_apartment
            st.session_state.pop("_active_demo_scenario", None)
            st.rerun()
    ui.card_end()

    st.markdown(f"**{t('building_id')}:** {sel_building}  |  **{t('apartment_id')}:** {sel_apartment}")


def page_explorer():
    st.subheader(t("nav_explorer"))
    if ts is None or ts.empty:
        ui.empty_state()
        return

    fc1, fc2, fc3 = st.columns(3)
    with fc1:
        f_building = st.multiselect("Building", sorted(ts["Building_ID"].dropna().unique().tolist()))
    with fc2:
        f_apartment = st.multiselect("Apartment", sorted(ts["Apartment_ID"].dropna().unique().tolist()))
    with fc3:
        date_range = st.date_input(
            "Date range",
            value=(ts["Date"].min().date(), ts["Date"].max().date()),
            min_value=ts["Date"].min().date(), max_value=ts["Date"].max().date(),
        )

    search = st.text_input("Search records (any column)")
    filtered = ts.copy()
    if f_building:
        filtered = filtered[filtered["Building_ID"].isin(f_building)]
    if f_apartment:
        filtered = filtered[filtered["Apartment_ID"].isin(f_apartment)]
    if isinstance(date_range, tuple) and len(date_range) == 2:
        filtered = filtered[(filtered["Date"] >= pd.Timestamp(date_range[0])) & (filtered["Date"] <= pd.Timestamp(date_range[1]))]
    if search:
        mask = filtered.astype(str).apply(lambda col: col.str.contains(search, case=False, na=False)).any(axis=1)
        filtered = filtered[mask]

    st.metric(t("records_analyzed"), len(filtered))
    st.dataframe(filtered, use_container_width=True, height=460)


PAGE_MAP = {
    "overview": page_overview, "household": page_household, "fingerprint": page_fingerprint,
    "leak": page_leak, "building": page_building, "tank": page_tank, "ai": page_ai,
    "assistant": page_assistant, "profile": page_profile, "demo": page_demo, "explorer": page_explorer,
}

# ---------------------------------------------------------------------------
# Render current page (never surface a raw traceback to the user)
# ---------------------------------------------------------------------------
ui.render_header()
if st.session_state["page"] not in ("demo", "explorer"):
    st.caption(f"{t('apartment_id')}: {st.session_state['profile_unit_label'] or sel_apartment}")
st.write("")

current_page = PAGE_MAP.get(st.session_state["page"], page_overview)
try:
    current_page()
except Exception as exc:  # never surface a raw traceback to a normal user
    st.error(t("error_generic"))
    if st.session_state["demo_mode"]:
        with st.expander("Developer detail"):
            st.exception(exc)

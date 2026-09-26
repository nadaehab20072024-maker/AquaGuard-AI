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
from modules import building_balance, tank_pump, smart_forms, ai_insights, ui

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
    "profile_devices": 6,
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
    st.markdown(
        f"""
        <div style="text-align:center; margin-top:6vh;">
            <div style="font-size:3rem;">💧</div>
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
        c3, c4 = st.columns(2)
        with c3:
            members = st.number_input(t("onboard_members"), min_value=1, max_value=20, value=4)
        with c4:
            devices = st.number_input(t("onboard_devices"), min_value=0, max_value=30, value=6)
        submitted = st.form_submit_button(t("onboard_submit"), type="primary", use_container_width=True)

    st.caption(t("onboard_note"))

    if submitted:
        with st.spinner(t("onboard_analyzing")):
            b, a = assign_household_from_labels(building_label or "household", unit_label or str(members))
            st.session_state["assigned_building"] = b
            st.session_state["assigned_apartment"] = a
            st.session_state["profile_members"] = int(members)
            st.session_state["profile_devices"] = int(devices)
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


def resolve_demo_scenario(choice, apt_daily_all, building_df, pairs):
    """Pick a REAL apartment/building from the dataset matching the requested
    demo scenario. Returns (building, apartment) or (None, None) if the
    dataset doesn't contain such a scenario."""
    if choice == "leak":
        for b, a in pairs:
            sub = apt_daily_all[apt_daily_all["Apartment_ID"] == a]
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
            sub = apt_daily_all[apt_daily_all["Apartment_ID"] == a]
            if sub.empty:
                continue
            ratio = sub["Water_Consumption_Liters"].max() / max(sub["Water_Consumption_Liters"].median(), 1)
            if ratio > best_ratio:
                best_ratio, best = ratio, (b, a)
        return best if best else (None, None)
    if choice == "building_imbalance":
        if building_df is None or building_df.empty or "Unaccounted_Water_Liters" not in building_df.columns:
            return None, None
        row = building_df.loc[building_df["Unaccounted_Water_Liters"].idxmax()]
        b = int(row["Building_ID"])
        apts = sorted(a for bb, a in pairs if bb == b)
        return (b, apts[0]) if apts else (None, None)
    if choice == "tank_pump":
        if building_df is None or building_df.empty or "Pump_State" not in building_df.columns:
            return None, None
        cont = building_df[building_df["Pump_State"].astype(str).str.lower() == "continuous"]
        if cont.empty:
            return None, None
        b = int(cont.iloc[0]["Building_ID"])
        apts = sorted(a for bb, a in pairs if bb == b)
        return (b, apts[0]) if apts else (None, None)
    if choice == "normal":
        for b, a in pairs:
            sub = apt_daily_all[apt_daily_all["Apartment_ID"] == a]
            fp_ = fingerprint.build_fingerprint(sub)
            if fp_.get("available") and fp_.get("trend") == "Stable":
                return b, a
        return pairs[0] if pairs else (None, None)
    return None, None


DEMO_SCENARIOS = {
    "en": {
        "normal": "Normal Household",
        "high_usage": "High Legitimate Usage",
        "leak": "Possible Hidden Leak",
        "building_imbalance": "Shared Building Water Loss",
        "tank_pump": "Tank/Pump Issue",
    },
    "ar": {
        "normal": "منزل طبيعي",
        "high_usage": "استخدام مرتفع مشروع",
        "leak": "احتمال تسرب مخفي",
        "building_imbalance": "فقدان مياه مشترك بالمبنى",
        "tank_pump": "مشكلة في الخزان/المضخة",
    },
}
DEMO_SCENARIO_TEXT = {
    "en": {
        "normal": "This household's consumption is stable and within its normal pattern.",
        "high_usage": "Simulated household activity is causing unusually high consumption.",
        "leak": "Night-time flow does not match this household's learned idle period.",
        "building_imbalance": "Main-meter water substantially exceeds apartment totals and known external use.",
        "tank_pump": "The pump is running continuously alongside an unexplained water input.",
    },
    "ar": {
        "normal": "استهلاك هذا المنزل مستقر وضمن نمطه الطبيعي.",
        "high_usage": "يتسبب نشاط منزلي محاكى في استهلاك مرتفع بشكل غير معتاد.",
        "leak": "تدفق الليل لا يتطابق مع فترة الخمول المتعلَّمة لهذا المنزل.",
        "building_imbalance": "مياه العداد الرئيسي تتجاوز بشكل كبير إجمالي الشقق والاستخدام الخارجي المعروف.",
        "tank_pump": "تعمل المضخة باستمرار مع وجود دخول مياه غير مبرر.",
    },
}

if st.session_state.get("_demo_jump") and pairs:
    choice = st.session_state.pop("_demo_jump")
    b, a = resolve_demo_scenario(choice, apt_daily_all, building_df, pairs)
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

    if load_warnings:
        with st.expander("⚠️ Data notices"):
            for w in load_warnings:
                st.caption(w)

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
    household_ctx["building_balance"] = building_balance.analyze_building(building_df, sel_building)
    household_ctx["tank_pump"] = tank_pump.analyze_tank_pump(building_df, sel_building)

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
    ui.card_start()
    st.markdown(f"### 📝 {t('smart_form_title')}")
    st.write(t("smart_form_lead"))
    st.write(f"**{t('smart_form_question')}**")
    choice = st.radio(
        "explain", smart_forms.EXPLANATION_OPTIONS, label_visibility="collapsed",
        key=f"smart_form_{sel_apartment}_{analysis.get('current_date')}",
    )
    if st.button(t("smart_form_submit"), key=f"submit_{sel_apartment}", type="primary"):
        smart_forms.record_explanation(sel_apartment, analysis["current_date"], choice)
        st.success(t("smart_form_recorded"))
        st.rerun()
    ui.card_end()


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
def page_overview():
    st.markdown(f"#### {greeting()}, {st.session_state['profile_unit_label'] or t('nav_household')}")
    st.caption(f"**{t('your_water_status')}**")
    ui.status_pill(analysis["status"])
    ui.status_explanation(analysis["status"])
    st.write("")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric(t("current_consumption"), f"{analysis['current_consumption']:.0f} L" if analysis['current_consumption'] is not None else "N/A")
    c2.metric(t("household_baseline"), analysis["baseline_text"])
    c3.metric(t("trend"), analysis["trend"])
    idle_val = analysis.get("night_flow_current")
    c4.metric(t("idle_flow"), f"{idle_val:.1f} L" if idle_val is not None else "N/A")

    st.write("")
    if not apt_daily.empty:
        render_consumption_chart(apt_daily, fp, days=30, key_suffix="overview")
    else:
        ui.empty_state()

    if analysis.get("smart_form_needed"):
        render_smart_form()

    facts = ai_insights.build_context_facts(household_ctx)
    insight = ai_insights.deterministic_insight(facts, st.session_state["lang"])
    ui.card_start()
    st.markdown(f"**🤖 {insight['headline']}**")
    st.write(insight["meaning"])
    ui.card_end()


def page_household():
    st.subheader(t("nav_household"))
    ui.status_pill(analysis["status"])
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
        fig.add_trace(go.Scatter(x=df["Date"], y=df["Night_Flow_2AM_5AM_Liters"], name="Observed",
                                  line=dict(color="#f97316", width=2)))
        expected = fp.get("expected_idle_flow")
        if expected is not None:
            fig.add_trace(go.Scatter(x=df["Date"], y=[expected] * len(df), name="Expected",
                                      line=dict(color="#22c55e", width=2, dash="dash")))
        fig.update_layout(template=CHART_TEMPLATE, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                           height=300, margin=dict(l=10, r=10, t=20, b=10), yaxis_title="Liters")
        st.plotly_chart(fig, use_container_width=True, key="night_flow_chart")
    else:
        ui.empty_state()

    if analysis.get("smart_form_needed"):
        render_smart_form()


def page_fingerprint():
    st.subheader(t("nav_fingerprint"))
    st.caption(t("fp_intro"))
    if not fp.get("available"):
        ui.empty_state(t("fp_not_ready"))
        return

    c1, c2, c3, c4 = st.columns(4)
    c1.metric(t("fp_normal_range"), f"{fp['normal_min']:.0f}–{fp['normal_max']:.0f} L")
    c2.metric(t("fp_avg"), f"{fp['average_daily']:.0f} L")
    c3.metric(t("trend"), fp["trend"])
    c4.metric(t("fp_confidence"), fp["confidence"])

    st.write("")
    ui.card_start()
    st.markdown(f"**{t('fp_idle_period')}:** {fp.get('learned_idle_period', 'Unavailable')}")
    exp_idle = fp.get("expected_idle_flow")
    st.markdown(f"**{t('fp_idle_flow')}:** " + (f"{exp_idle:.2f} L" if exp_idle is not None else "Unavailable"))
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
    view = leak_detection.leak_detection_view(apt_daily, fp, explained_dates)
    ui.status_pill(view["status"])
    st.write("")

    if view["status"] in ("Warning", "Critical"):
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

    if view["status"] in ("Warning", "Critical"):
        if st.button(f"🔧 {t('request_inspection')}", type="primary"):
            st.success(t("inspection_requested"))

    if view.get("smart_form_needed"):
        render_smart_form()
    elif view["status"] == "Normal":
        ui.empty_state(t("smart_form_none_needed"))


def page_building():
    st.subheader(t("nav_building"))
    bb = building_balance.analyze_building(building_df, sel_building) if building_df is not None else {"available": False}
    if not bb.get("available"):
        ui.empty_state(t("bb_not_available"))
        return

    ui.status_pill(bb["status"])
    st.write("")

    ui.card_start()
    st.markdown(f"**💧 {t('bb_main')}**  →  {bb['main_meter']:.0f} L")
    st.markdown(f"**🏠 {t('bb_apts')}**  →  {bb['apartment_total']:.0f} L")
    st.markdown(f"**🚿 {t('bb_ext')}**  →  {bb['legitimate_external']:.0f} L")
    st.markdown(f"**❓ {t('bb_unaccounted')}**  →  {bb['unaccounted']:.0f} L")
    ui.card_end()

    if bb.get("alert_text"):
        st.warning("⚠️ " + t("bb_alert"))
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
    tp = tank_pump.analyze_tank_pump(building_df, sel_building) if building_df is not None else {"available": False}
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

    c1, c2 = st.columns(2)
    c1.metric(t("tank_level"), f"{tp['tank_level']:.0f} %" if tp.get("tank_level") is not None else "N/A")
    c2.metric(t("pump_state"), tp.get("pump_state") or "N/A")

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


def page_assistant():
    st.subheader(t("nav_assistant"))
    st.caption(t("assistant_caption"))

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
        c3, c4 = st.columns(2)
        with c3:
            members = st.number_input(t("onboard_members"), min_value=1, max_value=20,
                                       value=st.session_state["profile_members"])
        with c4:
            devices = st.number_input(t("onboard_devices"), min_value=0, max_value=30,
                                       value=st.session_state["profile_devices"])
        saved = st.form_submit_button(t("profile_save"), type="primary")
    ui.card_end()

    if saved:
        st.session_state["profile_building_label"] = b_label
        st.session_state["profile_unit_label"] = u_label
        st.session_state["profile_members"] = int(members)
        st.session_state["profile_devices"] = int(devices)
        st.success(t("profile_saved"))
        st.caption(t("profile_update_note"))

    st.write("")
    st.markdown(f"**{t('household_members')}:** {profile_row['Household_Members'] if profile_row is not None else st.session_state['profile_members']}")
    st.markdown(f"**{t('fingerprint_confidence')}:** {fp.get('confidence', 'N/A') if fp.get('available') else 'N/A'}")

    recurring = smart_forms.get_all_explanations(sel_apartment)
    if recurring:
        st.markdown("#### " + ("Recorded explanations (this session)" if not ui.is_ar() else "التفسيرات المسجلة (هذه الجلسة)"))
        for d, reason in sorted(recurring.items()):
            st.write(f"- {d.date()}: {reason}")


def page_demo():
    st.subheader(t("demo_title"))
    st.caption(t("demo_subtitle"))
    st.write("")

    ui.card_start()
    st.markdown(f"**{t('demo_scenario')}**")
    scenario_keys = ["normal", "high_usage", "leak", "building_imbalance", "tank_pump"]
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

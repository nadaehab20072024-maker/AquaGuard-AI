"""
AquaGuard AI — Smart Water Monitoring & Leak Intelligence
=============================================================
Hackathon MVP. Runs entirely on simulated Stage-1 data (see /data).
Never claims a live meter / real-time sensor connection.

Run with:  streamlit run app.py
"""

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

ui.inject_css()

# ---------------------------------------------------------------------------
# Language gate (first-run screen)
# ---------------------------------------------------------------------------
if "lang" not in st.session_state:
    st.session_state["lang"] = None

if st.session_state["lang"] is None:
    st.markdown(
        """
        <div style="text-align:center; margin-top:8vh;">
            <div style="font-size:3rem;">💧</div>
            <div style="font-size:2.2rem; font-weight:800; background:linear-gradient(90deg,#22d3ee,#60a5fa);
                        -webkit-background-clip:text; -webkit-text-fill-color:transparent;">
                Welcome to AquaGuard AI
            </div>
            <div style="color:#93a4bf; margin-top:0.6rem; font-size:1.1rem;">
                Please choose your preferred language / الرجاء اختيار لغتك المفضلة
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    c1, c2, c3 = st.columns([1, 1, 1])
    with c2:
        col_en, col_ar = st.columns(2)
        with col_en:
            if st.button("🇬🇧 English", use_container_width=True):
                st.session_state["lang"] = "en"
                st.rerun()
        with col_ar:
            if st.button("🇴🇲 العربية", use_container_width=True):
                st.session_state["lang"] = "ar"
                st.rerun()
    st.stop()

t = ui.t

# ---------------------------------------------------------------------------
# Data load
# ---------------------------------------------------------------------------
data = data_loader.load_all_data()
ts = data["timeseries"]
profiles = data["profiles"]
building_df = data["building"]
load_warnings = data["warnings"]

apt_daily_all = data_loader.get_apartment_daily(ts) if ts is not None else pd.DataFrame()
pairs = data_loader.apartment_options(profiles, ts)


def resolve_demo_scenario(choice, apt_daily_all, building_df, pairs):
    """Pick a REAL apartment/building from the dataset matching the requested
    demo scenario. Returns (building, apartment) or (None, None) if the
    dataset doesn't contain such a scenario."""
    if choice == "Possible Hidden Leak":
        for b, a in pairs:
            sub = apt_daily_all[apt_daily_all["Apartment_ID"] == a]
            fp_ = fingerprint.build_fingerprint(sub)
            if fp_.get("available") and fp_.get("night_flow_available"):
                nights = sub["Night_Flow_2AM_5AM_Liters"].dropna()
                expected = fp_.get("expected_idle_flow") or 0
                if (nights > max(expected * 5, 10)).tail(7).sum() >= 3:
                    return b, a
        return None, None
    if choice == "High Legitimate Usage":
        best = None
        best_ratio = 0
        for b, a in pairs:
            sub = apt_daily_all[apt_daily_all["Apartment_ID"] == a]
            if sub.empty:
                continue
            ratio = sub["Water_Consumption_Liters"].max() / max(sub["Water_Consumption_Liters"].median(), 1)
            if ratio > best_ratio:
                best_ratio, best = ratio, (b, a)
        return best if best else (None, None)
    if choice == "Building Water Imbalance":
        if building_df is None or building_df.empty or "Unaccounted_Water_Liters" not in building_df.columns:
            return None, None
        row = building_df.loc[building_df["Unaccounted_Water_Liters"].idxmax()]
        b = int(row["Building_ID"])
        apts = sorted(a for bb, a in pairs if bb == b)
        return (b, apts[0]) if apts else (None, None)
    if choice == "Tank/Pump Anomaly":
        if building_df is None or building_df.empty or "Pump_State" not in building_df.columns:
            return None, None
        cont = building_df[building_df["Pump_State"].astype(str).str.lower() == "continuous"]
        if cont.empty:
            return None, None
        b = int(cont.iloc[0]["Building_ID"])
        apts = sorted(a for bb, a in pairs if bb == b)
        return (b, apts[0]) if apts else (None, None)
    if choice == "Normal Household":
        for b, a in pairs:
            sub = apt_daily_all[apt_daily_all["Apartment_ID"] == a]
            fp_ = fingerprint.build_fingerprint(sub)
            if fp_.get("available") and fp_.get("trend") == "Stable":
                return b, a
        return pairs[0] if pairs else (None, None)
    return None, None


# Resolve any pending demo-mode jump BEFORE the selection widgets are created,
# so the sidebar dropdowns visually reflect the jump (not just the analysis).
if st.session_state.get("_demo_jump") and pairs:
    choice = st.session_state.pop("_demo_jump")
    b, a = resolve_demo_scenario(choice, apt_daily_all, building_df, pairs)
    if b is not None:
        st.session_state["sb_building"] = b
        st.session_state["sb_apartment"] = a
        st.session_state["_demo_toast"] = f"Demo scenario '{choice}' → Building {b}, Apartment {a}"
    else:
        st.session_state["_demo_toast_warn"] = f"Scenario '{choice}' not found in the current dataset."

# ---------------------------------------------------------------------------
# Sidebar
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

    st.divider()

    if not pairs:
        st.error("No household data available.")
        st.stop()

    buildings = sorted(set(b for b, a in pairs))
    if "sb_building" not in st.session_state or st.session_state["sb_building"] not in buildings:
        st.session_state["sb_building"] = buildings[0]
    sel_building = st.selectbox(
        t("select_building"), buildings, format_func=lambda b: f"Building {b}", key="sb_building",
    )
    apts_in_building = sorted(a for b, a in pairs if b == sel_building)
    if "sb_apartment" not in st.session_state or st.session_state["sb_apartment"] not in apts_in_building:
        st.session_state["sb_apartment"] = apts_in_building[0]
    sel_apartment = st.selectbox(
        t("select_apartment"), apts_in_building, format_func=lambda a: f"Apartment {a}", key="sb_apartment",
    )

    st.divider()

    page = st.radio(
        "Navigation",
        [
            t("nav_overview"), t("nav_household"), t("nav_fingerprint"), t("nav_leak"),
            t("nav_building"), t("nav_tank"), t("nav_explorer"), t("nav_ai"), t("nav_assistant"),
        ],
        label_visibility="collapsed",
    )

    st.divider()
    with st.expander("⚙️ Demo Mode" if st.session_state["lang"] == "en" else "⚙️ وضع العرض التوضيحي"):
        demo_choices = [
            "Normal Household", "High Legitimate Usage", "Possible Hidden Leak",
            "Building Water Imbalance", "Tank/Pump Anomaly",
        ]
        demo_choice = st.selectbox("Scenario", demo_choices)
        if st.button("Apply Scenario"):
            st.session_state["_demo_jump"] = demo_choice
            st.rerun()

    if load_warnings:
        with st.expander("⚠️ Data notices"):
            for w in load_warnings:
                st.caption(w)

if "_demo_toast" in st.session_state:
    st.toast(st.session_state.pop("_demo_toast"))
if "_demo_toast_warn" in st.session_state:
    st.toast(st.session_state.pop("_demo_toast_warn"), icon="⚠️")

# ---------------------------------------------------------------------------
# Build the analysis context for the selected household (single source of truth)
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

household_ctx = {
    "apartment_id": sel_apartment,
    "building_id": sel_building,
    "analysis": analysis,
    "fingerprint": fp,
}
if building_df is not None:
    household_ctx["building_balance"] = building_balance.analyze_building(building_df, sel_building)
    household_ctx["tank_pump"] = tank_pump.analyze_tank_pump(building_df, sel_building)

ui.render_header()
st.markdown(f"**{t('building_id')}:** {sel_building}  |  **{t('apartment_id')}:** {sel_apartment}")
st.write("")

# ---------------------------------------------------------------------------
# PAGE: OVERVIEW
# ---------------------------------------------------------------------------
def page_overview():
    ui.status_pill(analysis["status"])
    st.write("")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric(t("current_consumption"), f"{analysis['current_consumption']:.0f} L" if analysis['current_consumption'] is not None else "N/A")
    with c2:
        st.metric(t("household_baseline"), analysis["baseline_text"])
    with c3:
        st.metric(t("trend"), analysis["trend"])
    with c4:
        idle_val = analysis.get("night_flow_current")
        st.metric(t("idle_flow"), f"{idle_val:.1f} L" if idle_val is not None else "N/A")

    c5, c6, c7 = st.columns(3)
    with c5:
        members = profile_row["Household_Members"] if profile_row is not None else "N/A"
        st.metric(t("household_members"), members)
    with c6:
        st.metric(t("leak_indicator"), analysis["leak_indicator"])
    with c7:
        st.metric("Fingerprint confidence" if st.session_state["lang"] == "en" else "ثقة البصمة", fp.get("confidence", "N/A") if fp.get("available") else "N/A")

    st.write("")
    ui.card_start()
    st.markdown(f"**{t('recommended_action')}**")
    st.write(analysis["recommended_action"])
    ui.card_end()

    if analysis.get("smart_form_needed"):
        render_smart_form()

    # quick chart
    if not apt_daily.empty:
        render_consumption_chart(apt_daily, fp, days=30, key_suffix="overview")


def render_smart_form():
    ui.card_start()
    st.markdown("### 📝 " + ("Smart Verification Form" if st.session_state["lang"] == "en" else "نموذج التحقق الذكي"))
    st.write(
        "Was there any unusual water-use activity during this period?"
        if st.session_state["lang"] == "en"
        else "هل كان هناك أي نشاط استخدام مياه غير معتاد خلال هذه الفترة؟"
    )
    choice = st.radio(
        "explain", smart_forms.EXPLANATION_OPTIONS, label_visibility="collapsed",
        key=f"smart_form_{sel_apartment}_{analysis.get('current_date')}",
    )
    if st.button("Submit" if st.session_state["lang"] == "en" else "إرسال", key=f"submit_{sel_apartment}"):
        smart_forms.record_explanation(sel_apartment, analysis["current_date"], choice)
        st.success("Recorded. Recalculating…" if st.session_state["lang"] == "en" else "تم التسجيل. جارٍ إعادة الحساب…")
        st.rerun()
    ui.card_end()


def render_consumption_chart(apt_daily, fp, days=30, key_suffix=""):
    df = apt_daily.tail(days)
    fig = go.Figure()
    if fp.get("available"):
        fig.add_hrect(y0=fp["normal_min"], y1=fp["normal_max"], fillcolor="#22d3ee", opacity=0.08, line_width=0)
    fig.add_trace(go.Scatter(
        x=df["Date"], y=df["Water_Consumption_Liters"], mode="lines+markers",
        name="Daily consumption", line=dict(color="#22d3ee", width=2),
        marker=dict(
            size=7,
            color=["#ef4444" if (fp.get("available") and v > fp["normal_max"]) else "#22d3ee"
                   for v in df["Water_Consumption_Liters"]],
        ),
    ))
    fig.update_layout(
        template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        height=340, margin=dict(l=10, r=10, t=30, b=10),
        yaxis_title="Liters / day", legend=dict(orientation="h", y=1.1),
    )
    st.plotly_chart(fig, use_container_width=True, key=f"chart_{key_suffix}")


# ---------------------------------------------------------------------------
# PAGE: HOUSEHOLD MONITORING
# ---------------------------------------------------------------------------
def page_household_monitoring():
    st.subheader(t("nav_household"))
    ui.status_pill(analysis["status"])
    st.write("")

    range_choice = st.radio(
        "Range", ["7 days", "30 days", "90 days", "Full history"], horizontal=True, index=1,
    )
    days_map = {"7 days": 7, "30 days": 30, "90 days": 90, "Full history": 10_000}
    if not apt_daily.empty:
        render_consumption_chart(apt_daily, fp, days=days_map[range_choice], key_suffix="household")

        st.markdown("#### " + ("Night / Idle Flow" if st.session_state["lang"] == "en" else "تدفق الليل / الخمول"))
        if "Night_Flow_2AM_5AM_Liters" in apt_daily.columns and apt_daily["Night_Flow_2AM_5AM_Liters"].notna().any():
            df = apt_daily.tail(days_map[range_choice])
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df["Date"], y=df["Night_Flow_2AM_5AM_Liters"], name="Observed night flow",
                                      line=dict(color="#f97316", width=2)))
            expected = fp.get("expected_idle_flow")
            if expected is not None:
                fig.add_trace(go.Scatter(x=df["Date"], y=[expected] * len(df), name="Learned expected idle flow",
                                          line=dict(color="#22c55e", width=2, dash="dash")))
            fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                               height=300, margin=dict(l=10, r=10, t=20, b=10), yaxis_title="Liters")
            st.plotly_chart(fig, use_container_width=True, key="night_flow_chart")
        else:
            st.info("Night-flow data is unavailable for this household.")
    else:
        st.warning("No time-series data available for this household.")

    if analysis.get("smart_form_needed"):
        render_smart_form()


# ---------------------------------------------------------------------------
# PAGE: CONSUMPTION FINGERPRINT
# ---------------------------------------------------------------------------
def page_fingerprint():
    st.subheader(t("nav_fingerprint"))
    if not fp.get("available"):
        st.warning("Not enough data to build a fingerprint for this household yet.")
        return

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Normal min", f"{fp['normal_min']:.0f} L")
    c2.metric("Normal max", f"{fp['normal_max']:.0f} L")
    c3.metric("Average daily", f"{fp['average_daily']:.0f} L")
    c4.metric("Median daily", f"{fp['median_daily']:.0f} L")

    c5, c6, c7, c8 = st.columns(4)
    c5.metric("Observations", fp["observation_count"])
    c6.metric("Confidence", fp["confidence"])
    c7.metric("Trend", fp["trend"])
    c8.metric("Last updated", str(fp["last_updated"].date()) if pd.notna(fp["last_updated"]) else "N/A")

    st.write("")
    ui.card_start()
    st.markdown("**Learned idle period:** " + fp.get("learned_idle_period", "Unavailable"))
    exp_idle = fp.get("expected_idle_flow")
    st.markdown(f"**Expected idle flow:** {exp_idle:.2f} L" if exp_idle is not None else "**Expected idle flow:** Unavailable")
    ui.card_end()

    ui.card_start()
    st.markdown("**Typical high-use days:** " + (", ".join(fp["typical_high_days"]) if fp["typical_high_days"] else "None detected"))
    st.markdown("**Typical low-use days:** " + (", ".join(fp["typical_low_days"]) if fp["typical_low_days"] else "None detected"))
    ui.card_end()

    if fp.get("by_weekday"):
        st.markdown("#### Weekday pattern")
        wd_df = pd.DataFrame(fp["by_weekday"]).T
        wd_df = wd_df.rename(columns={"median": "Median (L)", "mean": "Mean (L)", "count": "Days observed"})
        order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        wd_df = wd_df.reindex([d for d in order if d in wd_df.index])
        st.dataframe(wd_df.round(1), use_container_width=True)

    recurring = smart_forms.get_all_explanations(sel_apartment)
    if recurring:
        st.markdown("#### Recorded legitimate explanations (this session)")
        for d, reason in sorted(recurring.items()):
            st.write(f"- {d.date()}: {reason}")


# ---------------------------------------------------------------------------
# PAGE: LEAK DETECTION
# ---------------------------------------------------------------------------
def page_leak_detection():
    st.subheader(t("nav_leak"))
    view = leak_detection.leak_detection_view(apt_daily, fp, explained_dates)
    ui.status_pill(view["status"])
    st.write("")

    c1, c2 = st.columns(2)
    with c1:
        st.metric(t("leak_indicator"), view["leak_indicator"])
    with c2:
        st.metric("Persistence (unexplained high days)", view["persistence_days"])

    st.markdown("#### Evidence")
    for label, present in view["evidence_checklist"]:
        icon = "🔴" if present else "⚪"
        st.write(f"{icon} {label}")

    if view["leak_evidence"]:
        ui.card_start()
        for e in view["leak_evidence"]:
            st.write("• " + e)
        ui.card_end()

    if view["night_flow_series"] is not None and not view["night_flow_series"].empty:
        st.markdown("#### Night flow history")
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=view["night_flow_series"]["Date"], y=view["night_flow_series"]["Night_Flow_2AM_5AM_Liters"],
            marker_color=["#ef4444" if v > max((view.get("expected_idle_flow") or 0) * 5, 10) else "#22d3ee"
                          for v in view["night_flow_series"]["Night_Flow_2AM_5AM_Liters"]],
        ))
        fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                           height=300, margin=dict(l=10, r=10, t=20, b=10), yaxis_title="Liters")
        st.plotly_chart(fig, use_container_width=True, key="leak_night_chart")

    st.markdown(f"#### {t('recommended_action')}")
    st.info(view["recommended_action"])

    if view.get("smart_form_needed"):
        render_smart_form()


# ---------------------------------------------------------------------------
# PAGE: BUILDING WATER BALANCE
# ---------------------------------------------------------------------------
def page_building_balance():
    st.subheader(t("nav_building"))
    bb = building_balance.analyze_building(building_df, sel_building) if building_df is not None else {"available": False}
    if not bb.get("available"):
        st.warning(bb.get("reason", "Building meter data is unavailable for this building."))
        return

    ui.status_pill(bb["status"])
    st.write("")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Main Meter", f"{bb['main_meter']:.0f} L")
    c2.metric("Apartment Total", f"{bb['apartment_total']:.0f} L")
    c3.metric("Legitimate External Use", f"{bb['legitimate_external']:.0f} L")
    c4.metric("Unaccounted Water", f"{bb['unaccounted']:.0f} L")

    c5, c6 = st.columns(2)
    c5.metric("Classification", bb["classification"])
    c6.metric("Persistence (days)", bb["persistence_days"])

    if bb.get("alert_text"):
        st.warning("⚠️ " + bb["alert_text"])

    st.markdown("#### Historical comparison")
    hist = bb["table"].tail(30)
    fig = go.Figure()
    fig.add_trace(go.Bar(x=hist["Date"], y=hist["Main_Meter_Liters"], name="Main meter", marker_color="#60a5fa"))
    fig.add_trace(go.Bar(x=hist["Date"], y=hist["Apartment_Meters_Total_Liters"], name="Apartment total", marker_color="#22d3ee"))
    fig.add_trace(go.Scatter(x=hist["Date"], y=hist["Unaccounted_Water_Liters"], name="Unaccounted water",
                              line=dict(color="#ef4444", width=2), yaxis="y2"))
    fig.update_layout(
        template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        barmode="group", height=380, margin=dict(l=10, r=10, t=20, b=10),
        yaxis=dict(title="Liters"), yaxis2=dict(title="Unaccounted (L)", overlaying="y", side="right"),
        legend=dict(orientation="h", y=1.15),
    )
    st.plotly_chart(fig, use_container_width=True, key="building_chart")


# ---------------------------------------------------------------------------
# PAGE: TANK & PUMP
# ---------------------------------------------------------------------------
def page_tank_pump():
    st.subheader(t("nav_tank"))
    tp = tank_pump.analyze_tank_pump(building_df, sel_building) if building_df is not None else {"available": False}
    if not tp.get("available"):
        st.warning("Tank/pump data is unavailable for this building.")
        return

    ui.status_pill(tp["status"] if tp["status"] in ("Normal", "Monitoring") else "Warning")
    st.write("")
    c1, c2 = st.columns(2)
    c1.metric("Tank Level", f"{tp['tank_level']:.0f} %" if tp.get("tank_level") is not None else "Unavailable")
    c2.metric("Pump State", tp.get("pump_state") or "Unavailable")

    st.markdown(f"**Status:** {tp['status']}")
    if tp["findings"]:
        st.markdown("#### Findings")
        for f_ in tp["findings"]:
            st.write("• " + f_)

    st.markdown("#### Recent history")
    hist = tp["table"].tail(30)
    fig = go.Figure()
    if "Tank_Level_Percent" in hist.columns:
        fig.add_trace(go.Scatter(x=hist["Date"], y=hist["Tank_Level_Percent"], name="Tank level (%)",
                                  line=dict(color="#22d3ee", width=2)))
    fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                       height=300, margin=dict(l=10, r=10, t=20, b=10), yaxis_title="Tank level (%)")
    st.plotly_chart(fig, use_container_width=True, key="tank_chart")

    if tp["status"] == "Possible tank/float issue":
        st.error(
            "⚠️ Critical pump/tank alert — water input is substantially higher than explained household use, "
            "while the tank appears near full and the pump is still running. A tank float/overflow problem is "
            "possible. Close the main valve if safe to do so and arrange technical inspection."
        )
    elif tp["status"] == "Possible abnormal pump operation":
        st.warning("⚠️ Possible abnormal pump operation detected — the pump is running continuously with an unexplained water input.")


# ---------------------------------------------------------------------------
# PAGE: DATA EXPLORER
# ---------------------------------------------------------------------------
def page_data_explorer():
    st.subheader(t("nav_explorer"))
    if ts is None or ts.empty:
        st.warning("Time-series data unavailable.")
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


# ---------------------------------------------------------------------------
# PAGE: AI INSIGHTS
# ---------------------------------------------------------------------------
def page_ai_insights():
    st.subheader(t("nav_ai"))
    facts = ai_insights.build_context_facts(household_ctx)
    insight = ai_insights.deterministic_insight(facts, st.session_state["lang"])

    ui.card_start()
    st.markdown(f"### 🤖 {insight['headline']}")
    st.markdown(f"**{insight['why_label']}**")
    for r in insight["why"]:
        st.write("• " + r)
    st.markdown(f"**{insight['meaning_label']}**")
    st.write(insight["meaning"])
    st.markdown(f"**{insight['action_label']}**")
    st.write(insight["action"])
    ui.card_end()

    with st.expander("Facts used for this insight (transparency)"):
        st.json(facts)


# ---------------------------------------------------------------------------
# PAGE: AI ASSISTANT
# ---------------------------------------------------------------------------
def page_ai_assistant():
    st.subheader(t("nav_assistant"))
    st.caption(
        "Ask about the currently selected household's AquaGuard data."
        if st.session_state["lang"] == "en"
        else "اسأل عن بيانات أكواجارد للمنزل المحدد حاليًا."
    )

    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = []

    for role, msg in st.session_state["chat_history"]:
        with st.chat_message(role):
            st.write(msg)

    examples = [
        "Why is my status warning?", "Why did my consumption increase?",
        "Is there a possible hidden leak?", "What is my normal range?",
    ] if st.session_state["lang"] == "en" else [
        "لماذا حالتي تحذير؟", "لماذا زاد استهلاكي؟", "هل هناك احتمال تسرب مخفي؟", "ما هو نطاقي الطبيعي؟",
    ]
    st.caption(("Try: " if st.session_state["lang"] == "en" else "جرّب: ") + " · ".join(examples))

    prompt = st.chat_input("Ask AquaGuard…" if st.session_state["lang"] == "en" else "اسأل أكواجارد…")
    if prompt:
        st.session_state["chat_history"].append(("user", prompt))
        facts = ai_insights.build_context_facts(household_ctx)
        det_answer = ai_insights.answer_question(prompt, facts, st.session_state["lang"])
        final_answer = ai_insights.llm_rephrase(facts, prompt, st.session_state["lang"], det_answer)
        st.session_state["chat_history"].append(("assistant", final_answer))
        st.rerun()


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------
page_map = {
    t("nav_overview"): page_overview,
    t("nav_household"): page_household_monitoring,
    t("nav_fingerprint"): page_fingerprint,
    t("nav_leak"): page_leak_detection,
    t("nav_building"): page_building_balance,
    t("nav_tank"): page_tank_pump,
    t("nav_explorer"): page_data_explorer,
    t("nav_ai"): page_ai_insights,
    t("nav_assistant"): page_ai_assistant,
}
page_map[page]()

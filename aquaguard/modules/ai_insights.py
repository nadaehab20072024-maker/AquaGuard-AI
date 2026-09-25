"""
AquaGuard AI — Insights & Assistant
======================================
Two layers:

1. Deterministic insight generator — always available, uses only the
   already-computed analysis numbers (never invents figures). Powers the
   "AI Insights" page and is the fallback for the chat assistant.

2. Optional LLM-backed assistant — if an Anthropic API key is present in
   st.secrets, the deterministic facts are handed to the model purely to
   improve the *phrasing* of the explanation. The model is never given the
   raw dataset and is never allowed to answer general-purpose questions;
   it only rephrases the facts AquaGuard already computed.
"""

import json
import streamlit as st

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None


def _get_api_key():
    try:
        return st.secrets.get("ANTHROPIC_API_KEY")
    except Exception:
        return None


def build_context_facts(household_ctx: dict) -> dict:
    """Collect a compact, English, fact-only summary of the current household
    analysis. This is the ONLY information ever passed to an LLM, and is also
    what the deterministic engine renders directly."""
    a = household_ctx.get("analysis", {})
    fp = household_ctx.get("fingerprint", {})
    facts = {
        "apartment_id": household_ctx.get("apartment_id"),
        "building_id": household_ctx.get("building_id"),
        "status": a.get("status"),
        "current_consumption_liters": a.get("current_consumption"),
        "baseline_range": a.get("baseline_text"),
        "trend": a.get("trend"),
        "persistence_days": a.get("persistence_days"),
        "leak_indicator": a.get("leak_indicator"),
        "night_flow_current": a.get("night_flow_current"),
        "night_flow_expected": a.get("night_flow_expected"),
        "abnormal_night_count_7d": a.get("abnormal_night_count_7d"),
        "reasons": a.get("reasons"),
        "recommended_action": a.get("recommended_action"),
        "fingerprint_confidence": fp.get("confidence"),
    }
    if "building_balance" in household_ctx:
        bb = household_ctx["building_balance"]
        if bb.get("available"):
            facts["building_unaccounted_water"] = bb.get("unaccounted")
            facts["building_classification"] = bb.get("classification")
    if "tank_pump" in household_ctx:
        tp = household_ctx["tank_pump"]
        if tp.get("available"):
            facts["tank_pump_status"] = tp.get("status")
    return facts


def deterministic_insight(facts: dict, lang: str = "en") -> dict:
    """Return a structured insight: headline, why, meaning, action — built
    purely from template logic over the facts dict, in the requested
    language."""
    status = facts.get("status", "Normal")
    reasons = facts.get("reasons") or []

    if lang == "ar":
        headline_map = {
            "Normal": "استهلاك المياه ضمن النطاق الطبيعي لهذا المنزل.",
            "Monitoring": "تمت ملاحظة زيادة طفيفة، ويستمر النظام في المراقبة.",
            "Warning": "استهلاك المياه أعلى من المعتاد بشكل متكرر لهذا المنزل.",
            "Critical": "تم رصد نمط استهلاك غير طبيعي وقوي يستدعي الانتباه العاجل.",
        }
        meaning_map = {
            "Normal": "لا توجد مؤشرات على تسرب أو استخدام غير طبيعي.",
            "Monitoring": "من المبكر تأكيد وجود مشكلة؛ يوم واحد غير معتاد لا يعني تسربًا.",
            "Warning": "قد يكون هناك استخدام غير مبرر أو تسرب مخفي محتمل.",
            "Critical": "احتمال وجود تسرب مخفي أو مشكلة في الشبكة الداخلية.",
        }
        action = facts.get("recommended_action", "")
        why_label, meaning_label, action_label = "لماذا؟", "ماذا يعني هذا؟", "الإجراء الموصى به"
    else:
        headline_map = {
            "Normal": "Water consumption is within this household's normal pattern.",
            "Monitoring": "A mild increase has been observed; AquaGuard is monitoring.",
            "Warning": "Water consumption has been repeatedly above this household's baseline.",
            "Critical": "A strong, persistent abnormal pattern has been detected.",
        }
        meaning_map = {
            "Normal": "No indication of a leak or abnormal usage.",
            "Monitoring": "Too early to confirm anything — a single unusual day is not a leak.",
            "Warning": "Possible unexplained usage or a possible hidden leak.",
            "Critical": "Possible hidden leak or a supply-line issue that deserves prompt attention.",
        }
        action = facts.get("recommended_action", "")
        why_label, meaning_label, action_label = "Why?", "What does this mean?", "Recommended action"

    return {
        "headline": headline_map.get(status, headline_map["Normal"]),
        "why_label": why_label,
        "why": reasons,
        "meaning_label": meaning_label,
        "meaning": meaning_map.get(status, meaning_map["Normal"]),
        "action_label": action_label,
        "action": action,
    }


def answer_question(question: str, facts: dict, lang: str = "en") -> str:
    """Deterministic local Q&A engine — pattern-matches the question to the
    facts already computed for the selected household. Used whenever no API
    key is configured, and as a safety net if the API call fails."""
    q = question.lower()
    status = facts.get("status", "Normal")
    cons = facts.get("current_consumption_liters")
    baseline = facts.get("baseline_range")
    trend = facts.get("trend")
    leak = facts.get("leak_indicator")
    reasons = facts.get("reasons") or []
    night_now = facts.get("night_flow_current")
    night_exp = facts.get("night_flow_expected")

    def L(en, ar):
        return ar if lang == "ar" else en

    if any(k in q for k in ["why is my status", "why status", "لماذا الحالة", "سبب الحالة"]):
        return L(
            f"The status is '{status}' because: " + " ".join(reasons),
            f"الحالة هي '{status}' للأسباب التالية: " + " ".join(reasons),
        )
    if any(k in q for k in ["consumption increase", "why did my consumption", "زيادة الاستهلاك", "لماذا زاد"]):
        return L(
            f"Current consumption is {cons:.0f} L against a normal range of {baseline}. The recent trend is '{trend}'.",
            f"الاستهلاك الحالي هو {cons:.0f} لتر مقابل النطاق الطبيعي {baseline}. الاتجاه الحالي هو '{trend}'.",
        )
    if any(k in q for k in ["hidden leak", "leak", "تسرب"]):
        if leak == "Possible hidden leak":
            return L(
                f"Yes, there is a possible hidden leak. Night flow is {night_now} L against an expected idle flow of about {night_exp} L, repeated over several nights.",
                f"نعم، هناك احتمال وجود تسرب مخفي. تدفق الليل هو {night_now} لتر مقابل التدفق المتوقع في وضع الخمول حوالي {night_exp} لتر، وتكرر ذلك عدة ليالٍ.",
            )
        return L(
            "No strong hidden-leak evidence at the moment — night flow is close to this household's expected idle level.",
            "لا توجد مؤشرات قوية على تسرب مخفي حاليًا — تدفق الليل قريب من المستوى المتوقع لهذا المنزل.",
        )
    if any(k in q for k in ["normal range", "baseline", "النطاق الطبيعي", "الخط الأساسي"]):
        return L(f"This household's normal daily range is {baseline}.", f"النطاق اليومي الطبيعي لهذا المنزل هو {baseline}.")
    if any(k in q for k in ["last 7 days", "past week", "آخر 7 أيام", "الأسبوع الماضي"]):
        return L(
            f"Over the recent period, the trend has been '{trend}' with {facts.get('persistence_days', 0)} consecutive unexplained high day(s).",
            f"خلال الفترة الأخيرة، كان الاتجاه '{trend}' مع {facts.get('persistence_days', 0)} يوم/أيام متتالية غير مبررة من الارتفاع.",
        )
    if any(k in q for k in ["night flow", "تدفق الليل"]):
        return L(
            f"Night flow (02:00–05:00) is currently {night_now} L, versus this household's expected idle flow of about {night_exp} L.",
            f"تدفق الليل (02:00–05:00) حاليًا {night_now} لتر، مقابل التدفق المتوقع لهذا المنزل حوالي {night_exp} لتر.",
        )
    if any(k in q for k in ["building water balance", "توازن مياه المبنى", "unaccounted"]):
        bb_class = facts.get("building_classification")
        bb_val = facts.get("building_unaccounted_water")
        if bb_class is not None:
            return L(
                f"The building's unaccounted water is currently {bb_val:.0f} L, classified as '{bb_class}'.",
                f"المياه غير المحسوبة في المبنى حاليًا {bb_val:.0f} لتر، مصنفة كـ '{bb_class}'.",
            )
        return L("Building water balance data is not available for this building.", "بيانات توازن مياه المبنى غير متوفرة لهذا المبنى.")

    # Fallback generic summary
    return L(
        f"Current status: {status}. Consumption: {cons:.0f} L vs normal range {baseline}. Trend: {trend}. Leak indicator: {leak}.",
        f"الحالة الحالية: {status}. الاستهلاك: {cons:.0f} لتر مقابل النطاق الطبيعي {baseline}. الاتجاه: {trend}. مؤشر التسرب: {leak}.",
    )


def llm_rephrase(facts: dict, question: str, lang: str, deterministic_answer: str) -> str:
    """Optionally improve phrasing via the Anthropic API. Falls back silently
    to the deterministic answer on any failure (missing key, no network,
    bad response, etc.). Never sends secrets to the UI; never sends raw
    per-record data — only the aggregated facts dict."""
    api_key = _get_api_key()
    if not api_key or requests is None:
        return deterministic_answer

    system = (
        "You are AquaGuard AI's assistant. You may ONLY use the JSON facts you are given about "
        "one household's water-consumption analysis. Do not invent numbers. Do not answer questions "
        "unrelated to this household's water data. Respond in "
        + ("Arabic" if lang == "ar" else "English")
        + " in 2-4 concise sentences. Never claim a leak is confirmed — only 'possible'."
    )
    user_msg = f"Facts: {json.dumps(facts, default=str)}\n\nQuestion: {question}\n\nBaseline deterministic answer (you may improve phrasing but keep it factually identical): {deterministic_answer}"

    try:
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-sonnet-4-6",
                "max_tokens": 300,
                "system": system,
                "messages": [{"role": "user", "content": user_msg}],
            },
            timeout=8,
        )
        if resp.status_code != 200:
            return deterministic_answer
        data = resp.json()
        parts = [b.get("text", "") for b in data.get("content", []) if b.get("type") == "text"]
        text = "\n".join(p for p in parts if p).strip()
        return text or deterministic_answer
    except Exception:
        return deterministic_answer

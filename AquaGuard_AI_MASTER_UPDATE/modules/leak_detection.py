"""
AquaGuard AI — Leak Detection
===============================
Builds the detailed evidence view for the dedicated Leak Detection page.
Reuses the same status/analysis engine as the Overview page (single source
of truth) and adds the night-flow-focused evidence trail.

Never states a confirmed leak — only "Possible hidden leak".
"""

import pandas as pd
from modules.anomaly_detection import analyze_household


_CHECKLIST_LABELS = {
    "en": [
        "Daily consumption anomaly",
        "Repeated abnormal consumption (persistence)",
        "Night flow above learned idle level",
        "Persistent abnormal night flow (3+ of last 7 nights)",
        "Trend increasing",
    ],
    "ar": [
        "شذوذ في الاستهلاك اليومي",
        "استهلاك غير طبيعي متكرر (استمرارية)",
        "تدفق الليل أعلى من مستوى الخمول المتعلَّم",
        "تدفق ليلي غير طبيعي مستمر (3 أو أكثر من آخر 7 ليالٍ)",
        "الاتجاه في ازدياد",
    ],
}


def leak_detection_view(apt_daily: pd.DataFrame, fp: dict, explained_dates=None, lang: str = "en") -> dict:
    analysis = analyze_household(apt_daily, fp, explained_dates)

    view = dict(analysis)
    view["night_flow_series"] = None
    view["expected_idle_flow"] = fp.get("expected_idle_flow") if fp.get("available") else None

    if apt_daily is not None and not apt_daily.empty and "Night_Flow_2AM_5AM_Liters" in apt_daily.columns:
        series = apt_daily[["Date", "Night_Flow_2AM_5AM_Liters"]].dropna()
        view["night_flow_series"] = series

    # Build a plain, bilingual evidence checklist for the UI
    labels = _CHECKLIST_LABELS.get(lang, _CHECKLIST_LABELS["en"])
    flags = [
        analysis["deviation_kind"] == "high",
        analysis["persistence_days"] >= 2,
        analysis.get("abnormal_night_count_7d", 0) >= 1,
        analysis.get("abnormal_night_count_7d", 0) >= 3,
        fp.get("trend") == "Increasing",
    ]
    view["evidence_checklist"] = list(zip(labels, flags))

    return view

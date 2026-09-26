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


def leak_detection_view(apt_daily: pd.DataFrame, fp: dict, explained_dates=None) -> dict:
    analysis = analyze_household(apt_daily, fp, explained_dates)

    view = dict(analysis)
    view["night_flow_series"] = None
    view["expected_idle_flow"] = fp.get("expected_idle_flow") if fp.get("available") else None

    if apt_daily is not None and not apt_daily.empty and "Night_Flow_2AM_5AM_Liters" in apt_daily.columns:
        series = apt_daily[["Date", "Night_Flow_2AM_5AM_Liters"]].dropna()
        view["night_flow_series"] = series

    # Build a plain evidence checklist for the UI
    checklist = []
    checklist.append(("Daily consumption anomaly", analysis["deviation_kind"] == "high"))
    checklist.append(("Repeated abnormal consumption (persistence)", analysis["persistence_days"] >= 2))
    checklist.append(("Night flow above learned idle level", analysis.get("abnormal_night_count_7d", 0) >= 1))
    checklist.append(("Persistent abnormal night flow (3+ of last 7 nights)", analysis.get("abnormal_night_count_7d", 0) >= 3))
    checklist.append(("Trend increasing", fp.get("trend") == "Increasing"))
    view["evidence_checklist"] = checklist

    return view

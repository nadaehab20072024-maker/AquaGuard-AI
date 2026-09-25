"""
AquaGuard AI — Anomaly & Status Engine
========================================
Transparent, rule-based (not black-box) engine that turns a household's
Consumption Fingerprint + recent readings into a user-facing status.

Internally uses a fine-grained severity scale (kept private — never shown
to the user as a raw table, per spec) that maps to four public statuses:
    Normal -> Monitoring -> Warning -> Critical

A single abnormal day is never enough on its own to reach Warning/Critical
unless supported by strong night-flow evidence.
"""

import numpy as np
import pandas as pd

PUBLIC_STATUSES = ["Normal", "Monitoring", "Warning", "Critical"]


def _weekday_expected_range(fp: dict, weekday: str):
    """Return (low, high) expected band for a specific weekday if enough
    history exists for that weekday; otherwise fall back to the overall band."""
    by_wd = fp.get("by_weekday", {}) or {}
    wd_stats = by_wd.get(weekday)
    if wd_stats and wd_stats.get("count", 0) >= 3:
        median = wd_stats["median"]
        # +/- 30% band around that weekday's own median
        return median * 0.7, median * 1.3, "weekday-specific"
    return fp.get("normal_min"), fp.get("normal_max"), "overall"


def _day_deviation(value: float, fp: dict, weekday: str):
    low, high, basis = _weekday_expected_range(fp, weekday)
    if low is None or high is None:
        return "unknown", 0.0, basis
    if value > high:
        overshoot = (value - high) / high if high > 0 else 0
        return "high", overshoot, basis
    if value < low:
        undershoot = (low - value) / low if low > 0 else 0
        return "low", undershoot, basis
    return "normal", 0.0, basis


def analyze_household(apt_daily: pd.DataFrame, fp: dict, explained_dates: set | None = None) -> dict:
    """Full apartment-level analysis for the most recent available day.

    explained_dates: set of pandas.Timestamp dates the user has explained via
    the Smart Form during this session — these are excluded from anomaly
    escalation (but still shown in the trace).
    """
    explained_dates = explained_dates or set()
    result = {
        "status": "Normal",
        "internal_level": "L2",
        "current_consumption": None,
        "current_date": None,
        "baseline_text": "Unavailable",
        "trend": fp.get("trend", "Unavailable") if fp.get("available") else "Unavailable",
        "leak_indicator": "None",
        "leak_evidence": [],
        "reasons": [],
        "persistence_days": 0,
        "night_flow_current": None,
        "night_flow_expected": fp.get("expected_idle_flow") if fp.get("available") else None,
        "recommended_action": "Continue normal monitoring.",
        "smart_form_needed": False,
        "explained_today": False,
    }

    if apt_daily is None or apt_daily.empty or not fp.get("available"):
        result["status"] = "Monitoring"
        result["reasons"].append("Insufficient historical data to build a confident fingerprint yet.")
        return result

    apt_daily = apt_daily.sort_values("Date")
    latest = apt_daily.iloc[-1]
    result["current_consumption"] = float(latest["Water_Consumption_Liters"]) if pd.notna(latest.get("Water_Consumption_Liters")) else None
    result["current_date"] = latest.get("Date")
    result["baseline_text"] = f"{fp['normal_min']:.0f}–{fp['normal_max']:.0f} L"

    weekday = latest.get("Weekday", "")
    deviation_kind, deviation_magnitude, basis = _day_deviation(result["current_consumption"] or 0.0, fp, weekday)
    result["deviation_kind"] = deviation_kind
    result["deviation_basis"] = basis

    # ---- Persistence: consecutive recent days flagged "high" and unexplained ----
    tail = apt_daily.tail(7).copy()
    flagged = []
    for _, row in tail.iterrows():
        wd = row.get("Weekday", "")
        kind, mag, _ = _day_deviation(row["Water_Consumption_Liters"], fp, wd)
        is_explained = row["Date"] in explained_dates
        flagged.append(kind == "high" and not is_explained)
    persistence = 0
    for f in reversed(flagged):
        if f:
            persistence += 1
        else:
            break
    result["persistence_days"] = persistence
    result["explained_today"] = latest["Date"] in explained_dates

    # ---- Night flow / hidden leak evidence ----
    night_val = latest.get("Night_Flow_2AM_5AM_Liters")
    if pd.notna(night_val):
        result["night_flow_current"] = float(night_val)
        expected = fp.get("expected_idle_flow") or 0.0
        night_history = apt_daily["Night_Flow_2AM_5AM_Liters"].dropna()
        # how many of the last 7 nights are far above the household's own expected idle flow
        recent_nights = night_history.tail(7)
        threshold = max(expected * 5, expected + 5, 10.0)  # household-relative, with a small absolute floor
        abnormal_nights = int((recent_nights > threshold).sum())
        result["abnormal_night_count_7d"] = abnormal_nights
        if abnormal_nights >= 3:
            result["leak_indicator"] = "Possible hidden leak"
            result["leak_evidence"].append(
                f"Night flow (02:00–05:00) has been abnormally high on {abnormal_nights} of the last "
                f"{len(recent_nights)} nights, versus a learned expected idle flow of about {expected:.1f} L."
            )
        elif abnormal_nights >= 1:
            result["leak_evidence"].append(
                f"Night flow was abnormally high on {abnormal_nights} of the last {len(recent_nights)} nights."
            )

    # ---- Status decision ----
    reasons = result["reasons"]
    level = "L2"

    if deviation_kind == "high":
        reasons.append(
            f"Today's consumption ({result['current_consumption']:.0f} L) is above this household's "
            f"{('weekday-specific' if basis=='weekday-specific' else 'overall')} normal range "
            f"({fp['normal_min']:.0f}–{fp['normal_max']:.0f} L)."
        )
    elif deviation_kind == "low":
        reasons.append("Today's consumption is below the household's normal range (no leak concern from this alone).")
    else:
        reasons.append("Today's consumption is within this household's normal range.")

    if result["explained_today"]:
        reasons.append("This period was explained by the household via the Smart Form.")

    # base level from persistence (only counts unexplained high days)
    if persistence == 0:
        level = "L2"
    elif persistence == 1:
        level = "L3"
    elif persistence == 2:
        level = "L4"
    elif persistence == 3:
        level = "L6"
    elif persistence >= 4:
        level = "L7"

    # escalate strongly if hidden-leak evidence present
    if result["leak_indicator"] == "Possible hidden leak":
        level = "L8" if persistence >= 1 or result.get("abnormal_night_count_7d", 0) >= 5 else "L7"
        reasons.append("Repeated abnormal night-time flow during the household's learned idle period is a strong hidden-leak signal.")

    if result["explained_today"] and persistence <= 1:
        level = "L2"

    level_to_status = {
        "L1": "Normal", "L2": "Normal", "L3": "Monitoring", "L4": "Monitoring",
        "L5": "Warning", "L6": "Warning", "L7": "Warning", "L8": "Critical",
    }
    status = level_to_status.get(level, "Monitoring")
    result["internal_level"] = level
    result["status"] = status

    # Smart form trigger: abnormal pattern reaching monitoring+ without an explanation yet
    if status in ("Monitoring", "Warning", "Critical") and not result["explained_today"] and deviation_kind == "high":
        result["smart_form_needed"] = True

    # Recommended action
    if status == "Critical":
        result["recommended_action"] = "Check fixtures and internal supply lines promptly; consider a technical inspection."
    elif status == "Warning":
        result["recommended_action"] = "Inspect visible fixtures (taps, toilets, washing machine hoses) and confirm whether any known activity explains the pattern."
    elif status == "Monitoring":
        result["recommended_action"] = "No action required yet — AquaGuard will continue monitoring the next few days."
    else:
        result["recommended_action"] = "No action needed. Consumption is within the household's normal pattern."

    result["reasons"] = reasons
    return result

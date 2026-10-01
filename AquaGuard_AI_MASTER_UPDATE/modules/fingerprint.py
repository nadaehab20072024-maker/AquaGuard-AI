"""
AquaGuard AI — Consumption Fingerprint
=======================================
Builds a household-specific "normal behavior" profile from historical daily
data. Nothing here is a fixed, global threshold — every number is computed
from that one apartment's own history.

Learning strategy (matches the project's operations spec):
    - The first ~7 days of history are treated as an initial "warm-up"
      fingerprint (assumed representative, since no anomaly has yet been
      confirmed).
    - From day 8 onward, AquaGuard walks forward day by day. Each new day is
      compared against the fingerprint learned SO FAR. If it looks normal
      (or the user has explained it via the Smart Form), it is folded into
      the learned baseline. If it looks abnormal, it is excluded from the
      baseline — so a persistent, unexplained anomaly (e.g. a hidden leak)
      never drags the household's own "normal" definition up to meet it.

This online/incremental approach matters: a simple global median over the
whole history would be contaminated once an anomaly (like a leak) persists
for a large fraction of the observed days.
"""

import pandas as pd

MIN_OBS_FOR_CONFIDENT_FINGERPRINT = 7  # matches the "first 7 days" learning period in the spec
SEED_DAYS = 7
K_MAD = 3.0  # outlier threshold in scaled-MAD units for folding a day into the learned baseline


def _robust_stats(values: pd.Series):
    values = pd.Series(values).dropna()
    if values.empty:
        return None
    median = float(values.median())
    mad = float((values - median).abs().median())
    scaled_mad = mad * 1.4826 if mad > 0 else (float(values.std(ddof=0)) if len(values) > 1 else 0.0)
    return {
        "median": median,
        "mean": float(values.mean()),
        "std": float(values.std(ddof=0)) if len(values) > 1 else 0.0,
        "mad": scaled_mad,
        "min": float(values.min()),
        "max": float(values.max()),
        "p10": float(values.quantile(0.10)),
        "p90": float(values.quantile(0.90)),
        "n": int(len(values)),
    }


def _is_outlier_high(value, stats_, abs_floor=0.0):
    """Is `value` a high-side outlier relative to already-learned stats_?"""
    if stats_ is None or pd.isna(value):
        return False
    median, mad = stats_["median"], stats_["mad"]
    threshold = max(median + K_MAD * mad, median * 1.5, abs_floor)
    return value > threshold


def _learn_incrementally(daily: pd.DataFrame, value_col: str, explained_dates: set):
    """Walk the sorted daily rows forward, seeding on the first SEED_DAYS rows
    and only folding later rows into the learned pool when they look normal
    (or were explained by the user). Returns a boolean Series mask."""
    values = daily[value_col] if value_col in daily.columns else pd.Series(dtype=float)
    n = len(daily)
    included = [False] * n
    seed_n = min(SEED_DAYS, n)
    for i in range(seed_n):
        included[i] = True

    for i in range(seed_n, n):
        pool_mask = pd.Series(included[:i])
        pool_so_far = values.iloc[:i][pool_mask.values]
        stats_ = _robust_stats(pool_so_far)
        val = values.iloc[i]
        date_i = daily["Date"].iloc[i] if "Date" in daily.columns else None
        is_explained = date_i in explained_dates if explained_dates else False
        if is_explained or not _is_outlier_high(val, stats_):
            included[i] = True
        else:
            included[i] = False
    return pd.Series(included, index=daily.index)


def build_fingerprint(apt_daily: pd.DataFrame, explained_dates: set | None = None) -> dict:
    """Build the Consumption Fingerprint for a single apartment.

    apt_daily: daily rows for ONE apartment only, containing
    Water_Consumption_Liters and optionally Night_Flow_2AM_5AM_Liters and
    Idle_Time_Flow_Liters. Will be sorted by Date internally.
    explained_dates: dates the household explained via the Smart Form this
    session — always folded into the learned baseline as legitimate.
    """
    explained_dates = explained_dates or set()
    fp = {"available": False}
    if apt_daily is None or apt_daily.empty or "Water_Consumption_Liters" not in apt_daily.columns:
        return fp

    apt_daily = apt_daily.sort_values("Date").reset_index(drop=True)

    # --- Incrementally learn which days represent "normal" consumption ---
    included_mask = _learn_incrementally(apt_daily, "Water_Consumption_Liters", explained_dates)
    learned = apt_daily[included_mask]
    overall = _robust_stats(learned["Water_Consumption_Liters"])
    if overall is None:
        return fp

    fp["available"] = True
    fp["overall"] = overall
    fp["observation_count"] = int(len(apt_daily))
    fp["learned_normal_days"] = int(included_mask.sum())
    fp["excluded_anomalous_days"] = int((~included_mask).sum())
    fp["last_updated"] = apt_daily["Date"].max()
    fp["confidence"] = "High" if fp["observation_count"] >= 14 else (
        "Medium" if fp["observation_count"] >= MIN_OBS_FOR_CONFIDENT_FINGERPRINT else "Low"
    )

    fp["normal_min"] = round(overall["p10"], 1)
    fp["normal_max"] = round(overall["p90"], 1)
    fp["average_daily"] = round(overall["mean"], 1)
    fp["median_daily"] = round(overall["median"], 1)

    # Weekday pattern — computed from the LEARNED (normal) pool only
    if "Weekday" in apt_daily.columns:
        by_weekday = learned.groupby("Weekday")["Water_Consumption_Liters"].agg(["median", "mean", "count"])
        fp["by_weekday"] = by_weekday.to_dict(orient="index")
    else:
        fp["by_weekday"] = {}

    high_days, low_days = [], []
    if fp["by_weekday"]:
        overall_median = overall["median"]
        for wd, stats_ in fp["by_weekday"].items():
            if stats_["count"] == 0:
                continue
            if stats_["median"] >= overall_median * 1.15:
                high_days.append(wd)
            elif stats_["median"] <= overall_median * 0.85:
                low_days.append(wd)
    fp["typical_high_days"] = high_days
    fp["typical_low_days"] = low_days
    fp["friday_pattern"] = fp["by_weekday"].get("Friday")
    fp["saturday_pattern"] = fp["by_weekday"].get("Saturday")

    # Trend: compare most recent window vs the window before it (full history, not just the
    # learned pool — the trend SHOULD reflect a real ongoing increase even while unexplained)
    consumption = apt_daily["Water_Consumption_Liters"]
    n = len(apt_daily)
    window = min(7, max(3, n // 3)) if n >= 6 else max(2, n // 2)
    if n >= window * 2:
        recent = consumption.iloc[-window:].median()
        prior = consumption.iloc[-2 * window:-window].median()
    elif n >= 4:
        half = n // 2
        recent = consumption.iloc[-half:].median()
        prior = consumption.iloc[:-half].median()
    else:
        recent = prior = overall["median"]

    pct_change = (recent - prior) / prior * 100 if prior and prior > 0 else 0.0
    fp["trend_pct_change"] = round(pct_change, 1)
    if pct_change >= 12:
        fp["trend"] = "Increasing"
    elif pct_change <= -12:
        fp["trend"] = "Decreasing"
    else:
        fp["trend"] = "Stable"

    # --- Night flow / idle learning (same incremental approach, its own outlier pool) ---
    if "Night_Flow_2AM_5AM_Liters" in apt_daily.columns and apt_daily["Night_Flow_2AM_5AM_Liters"].notna().any():
        night_included_mask = _learn_incrementally(apt_daily, "Night_Flow_2AM_5AM_Liters", explained_dates)
        learned_nights = apt_daily.loc[night_included_mask, "Night_Flow_2AM_5AM_Liters"].dropna()
        night_stats = _robust_stats(learned_nights)
        fp["night_flow_available"] = True
        fp["expected_idle_flow"] = round(night_stats["median"], 2) if night_stats else None
        fp["night_flow_stats"] = night_stats
        fp["night_learned_normal_nights"] = int(night_included_mask.sum())
        fp["night_excluded_anomalous_nights"] = int((~night_included_mask).sum())
        if night_stats and overall["median"] > 0:
            fp["learned_idle_period"] = (
                "02:00–05:00 (Night)" if night_stats["median"] < overall["median"] * 0.05
                else "Not clearly idle (household shows night activity)"
            )
        else:
            fp["learned_idle_period"] = "Unavailable"
    else:
        fp["night_flow_available"] = False
        fp["expected_idle_flow"] = None
        fp["learned_idle_period"] = "Unavailable (no night-flow data)"

    fp["recurring_legitimate_patterns"] = []  # filled in by session-recorded explanations elsewhere

    return fp


def household_baseline_range_text(fp: dict) -> str:
    if not fp.get("available"):
        return "Unavailable"
    return f"{fp['normal_min']:.0f}–{fp['normal_max']:.0f} L"

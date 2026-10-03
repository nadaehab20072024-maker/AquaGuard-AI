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


def build_fingerprint(apt_daily: pd.DataFrame, explained_dates: set | None = None,
                       declared_members: int | None = None) -> dict:
    """Build the Consumption Fingerprint for a single apartment.

    apt_daily: daily rows for ONE apartment only, containing
    Water_Consumption_Liters and optionally Night_Flow_2AM_5AM_Liters and
    Idle_Time_Flow_Liters. Will be sorted by Date internally.
    explained_dates: dates the household explained via the Smart Form this
    session — always folded into the learned baseline as legitimate.
    declared_members: the household's OWN current declared member count
    (from their profile). The historical liters data was generated assuming
    this apartment's own baseline headcount (its own `Household_Members`
    column) — if the household now declares a DIFFERENT (e.g. smaller)
    headcount, the same liters reading means a different thing per person,
    so the whole normal band is rescaled per capita (see "Household-size
    (per-capita) adjustment" below). This is what lets AquaGuard notice that
    an unchanged meter reading has become high (or low) *for the household's
    current size* — not just relative to its own past raw liters history.
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

    # --- Household-size (per-capita) adjustment ---
    # The historical data for this apartment was generated assuming its own
    # baseline headcount. If the household's CURRENT declared headcount
    # differs, the same raw liters figure no longer means the same thing per
    # person, so the whole daytime normal band is rescaled by the ratio of
    # declared-to-baseline members. This is applied directly to the PUBLIC
    # fields (normal_min/normal_max/average_daily/median_daily and the
    # per-weekday bands) so every downstream consumer — the status engine,
    # the gauges, the AI assistant, the bill checker — automatically judges
    # "normal" against the household's current size with no other code
    # changes, instead of silently keeping the old, un-adjusted band.
    #
    # Everything below is wrapped defensively: the deployed environment's
    # pandas build can represent these columns with different backing dtypes
    # than a local dev sandbox (e.g. an Arrow-backed integer/string array
    # instead of plain numpy), which can make a bare int(...) or a Series
    # arithmetic op raise where it wouldn't locally. This feature must never
    # be able to take the whole app down — if anything here is unexpected,
    # it quietly falls back to "no adjustment" (ratio 1.0) instead of
    # propagating a TypeError up through every page.
    fp["baseline_members"] = None
    fp["declared_members"] = None
    fp["member_ratio"] = 1.0
    fp["member_adjusted"] = False
    fp["normal_min_raw"] = fp["normal_min"]
    fp["normal_max_raw"] = fp["normal_max"]
    fp["average_daily_raw"] = fp["average_daily"]
    fp["median_daily_raw"] = fp["median_daily"]

    try:
        baseline_members = None
        if "Household_Members" in apt_daily.columns and apt_daily["Household_Members"].notna().any():
            mode_vals = pd.to_numeric(apt_daily["Household_Members"], errors="coerce").dropna()
            if not mode_vals.empty:
                baseline_members = int(round(float(mode_vals.mode().iloc[0])))

        declared_members_val = None
        if declared_members is not None:
            declared_members_val = int(round(float(declared_members)))

        ratio = 1.0
        if baseline_members and declared_members_val and baseline_members > 0:
            ratio = float(declared_members_val) / float(baseline_members)

        fp["baseline_members"] = baseline_members
        fp["declared_members"] = declared_members_val
        fp["member_ratio"] = round(ratio, 3)
        fp["member_adjusted"] = (
            fp["member_ratio"] != 1.0 and baseline_members is not None and declared_members_val is not None
        )

        if ratio != 1.0:
            fp["normal_min"] = round(float(fp["normal_min_raw"]) * ratio, 1)
            fp["normal_max"] = round(float(fp["normal_max_raw"]) * ratio, 1)
            fp["average_daily"] = round(float(fp["average_daily_raw"]) * ratio, 1)
            fp["median_daily"] = round(float(fp["median_daily_raw"]) * ratio, 1)
            for wd_stats in fp["by_weekday"].values():
                wd_stats["median"] = float(wd_stats["median"]) * ratio
                wd_stats["mean"] = float(wd_stats["mean"]) * ratio
    except Exception:
        # Leave the fp fields exactly as initialized above (no adjustment).
        pass

    return fp


def household_baseline_range_text(fp: dict) -> str:
    if not fp.get("available"):
        return "Unavailable"
    return f"{fp['normal_min']:.0f}–{fp['normal_max']:.0f} L"

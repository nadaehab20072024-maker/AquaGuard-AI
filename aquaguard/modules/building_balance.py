"""
AquaGuard AI — Building Water Balance
========================================
Unaccounted_Water = Main_Meter - Apartment_Total - Legitimate_External_Use

Classifies whether an imbalance is isolated, repeated, persistent or
increasing, and never claims physical confirmation of a leak — only
"Possible shared/external water loss".
"""

import pandas as pd


def analyze_building(building_df: pd.DataFrame, building_id) -> dict:
    result = {"available": False}
    if building_df is None or building_df.empty:
        return result

    bdf = building_df[building_df["Building_ID"] == building_id].sort_values("Date").copy()
    if bdf.empty:
        return result

    required = ["Main_Meter_Liters", "Apartment_Meters_Total_Liters"]
    if not all(c in bdf.columns for c in required):
        result["reason"] = "Required building-meter columns are unavailable."
        return result

    if "Unaccounted_Water_Liters" not in bdf.columns:
        ext = bdf["Legitimate_External_Use_Liters"] if "Legitimate_External_Use_Liters" in bdf.columns else 0
        bdf["Unaccounted_Water_Liters"] = bdf["Main_Meter_Liters"] - bdf["Apartment_Meters_Total_Liters"] - ext

    result["available"] = True
    result["table"] = bdf
    latest = bdf.iloc[-1]
    result["latest_date"] = latest["Date"]
    result["main_meter"] = float(latest["Main_Meter_Liters"])
    result["apartment_total"] = float(latest["Apartment_Meters_Total_Liters"])
    result["legitimate_external"] = float(latest.get("Legitimate_External_Use_Liters", 0) or 0)
    result["unaccounted"] = float(latest["Unaccounted_Water_Liters"])

    # meaningful imbalance threshold: relative to that building's own typical apartment total
    typical_total = bdf["Apartment_Meters_Total_Liters"].median()
    threshold = max(typical_total * 0.05, 50.0)  # >5% of typical daily total, floor 50L

    tail = bdf.tail(14).copy()
    tail["is_imbalanced"] = tail["Unaccounted_Water_Liters"] > threshold
    imbalanced_count = int(tail["is_imbalanced"].sum())
    result["imbalanced_days_14"] = imbalanced_count
    result["threshold"] = threshold

    # persistence: consecutive imbalanced days at the tail
    persistence = 0
    for v in reversed(tail["is_imbalanced"].tolist()):
        if v:
            persistence += 1
        else:
            break
    result["persistence_days"] = persistence

    # trend of unaccounted water (recent vs prior window)
    n = len(bdf)
    window = min(7, max(2, n // 3))
    if n >= window * 2:
        recent = bdf["Unaccounted_Water_Liters"].tail(window).mean()
        prior = bdf["Unaccounted_Water_Liters"].iloc[-2 * window:-window].mean()
        increasing = recent > prior * 1.15 if prior > 0 else recent > threshold
    else:
        increasing = False
    result["increasing"] = bool(increasing)

    is_imbalanced_today = result["unaccounted"] > threshold
    if not is_imbalanced_today and imbalanced_count == 0:
        result["classification"] = "Balanced"
        result["status"] = "Normal"
    elif persistence <= 1 and imbalanced_count <= 2:
        result["classification"] = "Isolated"
        result["status"] = "Monitoring"
    elif persistence >= 2 and imbalanced_count < 7:
        result["classification"] = "Repeated"
        result["status"] = "Warning"
    else:
        result["classification"] = "Persistent"
        result["status"] = "Warning" if not increasing else "Critical"

    result["alert_text"] = None
    if result["classification"] in ("Repeated", "Persistent"):
        result["alert_text"] = (
            "Possible external/shared-pipe water loss — the building main meter is recording more water "
            "than the apartment meters and known external usage can explain."
        )

    return result

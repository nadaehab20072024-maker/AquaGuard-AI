"""
AquaGuard AI — Tank & Pump Protection
========================================
Looks for signs of a tank float / overflow / pump-run problem using
multiple corroborating signals, never a single reading alone. Never
claims a component is definitely broken — only "possible" / "suspected".
"""

import pandas as pd
from modules.building_balance import analyze_building


def analyze_tank_pump(building_df: pd.DataFrame, building_id) -> dict:
    result = {"available": False}
    if building_df is None or building_df.empty:
        return result

    bdf = building_df[building_df["Building_ID"] == building_id].sort_values("Date").copy()
    if bdf.empty:
        return result

    has_tank = "Tank_Level_Percent" in bdf.columns and bdf["Tank_Level_Percent"].notna().any()
    has_pump = "Pump_State" in bdf.columns and bdf["Pump_State"].notna().any()

    result["available"] = True
    result["tank_available"] = has_tank
    result["pump_available"] = has_pump
    result["table"] = bdf

    latest = bdf.iloc[-1]
    result["latest_date"] = latest["Date"]
    result["tank_level"] = float(latest["Tank_Level_Percent"]) if has_tank and pd.notna(latest.get("Tank_Level_Percent")) else None
    result["pump_state"] = str(latest["Pump_State"]) if has_pump and pd.notna(latest.get("Pump_State")) else None

    balance = analyze_building(building_df, building_id)
    result["balance"] = balance

    status = "Normal"
    findings = []

    tank_near_full = has_tank and result["tank_level"] is not None and result["tank_level"] >= 95
    pump_continuous = has_pump and result["pump_state"] is not None and str(result["pump_state"]).strip().lower() == "continuous"
    unexplained_input = balance.get("available") and balance.get("unaccounted", 0) > balance.get("threshold", 1e9)

    if tank_near_full:
        findings.append(f"Tank level is near full ({result['tank_level']:.0f}%).")
    if pump_continuous:
        findings.append("Pump has been running continuously rather than cycling normally.")
    if unexplained_input:
        findings.append("Water entering the building is substantially higher than apartment consumption and known external use can explain.")

    if tank_near_full and pump_continuous and unexplained_input:
        status = "Possible tank/float issue"
    elif pump_continuous and unexplained_input:
        status = "Possible abnormal pump operation"
    elif tank_near_full or pump_continuous or unexplained_input:
        status = "Monitoring"
    else:
        status = "Normal"

    result["status"] = status
    result["findings"] = findings
    return result

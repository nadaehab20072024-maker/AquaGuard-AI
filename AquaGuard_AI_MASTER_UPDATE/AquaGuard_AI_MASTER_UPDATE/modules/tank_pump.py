"""
AquaGuard AI — Tank & Pump Protection
========================================
Looks for signs of a tank float / overflow / pump-run problem using
multiple corroborating signals, never a single reading alone. Never
claims a component is definitely broken — only "possible" / "suspected".

This module defers its headline classification to
modules.building_balance.classify_building_issue() so the Building page and
the Tank & Pump page never present two different, conflicting conclusions
about the same building — they both read from the same evidence-based
classification, just presented from a different angle.
"""

import pandas as pd
from modules.building_balance import analyze_building


def analyze_tank_pump(building_df: pd.DataFrame, building_id, lang: str = "en") -> dict:
    result = {"available": False}
    if building_df is None or building_df.empty:
        return result

    bdf = building_df[building_df["Building_ID"] == building_id].sort_values("Date").copy()
    if bdf.empty:
        return result

    has_tank = "Tank_Level_Percent" in bdf.columns and bdf["Tank_Level_Percent"].notna().any()
    has_pump = "Pump_State" in bdf.columns and bdf["Pump_State"].notna().any()
    has_float_valve = "Tank_Float_Valve_Status" in bdf.columns and bdf["Tank_Float_Valve_Status"].notna().any()
    has_motor = "Pump_Motor_Status" in bdf.columns and bdf["Pump_Motor_Status"].notna().any()

    result["available"] = True
    result["tank_available"] = has_tank
    result["pump_available"] = has_pump
    result["table"] = bdf

    latest = bdf.iloc[-1]
    result["latest_date"] = latest["Date"]
    result["tank_level"] = float(latest["Tank_Level_Percent"]) if has_tank and pd.notna(latest.get("Tank_Level_Percent")) else None
    result["expected_tank_level"] = (
        float(latest["Expected_Tank_Level_Percent"])
        if "Expected_Tank_Level_Percent" in bdf.columns and pd.notna(latest.get("Expected_Tank_Level_Percent"))
        else None
    )
    result["pump_state"] = str(latest["Pump_State"]) if has_pump and pd.notna(latest.get("Pump_State")) else None
    result["float_valve_status"] = (
        str(latest["Tank_Float_Valve_Status"]) if has_float_valve and pd.notna(latest.get("Tank_Float_Valve_Status")) else None
    )
    result["pump_motor_status"] = (
        str(latest["Pump_Motor_Status"]) if has_motor and pd.notna(latest.get("Pump_Motor_Status")) else None
    )
    result["pump_runtime_hours"] = (
        float(latest["Pump_Runtime_Hours"])
        if "Pump_Runtime_Hours" in bdf.columns and pd.notna(latest.get("Pump_Runtime_Hours"))
        else None
    )
    result["pump_motor_current"] = (
        float(latest["Pump_Motor_Current_A"])
        if "Pump_Motor_Current_A" in bdf.columns and pd.notna(latest.get("Pump_Motor_Current_A"))
        else None
    )

    balance = analyze_building(building_df, building_id, lang=lang)
    result["balance"] = balance

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
    findings.extend(balance.get("issue_evidence", []) if balance.get("issue_type") in ("tank_float_valve", "pump_motor_issue") else [])

    # Defer the headline classification to the shared, evidence-based
    # building-wide issue classifier so this page and the Building page agree.
    issue_type = balance.get("issue_type")
    if issue_type == "tank_float_valve":
        status = "Possible tank/float issue"
    elif issue_type == "pump_motor_issue":
        status = "Possible abnormal pump operation"
    elif tank_near_full or pump_continuous or unexplained_input:
        status = "Monitoring"
    else:
        status = "Normal"

    result["status"] = status
    result["findings"] = findings
    result["issue_type"] = issue_type
    result["issue_label"] = balance.get("issue_label")
    result["issue_what"] = balance.get("issue_what")
    result["issue_why"] = balance.get("issue_why")
    result["issue_action"] = balance.get("issue_action")
    return result

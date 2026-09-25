"""
AquaGuard AI — Data Loader
==========================
Loads the three Stage-1 simulated data files and normalizes their columns.

Design goal (per project spec):
    DATA SOURCE -> ANALYSIS ENGINE -> DASHBOARD/AI
The data source can change (Stage 1 simulated files -> Stage 2 real sensors)
without the analysis engine changing, as long as it keeps receiving frames
with these canonical columns.

This module never invents data. If a file or an expected column is missing,
it records that fact in AVAILABILITY / load warnings instead of crashing or
fabricating values.
"""

import os
import pandas as pd
import streamlit as st

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

TIMESERIES_FILE = os.path.join(DATA_DIR, "apartment_timeseries.csv")
PROFILES_FILE = os.path.join(DATA_DIR, "household_profiles.csv")
BUILDING_FILE = os.path.join(DATA_DIR, "building_meter_tank.csv")

# Canonical column name -> list of acceptable aliases (lowercased, no spaces/underscores)
TIMESERIES_ALIASES = {
    "Timestamp": ["timestamp", "datetime", "time"],
    "Apartment_ID": ["apartmentid", "apartment", "aptid"],
    "Building_ID": ["buildingid", "building"],
    "Date": ["date"],
    "Period": ["period", "timewindow", "timeofday"],
    "Household_Members": ["householdmembers", "members", "occupants"],
    "Water_Using_Appliances": ["waterusingappliances", "appliances", "devices", "waterusingdevices"],
    "Water_Consumption_Liters": ["waterconsumptionliters", "dailyconsumptionliters", "consumptionliters", "consumption"],
    "Night_Flow_2AM_5AM_Liters": ["nightflow2am5amliters", "nightflowliters", "nightflow"],
    "Idle_Time_Flow_Liters": ["idletimeflowliters", "idleflowliters", "idleflow"],
}

PROFILE_ALIASES = {
    "Apartment_ID": ["apartmentid", "apartment", "aptid"],
    "Building_ID": ["buildingid", "building"],
    "Household_Members": ["householdmembers", "members", "occupants"],
    "Water_Using_Appliances": ["waterusingappliances", "appliances", "devices"],
}

BUILDING_ALIASES = {
    "Date": ["date"],
    "Building_ID": ["buildingid", "building"],
    "Apartment_Meters_Total_Liters": ["apartmentmeterstotalliters", "apartmenttotal", "apartmenttotalliters"],
    "Legitimate_External_Use_Liters": ["legitimateexternaluseliters", "legitimateexternalwateruse", "externaluse"],
    "Unaccounted_Water_Liters": ["unaccountedwaterliters", "unaccountedwater"],
    "Main_Meter_Liters": ["mainmeterliters", "mainmeter"],
    "Tank_Level_Percent": ["tanklevelpercent", "tanklevel"],
    "Pump_State": ["pumpstate", "pumprun", "pumpruntime"],
}


def _norm(colname: str) -> str:
    return "".join(ch for ch in str(colname).lower() if ch.isalnum())


def _map_columns(df: pd.DataFrame, alias_map: dict) -> tuple[pd.DataFrame, list]:
    """Rename whatever columns exist in df to canonical names using alias_map.
    Returns (renamed_df, list_of_missing_canonical_columns)."""
    normalized_lookup = {_norm(c): c for c in df.columns}
    rename_dict = {}
    missing = []
    for canonical, aliases in alias_map.items():
        candidates = [_norm(canonical)] + aliases
        found = None
        for cand in candidates:
            if cand in normalized_lookup:
                found = normalized_lookup[cand]
                break
        if found is not None:
            rename_dict[found] = canonical
        else:
            missing.append(canonical)
    df = df.rename(columns=rename_dict)
    return df, missing


@st.cache_data(show_spinner=False)
def load_all_data():
    """Load and normalize all three data sources.

    Returns a dict with:
        timeseries (DataFrame or None)
        profiles (DataFrame or None)
        building (DataFrame or None)
        warnings (list of str) — human readable notes on missing files/columns
    """
    warnings = []
    result = {"timeseries": None, "profiles": None, "building": None, "warnings": warnings}

    # --- Time series (apartment-level) ---
    if os.path.exists(TIMESERIES_FILE):
        try:
            ts = pd.read_csv(TIMESERIES_FILE)
            ts, missing = _map_columns(ts, TIMESERIES_ALIASES)
            if missing:
                warnings.append(
                    f"Apartment time-series file is missing columns: {', '.join(missing)}. "
                    "Related features will be marked unavailable."
                )
            if "Date" in ts.columns:
                ts["Date"] = pd.to_datetime(ts["Date"], errors="coerce")
            if "Timestamp" in ts.columns:
                ts["Timestamp"] = pd.to_datetime(ts["Timestamp"], errors="coerce")
            for col in ["Apartment_ID", "Building_ID"]:
                if col in ts.columns:
                    ts[col] = pd.to_numeric(ts[col], errors="coerce").astype("Int64")
            for col in ["Water_Consumption_Liters", "Night_Flow_2AM_5AM_Liters", "Idle_Time_Flow_Liters"]:
                if col in ts.columns:
                    ts[col] = pd.to_numeric(ts[col], errors="coerce")
            if "Date" in ts.columns:
                ts["Weekday"] = ts["Date"].dt.day_name()
            result["timeseries"] = ts
        except Exception as e:
            warnings.append(f"Could not read apartment time-series file: {e}")
    else:
        warnings.append("Apartment time-series data file was not found. Household-level analysis is unavailable.")

    # --- Household profiles ---
    if os.path.exists(PROFILES_FILE):
        try:
            prof = pd.read_csv(PROFILES_FILE)
            prof, missing = _map_columns(prof, PROFILE_ALIASES)
            if missing:
                warnings.append(f"Household profile file is missing columns: {', '.join(missing)}.")
            for col in ["Apartment_ID", "Building_ID", "Household_Members", "Water_Using_Appliances"]:
                if col in prof.columns:
                    prof[col] = pd.to_numeric(prof[col], errors="coerce").astype("Int64")
            result["profiles"] = prof
        except Exception as e:
            warnings.append(f"Could not read household profile file: {e}")
    else:
        warnings.append("Household profile data file was not found. Household setup details are unavailable.")

    # --- Building meter / tank / pump ---
    if os.path.exists(BUILDING_FILE):
        try:
            bld = pd.read_csv(BUILDING_FILE)
            bld, missing = _map_columns(bld, BUILDING_ALIASES)
            if missing:
                warnings.append(
                    f"Building meter/tank file is missing columns: {', '.join(missing)}. "
                    "Building Water Balance / Tank & Pump features relying on them will be limited."
                )
            if "Date" in bld.columns:
                bld["Date"] = pd.to_datetime(bld["Date"], errors="coerce")
            if "Building_ID" in bld.columns:
                bld["Building_ID"] = pd.to_numeric(bld["Building_ID"], errors="coerce").astype("Int64")
            for col in [
                "Apartment_Meters_Total_Liters", "Legitimate_External_Use_Liters",
                "Unaccounted_Water_Liters", "Main_Meter_Liters", "Tank_Level_Percent",
            ]:
                if col in bld.columns:
                    bld[col] = pd.to_numeric(bld[col], errors="coerce")
            result["building"] = bld
        except Exception as e:
            warnings.append(f"Could not read building meter/tank file: {e}")
    else:
        warnings.append("Building meter/tank data file was not found. Building Water Balance and Tank & Pump pages are unavailable.")

    return result


def get_apartment_daily(ts: pd.DataFrame) -> pd.DataFrame:
    """Aggregate the 4x/day time-series into one row per apartment per day.
    Keeps daily total consumption, the night-flow reading and the idle-flow
    reading(s) for that day."""
    if ts is None or ts.empty:
        return pd.DataFrame()

    agg = {}
    if "Water_Consumption_Liters" in ts.columns:
        agg["Water_Consumption_Liters"] = "sum"
    if "Night_Flow_2AM_5AM_Liters" in ts.columns:
        agg["Night_Flow_2AM_5AM_Liters"] = "max"  # only populated on the Night row; max collapses NaNs
    if "Idle_Time_Flow_Liters" in ts.columns:
        agg["Idle_Time_Flow_Liters"] = "sum"

    group_cols = ["Apartment_ID", "Building_ID", "Date"]
    group_cols = [c for c in group_cols if c in ts.columns]
    daily = ts.groupby(group_cols, as_index=False).agg(agg)
    if "Date" in daily.columns:
        daily = daily.sort_values(["Apartment_ID", "Date"])
        daily["Weekday"] = daily["Date"].dt.day_name()
    return daily


def apartment_options(profiles: pd.DataFrame, ts: pd.DataFrame):
    """Return sorted list of (Building_ID, Apartment_ID) tuples available in the data."""
    src = profiles if profiles is not None and not profiles.empty else ts
    if src is None or src.empty:
        return []
    pairs = src[["Building_ID", "Apartment_ID"]].dropna().drop_duplicates()
    pairs = pairs.sort_values(["Building_ID", "Apartment_ID"])
    return list(pairs.itertuples(index=False, name=None))

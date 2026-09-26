"""
AquaGuard AI — Data Loader
==========================
Loads the simulated data files and normalizes their columns onto one
canonical schema, so the analysis engine never has to care which physical
CSV shape produced a row.

Design goal (per project spec):
    DATA SOURCE -> ANALYSIS ENGINE -> DASHBOARD/AI
The data source can change (Stage 1 files -> the FINAL demo dataset ->
eventually real sensors) without the analysis engine changing, as long as
it keeps receiving frames with these canonical columns.

Two dataset generations are supported side by side:
    - Stage 1 RAW files  (apartment_timeseries.csv, household_profiles.csv,
      building_meter_tank.csv) — numeric Building_ID/Apartment_ID, 4
      readings/day.
    - FINAL demo dataset (apartment_timeseries_v2.csv, household_profiles_v2.csv,
      building_meter_tank_v2.csv) — string IDs ("B101"/"A101"), one row/day,
      richer building-level signals (tank float valve, pump motor, external
      pipe loss) and ground-truth scenario labels for the Demo Center.

The FINAL dataset is preferred automatically when present; the Stage 1 files
are kept on disk untouched and are used as a fallback if the v2 files are
ever removed. Neither file is deleted or modified by this loader.

This module never invents data. If a file or an expected column is missing,
it records that fact in the returned "warnings" list instead of crashing or
fabricating values, and marks the dependent feature unavailable.
"""

import os
import pandas as pd
import streamlit as st

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")


def _first_existing(*names):
    for name in names:
        path = os.path.join(DATA_DIR, name)
        if os.path.exists(path):
            return path
    return os.path.join(DATA_DIR, names[0])


# Prefer the FINAL demo dataset (v2); fall back to the original Stage 1 files.
TIMESERIES_FILE = _first_existing("apartment_timeseries_v2.csv", "apartment_timeseries.csv")
PROFILES_FILE = _first_existing("household_profiles_v2.csv", "household_profiles.csv")
BUILDING_FILE = _first_existing("building_meter_tank_v2.csv", "building_meter_tank.csv")

# ---------------------------------------------------------------------------
# Canonical column name -> list of acceptable aliases (lowercased, no
# spaces/underscores). REQUIRED_* columns trigger a load warning when
# missing; OPTIONAL_* extras (present only in some dataset generations)
# never do — their absence just leaves the dependent feature unavailable.
# ---------------------------------------------------------------------------
TIMESERIES_ALIASES = {
    "Timestamp": ["timestamp", "datetime", "time"],
    "Apartment_ID": ["apartmentid", "apartment", "aptid"],
    "Building_ID": ["buildingid", "building"],
    "Date": ["date"],
    "Period": ["period", "timewindow", "timeofday"],
    "Household_Members": ["householdmembers", "members", "occupants", "initialhouseholdmembers"],
    "Water_Consumption_Liters": [
        "waterconsumptionliters", "dailyconsumptionliters", "consumptionliters", "consumption",
    ],
    "Night_Flow_2AM_5AM_Liters": ["nightflow2am5amliters", "nightflowliters", "nightflow"],
    "Idle_Time_Flow_Liters": ["idletimeflowliters", "idleflowliters", "idleflow"],
}

TIMESERIES_OPTIONAL_ALIASES = {
    # Present only in the FINAL demo dataset — ground truth used solely by
    # the Demo Center to narrate a scenario; never used to short-circuit the
    # real analysis engine that a normal user's dashboard runs on.
    "Water_Using_Appliances": ["waterusingappliances", "appliances", "devices", "waterusingdevices"],
    "Household_Scenario": ["householdscenario"],
    "Building_Wide_Case": ["buildingwidecase"],
    "Smart_Form_Required": ["smartformrequired"],
    "Smart_Form_User_Response": ["smartformuserresponse"],
    "Expected_Status": ["expectedstatus"],
    "Leak_Type": ["leaktype"],
}

PROFILE_ALIASES = {
    "Apartment_ID": ["apartmentid", "apartment", "aptid"],
    "Building_ID": ["buildingid", "building"],
    "Household_Members": ["householdmembers", "members", "occupants", "initialhouseholdmembers"],
}

PROFILE_OPTIONAL_ALIASES = {
    "Water_Using_Appliances": ["waterusingappliances", "appliances", "devices"],
    "Household_Scenario": ["householdscenario"],
    "Building_Wide_Case": ["buildingwidecase"],
    "Baseline_Daily_Consumption_Liters": ["baselinedailyconsumptionliters"],
    "Learned_Idle_Flow_Liters": ["learnedidleflowliters"],
    "Fingerprint_Status": ["fingerprintstatus"],
}

BUILDING_ALIASES = {
    "Date": ["date"],
    "Building_ID": ["buildingid", "building"],
    "Apartment_Meters_Total_Liters": [
        "apartmentmeterstotalliters", "apartmenttotal", "apartmenttotalliters",
        "totalapartmentconsumptionliters",
    ],
    "Legitimate_External_Use_Liters": [
        "legitimateexternaluseliters", "legitimateexternalwateruse", "externaluse",
        "legitimateexternalwateruseliters",
    ],
    "Unaccounted_Water_Liters": ["unaccountedwaterliters", "unaccountedwater"],
    "Main_Meter_Liters": ["mainmeterliters", "mainmeter", "mainmeterwaterliters"],
    "Tank_Level_Percent": ["tanklevelpercent", "tanklevel"],
}

BUILDING_OPTIONAL_ALIASES = {
    # Only in the FINAL demo dataset — power the differentiated building-wide
    # diagnosis (external pipe / tank float / pump-motor / generic loss).
    "Pump_State": ["pumpstate", "pumprun"],
    "Building_Wide_Case": ["buildingwidecase"],
    "Building_Status": ["buildingstatus"],
    "Expected_Tank_Level_Percent": ["expectedtanklevelpercent"],
    "Pump_Runtime_Hours": ["pumpruntimehours", "pumpruntime"],
    "Pump_Motor_Current_A": ["pumpmotorcurrenta", "pumpmotorcurrent"],
    "Pump_Motor_Status": ["pumpmotorstatus"],
    "Tank_Float_Valve_Status": ["tankfloatvalvestatus"],
    "External_Supply_Pipe_Loss_Liters": ["externalsupplypipelossliters"],
    "Tank_Overflow_Loss_Liters": ["tankoverflowlossliters"],
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


def _clean_id(series: pd.Series) -> pd.Series:
    """IDs are treated as plain strings everywhere (both "101" and "A101"
    style datasets), never coerced to numbers — coercing "A101" to numeric
    would silently turn every row into NaN and empty the dashboard."""
    return series.astype(str).str.strip()


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
            ts, _ = _map_columns(ts, TIMESERIES_OPTIONAL_ALIASES)
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
                    ts[col] = _clean_id(ts[col])
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
            prof, _ = _map_columns(prof, PROFILE_OPTIONAL_ALIASES)
            if missing:
                warnings.append(f"Household profile file is missing columns: {', '.join(missing)}.")
            for col in ["Apartment_ID", "Building_ID"]:
                if col in prof.columns:
                    prof[col] = _clean_id(prof[col])
            for col in ["Household_Members", "Water_Using_Appliances"]:
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
            bld, _ = _map_columns(bld, BUILDING_OPTIONAL_ALIASES)
            if missing:
                warnings.append(
                    f"Building meter/tank file is missing columns: {', '.join(missing)}. "
                    "Building Water Balance / Tank & Pump features relying on them will be limited."
                )
            if "Date" in bld.columns:
                bld["Date"] = pd.to_datetime(bld["Date"], errors="coerce")
            if "Building_ID" in bld.columns:
                bld["Building_ID"] = _clean_id(bld["Building_ID"])
            for col in [
                "Apartment_Meters_Total_Liters", "Legitimate_External_Use_Liters",
                "Unaccounted_Water_Liters", "Main_Meter_Liters", "Tank_Level_Percent",
                "Expected_Tank_Level_Percent", "Pump_Runtime_Hours", "Pump_Motor_Current_A",
                "External_Supply_Pipe_Loss_Liters", "Tank_Overflow_Loss_Liters",
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
    """Aggregate the time-series into one row per apartment per day. Handles
    both the Stage 1 shape (4 readings/day, needs summing) and the FINAL
    demo dataset shape (already one row/day — summing is a no-op)."""
    if ts is None or ts.empty:
        return pd.DataFrame()

    agg = {}
    if "Water_Consumption_Liters" in ts.columns:
        agg["Water_Consumption_Liters"] = "sum"
    if "Night_Flow_2AM_5AM_Liters" in ts.columns:
        agg["Night_Flow_2AM_5AM_Liters"] = "max"  # only populated on the Night row; max collapses NaNs
    if "Idle_Time_Flow_Liters" in ts.columns:
        agg["Idle_Time_Flow_Liters"] = "sum"

    # Carry ground-truth demo labels through (first value per day is fine —
    # they don't vary within a single apartment-day).
    for extra in ("Household_Scenario", "Building_Wide_Case", "Smart_Form_Required",
                  "Smart_Form_User_Response", "Expected_Status", "Leak_Type"):
        if extra in ts.columns:
            agg[extra] = "first"

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

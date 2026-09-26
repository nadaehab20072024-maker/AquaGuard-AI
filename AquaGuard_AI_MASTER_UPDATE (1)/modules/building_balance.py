"""
AquaGuard AI — Building Water Balance & Building-Wide Issue Differentiation
=============================================================================
Unaccounted_Water = Main_Meter - Apartment_Total - Legitimate_External_Use

Classifies whether an imbalance is isolated, repeated, persistent or
increasing, and never claims physical confirmation of a fault — only
"possible" / "suspected".

Building-wide problems are NOT all the same thing, and each needs its own
evidence and its own recommended action:

    1. External Supply Pipe Leak  — the loss happens BEFORE the apartment
       meters, so apartment consumption looks normal while the main meter
       reads high. Evidence: External_Supply_Pipe_Loss_Liters (when the
       dataset provides it) plus a persistent Main-vs-Apartment gap.
    2. Tank Float Valve / Overflow — the tank overfills or a float valve
       sticks. Evidence: Tank_Float_Valve_Status, Tank_Overflow_Loss_Liters,
       and Tank_Level_Percent drifting away from Expected_Tank_Level_Percent.
    3. Pump / Motor Issue — abnormal pump behavior. Evidence:
       Pump_Motor_Status, Pump_Runtime_Hours and Pump_Motor_Current_A
       deviating from that building's own typical operating range.
    4. Building-Wide Water Loss (generic) — unaccounted water is
       persistently high but none of the above specific signals are present
       (or the dataset doesn't provide them) — a general investigation is
       recommended rather than pointing at one component.

These are building-level findings and are always kept separate from any
single apartment's own status — a building can have a building-wide issue
while every individual household inside it (or just one of them) is
independently Normal, Monitoring, Warning or Critical.
"""

import pandas as pd

ISSUE_ORDER = ["external_pipe_leak", "tank_float_valve", "pump_motor_issue", "building_wide_loss"]

_ISSUE_TEXT = {
    "external_pipe_leak": {
        "en": {
            "label": "Possible External Supply Pipe Leak",
            "what": "The building's main meter is recording noticeably more water than all apartment meters plus known external use can explain.",
            "why": "This gap occurs BEFORE water reaches any apartment meter, so it cannot be attributed to a single household — the loss is most likely in the shared supply line feeding the building.",
            "action": "Have the building's external supply line (before the apartment meters) inspected for leaks.",
        },
        "ar": {
            "label": "احتمال تسرب في خط الإمداد الخارجي",
            "what": "يسجل العداد الرئيسي للمبنى كمية مياه أكبر بشكل ملحوظ مما يمكن تفسيره بمجموع عدادات الشقق والاستخدام الخارجي المعروف.",
            "why": "تحدث هذه الفجوة قبل وصول المياه إلى أي عداد شقة، لذا لا يمكن أن تُنسب إلى منزل واحد — الفقد على الأرجح في خط الإمداد المشترك الذي يغذي المبنى.",
            "action": "يوصى بفحص خط الإمداد الخارجي للمبنى (قبل عدادات الشقق) بحثًا عن تسربات.",
        },
    },
    "tank_float_valve": {
        "en": {
            "label": "Possible Tank Float Valve / Overflow Issue",
            "what": "The rooftop tank's level and overflow behavior don't match what's expected for this building.",
            "why": "A stuck or worn float valve can let the tank keep filling past its intended level, wasting water through the overflow path.",
            "action": "Have the tank's float valve and overflow path inspected and serviced.",
        },
        "ar": {
            "label": "احتمال عطل في صمام عوامة الخزان / فيضان",
            "what": "مستوى خزان السطح وسلوك الفيضان لا يطابقان ما هو متوقع لهذا المبنى.",
            "why": "قد يسمح صمام عوامة عالق أو متآكل باستمرار امتلاء الخزان بعد مستواه المقصود، مما يهدر المياه عبر مسار الفيضان.",
            "action": "يوصى بفحص وصيانة صمام عوامة الخزان ومسار الفيضان.",
        },
    },
    "pump_motor_issue": {
        "en": {
            "label": "Possible Pump / Motor Issue",
            "what": "The pump's runtime and/or motor current look abnormal compared with this building's own typical operating pattern.",
            "why": "A pump cycling far more (or drawing power far outside its normal range) than usual can point to a developing mechanical or electrical issue.",
            "action": "Have the tank pump and its motor inspected — this does not necessarily mean the pump has failed, only that its behavior looks unusual.",
        },
        "ar": {
            "label": "احتمال مشكلة في المضخة / المحرك",
            "what": "ساعات تشغيل المضخة و/أو تيار المحرك تبدو غير طبيعية مقارنة بنمط التشغيل المعتاد لهذا المبنى.",
            "why": "قد تشير مضخة تعمل بشكل أكثر بكثير من المعتاد (أو تسحب تيارًا خارج نطاقها الطبيعي) إلى مشكلة ميكانيكية أو كهربائية ناشئة.",
            "action": "يوصى بفحص مضخة الخزان ومحركها — هذا لا يعني بالضرورة أن المضخة تعطلت، بل أن سلوكها يبدو غير معتاد.",
        },
    },
    "building_wide_loss": {
        "en": {
            "label": "Building-Wide Water Loss",
            "what": "Unaccounted water at the building level has been persistently high, without one specific cause standing out yet.",
            "why": "The gap between the main meter and apartment meters plus known external use has stayed above this building's own normal range for multiple days.",
            "action": "Ask the building's maintenance team to investigate shared infrastructure (supply lines, tank, pump, and common-area usage) as a whole.",
        },
        "ar": {
            "label": "فقدان مياه على مستوى المبنى",
            "what": "المياه غير المحتسبة على مستوى المبنى مرتفعة باستمرار، دون وجود سبب واحد واضح حتى الآن.",
            "why": "ظلت الفجوة بين العداد الرئيسي وعدادات الشقق والاستخدام الخارجي المعروف أعلى من النطاق الطبيعي لهذا المبنى لعدة أيام.",
            "action": "يُنصح بأن يقوم فريق صيانة المبنى بالتحقيق في البنية التحتية المشتركة (خطوط الإمداد، الخزان، المضخة، واستخدام المناطق المشتركة) ككل.",
        },
    },
}


def _normal(val) -> bool:
    return str(val).strip().lower() in ("normal", "ok", "none", "nan", "")


def classify_building_issue(bdf: pd.DataFrame, unaccounted_is_meaningful: bool) -> dict:
    """Look at the building's own operational signals (not any ground-truth
    label) and decide which — if any — of the four differentiated
    building-wide issues the evidence points to. Returns
    {"issue_type": str|None, "evidence": [str, ...]}."""
    tail = bdf.tail(14)
    if tail.empty:
        return {"issue_type": None, "evidence": []}

    # ---- 1. External supply pipe leak: loss occurs before apartment meters ----
    if "External_Supply_Pipe_Loss_Liters" in bdf.columns:
        recent_pipe_loss = tail["External_Supply_Pipe_Loss_Liters"].dropna()
        if not recent_pipe_loss.empty and recent_pipe_loss.mean() > 5.0 and (recent_pipe_loss > 0).sum() >= 3:
            return {
                "issue_type": "external_pipe_leak",
                "evidence": [
                    f"Estimated external supply-line loss has averaged about {recent_pipe_loss.mean():.0f} L/day "
                    f"over the last {len(recent_pipe_loss)} days, occurring before the apartment meters."
                ],
            }

    # ---- 2. Tank float valve / overflow ----
    float_bad = False
    evidence2 = []
    if "Tank_Float_Valve_Status" in bdf.columns:
        latest_float = tail["Tank_Float_Valve_Status"].dropna()
        if not latest_float.empty and not _normal(latest_float.iloc[-1]):
            float_bad = True
            evidence2.append(f"Tank float valve status has been reported as '{latest_float.iloc[-1]}'.")
    if "Tank_Overflow_Loss_Liters" in bdf.columns:
        overflow = tail["Tank_Overflow_Loss_Liters"].dropna()
        if not overflow.empty and overflow.mean() > 5.0 and (overflow > 0).sum() >= 3:
            float_bad = True
            evidence2.append(f"Tank overflow loss has averaged about {overflow.mean():.0f} L/day over the last {len(overflow)} days.")
    if float_bad and "Tank_Level_Percent" in bdf.columns and "Expected_Tank_Level_Percent" in bdf.columns:
        # only used as CORROBORATING evidence once a float-valve/overflow signal already fired —
        # a tank-level gap alone can also be caused by a pump issue (see below), so it must not
        # be enough on its own to point at the float valve.
        gap = (tail["Tank_Level_Percent"] - tail["Expected_Tank_Level_Percent"]).dropna()
        if not gap.empty and gap.abs().mean() >= 8:
            evidence2.append(
                f"Tank level has differed from its expected level by about {gap.abs().mean():.0f} percentage points on average."
            )
    if float_bad:
        return {"issue_type": "tank_float_valve", "evidence": evidence2}

    # ---- 3. Pump / motor issue ----
    pump_bad = False
    evidence3 = []
    if "Pump_Motor_Status" in bdf.columns:
        latest_pump = tail["Pump_Motor_Status"].dropna()
        if not latest_pump.empty and not _normal(latest_pump.iloc[-1]):
            pump_bad = True
            evidence3.append(f"Pump motor status has been reported as '{latest_pump.iloc[-1]}'.")
    if "Pump_Runtime_Hours" in bdf.columns and bdf["Pump_Runtime_Hours"].notna().sum() >= 7:
        overall_median = bdf["Pump_Runtime_Hours"].median()
        recent_runtime = tail["Pump_Runtime_Hours"].dropna()
        if not recent_runtime.empty and overall_median and recent_runtime.mean() > overall_median * 1.3:
            pump_bad = True
            evidence3.append(
                f"Pump runtime has averaged about {recent_runtime.mean():.1f} hrs/day recently, "
                f"versus a typical {overall_median:.1f} hrs/day for this building."
            )
    if "Pump_Motor_Current_A" in bdf.columns and bdf["Pump_Motor_Current_A"].notna().sum() >= 7:
        overall_median_c = bdf["Pump_Motor_Current_A"].median()
        recent_current = tail["Pump_Motor_Current_A"].dropna()
        if not recent_current.empty and overall_median_c:
            dev = abs(recent_current.mean() - overall_median_c) / overall_median_c
            if dev >= 0.25:
                pump_bad = True
                evidence3.append(
                    f"Pump motor current has averaged about {recent_current.mean():.2f} A recently, "
                    f"versus a typical {overall_median_c:.2f} A for this building's pump."
                )
    if pump_bad:
        return {"issue_type": "pump_motor_issue", "evidence": evidence3}

    # ---- 4. Generic building-wide water loss (fallback) ----
    if unaccounted_is_meaningful:
        return {
            "issue_type": "building_wide_loss",
            "evidence": ["Unaccounted water at the building level has stayed above this building's normal range."],
        }

    return {"issue_type": None, "evidence": []}


def analyze_building(building_df: pd.DataFrame, building_id, lang: str = "en") -> dict:
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

    # ---- Differentiated building-wide issue (what/why/action) ----
    meaningful = result["classification"] in ("Repeated", "Persistent")
    issue = classify_building_issue(bdf, meaningful)
    result["issue_type"] = issue["issue_type"]
    result["issue_evidence"] = issue["evidence"]
    if issue["issue_type"]:
        text = _ISSUE_TEXT[issue["issue_type"]].get(lang, _ISSUE_TEXT[issue["issue_type"]]["en"])
        result["issue_label"] = text["label"]
        result["issue_what"] = text["what"]
        result["issue_why"] = text["why"]
        result["issue_action"] = text["action"]
    else:
        result["issue_label"] = None
        result["issue_what"] = None
        result["issue_why"] = None
        result["issue_action"] = None

    return result

"""
AquaGuard AI — Water Bill Photo/PDF Analysis
===============================================
Lets a household attach a photo or PDF of their actual water bill in the
Assistant chat, and gives a plain-language read on whether the billed
consumption looks in line with their own learned normal pattern.

This is a best-effort text extraction (OCR for images via pytesseract,
direct text extraction for PDFs via pdfplumber) followed by a simple,
transparent regex parse for a consumption figure and, if present, an amount.
It never invents a number: if nothing readable is found, it says so plainly
and lets the household type the figure in themselves instead of guessing.

Verdict logic reuses the same Consumption Fingerprint that powers the rest of
the app, so the household gets one consistent story instead of a second,
disconnected "bill checker".
"""

import io
import re

import streamlit as st

try:
    import pytesseract
    from PIL import Image
    _OCR_AVAILABLE = True
except Exception:  # pragma: no cover
    _OCR_AVAILABLE = False

try:
    import pdfplumber
    _PDF_AVAILABLE = True
except Exception:  # pragma: no cover
    _PDF_AVAILABLE = False


def extract_text(uploaded_file) -> str:
    """Best-effort text extraction from an uploaded image or PDF. Returns an
    empty string (never raises) if nothing could be read."""
    name = (uploaded_file.name or "").lower()
    data = uploaded_file.getvalue()

    try:
        if name.endswith(".pdf") and _PDF_AVAILABLE:
            text_parts = []
            with pdfplumber.open(io.BytesIO(data)) as pdf:
                for page in pdf.pages[:5]:  # a bill is short — cap for safety
                    page_text = page.extract_text() or ""
                    text_parts.append(page_text)
            return "\n".join(text_parts).strip()

        if _OCR_AVAILABLE:
            image = Image.open(io.BytesIO(data)).convert("RGB")
            return pytesseract.image_to_string(image).strip()
    except Exception:
        return ""
    return ""


# ---------------------------------------------------------------------------
# Parsing — look for a consumption figure (m3/liters) and, optionally, an
# amount, near recognizable bilingual keywords. Deliberately conservative:
# a false "no reading found" is far safer than inventing a number.
# ---------------------------------------------------------------------------
_M3_KEYWORDS = r"(?:m\s*3|m³|cubic\s*meters?|متر\s*مكعب|م3|م³)"
_LITER_KEYWORDS = r"(?:liters?|litres?|لتر)"
_CONSUMPTION_CONTEXT = r"(?:consumption|usage|units?\s*used|استهلاك|الاستهلاك|كمية)"
_AMOUNT_CONTEXT = r"(?:total|amount\s*due|amount|bill\s*total|المبلغ|الإجمالي|إجمالي|المستحق)"
_CURRENCY = r"(?:omr|r\.?o\.?|ر\.ع|ريال|aed|sar|usd|\$)"

_NUM = r"(\d+(?:,\d{3})*(?:\.\d+)?)"


def _to_float(num_str: str) -> float:
    cleaned = num_str.replace(",", "")
    try:
        return float(cleaned)
    except ValueError:
        return None


def parse_bill_text(text: str) -> dict:
    """Return {'consumption_liters': float|None, 'amount': float|None,
    'currency': str|None, 'matched_snippet': str|None}."""
    result = {"consumption_liters": None, "amount": None, "currency": None, "matched_snippet": None}
    if not text:
        return result

    low = text.lower()

    # 1) A number immediately followed by an m3 unit — most reliable signal.
    m = re.search(_NUM + r"\s*" + _M3_KEYWORDS, low, re.IGNORECASE)
    if m:
        val = _to_float(m.group(1))
        if val is not None:
            result["consumption_liters"] = val * 1000.0
            result["matched_snippet"] = m.group(0)

    # 2) A number near a "consumption" keyword followed (within ~15 chars) by m3.
    if result["consumption_liters"] is None:
        m = re.search(_CONSUMPTION_CONTEXT + r".{0,20}?" + _NUM + r".{0,10}?" + _M3_KEYWORDS, low, re.IGNORECASE)
        if m:
            nums = re.findall(_NUM, m.group(0))
            if nums:
                val = _to_float(nums[-1])
                if val is not None:
                    result["consumption_liters"] = val * 1000.0
                    result["matched_snippet"] = m.group(0)

    # 3) A number directly followed by "liters".
    if result["consumption_liters"] is None:
        m = re.search(_NUM + r"\s*" + _LITER_KEYWORDS, low, re.IGNORECASE)
        if m:
            val = _to_float(m.group(1))
            if val is not None:
                result["consumption_liters"] = val
                result["matched_snippet"] = m.group(0)

    # 4) Amount due, with an optional currency nearby.
    m = re.search(_AMOUNT_CONTEXT + r".{0,20}?" + _NUM, low, re.IGNORECASE)
    if m:
        nums = re.findall(_NUM, m.group(0))
        if nums:
            val = _to_float(nums[-1])
            if val is not None:
                result["amount"] = val
                cur = re.search(_CURRENCY, low)
                if cur:
                    result["currency"] = cur.group(0).upper()

    return result


def analyze_bill(consumption_liters: float, fp: dict, lang: str = "en", billing_days: int = 30) -> dict:
    """Compare a billed consumption figure (already in liters, for the whole
    billing period) against this household's own learned fingerprint,
    scaled to the same period. Never claims exact accuracy — a bill photo
    is a rough estimate compared with a rule the household's own history."""
    ar = lang == "ar"
    result = {"available": False}
    if not fp.get("available"):
        result["message"] = (
            "لا توجد بيانات كافية بعد لبناء نمط استهلاك هذا المنزل، لذا لا أقدر أقارن الفاتورة بشيء بعد."
            if ar else
            "There isn't enough history yet to build this household's consumption pattern, so I can't compare the bill to anything yet."
        )
        return result

    expected_avg = fp["average_daily"] * billing_days
    expected_min = fp["normal_min"] * billing_days
    expected_max = fp["normal_max"] * billing_days

    result["available"] = True
    result["expected_min"] = expected_min
    result["expected_max"] = expected_max
    result["billed"] = consumption_liters

    if consumption_liters <= expected_max:
        verdict = "in_range"
        headline = (
            f"**الفاتورة تبدو ضمن النمط الطبيعي لهذا المنزل** — الاستهلاك المفوتَر حوالي {consumption_liters:.0f} لتر، "
            f"مقابل نطاق متوقع تقريبي {expected_min:.0f}–{expected_max:.0f} لتر لنفس المدة."
            if ar else
            f"**This bill looks within this household's normal pattern** — billed usage is about "
            f"{consumption_liters:.0f} L, against an expected range of roughly {expected_min:.0f}–{expected_max:.0f} L "
            f"for the same period."
        )
        note = (
            "هذا لا يستبعد وجود تسرب صغير جدًا، لكن لا يوجد مؤشر قوي من رقم الفاتورة وحده."
            if ar else
            "This doesn't rule out a very small leak, but there's no strong signal from the bill number alone."
        )
    else:
        over_pct = ((consumption_liters - expected_max) / expected_max) * 100 if expected_max else 0
        verdict = "above_range"
        headline = (
            f"**الفاتورة أعلى من النمط الطبيعي لهذا المنزل بحوالي {over_pct:.0f}%** — الاستهلاك المفوتَر حوالي "
            f"{consumption_liters:.0f} لتر، مقابل نطاق متوقع تقريبي {expected_min:.0f}–{expected_max:.0f} لتر لنفس المدة."
            if ar else
            f"**This bill is about {over_pct:.0f}% above this household's normal pattern** — billed usage is about "
            f"{consumption_liters:.0f} L, against an expected range of roughly {expected_min:.0f}–{expected_max:.0f} L "
            f"for the same period."
        )
        note = (
            "يُنصح بمراجعة صفحة 'التنبيهات' بالتطبيق لمعرفة إذا كان هناك دليل تدفق ليلي يدعم احتمال وجود تسرب."
            if ar else
            "It's worth checking the app's Alerts page to see if there's night-flow evidence supporting a possible leak."
        )

    result["verdict"] = verdict
    result["headline"] = headline
    result["note"] = note
    return result

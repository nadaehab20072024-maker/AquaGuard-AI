"""
AquaGuard AI — Smart Verification Form
=========================================
When AquaGuard sees unusual consumption but can't yet tell if it's legitimate,
it asks a short multiple-choice question instead of demanding raw numbers
from the user. Explanations are stored in Streamlit session state, keyed by
(apartment, date), so they persist for the rest of the session and feed back
into the status engine.
"""

import pandas as pd
import streamlit as st

EXPLANATION_OPTIONS = [
    "Guests or visitors",
    "Heavy cleaning",
    "Eid / holiday cleaning",
    "Unusual laundry",
    "Extra cooking or dishwashing",
    "Majlis / household event",
    "Other",
    "No known explanation",
]

LEGITIMATE_OPTIONS = set(EXPLANATION_OPTIONS) - {"No known explanation"}


def _store():
    if "smart_form_explanations" not in st.session_state:
        st.session_state["smart_form_explanations"] = {}
    return st.session_state["smart_form_explanations"]


def record_explanation(apartment_id, date, explanation: str):
    store = _store()
    store[(apartment_id, pd.Timestamp(date))] = explanation


def get_explained_dates(apartment_id) -> set:
    """Dates for this apartment explained with a *legitimate* reason
    (used to relax the status engine)."""
    store = _store()
    return {
        d for (apt, d), reason in store.items()
        if apt == apartment_id and reason in LEGITIMATE_OPTIONS
    }


def get_all_explanations(apartment_id) -> dict:
    store = _store()
    return {d: reason for (apt, d), reason in store.items() if apt == apartment_id}


def count_recurring_pattern(apartment_id, reason: str) -> int:
    store = _store()
    return sum(1 for (apt, d), r in store.items() if apt == apartment_id and r == reason)

"""
api.py — openFDA Device Recall API client
Handles all requests, pagination, and caching for the /device/recall endpoint.

KEY FIELD NOTES (from openFDA /device/recall searchable fields):
  - Classification is stored as "classification" → "Class I", "Class II", "Class III"
    There is NO numeric "device_class" field on this endpoint.
  - Date field is "event_date_initiated" → ISO string "YYYY-MM-DD"
  - No "voluntary_mandated" field on /device/recall (that's on /device/enforcement)
  - Available: recall_status, recalling_firm, reason_for_recall, product_description,
               root_cause_description, distribution_pattern, state, country,
               k_numbers, pma_numbers, product_code, res_event_number
"""

import time
import requests
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta

BASE_URL = "https://api.fda.gov/device/recall.json"

# The "classification" field in this endpoint uses these exact string values
CLASSIFICATION_VALUES = ["Class I", "Class II", "Class III"]

_PAGE_LIMIT = 100   # FDA hard cap per request


def _build_search_query(
    classifications: list[str] | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    keyword: str | None = None,
) -> str:
    """
    Build an openFDA Lucene-style query string.

    The 'classification' field holds plain-text values like 'Class I'.
    Dates use the 'event_date_initiated' field in YYYY-MM-DD format.
    """
    parts = []

    if classifications:
        # Use exact phrase matching for multi-word values like "Class I"
        class_parts = [f'classification:"{c}"' for c in classifications]
        parts.append("(" + " OR ".join(class_parts) + ")")

    if start_date and end_date:
        parts.append(f"event_date_initiated:[{start_date} TO {end_date}]")
    elif start_date:
        parts.append(f"event_date_initiated:[{start_date} TO *]")
    elif end_date:
        parts.append(f"event_date_initiated:[* TO {end_date}]")

    if keyword and keyword.strip():
        safe_kw = keyword.strip().replace('"', "")
        parts.append(f'reason_for_recall:"{safe_kw}"')

    return " AND ".join(parts) if parts else ""


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_recalls(
    classifications: tuple[str, ...] | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    keyword: str | None = None,
    max_records: int = 1000,
) -> pd.DataFrame:
    """
    Fetch device recall records from openFDA with pagination.

    Parameters
    ----------
    classifications : tuple of str, optional
        e.g. ("Class I", "Class II") — must match openFDA field values exactly
    start_date : str, optional
        "YYYY-MM-DD"
    end_date : str, optional
        "YYYY-MM-DD"
    keyword : str, optional
        Searched in reason_for_recall field
    max_records : int
        Total records ceiling (openFDA skip ceiling is 25 000)

    Returns
    -------
    pd.DataFrame  — empty if no results
    """
    query = _build_search_query(
        list(classifications) if classifications else None,
        start_date,
        end_date,
        keyword,
    )

    records: list[dict] = []
    skip = 0

    while len(records) < max_records:
        batch_size = min(_PAGE_LIMIT, max_records - len(records))
        params: dict = {"limit": batch_size, "skip": skip}
        if query:
            params["search"] = query

        try:
            resp = requests.get(BASE_URL, params=params, timeout=15)
            if resp.status_code == 404:
                break  # exhausted results
            resp.raise_for_status()
            data = resp.json()
        except requests.exceptions.HTTPError as e:
            raise RuntimeError(f"openFDA API error ({resp.status_code}): {e}") from e
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Network error: {e}") from e

        batch = data.get("results", [])
        if not batch:
            break

        records.extend(batch)

        total_available = data.get("meta", {}).get("results", {}).get("total", 0)
        fetched_so_far = skip + len(batch)
        if fetched_so_far >= total_available or fetched_so_far >= max_records:
            break

        skip += len(batch)
        time.sleep(0.05)  # be polite to the public API

    if not records:
        return pd.DataFrame()

    return _parse_records(records)


def _parse_records(records: list[dict]) -> pd.DataFrame:
    """
    Flatten raw API JSON into a clean, analysis-ready DataFrame.

    Field mapping (actual API → our column name):
      classification         → classification   ("Class I" / "Class II" / "Class III")
      event_date_initiated   → initiated_date   (datetime)
      recalling_firm         → recalling_firm
      reason_for_recall      → reason_for_recall
      product_description    → product_description
      root_cause_description → root_cause
      recall_status          → recall_status
      state                  → state
      product_code           → product_code
      openfda.device_name[0] → device_name      (if available)
    """
    rows = []
    for r in records:
        raw_date = r.get("event_date_initiated", "")
        initiated = pd.to_datetime(raw_date, errors="coerce")  # handles YYYY-MM-DD

        classification = r.get("classification", "").strip()

        # openfda sub-object has harmonized device info when available
        openfda = r.get("openfda", {}) or {}
        device_names = openfda.get("device_name", [])
        device_name = device_names[0] if device_names else ""

        medical_specialty = openfda.get("medical_specialty_description", [])
        specialty = medical_specialty[0] if medical_specialty else ""

        rows.append({
            "recall_number":      r.get("res_event_number", ""),
            "classification":     classification,
            "recall_status":      r.get("recall_status", "").strip(),
            "recalling_firm":     r.get("recalling_firm", "").strip(),
            "product_description": r.get("product_description", "").strip(),
            "reason_for_recall":  r.get("reason_for_recall", "").strip(),
            "root_cause":         r.get("root_cause_description", "").strip(),
            "action":             r.get("action", "").strip(),
            "distribution":       r.get("distribution_pattern", "").strip(),
            "product_quantity":   r.get("product_quantity", "").strip(),
            "product_code":       r.get("product_code", "").strip(),
            "device_name":        device_name,
            "specialty":          specialty,
            "state":              r.get("state", "").strip(),
            "country":            r.get("country", "").strip(),
            "initiated_date":     initiated,
        })

    df = pd.DataFrame(rows)

    # Derived time columns
    df["year"] = df["initiated_date"].dt.year
    df["year_month"] = (
        df["initiated_date"]
        .dt.to_period("M")
        .dt.to_timestamp()
    )

    # Normalise classification to canonical values; mark unknowns clearly
    valid = set(CLASSIFICATION_VALUES)
    df["classification"] = df["classification"].where(
        df["classification"].isin(valid), other="Unknown"
    )

    return df


def get_date_range_default() -> tuple[str, str]:
    """Sensible default: 5 years ago → today."""
    end = datetime.today()
    start = end - timedelta(days=365 * 5)
    return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")

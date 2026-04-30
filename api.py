"""
api.py — openFDA Device Recall API client

KEY FINDING: The 'classification' field (Class I/II/III) is NOT reliably
searchable via the openFDA query string — many records lack it entirely,
so filtering by it server-side returns zero results. Instead we fetch by
date + keyword only, then filter classification client-side in pandas.

Confirmed API fields on /device/recall:
  - event_date_initiated  → "YYYY-MM-DD"
  - reason_for_recall     → free text
  - recalling_firm        → string
  - recall_status         → "Ongoing" / "Completed" / "Terminated"
  - classification        → "Class I" / "Class II" / "Class III" (often missing)
  - product_description   → free text
  - root_cause_description→ free text
  - state, country        → strings
  - product_code          → 3-letter code
  - res_event_number      → recall ID
"""

import time
import requests
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta

BASE_URL = "https://api.fda.gov/device/recall.json"

CLASSIFICATION_VALUES = ["Class I", "Class II", "Class III"]

_PAGE_LIMIT = 100


def _build_search_query(
    start_date: str | None = None,
    end_date: str | None = None,
    keyword: str | None = None,
) -> str:
    """
    Build openFDA query string — date and keyword only.
    Classification is filtered client-side after fetch.
    """
    parts = []

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
    max_records: int = 500,
) -> pd.DataFrame:
    """
    Fetch device recall records from openFDA, filter classification client-side.
    """
    query = _build_search_query(start_date, end_date, keyword)

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
                break
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
        time.sleep(0.05)

    if not records:
        return pd.DataFrame()

    df = _parse_records(records)

    # Filter classification client-side
    if classifications:
        cls_set = set(classifications)
        # Keep rows that match OR rows with no classification (show as "Unknown")
        mask = df["classification"].isin(cls_set) | (df["classification"] == "Unknown")
        # Only filter if user didn't select all three — if all selected, keep everything
        if cls_set != set(CLASSIFICATION_VALUES):
            df = df[df["classification"].isin(cls_set)]

    return df


def _parse_records(records: list[dict]) -> pd.DataFrame:
    rows = []
    for r in records:
        raw_date = r.get("event_date_initiated", "")
        initiated = pd.to_datetime(raw_date, errors="coerce")

        classification = r.get("classification", "").strip()

        openfda = r.get("openfda", {}) or {}
        device_names = openfda.get("device_name", [])
        device_name = device_names[0] if device_names else ""

        rows.append({
            "recall_number":       r.get("res_event_number", ""),
            "classification":      classification,
            "recall_status":       r.get("recall_status", "").strip(),
            "recalling_firm":      r.get("recalling_firm", "").strip(),
            "product_description": r.get("product_description", "").strip(),
            "reason_for_recall":   r.get("reason_for_recall", "").strip(),
            "root_cause":          r.get("root_cause_description", "").strip(),
            "product_code":        r.get("product_code", "").strip(),
            "device_name":         device_name,
            "state":               r.get("state", "").strip(),
            "country":             r.get("country", "").strip(),
            "initiated_date":      initiated,
        })

    df = pd.DataFrame(rows)

    df["year"] = df["initiated_date"].dt.year
    df["year_month"] = (
        df["initiated_date"].dt.to_period("M").dt.to_timestamp()
    )

    # Normalize classification — anything not Class I/II/III → "Unknown"
    valid = set(CLASSIFICATION_VALUES)
    df["classification"] = df["classification"].where(
        df["classification"].isin(valid), other="Unknown"
    )

    return df


def get_date_range_default() -> tuple[str, str]:
    end = datetime.today()
    start = end - timedelta(days=365 * 5)
    return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")

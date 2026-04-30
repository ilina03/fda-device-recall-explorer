"""
classification_api.py — Device classification lookup via openFDA

The /device/recall endpoint rarely populates the 'classification' field.
This module cross-references product_code values against the
/device/classification endpoint, which reliably maps product codes
to Class I / II / III.

Usage:
    from classification_api import enrich_classification
    df = enrich_classification(df)  # adds/fills 'classification' column
"""

import time
import requests
import streamlit as st

CLASSIFICATION_URL = "https://api.fda.gov/device/classification.json"

CLASS_MAP = {
    "1": "Class I",
    "2": "Class II",
    "3": "Class III",
}


@st.cache_data(ttl=86400, show_spinner=False)  # cache for 24 hrs — classification rarely changes
def fetch_classifications(product_codes: tuple[str, ...]) -> dict[str, str]:
    """
    Given a tuple of product codes, return a dict mapping
    product_code → "Class I" / "Class II" / "Class III"

    Uses the /device/classification endpoint.
    Codes not found are omitted from the result.

    Parameters
    ----------
    product_codes : tuple of str
        e.g. ("FOZ", "MRY", "KZH")
        Must be a tuple (not list) so Streamlit can hash it for caching.

    Returns
    -------
    dict[str, str]
    """
    result = {}
    codes = [c for c in product_codes if c]  # drop empty strings

    # Batch in groups of 50 using OR queries to minimize API calls
    batch_size = 50
    for i in range(0, len(codes), batch_size):
        batch = codes[i : i + batch_size]
        query = " OR ".join(f'product_code:"{code}"' for code in batch)

        params = {
            "search": query,
            "limit":  min(100, len(batch) * 2),  # allow for multiple records per code
        }

        try:
            resp = requests.get(CLASSIFICATION_URL, params=params, timeout=15)
            if resp.status_code == 404:
                continue
            resp.raise_for_status()
            data = resp.json()
        except requests.exceptions.RequestException:
            continue  # skip this batch silently, leave as Unknown

        for record in data.get("results", []):
            code      = record.get("product_code", "").strip()
            raw_class = str(record.get("device_class", "")).strip()
            cls       = CLASS_MAP.get(raw_class)
            # "U" = unclassified, "N" = not classified — skip those
            if code and cls and code not in result:
                result[code] = cls

        time.sleep(0.05)

    return result


def enrich_classification(df) -> object:
    """
    Fill in missing 'classification' values in a recall DataFrame
    by looking up each record's product_code in /device/classification.

    Only looks up rows currently marked 'Unknown'.
    Leaves rows with existing Class I/II/III values untouched.

    Parameters
    ----------
    df : pd.DataFrame
        Output of api._parse_records() — must have 'product_code' and
        'classification' columns.

    Returns
    -------
    pd.DataFrame with 'classification' filled where possible.
    """
    import pandas as pd

    if df.empty:
        return df

    # Only look up codes for rows we don't already know the class for
    unknown_mask  = df["classification"] == "Unknown"
    codes_to_look_up = tuple(
        df.loc[unknown_mask, "product_code"]
        .dropna()
        .unique()
        .tolist()
    )

    if not codes_to_look_up:
        return df  # nothing to enrich

    code_to_class = fetch_classifications(codes_to_look_up)

    if not code_to_class:
        return df  # lookup returned nothing

    # Map product_code → classification, only for Unknown rows
    df = df.copy()
    looked_up = df.loc[unknown_mask, "product_code"].map(code_to_class)
    df.loc[unknown_mask, "classification"] = looked_up.fillna("Unknown")

    return df

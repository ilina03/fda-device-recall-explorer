# FDA Device Recall Explorer

[**Live App**](https://fda-device-recall.streamlit.app) · [**GitHub Pages**](https://ilina03.github.io/fda-device-recall-explorer)

A Streamlit dashboard for exploring FDA medical device recall data pulled 
directly from the openFDA API. Filter by recall classification, manufacturer, 
date range, and failure mode keyword - no account or API key needed.

Covers 37,000+ records from 2004 to present, updated weekly by the FDA.

---

## What it does

The FDA classifies device recalls by severity:

- **Class I** - reasonable probability of serious adverse health consequences or death
- **Class II** - may cause temporary or medically reversible adverse health consequences  
- **Class III** - unlikely to cause adverse health consequences

The dashboard lets you slice that data across several views:

- **Trend chart** - recall volume over time, monthly or quarterly, by classification
- **Manufacturer breakdown** - top recalling firms with a sortable detail table
- **Failure mode analysis** - keyword frequency across recall reason text (sterility, 
  labeling, software, and 14 others)
- **US state map** - recall counts by firm location
- **Raw data table** - full record view with CSV export

---

## One technical note

The openFDA `/device/recall` endpoint doesn't reliably populate the 
`classification` field. Hence, a large portion of records come back blank. To work 
around this, the app cross-references each record's `product_code` against the 
`/device/classification` endpoint, which maps codes to Class I/II/III 
consistently. Classification is then filtered client-side in pandas rather than 
in the API query.

---

## Run locally

```bash
git clone https://github.com/ilina03/fda-device-recall-explorer.git
cd fda-device-recall-explorer
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

**Dependencies:** Python 3.10+, Streamlit, pandas, Plotly, requests

---

Data from [openFDA /device/recall](https://open.fda.gov/apis/device/recall/) · 
For research use only, not for clinical decision-making · MIT License

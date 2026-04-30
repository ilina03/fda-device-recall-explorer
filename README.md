# FDA Device Recall Explorer

[**Live App**](https://your-app-url.streamlit.app) **·** [**Website**](https://your-username.github.io/fda-device-recall-explorer)

I built this because I wanted a faster way to explore FDA medical device recall data without digging through the openFDA docs. You can filter by classification, manufacturer, failure mode, date range. No API key needed.

Filter by Class I / II / III, date range, and failure mode keyword. Covers 37K+ records from 2004–present, updated weekly by the FDA.

\---

**What's in it**

* Recall trend over time — monthly or quarterly, by classification
* Top recalling manufacturers + sortable detail table
* Recall reason keyword analysis — sterility, software, labeling, and 17 more
* US map by state (firm location)
* Searchable raw data table with CSV export

\---

**Run it locally**

```bash
git clone https://github.com/your-username/fda-device-recall-explorer.git
cd fda-device-recall-explorer
python -m venv .venv \&\& source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

\---

Data from [openFDA /device/recall](https://open.fda.gov/apis/device/recall/) · For research use only, not for clinical decision-making · MIT License


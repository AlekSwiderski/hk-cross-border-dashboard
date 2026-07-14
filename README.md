# Hong Kong border movements

A Streamlit explorer for daily immigration clearances at Hong Kong control points. It covers arrivals and departures by passenger category, control point and transport mode.

## Data

The app requests the [Immigration Department daily passenger traffic file](https://www.immd.gov.hk/opendata/eng/transport/immigration_clearance/statistics_on_daily_passenger_traffic.csv) when it starts and caches the result for one hour. The repository snapshot is used when the official feed is unavailable.

The source counts passenger movements, not unique people. A person may appear in more than one row or on more than one date.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

Built by Alek Swiderski.

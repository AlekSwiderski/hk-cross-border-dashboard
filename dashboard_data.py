from io import BytesIO
from pathlib import Path

import pandas as pd
import requests
import streamlit as st


OFFICIAL_URL = "https://www.immd.gov.hk/opendata/eng/transport/immigration_clearance/statistics_on_daily_passenger_traffic.csv"
PASSENGER_COLUMNS = ["Hong Kong Residents", "Mainland Visitors", "Other Visitors"]
REQUIRED_COLUMNS = ["Date", "Control Point", "Arrival / Departure", *PASSENGER_COLUMNS, "Total"]

MODE_BY_CONTROL_POINT = {
    "Airport": "Air",
    "China Ferry Terminal": "Sea",
    "Express Rail Link West Kowloon": "Rail",
    "Harbour Control": "Sea",
    "Heung Yuen Wai": "Road",
    "Hong Kong-Zhuhai-Macao Bridge": "Bridge",
    "Hung Hom": "Rail",
    "Kai Tak Cruise Terminal": "Sea",
    "Lo Wu": "Rail",
    "Lok Ma Chau": "Road",
    "Lok Ma Chau Spur Line": "Rail",
    "Macao Ferry Terminal": "Sea",
    "Man Kam To": "Road",
    "Sha Tau Kok": "Road",
    "Shenzhen Bay": "Road",
    "Tuen Mun Ferry Terminal": "Sea",
}

WEEKDAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def prepare_traffic(raw: pd.DataFrame) -> pd.DataFrame:
    frame = raw.loc[:, ~raw.columns.astype(str).str.startswith("Unnamed")].copy()
    missing = set(REQUIRED_COLUMNS) - set(frame.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    frame["Date"] = pd.to_datetime(frame["Date"], format="%d-%m-%Y", errors="raise")
    frame["Control Point"] = frame["Control Point"].replace({"Macau Ferry Terminal": "Macao Ferry Terminal"})
    for column in [*PASSENGER_COLUMNS, "Total"]:
        frame[column] = pd.to_numeric(frame[column], errors="raise").astype("int64")

    if frame.duplicated(["Date", "Control Point", "Arrival / Departure"]).any():
        raise ValueError("Duplicate date, control point and direction rows found")
    if not frame["Arrival / Departure"].isin(["Arrival", "Departure"]).all():
        raise ValueError("Unexpected direction value")
    if (frame[[*PASSENGER_COLUMNS, "Total"]] < 0).any().any():
        raise ValueError("Negative passenger count found")
    if not frame[PASSENGER_COLUMNS].sum(axis=1).eq(frame["Total"]).all():
        raise ValueError("Passenger categories do not reconcile to Total")

    frame["Mode"] = frame["Control Point"].map(MODE_BY_CONTROL_POINT)
    if frame["Mode"].isna().any():
        unknown = sorted(frame.loc[frame["Mode"].isna(), "Control Point"].unique())
        raise ValueError(f"Unmapped control points: {unknown}")
    return frame.sort_values(["Date", "Control Point", "Arrival / Departure"]).reset_index(drop=True)


@st.cache_data(ttl=3600, show_spinner="Loading Immigration Department data...")
def load_dashboard_data(root: Path) -> tuple[pd.DataFrame, bool]:
    try:
        response = requests.get(OFFICIAL_URL, timeout=15)
        response.raise_for_status()
        raw = pd.read_csv(BytesIO(response.content), encoding="utf-8-sig")
        return prepare_traffic(raw), True
    except (requests.RequestException, ValueError, pd.errors.ParserError):
        raw = pd.read_csv(root / "daily_passenger_traffic.csv", encoding="utf-8-sig")
        return prepare_traffic(raw), False


def filter_traffic(
    traffic: pd.DataFrame,
    start_date: pd.Timestamp,
    end_date: pd.Timestamp,
    direction: str = "Both",
    mode: str = "All",
    control_point: str = "All",
) -> pd.DataFrame:
    mask = traffic["Date"].between(start_date, end_date)
    if direction != "Both":
        mask &= traffic["Arrival / Departure"].eq(direction)
    if mode != "All":
        mask &= traffic["Mode"].eq(mode)
    if control_point != "All":
        mask &= traffic["Control Point"].eq(control_point)
    return traffic.loc[mask].copy()


def weekday_direction_average(traffic: pd.DataFrame) -> pd.DataFrame:
    daily = traffic.groupby(["Date", "Arrival / Departure"], as_index=False)["Total"].sum()
    daily["Weekday"] = daily["Date"].dt.day_name()
    result = daily.groupby(["Weekday", "Arrival / Departure"], as_index=False)["Total"].mean()
    result = result.rename(columns={"Total": "Average movements"})
    result["Weekday"] = pd.Categorical(result["Weekday"], categories=WEEKDAY_ORDER, ordered=True)
    return result.sort_values(["Weekday", "Arrival / Departure"]).reset_index(drop=True)

from pathlib import Path

import pandas as pd

from dashboard_data import filter_traffic, prepare_traffic, weekday_direction_average


ROOT = Path(__file__).parents[1]


def local_traffic() -> pd.DataFrame:
    raw = pd.read_csv(ROOT / "daily_passenger_traffic.csv", encoding="utf-8-sig")
    return prepare_traffic(raw)


def test_source_grain_and_reconciliation():
    traffic = local_traffic()

    assert len(traffic) == 54_436
    assert not traffic.duplicated(["Date", "Control Point", "Arrival / Departure"]).any()
    assert traffic["Arrival / Departure"].isin(["Arrival", "Departure"]).all()
    assert traffic[["Hong Kong Residents", "Mainland Visitors", "Other Visitors"]].sum(axis=1).eq(traffic["Total"]).all()


def test_control_points_have_modes_and_names_are_normalized():
    traffic = local_traffic()

    assert not traffic["Mode"].isna().any()
    assert "Macau Ferry Terminal" not in set(traffic["Control Point"])
    assert "Macao Ferry Terminal" in set(traffic["Control Point"])


def test_filters_apply_together():
    traffic = local_traffic()
    result = filter_traffic(
        traffic,
        pd.Timestamp("2025-12-01"),
        pd.Timestamp("2025-12-07"),
        direction="Arrival",
        mode="Rail",
        control_point="Lo Wu",
    )

    assert result["Date"].nunique() == 7
    assert set(result["Arrival / Departure"]) == {"Arrival"}
    assert set(result["Mode"]) == {"Rail"}
    assert set(result["Control Point"]) == {"Lo Wu"}


def test_weekday_average_uses_daily_totals_before_averaging():
    sample = pd.DataFrame(
        {
            "Date": pd.to_datetime(["2026-07-06", "2026-07-06", "2026-07-13", "2026-07-13"]),
            "Arrival / Departure": ["Arrival"] * 4,
            "Total": [100, 300, 200, 400],
        }
    )
    result = weekday_direction_average(sample)

    monday_average = result.loc[result["Weekday"].eq("Monday"), "Average movements"].iloc[0]
    assert monday_average == 500

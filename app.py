from datetime import timedelta
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dashboard_data import (
    PASSENGER_COLUMNS,
    filter_traffic,
    load_dashboard_data,
    weekday_direction_average,
)


ROOT = Path(__file__).parent
ARRIVAL_COLOR = "#2d6473"
DEPARTURE_COLOR = "#b84a3d"
INK = "#17212b"
PAPER = "#f3f0e8"

st.set_page_config(
    page_title="Hong Kong border movements",
    page_icon=":material/passport:",
    layout="wide",
    initial_sidebar_state="collapsed",
)


def inject_styles() -> None:
    st.markdown(
        """
        <style>
        :root {
            --ink: #17212b;
            --muted: #62666a;
            --paper: #f3f0e8;
            --card: #fbfaf6;
            --rule: #d4cec1;
            --red: #b84a3d;
            --blue: #2d6473;
        }
        .stApp { background: var(--paper); color: var(--ink); }
        .block-container { max-width: 1210px; padding-top: 2.2rem; padding-bottom: 3rem; }
        [data-testid="stHeader"] { background: rgba(243, 240, 232, .94); }
        [data-testid="stToolbar"], #MainMenu, footer { display: none; }
        h1, h2, h3 { font-family: Georgia, "Times New Roman", serif !important; color: var(--ink); }
        h1 { font-size: clamp(2.7rem, 6vw, 5rem) !important; line-height: .98; letter-spacing: -.045em; }
        h2 { letter-spacing: -.025em; }
        p, label, button, input, [data-testid="stMetric"] { font-family: "Trebuchet MS", Verdana, sans-serif !important; }
        .eyebrow { color: var(--red); font: 700 .76rem "Trebuchet MS", sans-serif; letter-spacing: .14em; text-transform: uppercase; }
        .intro { color: var(--muted); font: 1.05rem/1.6 "Trebuchet MS", sans-serif; max-width: 780px; margin: .7rem 0 1.4rem; }
        .freshness { display: inline-block; border: 1px solid var(--rule); background: var(--card); padding: .42rem .65rem; color: var(--muted); font: .78rem "Trebuchet MS", sans-serif; letter-spacing: .03em; }
        .section-note { color: var(--muted); max-width: 800px; margin-top: -.35rem; }
        [data-testid="stMetric"] { background: var(--card); border-top: 3px solid var(--ink); border-bottom: 1px solid var(--rule); padding: .95rem 1rem; min-height: 116px; }
        [data-testid="stMetricLabel"] { color: var(--muted); }
        [data-testid="stMetricValue"] { font-family: Georgia, "Times New Roman", serif !important; font-size: 2rem; letter-spacing: -.035em; }
        button[data-baseweb="tab"] { padding-left: .25rem; padding-right: 1.4rem; font-weight: 600; }
        button[data-baseweb="tab"][aria-selected="true"] { color: var(--red); }
        [data-testid="stDataFrame"] { border: 1px solid var(--rule); }
        .source-box { margin-top: 1.5rem; padding: 1rem 0; border-top: 1px solid var(--rule); color: var(--muted); font: .82rem/1.55 "Trebuchet MS", sans-serif; }
        @media (max-width: 700px) {
            .block-container { padding: 1.25rem 1rem 2rem; }
            h1 { font-size: 2.75rem !important; }
            [data-testid="stMetric"] { min-height: 96px; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def base_layout(height: int = 420) -> dict:
    return dict(
        height=height,
        margin=dict(l=8, r=18, t=24, b=8),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Trebuchet MS", color=INK),
        hoverlabel=dict(bgcolor=INK, font_color="white", bordercolor=INK),
    )


def compact_number(value: float) -> str:
    if value >= 1_000_000_000:
        return f"{value / 1_000_000_000:.2f}bn"
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}m"
    if value >= 1_000:
        return f"{value / 1_000:.1f}k"
    return f"{value:,.0f}"


inject_styles()
traffic, live_source = load_dashboard_data(ROOT)

date_min = traffic["Date"].min()
date_max = traffic["Date"].max()

st.markdown('<div class="eyebrow">Immigration Department daily statistics</div>', unsafe_allow_html=True)
st.title("Hong Kong border movements")
st.markdown(
    '<div class="intro">Inbound and outbound passenger movements at Hong Kong control points. Counts refer to immigration clearances, so one person can appear more than once across the selected period.</div>',
    unsafe_allow_html=True,
)
source_text = "Official daily feed" if live_source else "Repository snapshot"
st.markdown(
    f'<span class="freshness">{source_text} · data through {date_max.strftime("%d %b %Y")}</span>',
    unsafe_allow_html=True,
)

st.markdown("<br>", unsafe_allow_html=True)
filter_cols = st.columns([1.65, 1, 1, 1.3])
with filter_cols[0]:
    chosen_dates = st.date_input(
        "Date range",
        value=(date_max.date() - timedelta(days=89), date_max.date()),
        min_value=date_min.date(),
        max_value=date_max.date(),
    )
with filter_cols[1]:
    direction = st.selectbox("Direction", ["Both", "Arrival", "Departure"])
with filter_cols[2]:
    mode = st.selectbox("Mode", ["All"] + sorted(traffic["Mode"].unique().tolist()))
with filter_cols[3]:
    control_point = st.selectbox("Control point", ["All"] + sorted(traffic["Control Point"].unique().tolist()))

if len(chosen_dates) != 2:
    st.info("Choose a start and end date.")
    st.stop()

start_date, end_date = map(pd.Timestamp, chosen_dates)
filtered = filter_traffic(traffic, start_date, end_date, direction, mode, control_point)
if filtered.empty:
    st.warning("No published movements match these filters.")
    st.stop()

calendar = pd.date_range(start_date, end_date, freq="D")
daily = filtered.groupby("Date", as_index=False)["Total"].sum().set_index("Date").reindex(calendar, fill_value=0)
daily.index.name = "Date"
daily = daily.reset_index()
daily["7-day average"] = daily["Total"].rolling(7, min_periods=1).mean()

total_movements = int(filtered["Total"].sum())
average_daily = float(daily["Total"].mean())
resident_share = filtered["Hong Kong Residents"].sum() / total_movements if total_movements else 0
busiest_point = filtered.groupby("Control Point")["Total"].sum().idxmax()

st.markdown("<br>", unsafe_allow_html=True)
metrics = st.columns(4)
metrics[0].metric("Passenger movements", compact_number(total_movements), help="Arrival and departure clearances in the selected period.")
metrics[1].metric("Average per day", compact_number(average_daily), help="Selected movements divided by calendar days in the date range.")
metrics[2].metric("Hong Kong resident share", f"{resident_share:.1%}")
metrics[3].metric("Busiest control point", busiest_point)

st.markdown("<br>", unsafe_allow_html=True)
overview_tab, mix_tab, pattern_tab, data_tab = st.tabs(["Overview", "Passenger mix", "Weekly pattern", "Data"])

with overview_tab:
    st.header("Movement over time")
    st.markdown(
        '<p class="section-note">Daily clearances are shown behind a seven-day average to make weekends and public-holiday peaks easier to read.</p>',
        unsafe_allow_html=True,
    )
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=daily["Date"],
            y=daily["Total"],
            mode="lines",
            name="Daily",
            line=dict(color="rgba(45,100,115,.25)", width=1),
            fill="tozeroy",
            fillcolor="rgba(45,100,115,.06)",
            hovertemplate="%{x|%d %b %Y}<br>%{y:,.0f} movements<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=daily["Date"],
            y=daily["7-day average"],
            mode="lines",
            name="7-day average",
            line=dict(color=INK, width=2.5),
            hovertemplate="%{x|%d %b %Y}<br>%{y:,.0f} seven-day average<extra></extra>",
        )
    )
    fig.update_layout(**base_layout(430), hovermode="x unified", legend=dict(orientation="h", y=1.04), xaxis_title=None, yaxis_title="Movements")
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor="#d8d2c6", zeroline=False)
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

    st.subheader("Control point share")
    point_totals = filtered.groupby("Control Point", as_index=False)["Total"].sum().sort_values("Total").tail(10)
    rank = go.Figure(
        go.Bar(
            x=point_totals["Total"],
            y=point_totals["Control Point"],
            orientation="h",
            marker_color=ARRIVAL_COLOR,
            text=point_totals["Total"].map(compact_number),
            textposition="outside",
            hovertemplate="%{y}<br>%{x:,.0f} movements<extra></extra>",
        )
    )
    rank.update_layout(**base_layout(420), showlegend=False, xaxis_title=None, yaxis_title=None)
    rank.update_xaxes(visible=False, range=[0, point_totals["Total"].max() * 1.18])
    rank.update_yaxes(showgrid=False)
    st.plotly_chart(rank, width="stretch", config={"displayModeBar": False})

with mix_tab:
    st.header("Who crossed the border")
    st.markdown(
        '<p class="section-note">The source separates Hong Kong residents, Mainland visitors and other visitors. The categories describe clearances, not unique people.</p>',
        unsafe_allow_html=True,
    )
    mix_colors = ["#2d6473", "#b84a3d", "#c28b3c"]
    mix_totals = filtered[PASSENGER_COLUMNS].sum()
    mix_fig = go.Figure()
    for column, color in zip(PASSENGER_COLUMNS, mix_colors):
        mix_fig.add_trace(
            go.Bar(
                x=[mix_totals[column]],
                y=["Passenger mix"],
                name=column,
                orientation="h",
                marker_color=color,
                text=[f"{mix_totals[column] / total_movements:.1%}"],
                textposition="inside",
                hovertemplate=f"{column}<br>%{{x:,.0f}} movements<extra></extra>",
            )
        )
    mix_fig.update_layout(**base_layout(180), barmode="stack", xaxis_visible=False, yaxis_visible=False, legend=dict(orientation="h", y=1.25))
    st.plotly_chart(mix_fig, width="stretch", config={"displayModeBar": False})

    monthly = filtered.groupby(pd.Grouper(key="Date", freq="MS"), as_index=False)[PASSENGER_COLUMNS].sum()
    trend = go.Figure()
    for column, color in zip(PASSENGER_COLUMNS, mix_colors):
        trend.add_trace(
            go.Scatter(
                x=monthly["Date"],
                y=monthly[column],
                name=column,
                mode="lines",
                stackgroup="mix",
                line=dict(color=color, width=1.5),
                hovertemplate=f"{column}<br>%{{y:,.0f}}<extra></extra>",
            )
        )
    trend.update_layout(**base_layout(420), hovermode="x unified", legend=dict(orientation="h", y=1.04), xaxis_title=None, yaxis_title="Monthly movements")
    trend.update_xaxes(showgrid=False)
    trend.update_yaxes(gridcolor="#d8d2c6", zeroline=False)
    st.plotly_chart(trend, width="stretch", config={"displayModeBar": False})

with pattern_tab:
    st.header("Average day by weekday")
    st.markdown(
        '<p class="section-note">Each date is totalled before the weekday average is calculated. This avoids understating traffic by averaging individual control-point records.</p>',
        unsafe_allow_html=True,
    )
    weekday = weekday_direction_average(filtered)
    pattern = go.Figure()
    directions = [direction] if direction != "Both" else ["Arrival", "Departure"]
    for item in directions:
        values = weekday.loc[weekday["Arrival / Departure"].eq(item)]
        pattern.add_trace(
            go.Bar(
                x=values["Weekday"],
                y=values["Average movements"],
                name=item,
                marker_color=ARRIVAL_COLOR if item == "Arrival" else DEPARTURE_COLOR,
                hovertemplate=f"{item}<br>%{{y:,.0f}} average movements<extra></extra>",
            )
        )
    pattern.update_layout(**base_layout(430), barmode="group", legend=dict(orientation="h", y=1.04), xaxis_title=None, yaxis_title="Average movements")
    pattern.update_xaxes(showgrid=False)
    pattern.update_yaxes(gridcolor="#d8d2c6", zeroline=False)
    st.plotly_chart(pattern, width="stretch", config={"displayModeBar": False})

with data_tab:
    st.header("Published rows")
    st.markdown(
        '<p class="section-note">One row is one control point, direction and date. Zeroes are retained because suspended or inactive services are part of the published record.</p>',
        unsafe_allow_html=True,
    )
    display_columns = ["Date", "Control Point", "Mode", "Arrival / Departure"] + PASSENGER_COLUMNS + ["Total"]
    display = filtered[display_columns].sort_values(["Date", "Control Point"], ascending=[False, True])
    st.dataframe(display, hide_index=True, width="stretch", height=480)
    st.download_button(
        "Download selected rows",
        display.to_csv(index=False).encode("utf-8"),
        file_name="hk_border_movements.csv",
        mime="text/csv",
    )

st.markdown(
    """
    <div class="source-box">
    Source: Hong Kong Immigration Department, Statistics on Daily Passenger Traffic. The official file is requested when the app starts and cached for one hour. The repository copy is used if that request fails.<br>
    Built by Alek Swiderski.
    </div>
    """,
    unsafe_allow_html=True,
)

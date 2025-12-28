import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import timedelta

st.set_page_config(
    page_title="Hong Kong Cross-Border Dashboard",
    page_icon="🇭🇰",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #dc3545, #c82333);
        color: white;
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 20px;
        text-align: center;
    }
    .main-header h1 {
        margin: 0;
        font-size: 2.2rem;
    }
    .main-header p {
        margin: 5px 0 0 0;
        opacity: 0.9;
    }
    .kpi-card {
        background: white;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        text-align: center;
        border-left: 4px solid #dc3545;
    }
    .kpi-value {
        font-size: 2rem;
        font-weight: bold;
        color: #dc3545;
    }
    .kpi-label {
        font-size: 0.9rem;
        color: #666;
        text-transform: uppercase;
    }
    .section-header {
        border-bottom: 2px solid #dc3545;
        padding-bottom: 10px;
        margin-bottom: 20px;
    }
    div[data-testid="stMetricValue"] {
        font-size: 1.8rem;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data
def load_data():
    df = pd.read_csv('daily_passenger_traffic.csv', encoding='utf-8-sig')

    # Clean column names
    df.columns = df.columns.str.strip()

    # Parse date
    df['Date'] = pd.to_datetime(df['Date'], format='%d-%m-%Y')
    df['Year'] = df['Date'].dt.year
    df['Month'] = df['Date'].dt.month
    df['Month_Name'] = df['Date'].dt.month_name()
    df['Day_of_Week'] = df['Date'].dt.day_name()
    df['Week'] = df['Date'].dt.isocalendar().week

    # Clean numeric columns
    for col in ['Hong Kong Residents', 'Mainland Visitors', 'Other Visitors', 'Total']:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)

    # Categorize control points by mode
    air_points = ['Airport']
    rail_points = ['Express Rail Link West Kowloon', 'Hung Hom', 'Lo Wu', 'Lok Ma Chau Spur Line']
    bridge_points = ['Hong Kong-Zhuhai-Macao Bridge']
    land_points = ['Lok Ma Chau', 'Man Kam To', 'Sha Tau Kok', 'Shenzhen Bay', 'Heung Yuen Wai']
    sea_points = ['China Ferry Terminal', 'Harbour Control', 'Kai Tak Cruise Terminal',
                  'Macau Ferry Terminal', 'Tuen Mun Ferry Terminal']

    def categorize_mode(cp):
        if cp in air_points:
            return 'Air'
        elif cp in rail_points:
            return 'Rail'
        elif cp in bridge_points:
            return 'Bridge'
        elif cp in land_points:
            return 'Land'
        elif cp in sea_points:
            return 'Sea'
        else:
            return 'Other'

    df['Transport_Mode'] = df['Control Point'].apply(categorize_mode)

    return df

df = load_data()

st.markdown("""
<div class="main-header">
    <h1>🇭🇰 Hong Kong Cross-Border Flow Dashboard</h1>
    <p>Daily Immigration Statistics from All Control Points | Data: Immigration Department</p>
</div>
""", unsafe_allow_html=True)

date_min = df['Date'].min()
date_max = df['Date'].max()

with st.sidebar:
    st.header("Filters")

    date_range = st.date_input(
        "Date Range",
        value=(date_max - timedelta(days=365), date_max),
        min_value=date_min.date(),
        max_value=date_max.date()
    )

    direction = st.selectbox(
        "Direction",
        options=['Both', 'Arrival', 'Departure'],
        index=0
    )

    all_control_points = ['All'] + sorted(df['Control Point'].unique().tolist())
    selected_cp = st.selectbox("Control Point", options=all_control_points, index=0)

    all_modes = ['All'] + sorted(df['Transport_Mode'].unique().tolist())
    selected_mode = st.selectbox("Transport Mode", options=all_modes, index=0)

filtered_df = df.copy()

if len(date_range) == 2:
    filtered_df = filtered_df[
        (filtered_df['Date'].dt.date >= date_range[0]) &
        (filtered_df['Date'].dt.date <= date_range[1])
    ]

if direction != 'Both':
    filtered_df = filtered_df[filtered_df['Arrival / Departure'] == direction]

if selected_cp != 'All':
    filtered_df = filtered_df[filtered_df['Control Point'] == selected_cp]

if selected_mode != 'All':
    filtered_df = filtered_df[filtered_df['Transport_Mode'] == selected_mode]

total_passengers = filtered_df['Total'].sum()
total_hk_residents = filtered_df['Hong Kong Residents'].sum()
total_mainland = filtered_df['Mainland Visitors'].sum()
total_others = filtered_df['Other Visitors'].sum()
days_in_range = (filtered_df['Date'].max() - filtered_df['Date'].min()).days + 1
daily_avg = total_passengers / max(days_in_range, 1)
mainland_pct = (total_mainland / total_passengers * 100) if total_passengers > 0 else 0
busiest_cp = filtered_df.groupby('Control Point')['Total'].sum().idxmax() if len(filtered_df) > 0 else "N/A"

st.markdown("### Key Metrics")
col1, col2, col3, col4, col5, col6 = st.columns(6)

with col1:
    st.metric("Total Passengers", f"{total_passengers:,.0f}", help="Total passenger movements in selected period")

with col2:
    st.metric("Daily Average", f"{daily_avg:,.0f}", help="Average daily passenger movements")

with col3:
    st.metric("HK Residents", f"{total_hk_residents:,.0f}", help="Hong Kong resident movements")

with col4:
    st.metric("Mainland Visitors", f"{total_mainland:,.0f}", help="Mainland China visitor movements")

with col5:
    st.metric("Mainland %", f"{mainland_pct:.1f}%", help="Percentage of Mainland visitors")

with col6:
    st.metric("Busiest Point", busiest_cp[:15] + "..." if len(busiest_cp) > 15 else busiest_cp, help="Control point with highest traffic")

st.markdown("---")

tab1, tab2, tab3, tab4, tab5 = st.tabs(["📈 Trends", "🚉 Control Points", "👥 Passenger Mix", "🗓️ Patterns", "📊 Data"])

with tab1:
    st.markdown("### Daily Traffic Trends")

    daily_totals = filtered_df.groupby('Date').agg({
        'Total': 'sum',
        'Hong Kong Residents': 'sum',
        'Mainland Visitors': 'sum',
        'Other Visitors': 'sum'
    }).reset_index()
    daily_totals['7-Day Avg'] = daily_totals['Total'].rolling(window=7, min_periods=1).mean()

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=daily_totals['Date'],
        y=daily_totals['Total'],
        name='Daily Total',
        line=dict(color='rgba(220, 53, 69, 0.3)', width=1),
        fill='tozeroy',
        fillcolor='rgba(220, 53, 69, 0.1)'
    ))

    fig.add_trace(go.Scatter(
        x=daily_totals['Date'],
        y=daily_totals['7-Day Avg'],
        name='7-Day Moving Average',
        line=dict(color='#dc3545', width=3)
    ))

    fig.update_layout(
        height=400,
        hovermode='x unified',
        legend=dict(orientation='h', yanchor='bottom', y=1.02),
        xaxis_title='',
        yaxis_title='Passengers',
        yaxis=dict(gridcolor='#f0f0f0'),
        plot_bgcolor='white'
    )

    st.plotly_chart(fig, use_container_width=True)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Monthly Totals by Year")
        monthly = filtered_df.groupby(['Year', 'Month_Name', 'Month'])['Total'].sum().reset_index()
        monthly = monthly.sort_values(['Year', 'Month'])

        fig_monthly = px.bar(
            monthly,
            x='Month_Name',
            y='Total',
            color='Year',
            barmode='group',
            category_orders={'Month_Name': ['January', 'February', 'March', 'April', 'May', 'June',
                                            'July', 'August', 'September', 'October', 'November', 'December']},
            color_discrete_sequence=px.colors.sequential.Reds_r
        )
        fig_monthly.update_layout(
            height=350,
            xaxis_title='',
            yaxis_title='Total Passengers',
            legend_title='Year'
        )
        st.plotly_chart(fig_monthly, use_container_width=True)

    with col2:
        st.markdown("### Year-over-Year Recovery")
        yearly = filtered_df.groupby('Year')['Total'].sum().reset_index()

        fig_yearly = go.Figure()

        fig_yearly.add_trace(go.Bar(
            x=yearly['Year'],
            y=yearly['Total'],
            marker_color='#dc3545',
            name='Total Passengers'
        ))

        fig_yearly.update_layout(
            height=350,
            xaxis_title='Year',
            yaxis_title='Total Passengers'
        )
        st.plotly_chart(fig_yearly, use_container_width=True)

with tab2:
    st.markdown("### Control Point Analysis")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### Top Control Points by Traffic")
        cp_totals = filtered_df.groupby('Control Point')['Total'].sum().sort_values(ascending=True).tail(10).reset_index()

        fig_cp = px.bar(
            cp_totals,
            y='Control Point',
            x='Total',
            orientation='h',
            color='Total',
            color_continuous_scale='Reds'
        )
        fig_cp.update_layout(
            height=400,
            showlegend=False,
            xaxis_title='Total Passengers',
            yaxis_title='',
            coloraxis_showscale=False
        )
        st.plotly_chart(fig_cp, use_container_width=True)

    with col2:
        st.markdown("#### Traffic by Transport Mode")
        mode_totals = filtered_df.groupby('Transport_Mode')['Total'].sum().reset_index()

        fig_mode = px.pie(
            mode_totals,
            values='Total',
            names='Transport_Mode',
            color_discrete_sequence=px.colors.sequential.RdBu,
            hole=0.4
        )
        fig_mode.update_traces(textposition='inside', textinfo='percent+label')
        fig_mode.update_layout(height=400, showlegend=False)
        st.plotly_chart(fig_mode, use_container_width=True)

    st.markdown("### Control Point Trends Over Time")
    top_5_cp = filtered_df.groupby('Control Point')['Total'].sum().nlargest(5).index.tolist()
    cp_trends = filtered_df[filtered_df['Control Point'].isin(top_5_cp)].groupby(
        [pd.Grouper(key='Date', freq='M'), 'Control Point']
    )['Total'].sum().reset_index()

    fig_cp_trend = px.line(
        cp_trends,
        x='Date',
        y='Total',
        color='Control Point',
        color_discrete_sequence=px.colors.qualitative.Set1
    )
    fig_cp_trend.update_layout(
        height=350,
        xaxis_title='',
        yaxis_title='Monthly Passengers',
        legend=dict(orientation='h', yanchor='bottom', y=1.02)
    )
    st.plotly_chart(fig_cp_trend, use_container_width=True)

with tab3:
    st.markdown("### Passenger Type Analysis")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### Passenger Mix")
        mix_data = pd.DataFrame({
            'Category': ['HK Residents', 'Mainland Visitors', 'Other Visitors'],
            'Count': [total_hk_residents, total_mainland, total_others]
        })

        fig_mix = px.pie(
            mix_data,
            values='Count',
            names='Category',
            color_discrete_map={
                'HK Residents': '#3498db',
                'Mainland Visitors': '#e74c3c',
                'Other Visitors': '#2ecc71'
            },
            hole=0.4
        )
        fig_mix.update_traces(textposition='inside', textinfo='percent+label')
        fig_mix.update_layout(height=400)
        st.plotly_chart(fig_mix, use_container_width=True)

    with col2:
        st.markdown("#### Arrival vs Departure")
        direction_data = filtered_df.groupby('Arrival / Departure')['Total'].sum().reset_index()

        fig_dir = px.bar(
            direction_data,
            x='Arrival / Departure',
            y='Total',
            color='Arrival / Departure',
            color_discrete_map={'Arrival': '#28a745', 'Departure': '#dc3545'}
        )
        fig_dir.update_layout(
            height=400,
            showlegend=False,
            xaxis_title='',
            yaxis_title='Total Passengers'
        )
        st.plotly_chart(fig_dir, use_container_width=True)

    st.markdown("### Passenger Type Trends Over Time")

    monthly_by_type = filtered_df.groupby(pd.Grouper(key='Date', freq='M')).agg({
        'Hong Kong Residents': 'sum',
        'Mainland Visitors': 'sum',
        'Other Visitors': 'sum'
    }).reset_index()

    fig_type_trend = go.Figure()

    fig_type_trend.add_trace(go.Scatter(
        x=monthly_by_type['Date'],
        y=monthly_by_type['Hong Kong Residents'],
        name='HK Residents',
        stackgroup='one',
        fillcolor='rgba(52, 152, 219, 0.7)',
        line=dict(color='#3498db')
    ))

    fig_type_trend.add_trace(go.Scatter(
        x=monthly_by_type['Date'],
        y=monthly_by_type['Mainland Visitors'],
        name='Mainland Visitors',
        stackgroup='one',
        fillcolor='rgba(231, 76, 60, 0.7)',
        line=dict(color='#e74c3c')
    ))

    fig_type_trend.add_trace(go.Scatter(
        x=monthly_by_type['Date'],
        y=monthly_by_type['Other Visitors'],
        name='Other Visitors',
        stackgroup='one',
        fillcolor='rgba(46, 204, 113, 0.7)',
        line=dict(color='#2ecc71')
    ))

    fig_type_trend.update_layout(
        height=400,
        hovermode='x unified',
        legend=dict(orientation='h', yanchor='bottom', y=1.02),
        xaxis_title='',
        yaxis_title='Passengers'
    )
    st.plotly_chart(fig_type_trend, use_container_width=True)

with tab4:
    st.markdown("### Traffic Patterns")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### By Day of Week")
        dow_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        dow_data = filtered_df.groupby('Day_of_Week')['Total'].mean().reindex(dow_order).reset_index()
        dow_data.columns = ['Day', 'Average']

        fig_dow = px.bar(
            dow_data,
            x='Day',
            y='Average',
            color='Average',
            color_continuous_scale='Reds'
        )
        fig_dow.update_layout(
            height=350,
            xaxis_title='',
            yaxis_title='Avg Daily Passengers',
            coloraxis_showscale=False
        )
        st.plotly_chart(fig_dow, use_container_width=True)

    with col2:
        st.markdown("#### By Month")
        month_order = ['January', 'February', 'March', 'April', 'May', 'June',
                       'July', 'August', 'September', 'October', 'November', 'December']
        month_data = filtered_df.groupby('Month_Name')['Total'].mean().reindex(month_order).reset_index()
        month_data.columns = ['Month', 'Average']

        fig_month = px.bar(
            month_data,
            x='Month',
            y='Average',
            color='Average',
            color_continuous_scale='Reds'
        )
        fig_month.update_layout(
            height=350,
            xaxis_title='',
            yaxis_title='Avg Daily Passengers',
            coloraxis_showscale=False,
            xaxis_tickangle=-45
        )
        st.plotly_chart(fig_month, use_container_width=True)

    st.markdown("#### Traffic Heatmap: Day of Week × Control Point")
    top_8_cp = filtered_df.groupby('Control Point')['Total'].sum().nlargest(8).index.tolist()
    heatmap_data = filtered_df[filtered_df['Control Point'].isin(top_8_cp)].groupby(
        ['Day_of_Week', 'Control Point']
    )['Total'].mean().reset_index()

    heatmap_pivot = heatmap_data.pivot(index='Control Point', columns='Day_of_Week', values='Total')
    heatmap_pivot = heatmap_pivot.reindex(columns=dow_order)

    fig_heatmap = px.imshow(
        heatmap_pivot,
        color_continuous_scale='Reds',
        aspect='auto'
    )
    fig_heatmap.update_layout(
        height=400,
        xaxis_title='',
        yaxis_title=''
    )
    st.plotly_chart(fig_heatmap, use_container_width=True)

with tab5:
    st.markdown("### Raw Data")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.info(f"📅 Date Range: {date_min.strftime('%Y-%m-%d')} to {date_max.strftime('%Y-%m-%d')}")
    with col2:
        st.info(f"📍 Control Points: {df['Control Point'].nunique()}")
    with col3:
        st.info(f"📊 Total Records: {len(filtered_df):,}")

    st.dataframe(
        filtered_df[['Date', 'Control Point', 'Arrival / Departure', 'Hong Kong Residents',
                     'Mainland Visitors', 'Other Visitors', 'Total']].sort_values('Date', ascending=False),
        use_container_width=True,
        height=500
    )

    csv = filtered_df.to_csv(index=False)
    st.download_button(
        label="📥 Download Filtered Data as CSV",
        data=csv,
        file_name="hk_border_traffic_filtered.csv",
        mime="text/csv"
    )

st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; padding: 20px;'>
    <p>Data Source: <a href='https://data.gov.hk/en-data/dataset/hk-immd-set5-statistics-daily-passenger-traffic' target='_blank'>
    Hong Kong Immigration Department via DATA.GOV.HK</a></p>
    <p>Dashboard updates daily with official government data</p>
</div>
""", unsafe_allow_html=True)

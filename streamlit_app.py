import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from supabase import create_client, Client

# ---- Supabase Configuration ----
SUPABASE_URL = st.secrets["supabase"]["url"]
SUPABASE_KEY = st.secrets["supabase"]["key"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

@st.cache_data
def load_data():
    try:
        response = supabase.table("telematics").select("*").execute()
        df = pd.DataFrame(response.data)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.dropna(subset=['timestamp', 'latitude', 'longitude'])
        return df
    except Exception as e:
        st.error(f"Failed to fetch data from Supabase: {e}")
        return pd.DataFrame()

# ---- Streamlit UI Configuration ----
st.set_page_config(page_title="Telematics Dashboard", layout="wide")
st.title("\U0001F697 Telematics Dashboard")

# Load data
df = load_data()
if df.empty:
    st.stop()

# Sidebar filters
st.sidebar.header("Filters")
vehicle_types = df['vehicle_type'].unique()
selected_vehicle_type = st.sidebar.multiselect("Vehicle Type", vehicle_types, default=vehicle_types)
trip_ids = df['trip_id'].unique()
selected_trip_ids = st.sidebar.multiselect("Trip IDs", trip_ids, default=trip_ids)
filtered_df = df[df['vehicle_type'].isin(selected_vehicle_type) & df['trip_id'].isin(selected_trip_ids)]

# Overview Metrics
st.header("Overview")
col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    st.metric("Total Trips", len(filtered_df['trip_id'].unique()))
with col2:
    st.metric("Avg Speed (km/h)", f"{filtered_df['speed'].mean():.2f}")
with col3:
    st.metric("Speeding Events", int(filtered_df['speeding_flag'].sum()))
with col4:
    st.metric("Harsh Braking Events", int(filtered_df['harsh_braking'].sum()))
with col5:
    st.metric("Avg Fatigue Score", f"{filtered_df['fatigue_score'].mean():.2f}")

# Map Visualization
st.header("Vehicle Locations")
if not filtered_df.empty:
    st.map(filtered_df[['latitude', 'longitude']])
else:
    st.write("No location data available.")

# Time-Series Metrics
st.header("Metrics Over Time")
metric_options = ['speed', 'fuel_level', 'engine_temp', 'fatigue_score']
selected_metric = st.selectbox("Select Metric", metric_options)
fig_metric = px.line(filtered_df, x='timestamp', y=selected_metric, color='vehicle_type',
                     title=f"{selected_metric.replace('_', ' ').capitalize()} Over Time")
st.plotly_chart(fig_metric, use_container_width=True)

# Driver Behavior
st.header("Driver Behavior Analysis")
col1, col2 = st.columns(2)
with col1:
    state_counts = filtered_df['driver_state'].value_counts().reset_index()
    state_counts.columns = ['driver_state', 'count']
    fig_state = px.bar(state_counts, x='driver_state', y='count', title="Driver State Distribution")
    st.plotly_chart(fig_state, use_container_width=True)
with col2:
    fig_fatigue = px.histogram(filtered_df, x='fatigue_score', nbins=20, title="Fatigue Score Distribution")
    st.plotly_chart(fig_fatigue, use_container_width=True)

# Vehicle Health Monitoring
st.header("Vehicle Health Status")
health_counts = filtered_df['vehicle_health'].value_counts().reset_index()
health_counts.columns = ['vehicle_health', 'count']
fig_health = px.pie(health_counts, names='vehicle_health', values='count', title="Vehicle Health")
st.plotly_chart(fig_health, use_container_width=True)

# Engine Overheating
overheating_count = filtered_df['engine_overheat'].sum()
fig_temp = px.line(filtered_df, x='timestamp', y='engine_temp', color='vehicle_type',
                   title="Engine Temperature Over Time")
fig_temp.add_hline(y=110, line_dash="dash", line_color="red", annotation_text="Overheat Threshold")
st.plotly_chart(fig_temp, use_container_width=True)
st.write(f"**Insight**: {overheating_count} overheating events detected (temp > 110°C).")

# Accelerometer Insights
st.header("Accelerometer Insights")
fig_accel = px.line(filtered_df, x='timestamp', y=['accelerometer_x', 'accelerometer_y', 'accelerometer_z'],
                    title="Accelerometer Readings Over Time")
st.plotly_chart(fig_accel, use_container_width=True)

# Raw Data Table
st.header("Raw Data")
st.dataframe(filtered_df)

# Footer
st.markdown("---")
st.write("Built with Streamlit, Plotly, and Pandas. Data source: Supabase → Telematics Table")

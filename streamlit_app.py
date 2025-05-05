import streamlit as st
import time
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from supabase import create_client, Client

# Load data from Supabase
@st.cache_data(ttl=10)
def load_data():
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    supabase: Client = create_client(url, key)

    response = supabase.table("telematics") \
        .select("*") \
        .order("timestamp", desc=True) \
        .limit(500) \
        .execute()

    df = pd.DataFrame(response.data)
    df = df.sort_values("timestamp")

    # Clean and process data
    df['timestamp'] = pd.to_datetime(df['timestamp'], format='ISO8601', errors='coerce')
    numeric_cols = ['latitude', 'longitude', 'speed', 'fuel_level', 'engine_temp',
                    'accelerometer_x', 'accelerometer_y', 'accelerometer_z',
                    'head_direction', 'head_tilt', 'eye_closed_duration']
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    categorical_cols = ['driver_state', 'vehicle_health', 'vehicle_type']
    for col in categorical_cols:
        df[col] = df[col].astype(str).str.lower()
    df = df.dropna(subset=['timestamp', 'latitude', 'longitude'])
    return df

# Set page title and layout
st.set_page_config(page_title="Telematics Dashboard", layout="wide")
st.title("🚗 Telematics Dashboard")

# Load data
df = load_data()
if df.empty:
    st.stop()

# Sidebar for filters
st.sidebar.header("Filters")
vehicle_types = df['vehicle_type'].unique()
selected_vehicle_type = st.sidebar.multiselect("Select Vehicle Type", vehicle_types, default=vehicle_types)

# Manual data refresh button
if st.sidebar.button("🔄 Refresh Now"):
    st.cache_data.clear()
    st.query_params.update({"refresh": str(time.time())})

filtered_df = df[df['vehicle_type'].isin(selected_vehicle_type)]


# Overview Section
st.header("Overview")
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Total Trips", len(filtered_df))
with col2:
    st.metric("Avg Speed (km/h)", f"{filtered_df['speed'].mean():.2f}")
with col3:
    st.metric("Avg Fuel Level (%)", f"{filtered_df['fuel_level'].mean():.2f}")
with col4:
    drowsy_pct = (filtered_df['driver_state'] == 'drowsy').mean() * 100
    st.metric("Drowsy Drivers (%)", f"{drowsy_pct:.2f}")

# Map Visualization
st.header("Vehicle Locations")
if not filtered_df.empty:
    st.map(filtered_df[['latitude', 'longitude']].dropna())
else:
    st.write("No location data available.")

# Time-Series Analysis
st.header("Vehicle Metrics Over Time")
metric_options = ['speed', 'fuel_level', 'engine_temp']
selected_metric = st.selectbox("Select Metric", metric_options)
fig_time = px.line(filtered_df, x='timestamp', y=selected_metric, color='vehicle_type',
                   title=f"{selected_metric.capitalize()} Over Time")
fig_time.update_layout(xaxis_title="Timestamp", yaxis_title=selected_metric.capitalize())
st.plotly_chart(fig_time, use_container_width=True)

# Driver Behavior Analysis
st.header("Driver Behavior")
col1, col2 = st.columns(2)
with col1:
    driver_state_counts = filtered_df['driver_state'].value_counts().reset_index()
    driver_state_counts.columns = ['driver_state', 'count']
    fig_driver = px.bar(driver_state_counts, x='driver_state', y='count',
                        title="Driver State Distribution",
                        color='driver_state', color_discrete_sequence=px.colors.qualitative.Plotly)
    st.plotly_chart(fig_driver, use_container_width=True)
with col2:
    fig_eye = px.scatter(filtered_df, x='eye_closed_duration', y='driver_state',
                         color='driver_state', title="Eye Closed Duration vs Driver State",
                         hover_data=['timestamp', 'vehicle_type'])
    risky_df = filtered_df[filtered_df['eye_closed_duration'] > 2.5]
    if not risky_df.empty:
        fig_eye.add_trace(go.Scatter(x=risky_df['eye_closed_duration'], y=risky_df['driver_state'],
                                     mode='markers', marker=dict(color='red', size=10, symbol='x'),
                                     name='Risky (>2.5s)'))
    st.plotly_chart(fig_eye, use_container_width=True)
    st.write(f"**Insight**: {len(risky_df)} instances where eye closed duration > 2.5s, indicating potential risk.")

# Vehicle Health Monitoring
st.header("Vehicle Health")
col1, col2 = st.columns(2)
with col1:
    health_counts = filtered_df['vehicle_health'].value_counts().reset_index()
    health_counts.columns = ['vehicle_health', 'count']
    fig_health = px.pie(health_counts, names='vehicle_health', values='count',
                        title="Vehicle Health Status")
    st.plotly_chart(fig_health, use_container_width=True)
with col2:
    fig_temp = px.line(filtered_df, x='timestamp', y='engine_temp', color='vehicle_type',
                       title="Engine Temperature Over Time")
    fig_temp.add_hline(y=120, line_dash="dash", line_color="red", annotation_text="Overheating Threshold (120°C)")
    overheating_count = (filtered_df['engine_temp'] > 120).sum()
    st.plotly_chart(fig_temp, use_container_width=True)
    st.write(f"**Insight**: {overheating_count} instances of engine temperature > 120°C.")

# Accelerometer Insights
st.header("Accelerometer Readings")
fig_accel = px.line(filtered_df, x='timestamp', y=['accelerometer_x', 'accelerometer_y', 'accelerometer_z'],
                    title="Accelerometer Readings Over Time")
fig_accel.add_hline(y=2.5, line_dash="dash", line_color="orange", annotation_text="High Acceleration Threshold")
fig_accel.add_hline(y=-2.5, line_dash="dash", line_color="orange")
high_accel = filtered_df[(filtered_df['accelerometer_x'].abs() > 2.5) |
                         (filtered_df['accelerometer_y'].abs() > 2.5) |
                         (filtered_df['accelerometer_z'].abs() > 2.5)]
st.plotly_chart(fig_accel, use_container_width=True)
st.write(f"**Insight**: {len(high_accel)} high acceleration events detected (|x|, |y|, or |z| > 2.5), indicating potential harsh braking or sharp turns.")

# Raw Data Table
st.header("Raw Data")
st.dataframe(filtered_df)

# Footer
st.markdown("---")
st.write("Built with Streamlit, Pandas, and Plotly. Data source: Supabase telematics dataset.")

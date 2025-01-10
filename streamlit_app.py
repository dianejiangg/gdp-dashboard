import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
from datetime import datetime, timedelta
import time
import numpy as np

# Set page config
st.set_page_config(
    page_title="Earthquake Monitor",
    page_icon="🌍",
    layout="wide"
)

# Function to fetch earthquake data
def fetch_earthquake_data():
    url = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_week.geojson"
    response = requests.get(url)
    data = response.json()
    
    # Convert to DataFrame
    earthquakes = []
    for feature in data['features']:
        earthquakes.append({
            'time': datetime.fromtimestamp(feature['properties']['time']/1000.0),
            'magnitude': feature['properties']['mag'],
            'place': feature['properties']['place'],
            'depth': feature['geometry']['coordinates'][2],
            'latitude': feature['geometry']['coordinates'][1],
            'longitude': feature['geometry']['coordinates'][0]
        })
    
    return pd.DataFrame(earthquakes)

# App title
st.title('Real-time Earthquake Monitor')

# Load data
df = fetch_earthquake_data()

# Add time filter
time_filter = st.sidebar.selectbox(
    'Select Time Range',
    ['Last 24 Hours', 'Last 48 Hours', 'Last 7 Days']
)

# Filter data based on selection
now = pd.Timestamp.now()
if time_filter == 'Last 24 Hours':
    df = df[df['time'] > (now - pd.Timedelta(hours=24))]
elif time_filter == 'Last 48 Hours':
    df = df[df['time'] > (now - pd.Timedelta(hours=48))]

# Display key metrics
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Total Earthquakes", len(df))
with col2:
    st.metric("Average Magnitude", f"{df['magnitude'].mean():.2f}")
with col3:
    st.metric("Maximum Magnitude", f"{df['magnitude'].max():.2f}")
with col4:
    st.metric("Significant Events (M5.0+)", len(df[df['magnitude'] >= 5.0]))

# Create marker sizes for map (handling negative magnitudes)
df['marker_size'] = np.where(df['magnitude'] > 0, 
                            df['magnitude'] * 5,  # Multiply by 5 to make markers more visible
                            1)  # Default size for negative/zero magnitudes

# Create visualizations
st.subheader("Earthquake Locations")
fig = px.scatter_mapbox(df, 
    lat='latitude', 
    lon='longitude',
    size='marker_size',
    color='magnitude',
    hover_name='place',
    hover_data=['magnitude', 'depth', 'time'],
    zoom=1,
    mapbox_style='carto-positron')

# Adjust marker appearance
fig.update_traces(marker={'sizemin': 3})

st.plotly_chart(fig, use_container_width=True)

# Magnitude distribution
st.subheader("Magnitude Distribution")
fig_mag = px.histogram(df, 
                      x='magnitude', 
                      nbins=30,
                      title='Distribution of Earthquake Magnitudes')
fig_mag.update_layout(
    xaxis_title="Magnitude",
    yaxis_title="Count"
)
st.plotly_chart(fig_mag, use_container_width=True)

# Depth vs Magnitude scatter plot
st.subheader("Depth vs Magnitude")
fig_depth = px.scatter(df, 
                      x='depth', 
                      y='magnitude',
                      title='Earthquake Depth vs Magnitude',
                      color='magnitude',
                      size='marker_size')
fig_depth.update_layout(
    xaxis_title="Depth (km)",
    yaxis_title="Magnitude"
)
st.plotly_chart(fig_depth, use_container_width=True)

# Recent events table
st.subheader("Recent Events")
recent_df = df.copy()
recent_df['time'] = recent_df['time'].dt.strftime('%Y-%m-%d %H:%M:%S')
st.dataframe(
    recent_df.sort_values('time', ascending=False)
    .head(10)
    [['time', 'place', 'magnitude', 'depth']]
    .reset_index(drop=True)
    .style.format({
        'magnitude': '{:.1f}',
        'depth': '{:.1f} km'
    })
)

# Temporal Visualizations
st.header("Temporal Analysis")

# 1. Events Over Time
df['hour'] = df['time'].dt.hour
hourly_counts = df.groupby('hour').size().reset_index(name='count')
fig_hourly = px.line(hourly_counts, 
                     x='hour', 
                     y='count',
                     title='Earthquake Events by Hour of Day',
                     markers=True)
fig_hourly.update_layout(
    xaxis_title="Hour of Day",
    yaxis_title="Number of Events"
)
st.plotly_chart(fig_hourly, use_container_width=True)

# 2. Magnitude Timeline
fig_timeline = px.scatter(df.sort_values('time'), 
                         x='time', 
                         y='magnitude',
                         color='magnitude',
                         size='marker_size',
                         title='Earthquake Magnitudes Over Time')
fig_timeline.update_layout(
    xaxis_title="Time",
    yaxis_title="Magnitude"
)
st.plotly_chart(fig_timeline, use_container_width=True)

# 3. Rolling Average of Events
# Calculate events per hour with 6-hour rolling average
df['hour_bin'] = df['time'].dt.floor('H')
hourly_series = df.groupby('hour_bin').size()
hourly_series = hourly_series.reindex(
    pd.date_range(start=hourly_series.index.min(),
                 end=hourly_series.index.max(),
                 freq='H'),
    fill_value=0
)
rolling_avg = hourly_series.rolling(window=6).mean()

fig_rolling = go.Figure()
fig_rolling.add_trace(go.Scatter(
    x=rolling_avg.index,
    y=rolling_avg.values,
    mode='lines',
    name='6-hour Rolling Average'
))
fig_rolling.update_layout(
    title='6-Hour Rolling Average of Earthquake Frequency',
    xaxis_title="Time",
    yaxis_title="Average Number of Events per Hour"
)
st.plotly_chart(fig_rolling, use_container_width=True)

# 4. Heatmap of Events by Hour and Magnitude
df['magnitude_bin'] = pd.cut(df['magnitude'], 
                           bins=np.arange(-1, 8, 1),
                           labels=[f"{i}-{i+1}" for i in range(-1, 7)])
heatmap_data = pd.crosstab(df['hour'], df['magnitude_bin'])

fig_heatmap = px.imshow(heatmap_data,
                        title='Heatmap of Events by Hour and Magnitude',
                        labels=dict(x="Magnitude Range", y="Hour of Day", color="Number of Events"),
                        aspect='auto')
st.plotly_chart(fig_heatmap, use_container_width=True)

# Add refresh button
if st.button('Refresh Data'):
    st.experimental_rerun()

# Optional: Add auto-refresh using JavaScript
st.markdown(
    """
    <script>
        function reload() {
            window.location.reload();
        }
        setTimeout(reload, 300000); // Refresh every 5 minutes
    </script>
    """,
    unsafe_allow_html=True
)

import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import os

# Production: Prioritize secrets, then env var
api_key = st.secrets.get("WEATHER_API_KEY", os.getenv("WEATHER_API_KEY"))

# Dev fallback: Sidebar input (hide in prod by removing or via config)
if not api_key:
    st.sidebar.header("Dev: API Setup")
    api_key = st.sidebar.text_input("Visual Crossing API Key", type="password", 
                                    help="Set WEATHER_API_KEY in secrets.toml or env for production.")
    if not api_key:
        st.warning("Please set your API key via secrets/env or sidebar (dev only).")
        st.stop()

st.title("🌤️ Monthly Weather Forecaster")
st.markdown("Enter details below to get a 30-day weather forecast.")

# User inputs (defaults for Chennai, Nov 2025)
col1, col2 = st.columns(2)
with col1:
    city = st.text_input("City (e.g., Chennai)", value="Chennai")
with col2:
    year = st.number_input("Year", min_value=2020, max_value=2030, value=2025)

month = st.selectbox("Month", options=range(1, 13), index=10,  # November
                     format_func=lambda x: datetime(2023, x, 1).strftime("%B"))

@st.cache_data(ttl=3600)  # Cache for 1 hour
def fetch_monthly_data(city, year, month, api_key):
    """Cached API fetch for monthly data."""
    start_date = f"{year}-{month:02d}-01"
    if month == 12:
        end_date = f"{year}-12-31"
    else:
        end_date = datetime(year, month + 1, 1) - timedelta(days=1)
        end_date = end_date.strftime("%Y-%m-%d")
    
    url = f"https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/{city}/{start_date}/{end_date}"
    params = {
        "key": api_key,
        "include": "days",
        "unitGroup": "metric",
        "contentType": "json",
        "elements": "datetime,tempmax,tempmin,temp,conditions,precip"
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if "days" not in data:
            raise ValueError(f"API Error: {data.get('message', 'Invalid response')}")
        
        days_data = []
        for day in data["days"]:
            days_data.append({
                "Date": day["datetime"],
                "Max Temp (°C)": day["tempmax"],
                "Min Temp (°C)": day["tempmin"],
                "Avg Temp (°C)": day["temp"],
                "Conditions": day["conditions"],
                "Precip (mm)": day.get("precip", 0)
            })
        
        df = pd.DataFrame(days_data)
        df["Date"] = pd.to_datetime(df["Date"])
        return df
    
    except requests.exceptions.RequestException as e:
        st.error(f"API Request Failed: {e}. Check city name or API key.")
        return None
    except Exception as e:
        st.error(f"Unexpected Error: {e}")
        return None

# Fetch button with spinner
if st.button("Fetch Monthly Forecast", type="primary"):
    with st.spinner("Fetching forecast..."):
        df = fetch_monthly_data(city, year, month, api_key)
    
    if df is not None and not df.empty:
        month_name = datetime(year, month, 1).strftime("%B %Y")
        
        # Display table
        st.subheader(f"Daily Forecast for {month_name} in {city}")
        st.dataframe(df, use_container_width=True)
        
        # Summary stats
        st.subheader("Monthly Summary")
        col1, col2, col3, col4 = st.columns(4)
        avg_max = df["Max Temp (°C)"].mean()
        avg_min = df["Min Temp (°C)"].mean()
        total_precip = df["Precip (mm)"].sum()
        avg_precip = df["Precip (mm)"].mean()
        
        col1.metric("Avg High Temp", f"{avg_max:.1f}°C")
        col2.metric("Avg Low Temp", f"{avg_min:.1f}°C")
        col3.metric("Total Precip", f"{total_precip:.1f} mm")
        col4.metric("Avg Daily Precip", f"{avg_precip:.1f} mm")
        
        # Charts
        st.subheader("Temperature Trend")
        fig = px.line(df, x="Date", y=["Max Temp (°C)", "Min Temp (°C)", "Avg Temp (°C)"], 
                      title="Daily High/Low/Avg Temperatures")
        st.plotly_chart(fig, use_container_width=True)
        
        st.subheader("Precipitation")
        fig_precip = px.bar(df, x="Date", y="Precip (mm)", title="Daily Precipitation")
        st.plotly_chart(fig_precip, use_container_width=True)
    else:
        st.stop()

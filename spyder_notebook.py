# -*- coding: utf-8 -*-
"""
Created on Tue Jun 10 02:59:32 2025

@author: divya
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import warnings

warnings.filterwarnings('ignore')


# Load data
df = pd.read_csv("C:\\Users\\divya\\OneDrive\\Documents\\internsip\\AP DATA\\AP_MASTER_DATA.csv")
df['date'] = pd.to_datetime(df['date'], dayfirst=True)
df['year'] = df['date'].dt.year
# 🧼 Clean & Preprocess the Data


# Drop fully empty rows/columns just in case
df.dropna(how='all', inplace=True)
df.dropna(axis=1, how='all', inplace=True)

# Fill NA values in key fields with placeholders or 0
df['district'] = df['district'].fillna('Unknown').astype(str).str.strip().str.title()
df['year'] = pd.to_numeric(df['year'], errors='coerce')  # Convert to numeric
df = df.dropna(subset=['year'])  # Drop rows with invalid years
# Keep 'year' as integer for calculations, convert to string only for display in Streamlit
df['year'] = df['year'].astype(int)

# Clean other fields as needed (optional)
if 'crimes_reported' in df.columns:
    df['crimes_reported'] = pd.to_numeric(df['crimes_reported'], errors='coerce').fillna(0)

# Sanity check: Ensure no NaNs remain in selection filters
df['district'] = df['district'].replace('nan', 'Unknown')

# Metrics Calculation
# Add a check for division by zero for total_tourists
df['revenue_per_tourist'] = df.apply(
    lambda row: row['total_revenue'] / row['total_tourists'] if row['total_tourists'] != 0 else 0, axis=1
)
df['crimes_per_10k'] = df.apply(
    lambda row: (row['crimes_reported'] / row['total_tourists'] * 10000) if row['total_tourists'] != 0 else 0, axis=1
)
df['safety_index'] = 100 - df['crimes_per_10k']

# Sidebar
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["🏠 Tourism Pulse", "📊 District Deep Dive", "🟥 Tirupati Focus"])

# Filters - Convert year to string for display in selectbox
year_list_str = sorted(df['year'].unique().astype(str))
districts = sorted(df['district'].unique())

# Default to the last year in the list
if not year_list_str:
    selected_year_str = None # Handle case where df is empty
else:
    selected_year_str = st.sidebar.selectbox("Select Year", year_list_str, index=len(year_list_str)-1)

district_selected = st.sidebar.selectbox("Select District", districts)

# Convert selected_year_str back to integer for calculations
if selected_year_str is not None:
    year_selected = int(selected_year_str)
else:
    year_selected = None # Handle case where no year is selected

# ----------------------------- Dashboard 1 -----------------------------
if page == "🏠 Tourism Pulse" and year_selected is not None: # Ensure year_selected is valid
    st.title("🏠 Tourism Pulse: Andhra Pradesh at a Glance")
    df_yr = df[df['year'] == year_selected]

    # KPIs
    total_tourists = df_yr['total_tourists'].sum()
    total_revenue = df_yr['total_revenue'].sum()
    total_crimes = df_yr['crimes_reported'].sum()

    # Calculate revenue per tourist, handle division by zero
    revenue_per_tourist = total_revenue / total_tourists if total_tourists != 0 else 0

    # Calculate crime_yoy, ensuring the previous year exists in the data
    previous_year = year_selected - 1
    df_prev_yr = df[df['year'] == previous_year]
    crime_yoy = df_prev_yr['crimes_reported'].sum()

    col1, col2, col3, col4 = st.columns(4)

    # Ensure growth_rate_total exists and handle potential division by zero for delta calculation
    if 'growth_rate_total' in df_yr.columns and df_yr['growth_rate_total'].mean() is not np.nan:
        col1.metric("Total Tourists", f"{total_tourists:,}", delta=f"{df_yr['growth_rate_total'].mean():.2%}")
    else:
         col1.metric("Total Tourists", f"{total_tourists:,}")

    col2.metric("Total Revenue (₹Cr)", f"{total_revenue/1e7:.2f} Cr")

    # Handle potential division by zero for crime delta calculation
    if crime_yoy != 0:
         col3.metric("Crimes Reported", f"{total_crimes:,}", delta=f"{(total_crimes - crime_yoy)/crime_yoy:.2%}")
    else:
         col3.metric("Crimes Reported", f"{total_crimes:,}")

    col4.metric("Revenue/Tourist", f"₹{revenue_per_tourist:.0f}")

    # Choropleth - Add check if df_yr is empty
    st.subheader("📌 District-Wise Tourist Footfall")
    if not df_yr.empty:
        fig_map = px.choropleth(df_yr, geojson="https://raw.githubusercontent.com/datameet/maps/master/States/andhra-pradesh-districts.json",
                                locations="district", featureidkey="properties.DISTRICT",
                                color="total_tourists", hover_data=["total_revenue", "crimes_reported"])
        st.plotly_chart(fig_map)
    else:
        st.info("No data available for the selected year.")


    # Revenue Composition - Add check if df_yr is empty
    st.subheader("💸 Revenue Composition by District")
    if not df_yr.empty:
        fig_stack = px.bar(df_yr, x="district", y=["hotel_revenue", "bar_revenue", "boating_revenue"],
                           title="Stacked Revenue", labels={'value': 'Revenue', 'variable': 'Type'})
        st.plotly_chart(fig_stack)
    else:
        st.info("No data available for the selected year.")

    # Footfall Trend
    st.subheader("📈 Tourist Trends Over Time")
    df_state = df.groupby('year').sum(numeric_only=True).reset_index()
    fig_line = px.line(df_state, x='year', y=['domestic_tourists', 'foreign_tourists'],
                       labels={'value': 'Tourists', 'variable': 'Type'})
    st.plotly_chart(fig_line)

    # Heatmap Grid - Add check if pivot is empty
    st.subheader("🏨 Infrastructure Growth (Hotel Room Keys)")
    pivot = df.pivot_table(index='district', columns='year', values='hotel_room_keys', aggfunc='sum')
    if not pivot.empty:
        fig_heat = px.imshow(pivot, aspect="auto", color_continuous_scale="YlGnBu")
        st.plotly_chart(fig_heat)
    else:
        st.info("No infrastructure data available.")

    # Gauge Safety Index - Add check if df_yr is empty and safety_index is valid
    st.subheader("🔐 Safety Index")
    if not df_yr.empty and not df_yr['safety_index'].empty and not df_yr['safety_index'].isnull().all():
        avg_safety = df_yr['safety_index'].mean()
        gauge = go.Figure(go.Indicator(mode="gauge+number", value=avg_safety,
                                       gauge={'axis': {'range': [0, 100]},
                                              'bar': {'color': "darkblue"},
                                              'steps': [
                                                  {'range': [0, 70], 'color': "red"},
                                                  {'range': [70, 90], 'color': "yellow"},
                                                  {'range': [90, 100], 'color': "green"}]}))
        st.plotly_chart(gauge)
    else:
        st.info("Safety index data not available for the selected year.")


# ----------------------------- Dashboard 2 -----------------------------
elif page == "📊 District Deep Dive" and district_selected is not None:
    st.title(f"📊 {district_selected} District Performance Deep Dive")
    df_district = df[df['district'] == district_selected]

    # Monthly Trend - Add check if df_district is empty
    st.subheader("📅 Monthly Tourist Trend")
    if not df_district.empty:
        df_district['month'] = df_district['date'].dt.to_period("M").astype(str)
        fig_multi = px.line(df_district, x='month', y=['domestic_tourists', 'foreign_tourists'])
        st.plotly_chart(fig_multi)
    else:
        st.info(f"No data available for {district_selected}.")

    # Revenue by Type - Add check if df_district is empty
    st.subheader("📊 Monthly Revenue Composition")
    if not df_district.empty:
        fig_area = px.area(df_district, x='month', y=['hotel_revenue', 'bar_revenue', 'boating_revenue'])
        st.plotly_chart(fig_area)
    else:
        st.info(f"No revenue data available for {district_selected}.")

    # Hotel vs Tourist Growth - Add check if df_district is empty
    st.subheader("🏨 Hotel Rooms vs Tourist Growth")
    df_yr_district = df_district.groupby('year').sum(numeric_only=True).reset_index()
    if not df_yr_district.empty:
        fig_combo = go.Figure()
        fig_combo.add_trace(go.Bar(x=df_yr_district['year'], y=df_yr_district['hotel_room_keys'], name="Hotel Rooms"))
        fig_combo.add_trace(go.Line(x=df_yr_district['year'], y=df_yr_district['total_tourists'], name="Tourists"))
        st.plotly_chart(fig_combo)
    else:
        st.info(f"No annual growth data available for {district_selected}.")

    # Crime over Time - Add check if df_district is empty
    st.subheader("🚨 Crime Reported Over Time")
    if not df_district.empty:
        fig_crime = px.bar(df_district, x='month', y='crimes_reported',
                           hover_data=['total_tourists', 'crimes_per_10k'])
        st.plotly_chart(fig_crime)
    else:
        st.info(f"No crime data available for {district_selected}.")

# ----------------------------- Dashboard 3 -----------------------------
elif page == "🟥 Tirupati Focus":
    st.title("🟥 Tirupati Tourism Action Tracker")
    tiru = df[df['district'] == 'Tirupati']

    # Ensure there is data for Tirupati before proceeding
    if not tiru.empty:
        # Filter for 2024 data for KPIs
        tiru_2024 = tiru[tiru['year'] == 2024]

        # Display KPIs, handling potential empty 2024 data
        if not tiru_2024.empty:
            st.metric("Total Tourists (2024)", int(tiru_2024['total_tourists'].sum()))
            st.metric("Total Revenue (₹Cr)", f"{tiru_2024['total_revenue'].sum()/1e7:.2f} Cr")
            st.metric("Crimes Reported", tiru_2024['crimes_reported'].sum())
            st.metric("Crime/10k", f"{tiru_2024['crimes_per_10k'].mean():.1f}")
        else:
            st.info("No data available for Tirupati in 2024.")


        # Line: Crime vs Tourists - Add check if tiru is empty
        st.subheader("📉 Crime vs Tourists (Monthly)")
        tiru['month'] = tiru['date'].dt.to_period("M").astype(str)
        fig_line = px.line(tiru, x='month', y=['crimes_reported', 'total_tourists'])
        st.plotly_chart(fig_line)

        # Donut Revenue Share - Add check if tiru_2024 is empty
        st.subheader("💰 Revenue Breakdown")
        if not tiru_2024.empty:
            rev_2024 = tiru_2024[['hotel_revenue', 'bar_revenue', 'boating_revenue']].sum()
            fig_donut = px.pie(values=rev_2024, names=rev_2024.index, hole=0.5)
            st.plotly_chart(fig_donut)
        else:
             st.info("No revenue breakdown data available for Tirupati in 2024.")


        # Infra Trend - Add check if tiru is empty
        st.subheader("🏗️ Hotel Room Key Growth")
        tiru_agg_year = tiru.groupby('year').sum(numeric_only=True).reset_index()
        if not tiru_agg_year.empty:
            fig_bar = px.bar(tiru_agg_year,
                             x='year', y='hotel_room_keys',
                             hover_data={'hotel_room_keys': True})
            st.plotly_chart(fig_bar)
        else:
             st.info("No infrastructure growth data available for Tirupati.")


        # Policy Suggestion
        st.info("""
        📌 **Policy Recommendation:**
        - Increase patrols during winter (crimes peak Nov–Jan).
        - Revenue per tourist steady.
        - Recommend 500-room expansion.
        - Launch grievance helpline.
        """)
    else:
        st.info("No data available for Tirupati.")

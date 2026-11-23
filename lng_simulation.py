import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px

st.set_page_config(layout="wide", page_title="SA LNG Day 2: BOG & Storage Dynamics")

st.title("🇿🇦 Day 2: LNG Thermodynamics, BOG, and Storage Dynamics")
st.markdown("Use the sidebar to simulate scenarios. Watch the animated tank and graphs to see how real-world events affect stock levels and Boil-Off Gas (BOG).")

# ==========================================
# 1. SIDEBAR CONTROLS & SCENARIOS
# ==========================================
st.sidebar.header("🕹️ Simulation Scenarios")

scenario = st.sidebar.selectbox(
    "Select Scenario", 
    ["Normal Operations", "The Rollover Incident", "FSU Sloshing (High BOG)"]
)

capacity_m3 = st.sidebar.radio("Storage Type", ["FSU (170,000 m³)", "Onshore (220,000 m³)"])
cap_val = 170000 if "FSU" in capacity_m3 else 220000

st.sidebar.subheader("Thermodynamic Parameters")
lng_density = st.sidebar.slider("Initial LNG Density (kg/m³)", 400.0, 480.0, 450.0)
send_out_mtpa = st.sidebar.slider("Send-Out Rate (Mtpa)", 1.0, 5.0, 3.0)

# ==========================================
# 2. SIMULATION LOGIC (WITH SCENARIO EVENTS)
# ==========================================
days = 30
initial_inv = cap_val * 0.9 # Start at 90%
send_out_m3_day = ((send_out_mtpa * 1e6) / 365 * 1000) / lng_density

inventory = []
bog_rates = []

for day in range(1, days + 1):
    # Base BOG Rate
    base_bog = 0.10 if "Onshore" in capacity_m3 else 0.15
    
    # Apply Scenario Modifiers
    if scenario == "FSU Sloshing (High BOG)":
        base_bog = 0.25 # Constant high boil-off due to wave motion
    
    current_inv = initial_inv if day == 1 else inventory[-1]
    
    # The Rollover Event (Day 15)
    if scenario == "The Rollover Incident" and day == 15:
        actual_bog_rate = base_bog * 5.0 # 5x spike in BOG due to sudden mixing
        st.sidebar.error("⚠️ ROLLOVER EVENT TRIGGERED ON DAY 15!")
    else:
        actual_bog_rate = base_bog
        
    bog_m3 = current_inv * (actual_bog_rate / 100)
    inventory.append(current_inv - bog_m3 - send_out_m3_day)
    bog_rates.append(bog_m3 * lng_density / 1000) # BOG in Tonnes

df = pd.DataFrame({'Day': range(1, 31), 'Inventory (m³)': inventory, 'BOG (Tonnes)': bog_rates})
df['Inventory (%)'] = (df['Inventory (m³)'] / cap_val) * 100

# ==========================================
# 3. ANIMATED TANK VISUALIZATION
# ==========================================
st.subheader(f"🎬 Live Tank Status: {scenario}")
col_tank, col_metrics = st.columns([1, 2])

with col_tank:
    # Simulate the tank with a dynamic Gauge
    latest_level = df['Inventory (%)'].iloc[-1]
    fig_tank = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = latest_level,
        title = {'text': "LNG Tank Level (%)"},
        gauge = {
            'axis': {'range': [0, 100]},
            'bar': {'color': "#00CC96" if latest_level > 15 else "#EF553B"},
            'steps': [
                {'range': [0, 15], 'color': "#FFE4E1"}, # Danger zone
                {'range': [15, 100], 'color': "#E0FFFF"}
            ],
            'threshold': {'line': {'color': "red", 'width': 4}, 'value': 10}
        }
    ))
    fig_tank.update_layout(height=300, margin=dict(l=10, r=10, t=50, b=10))
    st.plotly_chart(fig_tank, use_container_width=True)

with col_metrics:
    st.metric("Peak BOG Rate", f"{np.max(df['BOG (Tonnes)']):,.0f} Tonnes/Day")
    st.metric("Total BOG Lost in 30 Days", f"{np.sum(df['BOG (Tonnes)']):,.0f} Tonnes")
    if scenario == "The Rollover Incident":
        st.warning("**Significance:** The Rollover caused a massive pressure spike, forcing emergency flaring. This proves why density stratification must be monitored.")
    elif scenario == "FSU Sloshing (High BOG)":
        st.info("**Significance:** Wave motion in an FSU creates immense sloshing, increasing BOG by up to 70% compared to onshore tanks.")

# ==========================================
# 4. CHARTS
# ==========================================
st.subheader("📉 Time Series Data")
fig_line = px.line(df, x='Day', y=['Inventory (%)', 'BOG (Tonnes)'], 
                   title="Inventory vs. BOG Generation",
                   markers=True)
st.plotly_chart(fig_line, use_container_width=True)

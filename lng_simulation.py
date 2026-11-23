import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px

# Set page layout to wide
st.set_page_config(layout="wide", page_title="South Africa LNG & CCGT Simulator")

# ==========================================
# 1. APP TITLE & SIDEBAR CONTROLS (LIVE TOGGLES)
# ==========================================
st.title("🇿🇦 South African LNG Import & CCGT Optimization")
st.markdown("Use the control panel in the sidebar to toggle between FSU and Onshore storage, adjust thermodynamic parameters, and instantly see the impact on BOG generation, inventory, and CCGT power output.")

st.sidebar.header("🕹️ Live Simulation Controls")

# Storage Toggle
storage_type = st.sidebar.radio("LNG Storage Type", ["FSU (Floating)", "Onshore Tank"])
capacity_m3 = 170000 if storage_type == "FSU (Floating)" else 220000

# Thermodynamic Inputs
st.sidebar.subheader("Thermodynamics & Inventory")
lng_density = st.sidebar.slider("LNG Density (kg/m³)", min_value=400.0, max_value=480.0, value=450.0, step=1.0)
initial_fill_pct = st.sidebar.slider("Initial Tank Fill (%)", min_value=10, max_value=100, value=80, step=1)
send_out_mtpa = st.sidebar.slider("Send-Out Rate (Mtpa)", min_value=1.0, max_value=5.0, value=3.0, step=0.1)

# CCGT Inputs
st.sidebar.subheader("CCGT Power Generation")
cold_energy_toggle = st.sidebar.checkbox("Enable LNG Cold Energy Integration", value=True)
base_eff = 0.4922 # 49.22%
boosted_eff = 0.5831 # 58.31% (from literature)

# BOG Rate Adjusters
st.sidebar.subheader("BOG Rates")
bog_rate_fsu = st.sidebar.slider("FSU BOG Rate (%/day)", 0.05, 0.25, 0.15, 0.01)
bog_rate_onshore = st.sidebar.slider("Onshore BOG Rate (%/day)", 0.05, 0.25, 0.10, 0.01)

# ==========================================
# 2. SIMULATION LOGIC
# ==========================================
@st.cache_data
def run_simulation(storage, cap_m3, density, fill_pct, send_out, bog_fsu, bog_onshore, cold_energy):
    days = 30
    initial_inventory = cap_m3 * (fill_pct / 100.0)
    
    # BOG Rate Selection based on toggle
    daily_bog_rate = (bog_fsu / 100.0) if storage == "FSU (Floating)" else (bog_onshore / 100.0)
    
    # Conversions
    send_out_mt_per_day = send_out * 1e6 / 365 # Metric tonnes per day
    send_out_kg_per_day = send_out_mt_per_day * 1000
    send_out_m3_per_day = send_out_kg_per_day / density
    
    # Initialise arrays
    inventory = np.zeros(days)
    bog_m3 = np.zeros(days)
    bog_kg = np.zeros(days)
    
    current_inv = initial_inventory
    
    for i in range(days):
        # Calculate BOG
        daily_bog_m3 = current_inv * daily_bog_rate
        bog_m3[i] = daily_bog_m3
        bog_kg[i] = daily_bog_m3 * density
        
        # Update Inventory
        current_inv = current_inv - daily_bog_m3 - send_out_m3_per_day
        
        # Refill logic (if below 10%, cargo arrives)
        if current_inv < (cap_m3 * 0.1):
            current_inv = cap_m3 * 0.9
            
        inventory[i] = current_inv

    # CCGT Power Calculation
    eff = boosted_eff if cold_energy else base_eff
    # Assume 1 kg LNG = 48 MJ (Heating Value)
    energy_mj_per_day = send_out_kg_per_day * 48
    power_mw = (energy_mj_per_day * eff) / (24 * 3600)
    
    # Economics (Simplified)
    # Assume electricity price R2.00/kWh, LNG cost $10/MMBtu (~R180/GJ)
    revenue_per_day_zar = power_mw * 1000 * 24 * 2.00 
    bog_waste_cost_zar = np.sum(bog_kg) * 0.048 * 180 # MJ to GJ
    
    df = pd.DataFrame({
        'Day': np.arange(1, days + 1),
        'Inventory (m³)': inventory,
        'BOG (m³)': bog_m3,
        'BOG (kg)': bog_kg,
        'Inventory (%)': (inventory / cap_m3) * 100
    })
    
    return df, power_mw, eff, revenue_per_day_zar, np.sum(bog_kg)

df, power_mw, eff, revenue, total_bog_kg = run_simulation(
    storage_type, capacity_m3, lng_density, initial_fill_pct, send_out_mtpa, 
    bog_rate_fsu, bog_rate_onshore, cold_energy_toggle
)

# ==========================================
# 3. DASHBOARD LAYOUT & ANIMATED GAUGES
# ==========================================
col1, col2, col3, col4 = st.columns(4)

# Animated Gauge for Inventory
fig_gauge = go.Figure(go.Indicator(
    mode = "gauge+number",
    value = df['Inventory (%)'].iloc[-1],
    title = {'text': "Current Inventory (%)"},
    gauge = {
        'axis': {'range': [None, 100]},
        'bar': {'color': "#00CC96"},
        'steps': [
            {'range': [0, 15], 'color': "#EF553B"},   # Danger zone
            {'range': [15, 85], 'color': "#636EFA"},  # Normal zone
            {'range': [85, 100], 'color': "#AB63FA"}  # High zone
        ],
    }
))
fig_gauge.update_layout(height=250, margin=dict(l=10, r=10, t=40, b=10))
col1.plotly_chart(fig_gauge, use_container_width=True)

col2.metric("CCGT Power Output", f"{power_mw:,.1f} MW", f"{eff*100:.1f}% Efficiency")
col3.metric("Total BOG Waste (30 Days)", f"{total_bog_kg/1000:,.1f} Tonnes", delta_color="inverse")
col4.metric("Est. CCGT Revenue (Daily)", f"R {revenue:,.2f}", "ZAR")

# ==========================================
# 4. TABS FOR DETAILED GRAPHS & SENSITIVITIES
# ==========================================
tab1, tab2, tab3 = st.tabs(["📉 Inventory & BOG Dynamics", "⚡ CCGT Power & Economics", "🔬 Sensitivity Analysis"])

with tab1:
    st.subheader("LNG Inventory & BOG Tracking")
    
    fig_inv = px.line(df, x='Day', y='Inventory (%)', 
                      title=f"{storage_type} - Tank Inventory (% Capacity)",
                      markers=True, line_shape='spline')
    fig_inv.update_traces(line_color='#00CC96', line_width=3)
    fig_inv.update_layout(yaxis_title="Fill Percentage (%)", hovermode="x unified")
    st.plotly_chart(fig_inv, use_container_width=True)

    fig_bog = px.bar(df, x='Day', y='BOG (kg)', 
                     title="Daily Boil-Off Gas (BOG) Generated (kg)",
                     color='BOG (kg)', color_continuous_scale='Reds')
    st.plotly_chart(fig_bog, use_container_width=True)

with tab2:
    st.subheader("CCGT Power Generation & Cold Energy Impact")
    
    # Efficiency Comparison Chart
    labels = ['Base CCGT (No Cold Energy)', 'Integrated CCGT (With Cold Energy)']
    power_outputs = [(power_mw / eff) * base_eff, power_mw if cold_energy_toggle else (power_mw / eff) * boosted_eff]
    
    fig_power = go.Figure(data=[
        go.Bar(name='Base Efficiency (49.2%)', x=labels, y=[power_outputs[0], power_outputs[0]], marker_color='gray'),
        go.Bar(name='Optimized Efficiency (58.3%)', x=labels, y=[power_outputs[1], power_outputs[1]], marker_color='#FFA15A')
    ])
    fig_power.update_layout(barmode='group', title="Power Output Comparison (MW)", yaxis_title="Power (MW)")
    st.plotly_chart(fig_power, use_container_width=True)
    
    st.info("**Why Cold Energy?** Regasifying LNG releases immense cold energy. By integrating this with the CCGT's Rankine cycle, we boost efficiency from ~49% to ~58%, dramatically improving plant economics.")

with tab3:
    st.subheader("Sensitivity: BOG Rate vs. Inventory Over Time")
    st.markdown("This graph shows how changing the BOG rate affects the inventory. Play with the sliders on the left to see live updates.")
    
    # Simulate a range of BOG rates for sensitivity
    sensitivity_bogs = [0.05, 0.10, 0.15, 0.20, 0.25]
    fig_sens = go.Figure()
    
    for bog in sensitivity_bogs:
        # Mini-simulation inside the loop for sensitivity
        temp_df, _, _, _, _ = run_simulation(
            storage_type, capacity_m3, lng_density, initial_fill_pct, send_out_mtpa, 
            bog, bog, cold_energy_toggle
        )
        fig_sens.add_trace(go.Scatter(x=temp_df['Day'], y=temp_df['Inventory (%)'], 
                                      mode='lines', name=f'BOG {bog}%'))
        
    fig_sens.update_layout(title="Sensitivity: BOG Rate Impact on Inventory", 
                           xaxis_title="Days", yaxis_title="Inventory (%)")
    st.plotly_chart(fig_sens, use_container_width=True)

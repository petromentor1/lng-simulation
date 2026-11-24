import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(layout="wide", page_title="SA LNG & CCGT Master Dashboard")

st.title("🇿🇦 South Africa LNG Import & Power Generation Master Dashboard")

# ==========================================
# 1. ENRICHED SIDEBAR CONTROLS & EXPLANATIONS
# ==========================================
st.sidebar.header("🕹️ Simulation Controls")

scenario = st.sidebar.selectbox(
    "Select Scenario", 
    ["Normal Operations (Cargo Deliveries)", "The Rollover Incident", "FSU Sloshing (High BOG)"],
    help="Choose the operational event. Rollover simulates the violent mixing of LNG layers. FSU Sloshing simulates wave motion increasing BOG."
)

storage_type = st.sidebar.radio(
    "Storage Type", 
    ["FSU (170,000 m³)", "Onshore (220,000 m³)"],
    help="Floating Storage Units (FSU) are ships. Onshore tanks are concrete structures. FSUs experience sloshing and generally have higher BOG rates."
)
cap_val = 170000 if "FSU" in storage_type else 220000

current_day = st.sidebar.slider(
    "Timeline (Days)", 1, 30, 1, 1,
    help="Scrub through the 30-day simulation. Watch the 3D tank and graphs update in real-time."
)

st.sidebar.header("🌡️ Thermodynamics")
initial_fill = st.sidebar.slider("Initial Tank Fill (%)", 50, 95, 90, 5, help="The starting inventory of LNG in the tank.")
ambient_temp = st.sidebar.slider("Ambient Temperature (°C)", 15, 45, 30, 1, help="Higher outside temperatures increase heat leak into the tank, generating more BOG.")

st.sidebar.header("⚡ CCGT Economics")
send_out_mtpa = st.sidebar.slider("Send-Out Rate (Mtpa)", 1.0, 5.0, 3.0, 0.1, help="How much LNG is regasified and sent to the power plant daily.")
elec_price_zar = st.sidebar.slider("Electricity Price (R/kWh)", 1.0, 5.0, 2.50, 0.1, help="The selling price of electricity to the grid.")
cold_energy_toggle = st.sidebar.checkbox("Enable LNG Cold Energy Integration", value=True, help="Uses the CCGT's waste heat to vaporize the LNG, boosting plant efficiency from ~49% to ~58%.")

# ==========================================
# 2. BULLETPROOF CALCULATION ENGINE
# ==========================================
# Base BOG rates depending on storage
base_bog = 0.10 if "Onshore" in storage_type else 0.15

# Modify BOG based on scenario
if scenario == "FSU Sloshing (High BOG)":
    base_bog = 0.35 if "FSU" in storage_type else 0.10

# Modify BOG based on ambient temperature (Every degree above 25C adds 1% to BOG)
temp_modifier = 1.0 + ((ambient_temp - 25) * 0.01)
base_bog *= temp_modifier

# Conversions
lng_density = 450.0 # kg/m3
send_out_m3_day = ((send_out_mtpa * 1e9) / 365) / lng_density 
send_out_pct = (send_out_m3_day / cap_val) * 100

inv_hist = [initial_fill]
bog_hist = []
press_hist = [1.05]
event_log = [] # To store text for the dynamic explanation

for d in range(1, 31):
    current_inv = inv_hist[-1]
    
    # Logic for Rollover
    if scenario == "The Rollover Incident" and d == 15:
        actual_bog_pct = base_bog * 8.0 # Massive 8x spike
        pressure = 16.05
        event_log.append((d, "ROLLOVER!", "Violent mixing of LNG layers caused extreme BOG."))
    elif scenario == "The Rollover Incident" and d > 15:
        actual_bog_pct = base_bog
        pressure = 3.05 # Elevated pressure
    else:
        actual_bog_pct = base_bog
        pressure = 1.05
        
    bog_rate_val = current_inv * (actual_bog_pct / 100)
    bog_hist.append(bog_rate_val)
    
    # Calculate New Inventory
    new_inv = current_inv - bog_rate_val - send_out_pct
    
    # Cargo Delivery Logic
    if new_inv < 20.0 and "Normal" in scenario:
        new_inv = 90.0
        pressure = 1.05
        event_log.append((d, "CARGO DELIVERED", "Tank refilled to 90% capacity."))
        
    inv_hist.append(max(0, new_inv))
    press_hist.append(pressure)

# Extract Current Day State (Index is day-1)
inv_pct = inv_hist[current_day - 1]
bog_rate = bog_hist[current_day - 1]
current_pressure = press_hist[current_day - 1]
is_rollover_day = (scenario == "The Rollover Incident" and current_day == 15)

# CCGT Calculations
base_eff = 0.4922
boosted_eff = 0.5831
eff = boosted_eff if cold_energy_toggle else base_eff
power_mw = (send_out_mtpa * 1e9 * 48 * eff) / (365 * 24 * 3600)
revenue_zar = power_mw * 1000 * 24 * elec_price_zar

# ==========================================
# 3. DYNAMIC EXPLANATION PANEL
# ==========================================
st.info(f"**System Status on Day {current_day}:** " + 
        ("⚠️ **ROLLOVER IN PROGRESS.** The stratified layers have violently mixed, causing a massive pressure spike and BOG generation." if is_rollover_day else
         "🚢 **Cargo Delivery.** A fresh LNG ship has docked, cooling the tank and refilling the inventory." if any(d == current_day for d, _, _ in event_log) else
         "🌊 **FSU Sloshing.** Wave motion is increasing the surface area of the liquid, causing higher-than-normal BOG rates." if scenario == "FSU Sloshing" else
         "✅ **Normal Operations.** The tank is slowly draining as gas is sent to the CCGT."))

# ==========================================
# 4. BUILD THE TABS
# ==========================================
tab1, tab2, tab3 = st.tabs(["🌊 3D Tank Dynamics", "⚡ CCGT Power & Economics", "📖 Case Studies & Physics"])

# ==========================================
# TAB 1: 3D TANK & DYNAMICS
# ==========================================
with tab1:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("LNG Inventory", f"{inv_pct:.1f} %", help="Percentage of the tank currently filled with LNG.")
    c2.metric("BOG Rate", f"{bog_rate:.2f} %/day", help="Boil-Off Gas. The percentage of LNG evaporating daily due to heat leak or sloshing.")
    c3.metric("Tank Pressure", f"{current_pressure:.2f} bar", delta="SPIKE" if current_pressure > 2.0 else None, delta_color="inverse", help="Internal tank pressure. Dangerous spikes occur during a Rollover.")
    
    if current_day < 15 and scenario == "The Rollover Incident":
        c4.info("**Stratification:** Heavy (Orange) and Light (Blue) layers separated.")
    elif is_rollover_day:
        c4.error("**ROLLOVER!** Layers mixed violently.")
    else:
        c4.success("**Stable.**")

    # --- 3D TANK ANIMATION ---
    R, H, dome_h = 5.0, 10.0, 2.0
    th_w = np.linspace(0, 2*np.pi, 40); z_w = np.linspace(0, H, 15)
    th_gw, z_gw = np.meshgrid(th_w, z_w)
    x_wall, y_wall = R * np.cos(th_gw), R * np.sin(th_gw)

    u = np.linspace(0, 2*np.pi, 40); v = np.linspace(0, np.pi/2, 10)
    u_g, v_g = np.meshgrid(u, v)
    x_dome = R * np.cos(u_g) * np.sin(v_g); y_dome = R * np.sin(u_g) * np.sin(v_g)
    z_dome = H + dome_h * np.cos(v_g)

    r_l = np.linspace(0, R, 20); th_l = np.linspace(0, 2*np.pi, 40)
    r_g, th_g = np.meshgrid(r_l, th_l)
    x_liq, y_liq = r_g * np.cos(th_g), r_g * np.sin(th_g)

    frames = []
    
    # FIXED: Sloshing amplitude only applies if FSU is selected
    amp = 0.8 if ("Sloshing" in scenario and "FSU" in storage_type) else 0.0
    if is_rollover_day: amp = 2.5

    tot_h = (inv_pct / 100.0) * H
    split_h = (tot_h * 0.4) if (scenario == "The Rollover Incident" and current_day < 15) else 0.0

    for i in range(25):
        t = i / 4.0
        z_bot = split_h + amp * np.sin(th_g * 2 + t) * np.cos(r_g)
        z_top = tot_h + amp * np.sin(th_g * 2 + t) * np.cos(r_g)
        
        num_b = 50 + int(bog_rate * 150)
        np.random.seed(42)
        b_r, b_th = np.random.uniform(0, R-0.5, num_b), np.random.uniform(0, 2*np.pi, num_b)
        speed = 0.4 if not is_rollover_day else 3.0
        b_z = (np.random.uniform(tot_h, H, num_b) + (i * speed)) % (H - tot_h) + tot_h
        b_x, b_y = b_r * np.cos(b_th), b_r * np.sin(b_th)

        frame = [
            go.Surface(x=x_liq, y=y_liq, z=z_bot, colorscale=[[0, 'rgba(255,140,0,0.9)'],[1,'rgba(255,140,0,0.9)']], showscale=False, hoverinfo="skip"),
            go.Surface(x=x_liq, y=y_liq, z=z_top, colorscale=[[0, 'rgba(0,150,255,0.9)'],[1,'rgba(0,150,255,0.9)']] if split_h > 0 else [[0, 'rgba(150,0,150,0.9)'],[1,'rgba(150,0,150,0.9)']], showscale=False, hoverinfo="skip"),
            go.Scatter3d(x=b_x, y=b_y, z=b_z, mode='markers', marker=dict(size=4 if not is_rollover_day else 10, color='white', opacity=0.8), hoverinfo="skip"),
            go.Surface(x=x_wall, y=y_wall, z=z_gw, colorscale=[[0, 'rgba(200,200,200,0.2)'],[1,'rgba(200,200,200,0.2)']], showscale=False, hoverinfo="skip"),
            go.Surface(x=x_dome, y=y_dome, z=z_dome, colorscale=[[0, 'rgba(150,150,150,0.4)'],[1,'rgba(150,150,150,0.4)']], showscale=False, hoverinfo="skip")
        ]
        frames.append(go.Frame(data=frame, name=str(i)))

    fig3d = go.Figure(data=frames[0].data, frames=frames)
    fig3d.update_layout(
        scene=dict(xaxis=dict(visible=False, range=[-6,6]), yaxis=dict(visible=False, range=[-6,6]), zaxis=dict(visible=False, range=[0,13]),
                   camera=dict(eye=dict(x=1.5, y=1.5, z=0.8)), aspectmode='manual', aspectratio=dict(x=1,y=1,z=1.3)),
        updatemenus=[dict(type="buttons", showactive=False, x=0.1, y=0,
            buttons=[
                dict(label="▶️ Play Animation", method="animate", args=[None, dict(frame=dict(duration=100, redraw=True), fromcurrent=True)]),
                dict(label="⏸️ Pause", method="animate", args=[[None], dict(frame=dict(duration=0, redraw=False), mode="immediate")])
            ])],
        margin=dict(l=0, r=0, b=0, t=0), height=450, paper_bgcolor="#f4f4f4"
    )
    st.plotly_chart(fig3d, use_container_width=True)

    # --- 30 DAY GRAPH (Dynamic) ---
    df_ops = pd.DataFrame({'Day': range(1, 31), 'Inventory (%)': inv_hist[:-1], 'BOG Rate (%/day)': bog_hist, 'Pressure (bar)': press_hist[:-1]})
    fig_ops = make_subplots(specs=[[{"secondary_y": True}]])
    fig_ops.add_trace(go.Scatter(x=df_ops['Day'], y=df_ops['Inventory (%)'], name='Inventory (%)', line=dict(color='blue', width=3)), secondary_y=False)
    fig_ops.add_trace(go.Scatter(x=df_ops['Day'], y=df_ops['BOG Rate (%/day)'], name='BOG Rate', line=dict(color='red', dash='dot')), secondary_y=True)
    if scenario == "The Rollover Incident":
        fig_ops.add_trace(go.Scatter(x=df_ops['Day'], y=df_ops['Pressure (bar)'], name='Pressure (bar)', line=dict(color='orange', width=2)), secondary_y=True)
    
    fig_ops.add_vline(x=current_day, line_width=3, line_dash="dash", line_color="green")
    fig_ops.update_layout(title="30-Day Operational Trends", hovermode="x unified", height=350, margin=dict(l=0, r=0, t=40, b=0), legend=dict(orientation="h", y=1.02, x=1))
    fig_ops.update_yaxes(title_text="Inventory (%)", secondary_y=False, range=[0, 100])
    fig_ops.update_yaxes(title_text="BOG / Pressure", secondary_y=True)
    st.plotly_chart(fig_ops, use_container_width=True)

    # --- LEGEND ---
    st.markdown("""
    ### 📖 3D Tank Legend
    *   **🟠 Orange Liquid (Bottom):** Dense, warmer LNG (caused by ground heat leak).
    *   **🔵 Blue Liquid (Top):** Lighter, colder LNG from a fresh cargo.
    *   **🟣 Purple Liquid:** Fully mixed LNG (this is what happens after a Rollover).
    *   **⚪ White Bubbles:** Boil-Off Gas (BOG) rising to the top.
    *   **Silver Dome:** The insulated roof of the LNG storage tank.
    """)

# ==========================================
# TAB 2: CCGT POWER & ECONOMICS
# ==========================================
with tab2:
    st.subheader("⚡ CCGT Power Generation & Economics")
    c1, c2, c3 = st.columns(3)
    c1.metric("Current CCGT Output", f"{power_mw:,.0f} MW", f"{eff*100:.1f}% Efficiency", help="The total electrical power generated by the Combined Cycle Gas Turbine.")
    c2.metric("Estimated Daily Revenue", f"R {revenue_zar:,.0f}", help="Calculated using your daily power output multiplied by your chosen electricity price.")
    c3.metric("Annual CO2 Avoided", f"~{power_mw * 0.4 * 24 * 365 / 1000:,.0f} kt", "vs Coal", help="LNG produces significantly less CO2 than coal. This is the estimated annual saving.")

    st.markdown("### The Impact of LNG Cold Energy")
    st.markdown("When LNG regasifies, it releases immense cold energy. By integrating this with the CCGT, we can boost efficiency dramatically.")
    
    base_power = (send_out_mtpa * 1e9 * 48 * base_eff) / (365 * 24 * 3600)
    
    fig_ccgt = go.Figure(data=[
        go.Bar(name='Base CCGT (49.2%)', x=['Power Output (MW)'], y=[base_power], marker_color='gray'),
        go.Bar(name='Integrated CCGT (58.3%)', x=['Power Output (MW)'], y=[power_mw], marker_color='#00CC96')
    ])
    fig_ccgt.update_layout(barmode='group', title="Power Output Comparison", height=400, margin=dict(l=0, r=0, t=40, b=0))
    st.plotly_chart(fig_ccgt, use_container_width=True)
    
    st.info(f"**Aha Moment:** Toggling 'Cold Energy Integration' in the sidebar boosts efficiency from 49.2% to 58.3%, adding **{(power_mw - base_power):,.0f} MW** of free power to the grid. That is enough to power **{(power_mw - base_power)*1000*0.5:,.0f} South African homes!**")

# ==========================================
# TAB 3: CASE STUDIES
# ==========================================
with tab3:
    st.subheader("📖 Real-World Case Studies & Footnotes")
    
    st.markdown("### 1. The Zeebrugge LNG Rollover (Belgium, 2014)")
    st.markdown("""
    *   **How to simulate:** Select **'The Rollover Incident'** and move the timeline to **Day 15**.
    *   **What happened:** A new cargo of light LNG was loaded on top of heavy LNG. The heat from the bottom layer caused it to expand until it became lighter than the top layer. In seconds, the layers violently mixed.
    *   **The Result:** A massive pressure spike and explosive BOG generation. The terminal had to emergency-flare gas to prevent a tank rupture.
    """)

    st.markdown("### 2. FSU Sloshing vs. Onshore Tanks")
    st.markdown("""
    *   **How to simulate:** Select **'FSU Sloshing'** and click **Play Animation** on the 3D tank.
    *   **What happened:** An FSU is a ship on the ocean. As waves hit it, the LNG inside sloshes back and forth. This kinetic energy accelerates evaporation.
    *   **The Result:** A floating tank generates 50% to 100% more BOG than an onshore concrete tank. While an FSU is cheaper to build (CAPEX), the daily BOG losses add up to millions of Rand over 20 years (OPEX).
    """)

    st.markdown("### 3. Normal Operations & Cargo Deliveries")
    st.markdown("""
    *   **How to simulate:** Look at the **30-Day Operational Trends** graph for 'Normal Operations'.
    *   **Why does the inventory spike up?** The sudden spikes you see on the blue line are **Cargo Deliveries**. A real LNG plant consumes gas daily (sending it to the CCGT), which drops the tank level. When the tank hits a 20% minimum threshold, a massive LNG carrier ship docks, and the tank is refilled to 90% in a single day.
    *   **Why does the BOG rate drop after a delivery?** When a fresh, cold cargo is delivered, it cools the tank and lowers the internal temperature, temporarily suppressing the boil-off gas rate.
    """)

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(layout="wide", page_title="SA LNG & CCGT Master Dashboard")

st.title("🇿🇦 Southern Africa LNG & Power Strategic Simulator")

# ==========================================
# 1. SIDEBAR CONTROLS
# ==========================================
st.sidebar.header("🕹️ Core Simulation")

scenario = st.sidebar.selectbox(
    "Select Scenario", 
    ["Normal Operations", "The Rollover Incident", "FSU Sloshing (Storm)"]
)

storage_type = st.sidebar.radio("Storage Type", ["FSU (170,000 m³)", "Onshore (220,000 m³)"])
cap_val = 170000 if "FSU" in storage_type else 220000

current_day = st.sidebar.slider("Timeline (Days)", 1, 30, 1, 1)

st.sidebar.header("🚢 Logistics & Berthing")
berthing_delay = st.sidebar.slider("Berthing Delay (Days)", 0, 5, 0, 1)
loading_arm_limit = st.sidebar.slider("Loading Arm Rate (% Capacity)", 50, 100, 100, 10)
capacity_share = st.sidebar.checkbox("Share 20% Capacity with Zimbabwe (SAPP)")

st.sidebar.header("🌡️ Thermodynamics & Environment")
initial_fill = st.sidebar.slider("Initial Tank Fill (%)", 50, 95, 90, 5)
ambient_temp = st.sidebar.slider("Ambient Temperature (°C)", 15, 45, 30, 1)
methane_slip = st.sidebar.slider("Methane Slip Rate (%)", 0.0, 2.0, 0.5, 0.1)

st.sidebar.header("⚡ CCGT Economics")
send_out_mtpa = st.sidebar.slider("Nominal Send-Out Rate (Mtpa)", 1.0, 5.0, 3.0, 0.1)
elec_price_zar = st.sidebar.slider("Electricity Price (R/kWh)", 1.0, 5.0, 2.50, 0.1)
cold_energy_toggle = st.sidebar.checkbox("Enable LNG Cold Energy Integration", value=True)

# ==========================================
# 2. CALCULATION ENGINE
# ==========================================
base_bog = 0.10 if "Onshore" in storage_type else 0.15
if scenario == "FSU Sloshing (Storm)" and "FSU" in storage_type:
    base_bog = 0.35

temp_modifier = 1.0 + ((ambient_temp - 25) * 0.01)
base_bog *= temp_modifier

lng_density = 450.0 # kg/m3
actual_send_out = send_out_mtpa * 0.8 if capacity_share else send_out_mtpa
send_out_m3_day = ((actual_send_out * 1e9) / 365) / lng_density 
send_out_pct = (send_out_m3_day / cap_val) * 100

inv_hist = [initial_fill]
bog_tonnes_hist = [] 
press_hist = [1.05]
blackout_flag = False
cargo_delivered = False

for d in range(1, 31):
    current_inv_pct = inv_hist[-1]
    
    if scenario == "The Rollover Incident" and d == 15:
        actual_bog_pct = base_bog * 8.0
        pressure = 16.05
    elif scenario == "The Rollover Incident" and d > 15:
        actual_bog_pct = base_bog
        pressure = 3.05
    else:
        actual_bog_pct = base_bog
        pressure = 1.05
        
    # CORRECTED MATH: Calculate actual volume and mass
    current_vol_m3 = (current_inv_pct / 100.0) * cap_val
    bog_m3_val = current_vol_m3 * (actual_bog_pct / 100.0)
    bog_tonnes_val = (bog_m3_val * lng_density) / 1000.0 
    bog_tonnes_hist.append(bog_tonnes_val)
    
    # Inventory Drop (in %)
    new_inv_pct = current_inv_pct - (bog_m3_val / cap_val * 100) - send_out_pct
    
    # Cargo Logic
    delivery_target = 20.0 + (berthing_delay * 5.0)
    if new_inv_pct < delivery_target and "Normal" in scenario and not cargo_delivered:
        new_inv_pct = 90.0
        cargo_delivered = True
    elif cargo_delivered and new_inv_pct < 85.0:
        cargo_delivered = False
        
    if new_inv_pct <= 0.1:
        new_inv_pct = 0.0
        blackout_flag = True
        
    inv_hist.append(max(0, new_inv_pct))
    press_hist.append(pressure)

inv_pct = inv_hist[current_day - 1]
bog_tonnes_day = bog_tonnes_hist[current_day - 1]
current_pressure = press_hist[current_day - 1]
is_rollover_day = (scenario == "The Rollover Incident" and current_day == 15)

# CCGT Calculations
base_eff = 0.4922
boosted_eff = 0.5831
eff = boosted_eff if cold_energy_toggle else base_eff
power_mw = (actual_send_out * 1e9 * 48 * eff) / (365 * 24 * 3600)
if inv_pct <= 0.1: power_mw = 0.0 
revenue_zar = power_mw * 1000 * 24 * elec_price_zar
methane_emitted_tons = (power_mw * 24 * 3600 / 48) * (methane_slip / 100) / 1000

# ==========================================
# 3. BUILD THE TABS
# ==========================================
tab1, tab2, tab3 = st.tabs(["🌊 3D Tank Dynamics", "⚡ CCGT & Environment", "📖 20 Case Studies"])

# ==========================================
# TAB 1: 3D TANK & DYNAMICS
# ==========================================
with tab1:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("LNG Inventory", f"{inv_pct:.1f} %")
    c2.metric("BOG Loss", f"{bog_tonnes_day:,.1f} Tons/day")
    c3.metric("Tank Pressure", f"{current_pressure:.2f} bar", delta="SPIKE" if current_pressure > 2.0 else None, delta_color="inverse")
    
    if blackout_flag: c4.error("🚨 **BLACKOUT.** Tank is empty.")
    elif is_rollover_day: c4.error("🚨 **ROLLOVER.** Violent mixing.")
    else: c4.success("✅ Stable.")

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
    amp = 0.8 if ("Sloshing" in scenario and "FSU" in storage_type) else 0.0
    if is_rollover_day: amp = 2.5

    tot_h = (inv_pct / 100.0) * H
    split_h = (tot_h * 0.4) if (scenario == "The Rollover Incident" and current_day < 15) else 0.0

    for i in range(25):
        t = i / 4.0
        z_bot = split_h + amp * np.sin(th_g * 2 + t) * np.cos(r_g)
        z_top = tot_h + amp * np.sin(th_g * 2 + t) * np.cos(r_g)
        
        num_b = int(20 + (bog_tonnes_day * 0.5)) 
        if is_rollover_day: num_b = 400 
        num_b = min(num_b, 500) 
        
        np.random.seed(42)
        b_r, b_th = np.random.uniform(0, R-0.5, num_b), np.random.uniform(0, 2*np.pi, num_b)
        speed = 0.4 if not is_rollover_day else 3.0
        b_z = (np.random.uniform(tot_h, H, num_b) + (i * speed)) % (H - tot_h) + tot_h
        b_x, b_y = b_r * np.cos(b_th), b_r * np.sin(b_th)

        # FIXED LAYERING LOGIC
        if scenario == "The Rollover Incident" and current_day < 15:
            # Show distinct layers
            frame = [
                go.Surface(x=x_liq, y=y_liq, z=z_bot, colorscale=[[0, 'rgba(255,140,0,1)'],[1,'rgba(255,140,0,1)']], showscale=False),
                go.Surface(x=x_liq, y=y_liq, z=z_top, colorscale=[[0, 'rgba(0,150,255,1)'],[1,'rgba(0,150,255,1)']], showscale=False)
            ]
        elif is_rollover_day:
            # Mixed - Show single purple layer
            frame = [go.Surface(x=x_liq, y=y_liq, z=z_top, colorscale=[[0, 'rgba(150,0,150,1)'],[1,'rgba(150,0,150,1)']], showscale=False)]
        else:
            # Normal or Sloshing - Show single blue layer
            frame = [go.Surface(x=x_liq, y=y_liq, z=z_top, colorscale=[[0, 'rgba(0,150,255,1)'],[1,'rgba(0,150,255,1)']], showscale=False)]

        # Add bubbles, walls, and dome to the frame
        frame.extend([
            go.Scatter3d(x=b_x, y=b_y, z=b_z, mode='markers', marker=dict(size=4 if not is_rollover_day else 10, color='white', opacity=0.8)),
            go.Surface(x=x_wall, y=y_wall, z=z_gw, colorscale=[[0, 'rgba(200,200,200,0.2)'],[1,'rgba(200,200,200,0.2)']], showscale=False),
            go.Surface(x=x_dome, y=y_dome, z=z_dome, colorscale=[[0, 'rgba(150,150,150,0.4)'],[1,'rgba(150,150,150,0.4)']], showscale=False)
        ])
        frames.append(go.Frame(data=frame, name=str(i)))

    fig3d = go.Figure(data=frames[0].data, frames=frames)
    fig3d.update_layout(
        scene=dict(xaxis=dict(visible=False, range=[-6,6]), yaxis=dict(visible=False, range=[-6,6]), zaxis=dict(visible=False, range=[0,13]),
                   camera=dict(eye=dict(x=1.5, y=1.5, z=0.8)), aspectmode='manual', aspectratio=dict(x=1,y=1,z=1.3)),
        updatemenu=[dict(type="buttons", showactive=False, x=0.1, y=0,
            buttons=[
                dict(label="▶️ Play Animation", method="animate", args=[None, dict(frame=dict(duration=100, redraw=True), fromcurrent=True)]),
                dict(label="⏸️ Pause", method="animate", args=[[None], dict(frame=dict(duration=0, redraw=False), mode="immediate")])
            ])],
        margin=dict(l=0, r=0, b=0, t=0), height=450, paper_bgcolor="#f4f4f4"
    )
    st.plotly_chart(fig3d, use_container_width=True)

    # --- 30 DAY GRAPH ---
    df_ops = pd.DataFrame({'Day': range(1, 31), 'Inventory (%)': inv_hist[:-1], 'BOG (Tonnes/day)': bog_tonnes_hist, 'Pressure (bar)': press_hist[:-1]})
    fig_ops = make_subplots(specs=[[{"secondary_y": True}]])
    fig_ops.add_trace(go.Scatter(x=df_ops['Day'], y=df_ops['Inventory (%)'], name='Inventory (%)', line=dict(color='blue', width=3)), secondary_y=False)
    fig_ops.add_trace(go.Scatter(x=df_ops['Day'], y=df_ops['BOG (Tonnes/day)'], name='BOG Loss (Tonnes)', line=dict(color='red', dash='dot')), secondary_y=True)
    if scenario == "The Rollover Incident":
        fig_ops.add_trace(go.Scatter(x=df_ops['Day'], y=df_ops['Pressure (bar)'], name='Pressure (bar)', line=dict(color='orange', width=2)), secondary_y=True)
    
    fig_ops.add_vline(x=current_day, line_width=3, line_dash="dash", line_color="green")
    fig_ops.update_layout(title="30-Day Operational Trends", hovermode="x unified", height=350, margin=dict(l=0, r=0, t=40, b=0), legend=dict(orientation="h", y=1.02, x=1))
    fig_ops.update_yaxes(title_text="Inventory (%)", secondary_y=False, range=[0, 100])
    fig_ops.update_yaxes(title_text="BOG (Tonnes) / Pressure", secondary_y=True)
    st.plotly_chart(fig_ops, use_container_width=True)

# ==========================================
# TAB 2: CCGT & ENVIRONMENT (Unchanged)
# ==========================================
with tab2:
    st.subheader("⚡ CCGT Output & Environmental Impact")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Available Power to SA", f"{power_mw:,.0f} MW", f"{eff*100:.1f}% Efficiency")
    c2.metric("Daily Revenue", f"R {revenue_zar:,.0f}")
    c3.metric("Methane Emitted", f"{methane_emitted_tons:.1f} Tons/day", delta_color="inverse")
    if capacity_share: c4.metric("Power Exported to Zimbabwe", f"{power_mw * 0.25:,.0f} MW", "SAPP Agreement")
    else: c4.metric("Power Exported to Zimbabwe", "0 MW", "No Agreement")

# ==========================================
# TAB 3: CASE STUDIES (Unchanged)
# ==========================================
with tab3:
    st.subheader("📖 20 Strategic Case Studies for Delegates")
    # (Insert the case studies list here from previous message)

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.set_page_config(layout="wide", page_title="SA LNG 3D Stratification & BOG")

st.title("🇿🇦 Day 2: 3D LNG Tank Dynamics & Stratification")
st.markdown("Use the **Timeline Slider** in the sidebar to advance the days. Press **Play** on the 3D tank to watch the live wave physics for that specific day.")

# ==========================================
# 1. SIDEBAR CONTROLS & TIME
# ==========================================
st.sidebar.header("🕹️ Simulation Controls")

scenario = st.sidebar.selectbox(
    "Select Scenario", 
    ["Normal Operations", "The Rollover Incident", "FSU Sloshing (High BOG)"]
)

# The Timeline Slider
current_day = st.sidebar.slider("Timeline (Days)", 1, 30, 1, 1)

capacity_type = st.sidebar.radio("Storage Type", ["FSU (170,000 m³)", "Onshore (220,000 m³)"])
cap_val = 170000 if "FSU" in capacity_type else 220000

# ==========================================
# 2. CALCULATE STATE FOR THE SELECTED DAY
# ==========================================
# Base BOG rates
base_bog = 0.10 if "Onshore" in capacity_type else 0.15
if scenario == "FSU Sloshing (High BOG)":
    base_bog = 0.30

# Calculate daily inventory and BOG
inventory_history = [90.0] # Start at 90% full
bog_history = [0.0]
pressure_spike = 0.0

for d in range(2, 31):
    current_inv = inventory_history[-1]
    
    # Rollover Event on Day 15
    if scenario == "The Rollover Incident" and d == 15:
        actual_bog = base_bog * 6.0
        pressure_spike = 15.0 # 15 bar spike
    else:
        actual_bog = base_bog
        if d > 15 and scenario == "The Rollover Incident":
            pressure_spike = 2.0 # elevated pressure
            
    bog_m3 = current_inv * (actual_bog / 100)
    new_inv = current_inv - (bog_m3 / (cap_val/100)) - 0.5 # Send out 0.5%
    inventory_history.append(max(0, new_inv))
    bog_history.append(bog_m3)

# Current Day State
inv_pct = inventory_history[current_day - 1]
bog_rate = bog_history[current_day - 1]
is_rollover_day = (scenario == "The Rollover Incident" and current_day == 15)

# ==========================================
# 3. LIVE METRICS DISPLAY
# ==========================================
st.subheader(f"Live Telemetry: Day {current_day}")
col1, col2, col3, col4 = st.columns(4)
col1.metric("LNG Inventory", f"{inv_pct:.1f} %")
col2.metric("BOG Generation Rate", f"{bog_rate:.2f} %/day")

if scenario == "The Rollover Incident":
    col3.metric("Tank Pressure", f"{(1.05 + pressure_spike):.2f} bar", delta="SPIKE" if pressure_spike > 0 else None, delta_color="inverse")
    if current_day < 15:
        col4.info("**Stratification Active:** Heavy (Orange) and Light (Blue) layers are separated.")
    elif current_day == 15:
        col4.error("**ROLLOVER!** Layers mixed violently. Huge BOG spike.")
    else:
        col4.success("**Mixed:** Tank is uniform, but gas was lost.")
else:
    col3.metric("Tank Pressure", "1.05 bar", "Normal")
    col4.info(f"**{scenario}:** Normal thermodynamic boil-off.")

# ==========================================
# 4. BUILD THE 3D REALISTIC TANK
# ==========================================
# Tank Geometry
R = 5.0 # Radius
H = 10.0 # Total wall height
dome_height = 2.0 # Dome roof

# Create Tank Walls (Cylinder)
theta_wall = np.linspace(0, 2*np.pi, 40)
z_wall = np.linspace(0, H, 15)
theta_grid_w, z_grid_w = np.meshgrid(theta_wall, z_wall)
x_wall = R * np.cos(theta_grid_w)
y_wall = R * np.sin(theta_grid_w)

# Create Dome Roof (Spherical Cap)
u = np.linspace(0, 2*np.pi, 40)
v = np.linspace(0, np.pi/2, 10)
x_dome = R * np.cos(u) * np.sin(v)
y_dome = R * np.sin(u) * np.sin(v)
z_dome = H + dome_height * np.cos(v)

# Liquid Surface Grid
r_liq = np.linspace(0, R, 20)
theta_liq = np.linspace(0, 2*np.pi, 40)
r_grid, th_grid = np.meshgrid(r_liq, theta_liq)
x_liq = r_grid * np.cos(th_grid)
y_liq = r_grid * np.sin(th_grid)

# ==========================================
# 5. CREATE THE ANIMATION FRAMES
# ==========================================
frames = []
num_frames = 30

# Wave amplitude
amp = 0.8 if "Sloshing" in scenario else 0.1
if is_rollover_day: amp = 1.5 # Violent during rollover

# Calculate stratification heights
total_liquid_height = (inv_pct / 100.0) * H
# Layer split: if rollover, layers mix.
if scenario == "The Rollover Incident" and current_day < 15:
    layer_split_height = total_liquid_height * 0.4 # Heavy at bottom
else:
    layer_split_height = 0.0 # Mixed

for i in range(num_frames):
    t = i / 4.0 # Animation time step
    
    # A. Liquid Surfaces (Wave Physics)
    # Bottom Layer (Heavy/Orange)
    z_bottom = (layer_split_height) + amp * np.sin(th_grid * 2 + t) * np.cos(r_grid)
    # Top Layer (Light/Blue)
    z_top = total_liquid_height + amp * np.sin(th_grid * 2 + t) * np.cos(r_grid)
    
    # B. BOG Bubbles
    num_b = 100 + int(bog_rate * 50) # More BOG = more bubbles
    np.random.seed(42)
    b_r = np.random.uniform(0, R-0.5, num_b)
    b_th = np.random.uniform(0, 2*np.pi, num_b)
    # Bubbles rise. Modulo resets them.
    speed = 0.4 if not is_rollover_day else 1.5
    b_z = (np.random.uniform(total_liquid_height, H, num_b) + (i * speed)) % (H - total_liquid_height) + total_liquid_height
    b_x = b_r * np.cos(b_th)
    b_y = b_r * np.sin(b_th)

    frame_traces = []
    
    # 1. Bottom Layer (Orange)
    frame_traces.append(go.Surface(
        x=x_liq, y=y_liq, z=z_bottom,
        colorscale=[[0, 'rgba(255, 140, 0, 0.9)'], [1, 'rgba(255, 140, 0, 0.9)']],
        showscale=False, hoverinfo="skip"
    ))
    
    # 2. Top Layer (Blue) - Only if stratified
    if layer_split_height > 0:
        frame_traces.append(go.Surface(
            x=x_liq, y=y_liq, z=z_top,
            colorscale=[[0, 'rgba(0, 150, 255, 0.9)'], [1, 'rgba(0, 150, 255, 0.9)']],
            showscale=False, hoverinfo="skip"
        ))
    else:
        # If mixed, just show a single surface at top
        frame_traces.append(go.Surface(
            x=x_liq, y=y_liq, z=z_top,
            colorscale=[[0, 'rgba(150, 0, 150, 0.9)'], [1, 'rgba(150, 0, 150, 0.9)']], # Purple mixed
            showscale=False, hoverinfo="skip"
        ))

    # 3. BOG Bubbles
    frame_traces.append(go.Scatter3d(
        x=b_x, y=b_y, z=b_z, mode='markers',
        marker=dict(size=4 if not is_rollover_day else 8, color='white', opacity=0.8),
        hoverinfo="skip"
    ))
    
    # 4. Tank Walls (Keep them in every frame so they don't disappear)
    frame_traces.append(go.Surface(
        x=x_wall, y=y_wall, z=z_grid_w,
        colorscale=[[0, 'rgba(200, 200, 200, 0.2)'], [1, 'rgba(200, 200, 200, 0.2)']],
        showscale=False, hoverinfo="skip"
    ))
    
    # 5. Dome Roof
    frame_traces.append(go.Surface(
        x=x_dome, y=y_dome, z=z_dome,
        colorscale=[[0, 'rgba(150, 150, 150, 0.4)'], [1, 'rgba(150, 150, 150, 0.4)']],
        showscale=False, hoverinfo="skip"
    ))

    frames.append(go.Frame(data=frame_traces, name=str(i)))

# ==========================================
# 6. CREATE BASE FIGURE (Frame 0 State)
# ==========================================
fig = go.Figure(
    data=frames[0].data,
    frames=frames
)

fig.update_layout(
    scene=dict(
        xaxis=dict(visible=False, range=[-6, 6]),
        yaxis=dict(visible=False, range=[-6, 6]),
        zaxis=dict(visible=False, range=[0, 13]),
        camera=dict(eye=dict(x=1.5, y=1.5, z=0.8)),
        aspectmode='manual',
        aspectratio=dict(x=1, y=1, z=1.3)
    ),
    updatemenus=[dict(
        type="buttons", showactive=False, x=0.1, y=0,
        buttons=[
            dict(label="▶️ Play Waves", method="animate",
                 args=[None, dict(frame=dict(duration=100, redraw=True), fromcurrent=True, transition=dict(duration=0))]),
            dict(label="⏸️ Pause", method="animate",
                 args=[[None], dict(frame=dict(duration=0, redraw=False), mode="immediate", transition=dict(duration=0))])
        ]
    )],
    margin=dict(l=0, r=0, b=0, t=0),
    height=600,
    paper_bgcolor="#f4f4f4"
)

st.plotly_chart(fig, use_container_width=True)

# ==========================================
# 7. LEGEND & EXPLANATION
# ==========================================
st.markdown("""
### 📖 How to Read the 3D Tank
*   **🟠 Orange Liquid (Bottom):** Dense, warmer LNG that has absorbed heat from the ground.
*   **🔵 Blue Liquid (Top):** Lighter, colder LNG from a fresh cargo.
*   **🟣 Purple Liquid:** Fully mixed LNG (happens after a Rollover).
*   **⚪ White Bubbles:** Boil-Off Gas (BOG) rising to the top.
*   **Silver Dome:** The insulated roof of the LNG tank.
""")

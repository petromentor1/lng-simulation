import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(layout="wide", page_title="SA LNG 3D Tank Dynamics")

st.title("🇿🇦 Day 2: 3D LNG Tank Dynamics & Stratification")

# ==========================================
# 1. SIDEBAR CONTROLS & TIME
# ==========================================
st.sidebar.header("🕹️ Simulation Controls")

scenario = st.sidebar.selectbox(
    "Select Scenario", 
    ["Normal Operations", "The Rollover Incident", "FSU Sloshing (High BOG)"]
)

current_day = st.sidebar.slider("Timeline (Days)", 1, 30, 1, 1)

capacity_type = st.sidebar.radio("Storage Type", ["FSU (170,000 m³)", "Onshore (220,000 m³)"])
cap_val = 170000 if "FSU" in capacity_type else 220000

# ==========================================
# 2. CALCULATE STATE FOR ALL 30 DAYS
# ==========================================
base_bog = 0.10 if "Onshore" in capacity_type else 0.15
if scenario == "FSU Sloshing (High BOG)" and "FSU" in capacity_type:
    base_bog = 0.30 # High sloshing only on FSU

inventory_history = [90.0]
bog_history = [0.0]
pressure_history = [1.05]

for d in range(2, 31):
    current_inv = inventory_history[-1]
    
    if scenario == "The Rollover Incident" and d == 15:
        actual_bog = base_bog * 6.0
        pressure = 16.05 # Massive spike
    elif scenario == "The Rollover Incident" and d > 15:
        actual_bog = base_bog
        pressure = 3.05 # Elevated after rollover
    else:
        actual_bog = base_bog
        pressure = 1.05
        
    bog_m3 = current_inv * (actual_bog / 100)
    new_inv = current_inv - (bog_m3 / (cap_val/100)) - 0.5
    inventory_history.append(max(0, new_inv))
    bog_history.append(bog_m3)
    pressure_history.append(pressure)

# Current Day State
inv_pct = inventory_history[current_day - 1]
bog_rate = bog_history[current_day - 1]
current_pressure = pressure_history[current_day - 1]
is_rollover_day = (scenario == "The Rollover Incident" and current_day == 15)

# ==========================================
# 3. LIVE METRICS DISPLAY
# ==========================================
st.subheader(f"Live Telemetry: Day {current_day}")
col1, col2, col3, col4 = st.columns(4)
col1.metric("LNG Inventory", f"{inv_pct:.1f} %")
col2.metric("BOG Rate", f"{bog_rate:.2f} %/day")
col3.metric("Tank Pressure", f"{current_pressure:.2f} bar", delta="SPIKE" if current_pressure > 2.0 else None, delta_color="inverse")

if current_day < 15 and scenario == "The Rollover Incident":
    col4.info("**Stratification Active:** Heavy (Orange) and Light (Blue) layers.")
elif is_rollover_day:
    col4.error("**ROLLOVER!** Layers mixed. Massive BOG & Pressure spike.")
else:
    col4.success("**Stable Operation.**")

# ==========================================
# 4. BUILD THE 3D REALISTIC TANK
# ==========================================
R, H, dome_height = 5.0, 10.0, 2.0

# Tank Walls
theta_wall = np.linspace(0, 2*np.pi, 40)
z_wall = np.linspace(0, H, 15)
theta_grid_w, z_grid_w = np.meshgrid(theta_wall, z_wall)
x_wall = R * np.cos(theta_grid_w)
y_wall = R * np.sin(theta_grid_w)

# Dome Roof
u = np.linspace(0, 2*np.pi, 40)
v = np.linspace(0, np.pi/2, 10)
u_grid, v_grid = np.meshgrid(u, v)
x_dome = R * np.cos(u_grid) * np.sin(v_grid)
y_dome = R * np.sin(u_grid) * np.sin(v_grid)
z_dome = H + dome_height * np.cos(v_grid)

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

# FIXED LOGIC: Onshore cannot slosh
amp = 0.8 if ("Sloshing" in scenario and "FSU" in capacity_type) else 0.05
if is_rollover_day: amp = 2.0 # Violent mixing

total_liquid_height = (inv_pct / 100.0) * H

# Stratification logic
if scenario == "The Rollover Incident" and current_day < 15:
    layer_split_height = total_liquid_height * 0.4
else:
    layer_split_height = 0.0

for i in range(num_frames):
    t = i / 4.0
    
    z_bottom = (layer_split_height) + amp * np.sin(th_grid * 2 + t) * np.cos(r_grid)
    z_top = total_liquid_height + amp * np.sin(th_grid * 2 + t) * np.cos(r_grid)
    
    # BOG Bubbles
    num_b = 50 + int(bog_rate * 100)
    np.random.seed(42)
    b_r = np.random.uniform(0, R-0.5, num_b)
    b_th = np.random.uniform(0, 2*np.pi, num_b)
    speed = 0.4 if not is_rollover_day else 2.0
    
    b_z = (np.random.uniform(total_liquid_height, H, num_b) + (i * speed)) % (H - total_liquid_height) + total_liquid_height
    b_x = b_r * np.cos(b_th)
    b_y = b_r * np.sin(b_th)

    frame_traces = [
        # 1. Bottom Layer
        go.Surface(x=x_liq, y=y_liq, z=z_bottom, colorscale=[[0, 'rgba(255, 140, 0, 0.9)'], [1, 'rgba(255, 140, 0, 0.9)']], showscale=False, hoverinfo="skip"),
        
        # 2. Top Layer
        go.Surface(x=x_liq, y=y_liq, z=z_top, 
                   colorscale=[[0, 'rgba(0, 150, 255, 0.9)'], [1, 'rgba(0, 150, 255, 0.9)']] if layer_split_height > 0 else [[0, 'rgba(150, 0, 150, 0.9)'], [1, 'rgba(150, 0, 150, 0.9)']], 
                   showscale=False, hoverinfo="skip"),
        
        # 3. BOG Bubbles
        go.Scatter3d(x=b_x, y=b_y, z=b_z, mode='markers', marker=dict(size=4 if not is_rollover_day else 8, color='white', opacity=0.8), hoverinfo="skip"),
        
        # 4. Tank Walls
        go.Surface(x=x_wall, y=y_wall, z=z_grid_w, colorscale=[[0, 'rgba(200, 200, 200, 0.2)'], [1, 'rgba(200, 200, 200, 0.2)']], showscale=False, hoverinfo="skip"),
        
        # 5. Dome Roof
        go.Surface(x=x_dome, y=y_dome, z=z_dome, colorscale=[[0, 'rgba(150, 150, 150, 0.4)'], [1, 'rgba(150, 150, 150, 0.4)']], showscale=False, hoverinfo="skip")
    ]
    frames.append(go.Frame(data=frame_traces, name=str(i)))

# ==========================================
# 6. CREATE BASE FIGURE
# ==========================================
fig = go.Figure(data=frames[0].data, frames=frames)
fig.update_layout(
    scene=dict(
        xaxis=dict(visible=False, range=[-6, 6]),
        yaxis=dict(visible=False, range=[-6, 6]),
        zaxis=dict(visible=False, range=[0, 13]),
        camera=dict(eye=dict(x=1.5, y=1.5, z=0.8)),
        aspectmode='manual', aspectratio=dict(x=1, y=1, z=1.3)
    ),
    updatemenus=[dict(
        type="buttons", showactive=False, x=0.1, y=0,
        buttons=[
            dict(label="▶️ Play Waves", method="animate", args=[None, dict(frame=dict(duration=100, redraw=True), fromcurrent=True, transition=dict(duration=0))]),
            dict(label="⏸️ Pause", method="animate", args=[[None], dict(frame=dict(duration=0, redraw=False), mode="immediate", transition=dict(duration=0))])
        ]
    )],
    margin=dict(l=0, r=0, b=0, t=0), height=500, paper_bgcolor="#f4f4f4"
)
st.plotly_chart(fig, use_container_width=True)

# ==========================================
# 7. TIME SERIES GRAPHS (With Spikes)
# ==========================================
st.markdown("### 📉 30-Day Operational Trends")
st.markdown("The **green dashed line** shows your current timeline position. Observe the massive spikes during the Rollover Incident.")

df = pd.DataFrame({
    'Day': range(1, 31),
    'Inventory (%)': inventory_history,
    'BOG Rate (%/day)': bog_history,
    'Pressure (bar)': pressure_history
})

# Create subplots with secondary y-axis
fig_graph = make_subplots(specs=[[{"secondary_y": True}]])

# Add Inventory
fig_graph.add_trace(go.Scatter(x=df['Day'], y=df['Inventory (%)'], name='Inventory (%)', line=dict(color='blue', width=3)), secondary_y=False)

# Add BOG Rate
fig_graph.add_trace(go.Scatter(x=df['Day'], y=df['BOG Rate (%/day)'], name='BOG Rate', line=dict(color='red', dash='dot')), secondary_y=True)

# Add Pressure (only if relevant)
if scenario == "The Rollover Incident":
    fig_graph.add_trace(go.Scatter(x=df['Day'], y=df['Pressure (bar)'], name='Pressure (bar)', line=dict(color='orange', width=2)), secondary_y=True)

# Add vertical line for current day
fig_graph.add_vline(x=current_day, line_width=3, line_dash="dash", line_color="green")

fig_graph.update_layout(
    title=f"Timeline: {scenario}",
    hovermode="x unified",
    height=400,
    margin=dict(l=0, r=0, t=40, b=0),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
)
fig_graph.update_yaxes(title_text="Inventory (%)", secondary_y=False, range=[0, 100])
fig_graph.update_yaxes(title_text="BOG Rate / Pressure", secondary_y=True)

st.plotly_chart(fig_graph, use_container_width=True)

# Legend
st.markdown("""
### 📖 3D Tank Legend
*   **🟠 Orange Liquid (Bottom):** Dense, warmer LNG.
*   **🔵 Blue Liquid (Top):** Lighter, colder LNG.
*   **🟣 Purple Liquid:** Fully mixed LNG (after Rollover).
*   **⚪ White Bubbles:** Boil-Off Gas (BOG).
*   **Silver Dome:** Insulated roof.
""")

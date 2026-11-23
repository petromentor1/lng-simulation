import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.set_page_config(layout="wide", page_title="SA LNG 3D Tank Dynamics")

st.title("🇿🇦 Day 2: 3D LNG Tank Simulation (BOG & Sloshing)")
st.markdown("Press the **Play button ▶️** below the 3D tank to watch the live movement of the Boil-Off Gas (BOG) bubbles and the sloshing liquid surface.")

# ==========================================
# 1. SIDEBAR CONTROLS
# ==========================================
st.sidebar.header("🎬 3D Animation Settings")

scenario = st.sidebar.selectbox(
    "Select Scenario", 
    ["Normal Operations", "The Rollover Incident", "FSU Sloshing (High BOG)"]
)

capacity_m3 = st.sidebar.radio("Storage Type", ["FSU (170,000 m³)", "Onshore (220,000 m³)"])

# ==========================================
# 2. GENERATE 3D GEOMETRY
# ==========================================
# Tank dimensions
tank_radius = 5.0
tank_height = 10.0
base_liquid_level = 6.0 if "Onshore" in capacity_m3 else 4.0

# Create the cylinder wall for the tank
theta = np.linspace(0, 2*np.pi, 60)
z_wall = np.linspace(0, tank_height, 20)
theta_grid, z_grid = np.meshgrid(theta, z_wall)
x_wall = tank_radius * np.cos(theta_grid)
y_wall = tank_radius * np.sin(theta_grid)

# Create the grid for the liquid surface
r_liq = np.linspace(0, tank_radius, 20)
theta_liq = np.linspace(0, 2*np.pi, 60)
r_grid, th_grid = np.meshgrid(r_liq, theta_liq)
x_liq = r_grid * np.cos(th_grid)
y_liq = r_grid * np.sin(th_grid)

# ==========================================
# 3. BUILD ANIMATION FRAMES
# ==========================================
frames = []
num_frames = 40 # Number of frames in the animation loop

# Define wave amplitude based on scenario
amplitude = 0.8 if "Sloshing" in scenario else 0.1

for i in range(num_frames):
    t = i / 5.0 # Time variable for wave motion
    
    # A. Animate Liquid Surface (Sloshing)
    # The wave moves as a function of time (t) and angle (th_grid)
    z_liq = base_liquid_level + amplitude * np.sin(th_grid * 2 + t) * np.cos(r_grid)
    
    # B. Animate BOG Particles (Rising bubbles)
    np.random.seed(42) # Keep random positions consistent across frames
    num_bubbles = 150
    # Generate random positions within the tank radius
    b_radius = np.random.uniform(0, tank_radius - 0.5, num_bubbles)
    b_theta = np.random.uniform(0, 2*np.pi, num_bubbles)
    
    # Move bubbles upward based on frame (i)
    # Modulo operator makes the bubbles reset at the top and fall to the bottom again
    b_z = (np.random.uniform(0, tank_height - base_liquid_level, num_bubbles) + (i * 0.5)) % (tank_height - base_liquid_level) + base_liquid_level
    
    b_x = b_radius * np.cos(b_theta)
    b_y = b_radius * np.sin(b_theta)

    # If Rollover, add a massive surge of bubbles
    if scenario == "The Rollover Incident" and i > 20:
        num_bubbles = 300
        b_z = (np.random.uniform(0, tank_height, num_bubbles) + (i * 1.5)) % tank_height
        b_x = np.random.uniform(-tank_radius+0.5, tank_radius-0.5, num_bubbles)
        b_y = np.random.uniform(-tank_radius+0.5, tank_radius-0.5, num_bubbles)
        
    # Create the frame
    frame = go.Frame(
        data=[
            # Trace 0: Liquid Surface
            go.Surface(
                x=x_liq, y=y_liq, z=z_liq,
                colorscale=[[0, 'rgba(0, 150, 255, 0.8)'], [1, 'rgba(0, 150, 255, 0.8)']],
                showscale=False, hoverinfo="skip", name="LNG Liquid"
            ),
            # Trace 1: BOG Bubbles
            go.Scatter3d(
                x=b_x, y=b_y, z=b_z,
                mode='markers',
                marker=dict(size=3, color='white', opacity=0.7),
                hoverinfo="skip", name="BOG Gas"
            )
        ],
        name=str(i)
    )
    frames.append(frame)

# ==========================================
# 4. CREATE THE BASE FIGURE
# ==========================================
fig = go.Figure(
    data=[
        # Initial Liquid Surface (Frame 0)
        go.Surface(
            x=x_liq, y=y_liq, z=base_liquid_level + np.zeros_like(x_liq),
            colorscale=[[0, 'rgba(0, 150, 255, 0.8)'], [1, 'rgba(0, 150, 255, 0.8)']],
            showscale=False, hoverinfo="skip", name="LNG Liquid"
        ),
        # Initial BOG Bubbles (Frame 0)
        go.Scatter3d(
            x=[0], y=[0], z=[0],
            mode='markers',
            marker=dict(size=3, color='white'),
            hoverinfo="skip", name="BOG Gas"
        ),
        # Tank Walls (Static)
        go.Surface(
            x=x_wall, y=y_wall, z=z_grid,
            colorscale=[[0, 'rgba(200, 200, 200, 0.1)'], [1, 'rgba(200, 200, 200, 0.1)']],
            showscale=False, hoverinfo="skip", name="Tank Wall"
        )
    ],
    frames=frames
)

# ==========================================
# 5. ADD PLAY BUTTON AND CAMERA SETTINGS
# ==========================================
fig.update_layout(
    scene=dict(
        xaxis=dict(visible=False, range=[-6, 6]),
        yaxis=dict(visible=False, range=[-6, 6]),
        zaxis=dict(visible=False, range=[0, 11]),
        camera=dict(eye=dict(x=1.5, y=1.5, z=0.8)), # Angled 3D view
        aspectmode='manual',
        aspectratio=dict(x=1, y=1, z=1.2)
    ),
    updatemenus=[dict(
        type="buttons",
        showactive=False,
        buttons=[
            dict(label="▶️ Play",
                 method="animate",
                 args=[None, dict(frame=dict(duration=100, redraw=True), fromcurrent=True, transition=dict(duration=0))]),
            dict(label="⏸️ Pause",
                 method="animate",
                 args=[[None], dict(frame=dict(duration=0, redraw=False), mode="immediate", transition=dict(duration=0))])
        ]
    )],
    margin=dict(l=0, r=0, b=0, t=0),
    height=600,
    paper_bgcolor="white"
)

# ==========================================
# 6. DISPLAY IN STREAMLIT
# ==========================================
st.plotly_chart(fig, use_container_width=True)

# Display info based on scenario
col1, col2 = st.columns(2)
with col1:
    if "Sloshing" in scenario:
        st.warning("**FSU Sloshing Physics:** Wave motion physically distorts the liquid surface, vastly increasing the surface area. This causes rapid vaporization (BOG).")
    elif scenario == "The Rollover Incident":
        st.error("**Rollover Incident:** Watch the aggressive surge of bubbles. In a real event, the sudden mixing of warm bottom layers causes explosive BOG generation.")
with col2:
    st.info("**Did you know?** In reality, BOG rises because the LNG at the bottom is slightly warmer (due to heat leak from the ground), causing convection currents.")

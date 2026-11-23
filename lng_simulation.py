import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.set_page_config(layout="wide", page_title="SA LNG Day 2: Visual Tank Dynamics")

st.title("🇿🇦 Day 2: LNG Storage Dynamics & Visual Animation")
st.markdown("Use the timeline slider in the sidebar to watch the liquid level, stratification, and sloshing in real-time.")

# ==========================================
# 1. SIDEBAR CONTROLS
# ==========================================
st.sidebar.header("🎬 Animation Controls")

scenario = st.sidebar.selectbox(
    "Select Scenario", 
    ["Normal Operations", "The Rollover Incident", "FSU Sloshing (High BOG)"]
)

# This slider acts as the "playhead" for our animation
day = st.sidebar.slider("Timeline (Days)", 1, 30, 1, 1)

capacity_m3 = st.sidebar.radio("Storage Type", ["FSU (170,000 m³)", "Onshore (220,000 m³)"])
cap_val = 170000 if "FSU" in capacity_m3 else 220000
lng_density = st.sidebar.slider("Initial LNG Density (kg/m³)", 400.0, 480.0, 450.0)

# ==========================================
# 2. SIMULATION LOGIC (Calculate state for selected Day)
# ==========================================
days = 30
initial_inv_pct = 90.0 # Start at 90% full
inventory_history = [initial_inv_pct]
bog_history = [0]

# Simulate the entire month to get the history up to the current day
for d in range(2, days + 1):
    current_inv = inventory_history[-1]
    base_bog = 0.10 if "Onshore" in capacity_m3 else 0.15
    
    if scenario == "FSU Sloshing (High BOG)":
        base_bog = 0.30 # High wave motion
        
    # The Rollover Event at Day 15
    if scenario == "The Rollover Incident" and d == 15:
        actual_bog = base_bog * 6.0 # 6x spike in BOG
    else:
        actual_bog = base_bog
        
    bog_m3 = current_inv * (actual_bog / 100)
    new_inv = current_inv - (bog_m3 / (cap_val/100)) - 0.5 # 0.5% sent out daily
    inventory_history.append(new_inv)
    bog_history.append(bog_m3)

# Get the state for the specifically selected day
current_inv_pct = max(0, inventory_history[day - 1])
current_bog = bog_history[day - 1]

# ==========================================
# 3. DRAWING THE PHYSICAL TANK
# ==========================================
st.subheader(f"Live Tank Cross-Section (Day {day})")

# Create figure
fig = go.Figure()

# Tank Geometry
tank_width = 10
tank_height = 10
wall_thickness = 0.2

# Draw the tank walls (Rectangle outline)
fig.add_shape(type="rect",
    x0=0, y0=0, x1=tank_width, y1=tank_height,
    line=dict(color="Black", width=4),
    fillcolor="rgba(255, 255, 255, 0.1)"
)

# Liquid Level (Convert % to physical height)
liquid_height = (current_inv_pct / 100) * tank_height

# 3A. Draw Sloshing Wave Effect
if "Sloshing" in scenario:
    # Create a sine wave for the surface
    x_wave = np.linspace(0, tank_width, 100)
    # The wave gets more violent if BOG is high
    amplitude = 0.6 if current_bog > 1.0 else 0.3
    y_wave = liquid_height + amplitude * np.sin(2 * np.pi * x_wave / 2)
    
    # Fill the liquid with the wave top
    fig.add_trace(go.Scatter(
        x=np.concatenate([x_wave, x_wave[::-1]]),
        y=np.concatenate([y_wave, np.zeros(100)]),
        fill='toself',
        fillcolor='rgba(0, 150, 255, 0.6)', # Blue LNG
        line=dict(color='rgba(0,0,0,0)'),
        name='LNG (Sloshing)'
    ))
else:
    # Flat surface for onshore / normal ops
    fig.add_shape(type="rect",
        x0=0, y0=0, x1=tank_width, y1=liquid_height,
        fillcolor="rgba(0, 150, 255, 0.6)", # Blue LNG
        line=dict(width=0)
    )

# 3B. Draw Stratification (Rollover)
if scenario == "The Rollover Incident":
    if day < 15:
        # Before rollover: Dense layer at bottom, light layer on top
        heavy_layer_height = liquid_height * 0.4
        # Heavy layer
        fig.add_shape(type="rect",
            x0=0, y0=0, x1=tank_width, y1=heavy_layer_height,
            fillcolor="rgba(255, 100, 0, 0.8)", # Orange heavy LNG
            line=dict(width=0)
        )
        # Light layer
        fig.add_shape(type="rect",
            x0=0, y0=heavy_layer_height, x1=tank_width, y1=liquid_height,
            fillcolor="rgba(0, 150, 255, 0.8)", # Blue light LNG
            line=dict(width=0)
        )
    elif day == 15:
        # THE ROLLOVER HAPPENS
        # Everything mixes into one violent purple/brown color
        fig.add_shape(type="rect",
            x0=0, y0=0, x1=tank_width, y1=liquid_height,
            fillcolor="rgba(150, 0, 150, 0.9)", # Mixed color
            line=dict(width=0)
        )
        # Add BOG Bubbles exploding out
        np.random.seed(42) # Fixed seed for visual consistency
        bubble_x = np.random.uniform(1, 9, 40)
        bubble_y = np.random.uniform(liquid_height * 0.5, tank_height, 40)
        fig.add_trace(go.Scatter(
            x=bubble_x, y=bubble_y, mode='markers',
            marker=dict(size=15, color='white', symbol='circle-open', line=dict(width=2)),
            name='BOG Explosion'
        ))
        
# Add text annotations
fig.add_annotation(x=tank_width/2, y=liquid_height/2, text=f"{current_inv_pct:.1f}% Full",
                   showarrow=False, font=dict(color="white", size=16))
if current_bog > 1.0:
    fig.add_annotation(x=tank_width/2, y=tank_height + 0.5, text="⚠️ HIGH BOG GENERATION",
                       showarrow=False, font=dict(color="red", size=16))

# Formatting
fig.update_layout(
    xaxis=dict(range=[-1, tank_width + 1], showgrid=False, zeroline=False, visible=False),
    yaxis=dict(range=[-1, tank_height + 2], showgrid=False, zeroline=False, visible=False),
    height=500,
    plot_bgcolor='rgba(240, 240, 240, 1)',
    margin=dict(l=20, r=20, t=20, b=20)
)

col_tank, col_info = st.columns([2, 1])

with col_tank:
    st.plotly_chart(fig, use_container_width=True)

with col_info:
    st.subheader("System State")
    st.metric("Inventory", f"{current_inv_pct:.1f} %")
    st.metric("BOG Rate", f"{current_bog:.2f} % / day")
    
    if scenario == "The Rollover Incident":
        if day < 15:
            st.info("**Stratification:** Heavier LNG (orange) is trapped at the bottom. Heat is being absorbed, but it can't boil because the lighter layer (blue) is pressing down on it.")
        elif day == 15:
            st.error("**ROLLOVER!** The bottom layer finally warmed up enough to become lighter than the top layer. They violently mixed in seconds, releasing massive pressure and BOG.")
        else:
            st.success("**Post-Rollover:** The tank is now uniform, but we lost massive amounts of gas.")
            
    elif "Sloshing" in scenario:
        st.warning("**Sloshing:** Wave motion against the tank walls drastically increases the surface area of the liquid, causing rapid evaporation (BOG).")

# Historical Graph
st.subheader("Historical Trends")
df = pd.DataFrame({'Day': range(1, 31), 'Inventory (%)': inventory_history, 'BOG (%)': bog_history})
fig_line = go.Figure()
fig_line.add_trace(go.Scatter(x=df['Day'], y=df['Inventory (%)'], name='Inventory (%)', line=dict(color='blue')))
fig_line.add_trace(go.Bar(x=df['Day'], y=df['BOG (%)'], name='BOG Generation', yaxis='y2', opacity=0.5))
fig_line.update_layout(
    yaxis=dict(title='Inventory (%)', range=[0, 100]),
    yaxis2=dict(title='BOG (%)', overlaying='y', side='right'),
    hovermode='x unified'
)
st.plotly_chart(fig_line, use_container_width=True)

import streamlit as st
import pandas as pd
import numpy as np
import time
import requests
import json
import asyncio
import threading
import datetime
from typing import Dict, Any, List

# Try importing from dummio
try:
    import sys
    import os
    import importlib
    
    # Prioritize the active local src/ directory
    src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
    if src_path not in sys.path:
        sys.path.insert(0, src_path)
        
    # Reload dummio modules if already cached to prevent Streamlit hot-reload import failures
    for mod_name in list(sys.modules.keys()):
        if mod_name == "dummio" or mod_name.startswith("dummio."):
            try:
                importlib.reload(sys.modules[mod_name])
            except Exception:
                pass
                
    from dummio.devices import VirtualDevice, IndustrialMotor, WindTurbine, SmartHVAC
    from dummio.models import SensorReading, AnomalyInjectionRequest
except Exception:
    from dummio.devices import VirtualDevice, IndustrialMotor, WindTurbine, SmartHVAC
    from dummio.models import SensorReading, AnomalyInjectionRequest

# Set page configurations
st.set_page_config(
    page_title="Dummio IoT Plotter & Dashboard",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom premium styling
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&family=Space+Grotesk:wght@400;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
    }
    
    .stHeadingContainer h1, .stHeadingContainer h2, .stHeadingContainer h3 {
        font-family: 'Space Grotesk', sans-serif;
        font-weight: 700;
    }
    
    /* Premium glassmorphic card container */
    .metric-card {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 18px;
        box-shadow: 0 4px 30px rgba(0, 0, 0, 0.1);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        transition: all 0.3s ease;
    }
    
    .metric-card:hover {
        transform: translateY(-2px);
        border-color: rgba(255, 255, 255, 0.25);
        box-shadow: 0 8px 30px rgba(0, 0, 0, 0.2);
    }
    
    /* System health indicator animation */
    @keyframes pulse-green {
        0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7); }
        70% { transform: scale(1); box-shadow: 0 0 0 10px rgba(16, 185, 129, 0); }
        100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
    }
    
    @keyframes pulse-red {
        0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.7); }
        70% { transform: scale(1); box-shadow: 0 0 0 10px rgba(239, 68, 68, 0); }
        100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(239, 68, 68, 0); }
    }
    
    .status-badge-healthy {
        background-color: rgba(16, 185, 129, 0.15);
        color: #10b981;
        border: 1px solid rgba(16, 185, 129, 0.3);
        padding: 6px 12px;
        border-radius: 20px;
        font-weight: 600;
        display: inline-flex;
        align-items: center;
        gap: 8px;
    }
    
    .status-badge-healthy::before {
        content: '';
        display: inline-block;
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background-color: #10b981;
        box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7);
        animation: pulse-green 2s infinite;
    }
    
    .status-badge-anomaly {
        background-color: rgba(239, 68, 68, 0.15);
        color: #ef4444;
        border: 1px solid rgba(239, 68, 68, 0.3);
        padding: 6px 12px;
        border-radius: 20px;
        font-weight: 600;
        display: inline-flex;
        align-items: center;
        gap: 8px;
    }
    
    .status-badge-anomaly::before {
        content: '';
        display: inline-block;
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background-color: #ef4444;
        box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.7);
        animation: pulse-red 1s infinite;
    }
    </style>
""", unsafe_allow_html=True)

# ----------------- DEVICE CONFIGURATIONS DICTIONARY -----------------

DEVICE_CONFIGS = {
    "IndustrialMotor": {
        "title": "Industrial Motor Preset",
        "description": "Simulates a manufacturing motor tracking rotational speed, housing temperature, electric draw, and physical vibrations.",
        "metrics": [
            {"key": "RPM", "label": "Rotational Speed", "unit": "RPM", "delta_key": "RPM"},
            {"key": "Temperature", "label": "Housing Temperature", "unit": "°C", "delta_key": "Temperature"},
            {"key": "Current", "label": "Current Draw", "unit": "A", "delta_key": "Current"}
        ],
        "vibration_keys": ["VibrationX", "VibrationY", "VibrationZ"],
        "anomalies": [
            {"type": "bearing_wear", "label": "🚨 Inject Bearing Wear", "help": "Simulates physical wear: progressive temperature spikes, increased current, and extreme vibration."},
            {"type": "mechanical_jam", "label": "🔥 Inject Mechanical Jam", "help": "Simulates rotor jam: RPM drops to 0, current draws spike to safety limits, housing overheats."}
        ]
    },
    "WindTurbine": {
        "title": "Wind Turbine Generator",
        "description": "Simulates a utility-scale wind power turbine generating electricity, showing wind dynamics and mechanical gear ratios.",
        "metrics": [
            {"key": "WindSpeed", "label": "Wind Speed", "unit": "m/s", "delta_key": "WindSpeed"},
            {"key": "RotorRPM", "label": "Rotor Speed", "unit": "RPM", "delta_key": "RotorRPM"},
            {"key": "PowerOutput", "label": "Power Output", "unit": "kW", "delta_key": "PowerOutput"}
        ],
        "vibration_keys": ["VibrationX", "VibrationY", "VibrationZ"],
        "anomalies": [
            {"type": "blade_imbalance", "label": "🚨 Inject Blade Imbalance", "help": "Blade surface ice/crack: causes massive low-frequency vibration and slight rotor drag."},
            {"type": "gearbox_slippage", "label": "🔥 Inject Gearbox Slippage", "help": "Gear friction breakdown: rotor speed accelerates, generator output falls, casing overheats."}
        ]
    },
    "SmartHVAC": {
        "title": "Smart Commercial HVAC",
        "description": "Simulates building climate loops managing thermal exchanges, compressor pressures, and electricity loads.",
        "metrics": [
            {"key": "RoomTemp", "label": "Room Temperature", "unit": "°C", "delta_key": "RoomTemp"},
            {"key": "CompressorPressure", "label": "Compressor Pressure", "unit": "PSI", "delta_key": "CompressorPressure"},
            {"key": "PowerLoad", "label": "Power Load", "unit": "kW", "delta_key": "PowerLoad"}
        ],
        "vibration_keys": ["VibrationX", "VibrationY", "VibrationZ"],
        "anomalies": [
            {"type": "refrigerant_leak", "label": "🚨 Inject Refrigerant Leak", "help": "Fluid pressure drops, compressor runs inefficiently, room temperature rises slowly."},
            {"type": "fan_failure", "label": "🔥 Inject Fan Failure", "help": "Condenser fan failure: pressure rises to critical limits, power consumption spikes, casing vibrates."}
        ]
    }
}

# ----------------- SIDEBAR DEVICE SELECTION -----------------

st.sidebar.markdown("<h2 style='text-align: center;'>⚡ Dummio Settings</h2>", unsafe_allow_html=True)
st.sidebar.markdown("---")

# New sidebar dropdown to select different simulated hardware devices
selected_device_name = st.sidebar.selectbox(
    "Select IoT Device Preset",
    ["Industrial Motor", "Wind Turbine", "Smart HVAC"],
    help="Choose the virtual hardware device preset you want to plot and control."
)

device_mapping = {
    "Industrial Motor": "IndustrialMotor",
    "Wind Turbine": "WindTurbine",
    "Smart HVAC": "SmartHVAC"
}
device_key = device_mapping[selected_device_name]
cfg = DEVICE_CONFIGS[device_key]

# ----------------- SESSION STATE STATE INITIALIZATION -----------------

if "history" not in st.session_state:
    st.session_state.history = []

if "current_device_key" not in st.session_state:
    st.session_state.current_device_key = device_key

if "local_device" not in st.session_state:
    if device_key == "IndustrialMotor":
        st.session_state.local_device = IndustrialMotor(start_test_broker=False)
    elif device_key == "WindTurbine":
        st.session_state.local_device = WindTurbine(start_test_broker=False)
    elif device_key == "SmartHVAC":
        st.session_state.local_device = SmartHVAC(start_test_broker=False)

# Reset buffers when switching devices
if st.session_state.current_device_key != device_key:
    st.session_state.current_device_key = device_key
    st.session_state.history = []
    st.session_state.ws_queue = []
    if device_key == "IndustrialMotor":
        st.session_state.local_device = IndustrialMotor(start_test_broker=False)
    elif device_key == "WindTurbine":
        st.session_state.local_device = WindTurbine(start_test_broker=False)
    elif device_key == "SmartHVAC":
        st.session_state.local_device = SmartHVAC(start_test_broker=False)
    st.rerun()

if "ws_connected" not in st.session_state:
    st.session_state.ws_connected = False

if "ws_queue" not in st.session_state:
    st.session_state.ws_queue = []

if "ws_thread" not in st.session_state:
    st.session_state.ws_thread = None

if "stop_ws_thread" not in st.session_state:
    st.session_state.stop_ws_thread = threading.Event()

# ----------------- WEBSOCKET BACKGROUND THREAD -----------------

def run_ws_listener(ws_url: str, queue_list: list, stop_event: threading.Event):
    """Background thread to read data from Dummio WebSocket server."""
    import websockets
    
    async def listen():
        while not stop_event.is_set():
            try:
                async with websockets.connect(ws_url, open_timeout=3.0) as ws:
                    st.session_state.ws_connected = True
                    while not stop_event.is_set():
                        try:
                            msg = await asyncio.wait_for(ws.recv(), timeout=1.0)
                            data = json.loads(msg)
                            queue_list.append(data)
                            if len(queue_list) > 200:
                                queue_list.pop(0)
                        except asyncio.TimeoutError:
                            continue
                        except Exception:
                            break
            except Exception:
                st.session_state.ws_connected = False
                await asyncio.sleep(2.0)
                
        st.session_state.ws_connected = False

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(listen())
    loop.close()

def start_ws_client(ws_url: str):
    """Starts the WebSocket background listener if not already running."""
    if st.session_state.ws_thread is None or not st.session_state.ws_thread.is_alive():
        st.session_state.stop_ws_thread.clear()
        st.session_state.ws_thread = threading.Thread(
            target=run_ws_listener,
            args=(ws_url, st.session_state.ws_queue, st.session_state.stop_ws_thread),
            daemon=True
        )
        st.session_state.ws_thread.start()

def stop_ws_client():
    """Stops the WebSocket background listener."""
    if st.session_state.ws_thread is not None and st.session_state.ws_thread.is_alive():
        st.session_state.stop_ws_thread.set()
        st.session_state.ws_thread.join(timeout=1.0)
        st.session_state.ws_thread = None
        st.session_state.ws_connected = False

# ----------------- SIDEBAR MODE & FREQUENCY SELECTION -----------------

mode = st.sidebar.radio(
    "Select Engine Mode",
    ["Local Simulation Engine", "Connect to Live API Server"],
    help="Local mode runs the motor simulation thread in-app. Connected mode connects to a separate running Dummio server."
)

freq = st.sidebar.slider(
    "Refresh Interval (Seconds)",
    min_value=0.2,
    max_value=3.0,
    value=1.0,
    step=0.1,
    help="How frequently the dashboard polls or generates data points."
)

st.sidebar.markdown("---")

# Config parameters depending on Mode
if mode == "Local Simulation Engine":
    stop_ws_client()
    
    st.sidebar.subheader("Simulation Parameters")
    if device_key == "IndustrialMotor":
        base_rpm = st.sidebar.number_input("Base RPM", min_value=500.0, max_value=5000.0, value=1500.0, step=100.0)
        base_temp = st.sidebar.number_input("Base Temp (°C)", min_value=20.0, max_value=100.0, value=45.0, step=1.0)
        base_current = st.sidebar.number_input("Base Amperage (A)", min_value=1.0, max_value=50.0, value=10.0, step=0.5)
        
        st.session_state.local_device.base_rpm = base_rpm
        st.session_state.local_device.base_temp = base_temp
        st.session_state.local_device.base_current = base_current
        
    elif device_key == "WindTurbine":
        base_wind = st.sidebar.number_input("Base Wind Speed (m/s)", min_value=1.0, max_value=40.0, value=12.0, step=0.5)
        base_temp = st.sidebar.number_input("Base Generator Temp (°C)", min_value=20.0, max_value=120.0, value=55.0, step=1.0)
        base_power = st.sidebar.number_input("Base Power Output (kW)", min_value=100.0, max_value=5000.0, value=1500.0, step=50.0)
        
        st.session_state.local_device.base_wind = base_wind
        st.session_state.local_device.base_temp = base_temp
        st.session_state.local_device.base_power = base_power
        
    elif device_key == "SmartHVAC":
        target_temp = st.sidebar.number_input("Target Room Temp (°C)", min_value=16.0, max_value=30.0, value=21.0, step=0.5)
        ambient_temp = st.sidebar.number_input("Ambient Temp (°C)", min_value=15.0, max_value=50.0, value=32.0, step=1.0)
        base_pressure = st.sidebar.number_input("Base Compressor Pressure (PSI)", min_value=50.0, max_value=300.0, value=120.0, step=5.0)
        
        st.session_state.local_device.target_room_temp = target_temp
        st.session_state.local_device.ambient_temp = ambient_temp
        st.session_state.local_device.compressor_pressure = base_pressure
    
else:
    st.sidebar.subheader("API Connection")
    host = st.sidebar.text_input("Server Host", value="localhost")
    port = st.sidebar.number_input("Server Port", min_value=80, max_value=65535, value=8000)
    
    api_url = f"http://{host}:{port}"
    ws_url = f"ws://{host}:{port}/ws"
    
    start_ws_client(ws_url)
    
    if st.session_state.ws_connected:
        st.sidebar.success(f"Connected to Dummio Server at {host}:{port}!")
    else:
        st.sidebar.warning(f"Connecting to ws://{host}:{port}/ws...")
        st.sidebar.info("Tip: Start your server using `python examples/basic_template.py` to stream live data.")

# Clear History Button
if st.sidebar.button("Clear Dashboard History", use_container_width=True):
    st.session_state.history = []
    st.session_state.ws_queue = []
    st.rerun()

# ----------------- MAIN DASHBOARD INTERFACE -----------------

col_header, col_badge = st.columns([3, 1])

with col_header:
    st.title(f"⚡ Dummio: {cfg['title']}")
    st.markdown(cfg['description'])

# ----------------- GET CURRENT DATA POINT -----------------

current_reading = None

if mode == "Local Simulation Engine":
    st.session_state.local_device._check_anomaly_timeout()
    sensors = st.session_state.local_device.generate_sensors()
    
    reading_obj = SensorReading(
        timestamp=datetime.datetime.utcnow(),
        device_id=st.session_state.local_device.device_id,
        preset=st.session_state.local_device.preset_name,
        anomaly=1 if st.session_state.local_device.current_anomaly else 0,
        anomaly_type=st.session_state.local_device.current_anomaly,
        sensors=sensors
    )
    
    current_reading = json.loads(reading_obj.model_dump_json())
    st.session_state.history.append(current_reading)
    
    if len(st.session_state.history) > 200:
        st.session_state.history.pop(0)
        
    active_history = st.session_state.history
    
else:
    if st.session_state.ws_queue:
        current_reading = st.session_state.ws_queue[-1]
    active_history = st.session_state.ws_queue

# Render Health/Anomaly badge
anomaly_active = False
anomaly_type_name = "None"

if current_reading:
    anomaly_active = bool(current_reading.get("anomaly", 0))
    anomaly_type_name = current_reading.get("anomaly_type") or "None"

with col_badge:
    st.markdown("<div style='height: 15px;'></div>", unsafe_allow_html=True)
    if anomaly_active:
        st.markdown(f"<div style='text-align: right;'><span class='status-badge-anomaly'>ANOMALY: {anomaly_type_name.upper()}</span></div>", unsafe_allow_html=True)
    else:
        st.markdown("<div style='text-align: right;'><span class='status-badge-healthy'>SYSTEM HEALTHY</span></div>", unsafe_allow_html=True)

st.markdown("---")

# ----------------- FAILURE INJECTION CONTROLS -----------------

st.subheader("🛠️ Hardware Control Panel & Anomaly Injector")

col_a1, col_a2, col_clear = st.columns(3)

inject_type = None
clear_triggered = False
anom_list = cfg["anomalies"]

with col_a1:
    if st.button(anom_list[0]["label"], use_container_width=True, help=anom_list[0]["help"]):
        inject_type = anom_list[0]["type"]

with col_a2:
    if st.button(anom_list[1]["label"], use_container_width=True, help=anom_list[1]["help"]):
        inject_type = anom_list[1]["type"]

with col_clear:
    if st.button("✅ Clear Anomaly (Auto-Repair)", use_container_width=True, help="Clears active hardware anomalies and triggers system cooldown/repair."):
        clear_triggered = True

# Process physical triggers
if inject_type:
    if mode == "Local Simulation Engine":
        req = AnomalyInjectionRequest(anomaly_type=inject_type, duration_seconds=30)
        st.session_state.local_device.inject_anomaly(req)
        st.toast(f"Local {device_key} anomaly '{inject_type}' injected for 30s!", icon="🚨")
    else:
        try:
            res = requests.post(f"{api_url}/api/inject", json={"anomaly_type": inject_type, "duration_seconds": 30})
            if res.status_code == 200:
                st.toast(f"Server anomaly '{inject_type}' injected for 30s!", icon="🚨")
            else:
                st.error(f"Failed to inject anomaly: {res.text}")
        except Exception as e:
            st.error(f"Connection error to REST API: {e}")

if clear_triggered:
    if mode == "Local Simulation Engine":
        st.session_state.local_device.clear_anomaly()
        st.toast(f"Local {device_key} anomalies cleared!", icon="✅")
    else:
        try:
            res = requests.post(f"{api_url}/api/clear")
            if res.status_code == 200:
                st.toast(f"Server {device_key} anomalies cleared!", icon="✅")
            else:
                st.error(f"Failed to clear anomalies: {res.text}")
        except Exception as e:
            st.error(f"Connection error to REST API: {e}")

st.markdown("---")

# ----------------- LIVE METRICS PANEL -----------------

if current_reading:
    sensors_curr = current_reading.get("sensors", {})
    
    # Calculate Vibration Magnitude (Overall RMS value)
    vx = sensors_curr.get("VibrationX", 0.0)
    vy = sensors_curr.get("VibrationY", 0.0)
    vz = sensors_curr.get("VibrationZ", 0.0)
    vib_mag = round(np.sqrt(vx**2 + vy**2 + vz**2), 4)
    
    # Extract delta values from history if available
    prev_reading = active_history[-2] if len(active_history) >= 2 else None
    
    def get_delta(key, curr_val):
        if not prev_reading:
            return None
        prev_val = prev_reading.get("sensors", {}).get(key, curr_val)
        return round(curr_val - prev_val, 2)
        
    m_cfg_1 = cfg["metrics"][0]
    m_cfg_2 = cfg["metrics"][1]
    m_cfg_3 = cfg["metrics"][2]
    
    val_1 = sensors_curr.get(m_cfg_1["key"], 0.0)
    val_2 = sensors_curr.get(m_cfg_2["key"], 0.0)
    val_3 = sensors_curr.get(m_cfg_3["key"], 0.0)
    
    delta_1 = get_delta(m_cfg_1["delta_key"], val_1)
    delta_2 = get_delta(m_cfg_2["delta_key"], val_2)
    delta_3 = get_delta(m_cfg_3["delta_key"], val_3)
    
    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    
    with col_m1:
        color_1 = "#ef4444" if (delta_1 and delta_1 < 0 and m_cfg_1["key"] == "RPM") or (delta_1 and delta_1 > 0.5 and m_cfg_1["key"] in ["Temperature", "GeneratorTemp"]) else "#10b981"
        arrow_1 = "↓" if delta_1 and delta_1 < 0 else "↑"
        st.markdown(
            f"""<div class='metric-card'>
                <p style='margin:0;font-size:0.9rem;color:#9ca3af;text-transform:uppercase;font-weight:600;'>{m_cfg_1["label"]}</p>
                <h2 style='margin:5px 0;font-size:2.2rem;'>{val_1} <span style='font-size:1rem;color:#9ca3af;'>{m_cfg_1["unit"]}</span></h2>
                <p style='margin:0;font-size:0.85rem;color:{color_1};'>{arrow_1} {abs(delta_1) if delta_1 is not None else 0.0} delta</p>
            </div>""",
            unsafe_allow_html=True
        )
        
    with col_m2:
        color_2 = "#ef4444" if (delta_2 and delta_2 > 0.5 and m_cfg_2["key"] in ["Temperature", "GeneratorTemp", "CompressorPressure"]) else "#10b981"
        arrow_2 = "↑" if delta_2 and delta_2 >= 0 else "↓"
        st.markdown(
            f"""<div class='metric-card'>
                <p style='margin:0;font-size:0.9rem;color:#9ca3af;text-transform:uppercase;font-weight:600;'>{m_cfg_2["label"]}</p>
                <h2 style='margin:5px 0;font-size:2.2rem;'>{val_2} <span style='font-size:1rem;color:#9ca3af;'>{m_cfg_2["unit"]}</span></h2>
                <p style='margin:0;font-size:0.85rem;color:{color_2};'>{arrow_2} {abs(delta_2) if delta_2 is not None else 0.0} delta</p>
            </div>""",
            unsafe_allow_html=True
        )
        
    with col_m3:
        color_3 = "#ef4444" if (delta_3 and delta_3 > 1.0 and m_cfg_3["key"] in ["Current", "PowerLoad"]) else "#10b981"
        arrow_3 = "↑" if delta_3 and delta_3 >= 0 else "↓"
        st.markdown(
            f"""<div class='metric-card'>
                <p style='margin:0;font-size:0.9rem;color:#9ca3af;text-transform:uppercase;font-weight:600;'>{m_cfg_3["label"]}</p>
                <h2 style='margin:5px 0;font-size:2.2rem;'>{val_3} <span style='font-size:1rem;color:#9ca3af;'>{m_cfg_3["unit"]}</span></h2>
                <p style='margin:0;font-size:0.85rem;color:{color_3};'>{arrow_3} {abs(delta_3) if delta_3 is not None else 0.0} delta</p>
            </div>""",
            unsafe_allow_html=True
        )
        
    with col_m4:
        st.markdown(
            f"""<div class='metric-card'>
                <p style='margin:0;font-size:0.9rem;color:#9ca3af;text-transform:uppercase;font-weight:600;'>RMS Vibration (Overall)</p>
                <h2 style='margin:5px 0;font-size:2.2rem;'>{vib_mag} <span style='font-size:1rem;color:#9ca3af;'>G RMS</span></h2>
                <p style='margin:0;font-size:0.85rem;color:#9ca3af;'>X:{vx} | Y:{vy} | Z:{vz}</p>
            </div>""",
            unsafe_allow_html=True
        )
else:
    st.warning("Awaiting live stream telemetry... Check if the local simulator or API server is running.")

st.markdown("### 📈 Live Telemetry Charts (Last 50 Samples)")

# ----------------- REAL-TIME CHARTS PANEL -----------------

if len(active_history) > 0:
    df_data = []
    for r in active_history[-50:]:
        sensors_dict = r.get("sensors", {})
        ts = r.get("timestamp")
        if isinstance(ts, str):
            try:
                ts_dt = datetime.datetime.fromisoformat(ts.replace("Z", "+00:00"))
                ts_str = ts_dt.strftime("%H:%M:%S")
            except Exception:
                ts_str = ts
        else:
            ts_str = datetime.datetime.utcnow().strftime("%H:%M:%S")
            
        vx = sensors_dict.get("VibrationX", 0.0)
        vy = sensors_dict.get("VibrationY", 0.0)
        vz = sensors_dict.get("VibrationZ", 0.0)
        vib_rms = np.sqrt(vx**2 + vy**2 + vz**2)
        
        row = {
            "Time": ts_str,
            "Vibration X": vx,
            "Vibration Y": vy,
            "Vibration Z": vz,
            "Vibration RMS (G)": round(vib_rms, 4),
            "Anomaly Flag": r.get("anomaly", 0) * 10
        }
        
        for metric in cfg["metrics"]:
            lbl = f"{metric['label']} ({metric['unit']})"
            row[lbl] = sensors_dict.get(metric["key"], 0.0)
            
        df_data.append(row)
        
    df = pd.DataFrame(df_data)
    df.set_index("Time", inplace=True)
    
    tab1, tab2, tab3 = st.tabs(["📊 Main Engine Metrics", "📳 Vibration Spectrum", "🔍 Raw Telemetry JSON"])
    
    with tab1:
        st.markdown(f"**{', '.join([m['label'] for m in cfg['metrics']])}**")
        chart_cols = [f"{m['label']} ({m['unit']})" for m in cfg["metrics"]]
        chart_data_1 = df[chart_cols]
        st.line_chart(chart_data_1, use_container_width=True)
        
    with tab2:
        st.markdown("**Vibration amplitude across axes (X, Y, Z) and overall RMS G's**")
        chart_data_2 = df[["Vibration X", "Vibration Y", "Vibration Z", "Vibration RMS (G)"]]
        st.line_chart(chart_data_2, use_container_width=True)
        
    with tab3:
        st.markdown("**Live JSON packet feed structure**")
        st.json(current_reading)

else:
    st.info("No data in history buffer yet. The graphs will appear once telemetry streams start.")

# ----------------- REFRESH LOOP -----------------

time.sleep(freq)
st.rerun()

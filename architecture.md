# AWE Electrolyzer Test Rig - Software Architecture

## Overview

This architecture outlines the structure and behavior of a Python-based desktop application for controlling and monitoring an AWE electrolyzer test rig. The application will feature a user-friendly dashboard that visualizes live sensor data and allows manual control of actuators.

---

## 📁 Folder Structure

```plaintext
├── main.py                        # Entry point: launches the dashboard
│
├── config/
│   ├── devices.yaml               # Configuration for hardware channels, COM ports, scaling
│   └── constants.py              # General constants (e.g., sampling rates, relay mappings)
│
├── core/
│   ├── state.py                  # Global app state (connection status, test status, timer, etc.)
│   ├── dispatcher.py            # Routes actions (e.g., button presses) to correct services
│   └── timer.py                 # Central stopwatch / timer manager
│
├── services/
│   ├── ni_daq.py                 # NI cDAQ connection + polling (NI-9253 + NI-9485)
│   ├── pico_tc08.py             # Interface to Pico thermocouple logger
│   ├── bga244.py                # Serial interface to BGA244 analyzers
│   ├── cvm24p.py                # USB interface to Kolibrik CVM voltage monitor
│   └── controller_manager.py    # Initializes and manages all service lifecycles
│
├── ui/
│   ├── dashboard.py             # Main 2x2 grid layout + controls
│   ├── plots.py                 # Live plot rendering for pressure, voltage, temperature
│   ├── controls.py              # Buttons: Connect, Start, Pause/Resume, E-Stop, Valve toggles
│   └── status_indicators.py     # Connection indicators for each subsystem
│
├── data/
│   ├── logger.py                # Data saving service (to CSV or HDF5)
│   └── session_manager.py       # Handles test session folders, filenames, metadata
│
└── utils/
    ├── serial_utils.py          # Port scanning, RS-422 helpers
    └── helpers.py               # Miscellaneous (e.g., scaling 4-20mA signals, color maps)

🧠 Core Concepts
App State (core/state.py)
Centralized state container (e.g., a singleton or Pydantic BaseModel) that holds:

Test timer status and value

Connection status for each device

Current actuator states (valve, pump)

Latest sensor values (pressure, voltage, temperature, current)

Flags (paused, test running, emergency stop)

All services and UI components read/write from this shared state.

🔌 Services
All services implement a similar lifecycle:

connect()

disconnect()

start_polling()

stop_polling()

Each service continuously updates the global state.

ni_daq.py
Reads from NI-9253 (4-20mA sensors): 2 x pressure, 1 x current

Writes to NI-9485: 4 x solenoid valves, 1 x pump

Best available sampling rate used via NI-DAQmx Python API

pico_tc08.py
Uses Pico SDK to collect temperatures

Continuously updates shared state

bga244.py
Communicates with 3 BGA244 units over RS-422 (via USB)

Uses background threads or async polling to issue RATO?, PRES?, etc.

cvm24p.py
USB communication with CVM-24P using Modbus RTU or vendor protocol

Polls voltage values and logs cell voltages

controller_manager.py
Launches/stops all services

Used by "Connect to Hardware" button

📊 UI Dashboard
dashboard.py
Main layout in 2x2 grid:

Plot 1: Pressure vs time

Plot 2: Voltage vs time

Plot 3: Temperature vs time

Panel: Valve/pump states (color ON/OFF indicators)

controls.py
Buttons: Connect, Start Test, Pause/Resume, Emergency Stop

Toggle buttons for each valve and pump (manual control only)

status_indicators.py
For each device (NI DAQ, Pico, BGA, CVM), shows:

Connected ✅ / Disconnected ❌

Polling rate or error state

plots.py
Uses matplotlib, pyqtgraph, or similar for real-time rendering

Pulls data from state

💾 Data Logging
logger.py
Streams live sensor data into CSV or binary formats

One file per session, timestamped

session_manager.py
Creates folders for each test session

Manages metadata: test start time, operator, etc.

⚙️ Configuration
devices.yaml
Hardware-specific config:

COM port mappings

Scaling factors for sensors (e.g., mA → psi)

BGA gas types, baud rates, etc.

constants.py
Sampling rates, UI refresh rate, timeouts, relay channel IDs

🔄 Flow Summary
Operator launches main.py

UI shows disconnected state

Operator clicks “Connect to Hardware”

controller_manager.py spins up all services

Services update state, UI reflects connection status

Operator clicks “Start Test”

Timer starts, logging starts, plots begin drawing

Operator manually toggles valves/pumps

Operator clicks “Pause” or “E-Stop” as needed

On exit, session saved

🛠 Extensibility
This structure allows future additions:

Scheduler for valve/pump sequences

Power supply control (via TCP or serial)

Fault detection or interlocks

Remote dashboard view (web-based or VNC)
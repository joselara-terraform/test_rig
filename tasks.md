# tasks.md

Each task is atomic, testable, and narrowly scoped to ensure rapid iteration and validation.

---

## ✅ Phase 1: Project Scaffolding

### 1. Initialize project structure
**Start:** Create root folder `awe_tester/`  
**End:** Empty directory with `/core`, `/services`, `/ui`, `/config`, `/data`, `/utils`

---

### 2. Create entry point
**Start:** Create `main.py`  
**End:** `main.py` runs a placeholder dashboard window (e.g. "Hello, AWE")

---

### 3. Add app state singleton
**Start:** Create `core/state.py`  
**End:** A `GlobalState` class with fields for connection status and sensor values (mocked)

---

### 4. Create timer logic
**Start:** Add `core/timer.py`  
**End:** A stopwatch that can start, pause, resume, reset; updates time in state

---

## 🧩 Phase 2: UI Shell

### 5. Build dashboard window
**Start:** Create `ui/dashboard.py`  
**End:** Static 2x2 grid layout with placeholders for plots and valve state

---

### 6. Add test control buttons
**Start:** Create `ui/controls.py`  
**End:** Buttons: Connect, Start Test, Pause/Resume, Emergency Stop (all print to console)

---

### 7. Add connection status indicators
**Start:** Create `ui/status_indicators.py`  
**End:** Four indicators for NI DAQ, BGA, Pico, CVM (hardcoded: disconnected)

---

### 8. Connect UI to global state
**Start:** Wire dashboard elements to `GlobalState`  
**End:** Button presses update state and affect timer or indicators

---

## 🔌 Phase 3: Service Stubs + Connections

### 9. Create `controller_manager.py` service manager
**Start:** Create start/stop methods for each service  
**End:** Connect button launches all services (mocked)

---

### 10. Stub NI DAQ service
**Start:** Create `services/ni_daq.py`  
**End:** Mock read of 3 analog inputs + toggle of 5 digital outputs; updates `state`

---

### 11. Stub Pico thermocouple service
**Start:** Create `services/pico_tc08.py`  
**End:** Mock 8-channel temperature read; updates `state`

---

### 12. Stub BGA244 service
**Start:** Create `services/bga244.py`  
**End:** Simulate 3 BGA units returning gas ratios; updates `state`

---

### 13. Stub CVM-24P service
**Start:** Create `services/cvm24p.py`  
**End:** Simulate 24 cell voltages; updates `state`

---

## 📊 Phase 4: Visualization

### 14. Create pressure vs time plot
**Start:** Create `ui/plots.py` with 1 plot  
**End:** Live line plot from pressure data in `state`

---

### 15. Add voltage vs time plot
**Start:** Expand `plots.py`  
**End:** Live plot of CVM voltages (e.g., average or specific cell)

---

### 16. Add temperature vs time plot
**Start:** Expand `plots.py`  
**End:** Live plot from TC-08 mock data

---

### 17. Add valve/pump state indicators
**Start:** Build color-coded indicators in 2x2 grid  
**End:** Reflect ON/OFF state from `GlobalState`

---

## 🖲 Phase 5: Manual Controls

### 18. Add relay control buttons
**Start:** Add manual toggle buttons for 4 valves + 1 pump  
**End:** Toggles state and calls mocked DAQ relay service

---

### 19. Sync relay state with indicators
**Start:** When relay toggled, update `state`, and color reflects new value  
**End:** Relay state updates indicators immediately

---

## 💾 Phase 6: Logging

### 20. Implement session folder logic
**Start:** Create `data/session_manager.py`  
**End:** On start test: create timestamped folder + filename base

---

### 21. Implement CSV logger
**Start:** Create `data/logger.py`  
**End:** Start test begins periodic writes of `state` values to a CSV

---

## 🚦 Phase 7: Final Touches

### 22. Implement emergency stop
**Start:** Add kill button in UI  
**End:** All services stop, relays set to OFF, test paused

---

### 23. Hook up Pause/Resume logic
**Start:** Wire Pause/Resume to timer and data logger  
**End:** Freezes plots, data logging, timer; resumes on click

---

### 24. Graceful disconnect logic
**Start:** Add shutdown and cleanup paths  
**End:** All services clean up on exit; hardware safe state

---

### 25. Add real device.yaml parser
**Start:** Create `config/devices.yaml`  
**End:** NI channel numbers, serial ports, COM settings read from config file

---

### 26. Enable launching without hardware
**Start:** Add mock/fake mode if hardware not connected  
**End:** Dashboard runs standalone, shows “Disconnected” but is functional

---


## 🧩 Phase 8: NI DAQ (NI-9253, NI-9485)

### 27. Install NI-DAQmx and Python bindings
**Start:** Set up required Python packages and verify NI MAX sees the cDAQ  
**End:** A test script can list devices and read a dummy analog input channel

---

### 28. Read pressure and current via NI-9253
**Start:** Connect 4–20mA pressure sensors and current sensor  
**End:** `ni_daq.py` reads live analog values and scales to engineering units

---

### 29. Control relays via NI-9485
**Start:** Wire 4 solenoids and 1 pump to relay channels  
**End:** Button presses toggle physical relays and actuators function

---

### 30. Sync relay reads with `GlobalState`
**Start:** Add relay readback logic or state tracking  
**End:** UI indicators reflect real hardware state after physical actuation

---

## 🌡 Phase 9: Pico TC-08 Thermocouple Logger

### 31. Install Pico SDK and Python bindings
**Start:** Download Pico SDK and required Python wrapper  
**End:** TC-08 recognized by a test script that reads 1 thermocouple channel

---

### 32. Read 8 thermocouple channels
**Start:** Populate `pico_tc08.py` with polling logic  
**End:** State is updated with all channel temperatures every 1–2s

---

## 🌬 Phase 10: SRS BGA244 (RS-422 Serial)

### 33. Set up RS-422 to USB hardware
**Start:** Connect all 3 BGA244 units to known COM ports  
**End:** Device responds to `*IDN?` or `RATO?` queries

---

### 34. Poll gas ratio from each BGA
**Start:** Implement real serial communication in `bga244.py`  
**End:** Live RATO/PRES data is updated in state per device

---

### 35. Parse and scale BGA outputs
**Start:** Implement conversion logic (e.g., %H₂ from RATO)  
**End:** Outputs plotted as clean % values or ratios

---

## ⚡ Phase 11: Kolibrik CVM-24P Cell Voltage Monitor

### 36. Connect CVM via USB and install driver
**Start:** Verify CVM is detected and accessible via COM port  
**End:** Can send and receive basic Modbus/ASCII commands

---

### 37. Read cell voltages
**Start:** Implement `cvm24p.py` to read and parse cell array  
**End:** Average and/or individual cell voltages shown on plot
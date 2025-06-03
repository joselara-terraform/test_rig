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
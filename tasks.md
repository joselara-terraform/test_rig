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

## 🧪 Phase 3: Service Stubs + Mock Mode

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

## 🔌 Phase 6: Hardware Integration

### 20. NI cDAQ test script review + cleanup
**Start:** Review your existing NI DAQ test script  
**End:** Write cleaned standalone script for reading NI-9253 and toggling NI-9485 relays

---

### 21. Integrate NI cDAQ into service
**Start:** Replace mock logic in `ni_daq.py` with real analog + digital I/O  
**End:** Real data populates `state`, relays actuated from UI

---

### ✅ 22. Pico TC-08 test script review + cleanup
**Start:** Review your existing TC-08 test script  
**End:** Write cleaned standalone script for reading all 8 channels

**Completed with significant improvements:**
- ✅ Cross-platform DLL loading (Windows/Linux/macOS)
- ✅ Robust error handling and resource management
- ✅ Modular `PicoTC08` class structure ready for service integration
- ✅ Comprehensive configuration options via `PicoTC08Config`
- ✅ Better channel naming and status reporting
- ✅ Proper cleanup and disconnect procedures
- ✅ Temperature validation (disconnected sensor detection)
- ✅ Enhanced from original TC-08_test.py with professional structure

**Key Features:**
- Platform-specific DLL path detection
- Graceful fallback when SDK not installed
- 8-channel K-type thermocouple support with named channels
- Cold junction compensation configuration
- Real-time streaming with configurable sample rates
- Temperature validation and disconnected sensor detection

---

### ✅ 23. Integrate Pico TC-08 into service
**Start:** Replace mock logic in `pico_tc08.py` with real reads  
**End:** Temperature plots reflect real thermocouple values

**Completed with comprehensive integration:**
- ✅ Real hardware support with graceful fallback to mock mode
- ✅ Device configuration integration (no zero offsets for temperature sensors)
- ✅ Cross-platform DLL loading and error handling  
- ✅ GlobalState integration for dashboard temperature updates
- ✅ Direct thermocouple readings without calibration offsets
- ✅ Proper service lifecycle (connect/poll/disconnect)
- ✅ Thread-safe temperature polling at configured sample rates
- ✅ Channel naming and configuration from device config system
- ✅ Hardware/Mock mode detection and status reporting

**Integration Features:**
- `PicoTC08Hardware` class for low-level TC-08 interface
- `PicoTC08Service` maintains same interface for dashboard compatibility
- Real-time temperature streaming with 1 Hz sample rate
- Temperature validation and disconnected sensor detection
- Automatic hardware detection with fallback to mock data
- Configuration-driven channel setup (no zero offset calibration)

**Temperature Channels:**
- CH0: Inlet Temperature | CH1: Outlet Temperature
- CH2: Stack Temperature 1 | CH3: Stack Temperature 2  
- CH4: Ambient Temperature | CH5: Cooling System Temperature
- CH6: Gas Temperature | CH7: Case Temperature

---

### 24. BGA244 test script review + cleanup
**Start:** Review your existing BGA244 test script  
**End:** Write cleaned standalone script for sending `RATO?`, `PRES?`, etc. to all 3 devices

---

### 25. Integrate BGA244 into service
**Start:** Replace `bga244.py` with real serial logic and gas ratio parsing  
**End:** Plot reflects real-time gas ratios from all devices

---

### 26. CVM-24P test script review + cleanup
**Start:** Review your existing CVM-24P test script  
**End:** Write cleaned standalone script to retrieve all cell voltages

---

### 27. Integrate CVM-24P into service
**Start:** Replace `cvm24p.py` with real USB communication and parsing  
**End:** Real voltage values update plots and state

---

## 💾 Phase 7: Data Logging

### 28. Implement session folder logic
**Start:** Create `data/session_manager.py`  
**End:** On start test: create timestamped folder + filename base

---

### 29. Implement CSV logger
**Start:** Create `data/logger.py`  
**End:** Start test begins periodic writes of `state` values to a CSV

---

## ⚙️ Phase 8: Config Handling

### ✅ 30. Add real device.yaml parser
**Start:** Create `config/devices.yaml`  
**End:** NI channel numbers, serial ports, COM settings, **CALIBRATED ZERO OFFSETS** read from config file

**Key Requirements Implemented:**
- **✅ CALIBRATED ZERO OFFSETS for each sensor** - Primary requirement added
- ✅ Complete hardware configuration in YAML format
- ✅ Platform-specific overrides (Windows/Linux/macOS)
- ✅ Fallback configuration when PyYAML not available
- ✅ Device channel mappings and communication settings
- ✅ Sample rate configuration for all devices
- ✅ Calibration date tracking and validation
- ✅ Auto-zero offset application on startup

**Calibrated Zero Offsets Available For:**
- **4-20mA Sensors (NI cDAQ)**: 0.0 offset (4mA = true zero)
  - Pressure H2: 0.0 PSI offset
  - Pressure O2: 0.0 PSI offset 
  - Current: 0.0 A offset
- **Temperature Sensors**: NO zero offsets (direct thermocouple readings)
- **Gas Analyzers**: H2/O2/N2 concentration offsets (3 units)
- **Voltage Monitors**: Individual group offsets 6.7-15.1 mV (6 groups)

---

## 🔁 Phase 9: Mock Mode Support

### 31. Enable launching without hardware
**Start:** Add command-line flag or UI toggle  
**End:** Dashboard runs standalone, shows "Disconnected" but is functional

---
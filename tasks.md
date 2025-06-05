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

### ✅ 24. BGA244 test script review + cleanup
**Start:** Review your existing BGA244 test script  
**End:** Write cleaned standalone script for sending `RATO?`, `PRES?`, etc. to all 3 devices

**Completed with comprehensive enhancements:**
- ✅ Cross-platform serial port support (Windows/Linux/macOS)
- ✅ Support for multiple BGA244 units (3 gas analyzers)
- ✅ Robust error handling and resource management
- ✅ Modular class structure ready for service integration
- ✅ Comprehensive gas analysis commands (TCEL, PRES, NSOS, RATO)
- ✅ Gas configuration with CAS numbers for different gas types
- ✅ Individual device management and status tracking
- ✅ Enhanced from original BGA_test.py with professional structure

**Key Features:**
- `BGA244Device` class for individual gas analyzer interface
- `BGA244System` class for multi-unit management
- Serial communication with proper timeout and error handling
- Gas configuration: H2/O2/N2 analysis with primary/secondary gas setup
- Real-time measurement reading (temperature, pressure, speed of sound, concentrations)
- Cross-platform serial port detection and management
- Comprehensive command set for full BGA244 functionality

**BGA Unit Configuration:**
- BGA-1: Hydrogen Side Analyzer (H2 primary, O2 secondary)
- BGA-2: Oxygen Side Analyzer (O2 primary, H2 secondary)  
- BGA-3: Mixed Stream Analyzer (N2 primary, O2 secondary)

**Commands Implemented:**
- `*IDN?`: Device identification
- `MSMD 1`: Binary gas mode
- `GASP [CAS]`: Primary gas configuration
- `GASS [CAS]`: Secondary gas configuration
- `TCEL?`: Temperature reading
- `PRES?`: Pressure reading
- `NSOS?`: Speed of sound reading
- `RATO? 1/2`: Gas concentration readings

---

### ✅ 25. Integrate BGA244 into service
**Start:** Replace `bga244.py` with real serial logic and gas ratio parsing  
**End:** Plot reflects real-time gas ratios from all devices

**Completed with comprehensive integration as specified:**
- ✅ Real hardware integration with serial communication
- ✅ Individual BGA connection status (3 separate displays)
- ✅ Purge mode functionality (secondary gases → N2)
- ✅ Updated gas configurations as specified by user:
  - **BGA 1: H2 Header, H2 in O2** (primary H2, secondary O2)
  - **BGA 2: O2 Header, O2 in H2** (primary O2, secondary H2)
  - **BGA 3: De-oxo, H2 in O2** (primary H2, secondary O2)
- ✅ Service works with partial BGA connections (start test works despite disconnected BGAs)
- ✅ Mock fallback when hardware unavailable
- ✅ GlobalState integration for dashboard
- ✅ Device configuration integration with calibrated zero offsets
- ✅ Cross-platform serial port support (COM4 prioritized on Windows)

**Key Integration Features:**
- `BGA244Device` class for individual gas analyzer hardware interface
- `BGA244Service` class maintains same interface for dashboard compatibility
- Real-time gas concentration streaming with 0.2 Hz sample rate
- Individual connection tracking (`bga244_1`, `bga244_2`, `bga244_3`)
- Purge button functionality (toggles all secondary gases to N2)
- Hardware/Mock mode detection and graceful fallback
- Thread-safe gas concentration polling with proper lifecycle management
- Gas configuration via CAS numbers for binary gas mode

**UI Enhancements:**
- Status indicators updated to show 3 individual BGA connection statuses
- Purge button added to control panel with visual state indication
- Dashboard displays individual BGA statuses instead of combined status
- Test operations work even when some BGAs are disconnected

**Gas Analysis Commands:**
- `*IDN?`: Device identification and connection verification
- `MSMD 1`: Binary gas mode configuration
- `GASP [CAS]`: Primary gas configuration (H2 or O2)
- `GASS [CAS]`: Secondary gas configuration (O2, H2, or N2 in purge mode)
- `TCEL?`: Temperature measurement
- `PRES?`: Pressure measurement  
- `NSOS?`: Speed of sound measurement
- `RATO? 1/2`: Primary/secondary gas concentration readings

**Purge Mode Operation:**
- Normal mode: Uses configured secondary gas (O2 or H2)
- Purge mode: All secondary gases changed to N2 (nitrogen)
- Primary gases remain unchanged in purge mode
- Real-time reconfiguration of all connected BGA devices
- Visual indication in UI when purge mode is active

---

### ✅ 26. CVM-24P test script review + cleanup
**Start:** Review your existing CVM-24P test script  
**End:** Write cleaned standalone script to retrieve all cell voltages

---

### ✅ 27. Integrate CVM-24P into service
**Start:** Replace `cvm24p.py` with real USB communication and parsing  
**End:** Real voltage values update plots and state

**Completed with comprehensive hardware integration:**
- ✅ Real XC2 protocol communication via SerialBus at 1MHz baud rate
- ✅ Multi-module support: 5 CVM24P modules with 120 total channels (5 × 24)
- ✅ Hardware module discovery and initialization using broadcast echo
- ✅ Individual module management with persistent addressing
- ✅ Real-time voltage reading using `read_and_get_reg_by_name("ch_V")`
- ✅ GlobalState integration for dashboard voltage updates
- ✅ Thread-safe voltage polling at 10 Hz with async event loop integration
- ✅ Hardware/Mock mode detection with graceful fallback
- ✅ Device configuration integration with sample rate management
- ✅ Proper service lifecycle (connect/poll/disconnect) with robust error handling

**Hardware Integration Features:**
- `CVM24PModule` class for individual module interface with XC2Cvm24p devices
- `CVM24PService` maintains dashboard compatibility while using real hardware
- Serial port discovery and connection with cross-platform support
- Module initialization using `initial_structure_reading()` from CVM_test.py pattern
- Real voltage data streaming from electrolyzer cell monitoring
- Automatic hardware detection with fallback to mock when unavailable
- Event loop management for async XC2 protocol communication
- Module serial number tracking (158435, 158436, 158340, 158431, 158458)

**CVM24P Modules Discovered:**
- Module 158435 (Address 0xA7): 24 channels | Module 158436 (Address 0xA6): 24 channels
- Module 158340 (Address 0xA9): 24 channels | Module 158431 (Address 0xA8): 24 channels  
- Module 158458 (Address 0xA1): 24 channels

**Real Hardware Communication:**
- XC2 protocol via SerialBus with 1MHz baud rate (COM5 on Windows)
- Module discovery using `get_broadcast_echo()` and `get_serial_broadcast()`
- Device identification and initialization using `XC2Cvm24p` class
- Voltage reading using `device.read_and_get_reg_by_name("ch_V")` method
- 120-channel real-time monitoring for electrolyzer cell voltage analysis
- Hardware validation: 0.000V readings when no cells connected (correct behavior)

---

## 💾 Phase 7: Data Logging

### ✅ 28. Implement session folder logic
**Start:** Create `data/session_manager.py`  
**End:** On start test: create timestamped folder + filename base

**Completed with comprehensive session management system:**
- ✅ Timestamped session folders with structured organization
- ✅ Controller manager integration for test lifecycle management
- ✅ Global state integration with session tracking
- ✅ Configuration snapshots and metadata preservation
- ✅ Multi-directory organization (csv_data, plots, config, logs, analysis)
- ✅ File registration and path management system
- ✅ Session archiving and cleanup functionality
- ✅ Emergency stop integration with proper session handling

**Session Management Features:**
- `SessionManager` class for complete session lifecycle management
- Timestamped folder creation: `YYYY-MM-DD_HH-MM-SS_session_name`
- Structured subdirectories for organized data storage
- Session metadata tracking with JSON persistence
- File registration system with type categorization
- Configuration snapshot preservation at test start
- Session archiving for long-term storage management

**Controller Integration:**
- `start_test()` method creates new session with hardware validation
- `stop_test()` method finalizes session with duration and file count
- `emergency_stop()` method handles session cleanup during emergencies
- Global state synchronization for session tracking
- File path generation for data logging integration
- Service status preservation in session configuration

**Directory Structure Created:**
```
data/sessions/
  2025-06-04_17-35-33_Integration_Test_Session/
    ├── csv_data/          # Raw sensor data CSV files
    ├── plots/             # Generated plots and charts  
    ├── config/            # Configuration snapshots
    ├── logs/              # Log files and debug info
    ├── analysis/          # Post-test analysis results
    └── session_metadata.json
```

**Session Workflow:**
1. **Test Start**: Creates timestamped folder + saves device configuration
2. **Data Collection**: Provides file paths for CSV logging and plot generation
3. **Test Stop**: Finalizes metadata with duration and file inventory
4. **Emergency Stop**: Safely terminates session and hardware services
5. **Archival**: Automatic cleanup of old sessions after configurable period

**Integration Points:**
- Controller manager calls session start/stop during test lifecycle
- Global state tracks current session ID and status
- Service managers can request session file paths for data logging
- Configuration system provides device snapshots for reproducibility
- UI components can display current session information

---

### ✅ 29. Implement CSV logger
**Start:** Create `data/logger.py`  
**End:** Start test begins periodic writes of `state` values to a CSV

**Completed with comprehensive real-time data logging system:**
- ✅ Multi-file CSV logging with organized data separation
- ✅ Session integration for automatic start/stop with test lifecycle
- ✅ Controller manager integration with seamless workflow
- ✅ Thread-safe real-time data collection at configurable intervals
- ✅ Comprehensive sensor data coverage (pressure, temperature, voltage, gas)
- ✅ Emergency stop integration with proper file cleanup
- ✅ Robust error handling and file management

**CSV Logger Features:**
- `CSVLogger` class for real-time sensor data logging
- Multi-file organization: sensors, gas analysis, cell voltages, actuator states
- Configurable logging intervals (default 1 second)
- Automatic file registration with session manager
- Thread-safe data collection with proper synchronization
- File statistics and logging performance monitoring

**File Structure:**
- `main_sensors.csv`: Pressure, current, and temperature data (13 columns)
- `gas_analysis.csv`: BGA244 gas concentrations and purge mode (15 columns)  
- `cell_voltages.csv`: CVM24P individual cell voltages (122 columns)
- `actuator_states.csv`: Valve and pump states (7 columns)

**Controller Integration:**
- Automatic CSV logging start when `start_test()` is called
- Automatic CSV logging stop when `stop_test()` is called
- Emergency stop handling with immediate logging termination
- Session file path integration for organized data storage
- Logging status reporting in test lifecycle messages

**Data Collection:**
- Real-time polling from GlobalState at 1Hz intervals
- Millisecond timestamp precision for accurate time series
- Elapsed time tracking from test start
- Comprehensive sensor coverage: 160+ data points per log entry
- Proper data validation and error handling
- File flushing for immediate data persistence

**Test Results:**
- ✅ 4 CSV files created automatically per test session
- ✅ Real-time data logging during test execution
- ✅ Proper file cleanup and statistics on test stop
- ✅ Emergency stop integration verified
- ✅ Session folder organization maintained
- ✅ 6 log entries collected in 5-second test (1Hz rate verified)

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
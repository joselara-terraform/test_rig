# Standardized Logging System

**AWE Test Rig - Developer Documentation**

---

## Overview

The AWE Test Rig uses a standardized logging system that provides consistent, professional output across all components. Every log message follows a uniform format with timestamps, log levels, component identification, and optional structured details.

### Standard Format
```
[TIMESTAMP] [LEVEL] [COMPONENT] - MESSAGE
    └── Optional structured sublines with indents
```

### Example Output
```
[2025-08-01 12:08:30] SUCCESS  [DAQ]          - NI cDAQ connected and polling at 100 Hz
    • Found: cDAQ9187-23E902C
    → 8 analog channels configured
    → 7 digital outputs configured
[2025-08-01 12:08:30] INFO     [UI]           - Connect button clicked
[2025-08-01 12:08:30] WARNING  [BGA244]       - No BGA244 hardware detected
    → All BGAs will show no data until connected
[2025-08-01 12:08:30] ERROR    [FileSystem]   - Cannot write to log directory
    → Path: /var/log/test_rig/
    → Error: Permission denied
    → Solution: Check directory permissions
```

---

## Quick Start

### 1. Import the Logger
```python
from utils.logger import log
```

### 2. Basic Usage
```python
# General information
log.info("Component", "What's happening")

# Successful operations  
log.success("Component", "What succeeded")

# Warning conditions
log.warning("Component", "What needs attention")

# Error conditions
log.error("Component", "What went wrong")
```

### 3. With Structured Details
```python
log.success("Hardware", "Sensors initialized", [
    "• Temperature: 8 channels",
    "• Pressure: 6 channels",
    "→ All sensors ready"
])
```

---

## Log Levels

### 📘 INFO - General Information
**When to use:** Status updates, user actions, normal operations

```python
log.info("System", "Starting application")
log.info("UI", "Connect button clicked") 
log.info("Config", "Loading device configuration")
log.info("SessionMgr", "Creating new test session")
```

**Terminal Output:** Blue colored level indicator

### ✅ SUCCESS - Successful Operations  
**When to use:** Operations that completed successfully, confirmations

```python
log.success("DAQ", "NI cDAQ connected successfully")
log.success("System", "All 4 services started successfully")
log.success("TestRunner", "Test session completed")
log.success("DataLogger", "CSV logging started successfully")
```

**Terminal Output:** Green colored level indicator

### ⚠️ WARNING - Warning Conditions
**When to use:** Non-critical issues, fallbacks, degraded performance

```python
log.warning("Sensor", "Calibration date expired - using defaults")
log.warning("Memory", "High memory usage: 85%")
log.warning("BGA244", "No hardware detected")
log.warning("Network", "Connection slow - retrying")
```

**Terminal Output:** Yellow colored level indicator

### ❌ ERROR - Error Conditions
**When to use:** Failures, critical problems, exceptions

```python
log.error("Database", "Connection failed")
log.error("FileSystem", "Cannot write to directory")
log.error("Hardware", "Sensor timeout")
log.error("Communication", "Serial port connection failed")
```

**Terminal Output:** Red colored level indicator

---

## Component Naming Conventions

### Hardware Components
- `"DAQ"` - Data acquisition (NI cDAQ)
- `"TC08"` - Temperature controller (Pico TC-08)
- `"BGA244"` - Gas analyzer
- `"CVM24P"` - Cell voltage monitor
- `"Sensors"` - General sensor operations
- `"Actuators"` - Valve/pump control

### Software Components  
- `"System"` - Overall system operations, initialization
- `"Libraries"` - Library loading, dependencies
- `"ConfigLoader"` - Configuration file operations
- `"SessionMgr"` - Session management
- `"DataLogger"` - CSV/data logging operations
- `"PostProcessor"` - Analysis and plot generation
- `"TestRunner"` - Test execution control

### User Interface
- `"UI"` - User interface interactions
- `"Dashboard"` - Main application window
- `"Controls"` - Control panel operations

### Best Practices for Component Names
- **Keep short and clear:** `"DAQ"` not `"DataAcquisition"`
- **Use PascalCase:** `"SessionMgr"` not `"session_mgr"`
- **Be consistent:** Use the same component name throughout a module
- **Avoid acronyms unless well-known:** `"TC08"` is OK, `"PTMS"` is not

---

## Structured Sublines

Use sublines to provide detailed information without cluttering the main message.

### Bullet Styles
- `"→"` - Process steps, actions, results
- `"•"` - List items, enumeration  
- Custom prefixes for specific contexts

### Examples

**Service Startup:**
```python
log.success("MyService", "Service started successfully", [
    "→ Port: 8080",
    "→ Connections: 0/100",
    "→ Status: Ready"
])
```

**Hardware Initialization:**
```python
log.success("Sensors", "All sensors initialized", [
    "• PT01: 0.0 PSI (Ready)",
    "• PT02: 0.0 PSI (Ready)", 
    "• PT03: Not connected",
    "→ 2/3 sensors active"
])
```

**Error with Troubleshooting:**
```python
log.error("Serial", "Connection failed", [
    "→ Port: /dev/ttyUSB0",
    "→ Error: Permission denied",
    "→ Solution: sudo chmod 666 /dev/ttyUSB0"
])
```

---

## Real-World Usage Patterns

### Service Startup Pattern
```python
def start_service(self):
    log.info("MyService", "Starting service initialization")
    
    try:
        # ... initialization logic ...
        
        log.success("MyService", "Service started successfully", [
            f"→ Port: {self.port}",
            f"→ Max connections: {self.max_connections}",
            "→ Status: Ready"
        ])
        return True
        
    except Exception as e:
        log.error("MyService", f"Service startup failed: {e}")
        return False
```

### Configuration Loading Pattern
```python
def load_configuration(self):
    log.info("ConfigLoader", "Loading device configuration")
    
    try:
        config = self._load_yaml_file()
        device_count = len(config.get('devices', {}))
        
        log.success("ConfigLoader", "Configuration loaded successfully", [
            f"→ Devices: {device_count} configured",
            f"→ Calibration: {config.get('calibration_date')}"
        ])
        return config
        
    except FileNotFoundError:
        log.error("ConfigLoader", "Configuration file not found", [
            "→ Expected: config/devices.yaml",
            "→ Check file exists and permissions"
        ])
        return None
```

### Hardware Connection Pattern
```python
def connect_hardware(self):
    log.info("Hardware", "Connecting to sensors")
    
    connected_count = 0
    for sensor in self.sensors:
        try:
            sensor.connect()
            connected_count += 1
        except Exception as e:
            log.warning("Hardware", f"Sensor {sensor.name} failed to connect: {e}")
    
    if connected_count == len(self.sensors):
        log.success("Hardware", "All sensors connected")
    elif connected_count > 0:
        log.warning("Hardware", f"Partial connection: {connected_count}/{len(self.sensors)} sensors")
    else:
        log.error("Hardware", "No sensors connected")
    
    return connected_count > 0
```

### Test Session Pattern
```python
def start_test_session(self, session_name):
    log.info("TestRunner", "Starting new test session")
    
    try:
        session = self.create_session(session_name)
        self.start_logging()
        self.start_timer()
        
        log.success("TestRunner", "Test session started", [
            f"→ Session: {session_name}",
            "→ CSV logging: Active",
            "→ Timer: Started",
            "→ Duration: 0:00:00"
        ])
        return session
        
    except Exception as e:
        log.error("TestRunner", f"Failed to start test session: {e}")
        return None
```

---

## Best Practices

### ✅ DO

**Clear and Concise Messages**
```python
log.info("Database", "Connecting to sensor database")
log.success("Calibration", "All sensors calibrated successfully")
log.warning("Memory", "High memory usage: 85%")
```

**Use Structured Details for Complex Information**
```python
log.success("Hardware", "System initialization complete", [
    "• Sensors: 15 active",
    "• Storage: 2.5GB available",
    "• Memory: 45% used",
    "→ Status: All systems operational"
])
```

**Include Context in Error Messages**
```python
log.error("FileSystem", "Cannot write to log directory", [
    "→ Path: /var/log/test_rig/",
    "→ Error: Permission denied",
    "→ Solution: Check directory permissions"
])
```

**Use Consistent Component Names**
```python
# Throughout your module, always use the same component name
log.info("SessionMgr", "Creating new session")
log.success("SessionMgr", "Session created successfully") 
log.error("SessionMgr", "Session creation failed")
```

### ❌ DON'T

**Too Verbose**
```python
# Bad
log.info("System", "The system is now starting up and initializing all the hardware components and software services")

# Good  
log.info("System", "Starting system initialization")
```

**Too Cryptic**
```python
# Bad
log.error("DB", "Err 42")

# Good
log.error("Database", "Connection timeout after 30 seconds")
```

**Inconsistent Component Names**
```python
# Bad - inconsistent naming
log.info("temp_sensor", "Starting temperature reading")
log.success("TEMP_SENSOR", "Temperature read successfully")
log.error("TempSensor", "Temperature reading failed")

# Good - consistent naming
log.info("TempSensor", "Starting temperature reading")
log.success("TempSensor", "Temperature read successfully")
log.error("TempSensor", "Temperature reading failed")
```

**Missing Important Context**
```python
# Bad - what connection? why did it fail?
log.error("Connection", "Failed")

# Good - specific and actionable
log.error("Database", "Connection failed: timeout after 30s")
```

---

## Advanced Patterns

### Progress Tracking
```python
def calibrate_all_sensors(self):
    total_sensors = len(self.sensors)
    log.info("Calibration", "Starting sensor calibration sequence")
    
    failed_count = 0
    start_time = time.time()
    
    for i, sensor in enumerate(self.sensors):
        try:
            sensor.calibrate()
        except Exception as e:
            failed_count += 1
            log.warning("Calibration", f"Sensor {sensor.name} calibration failed: {e}")
    
    duration = time.time() - start_time
    success_count = total_sensors - failed_count
    
    if failed_count == 0:
        log.success("Calibration", "All sensors calibrated successfully", [
            f"→ Sensors: {total_sensors} processed",
            "→ Failures: 0",
            f"→ Duration: {duration:.1f}s"
        ])
    else:
        log.warning("Calibration", "Calibration completed with issues", [
            f"→ Success: {success_count}/{total_sensors}",
            f"→ Failures: {failed_count}",
            f"→ Duration: {duration:.1f}s"
        ])
```

### Conditional Logging Based on State
```python
def report_system_health(self):
    error_count = self.get_error_count()
    warning_count = self.get_warning_count()
    
    if error_count == 0 and warning_count == 0:
        log.success("Health", "All systems healthy")
    elif error_count == 0 and warning_count < 5:
        log.warning("Health", f"Minor issues detected: {warning_count} warnings")
    elif error_count < 3:
        log.warning("Health", f"Issues detected: {error_count} errors, {warning_count} warnings")
    else:
        log.error("Health", f"Critical system issues: {error_count} errors, {warning_count} warnings")
```

### Resource Monitoring
```python
def monitor_resources(self):
    memory_usage = self.get_memory_usage_percent()
    disk_usage = self.get_disk_usage_percent()
    
    # Memory monitoring
    if memory_usage > 90:
        log.error("Memory", f"Critical memory usage: {memory_usage}%")
    elif memory_usage > 80:
        log.warning("Memory", f"High memory usage: {memory_usage}%")
    
    # Disk monitoring  
    if disk_usage > 95:
        log.error("Storage", f"Critical disk usage: {disk_usage}%")
    elif disk_usage > 85:
        log.warning("Storage", f"High disk usage: {disk_usage}%")
```

### Retry Logic with Logging
```python
def connect_with_retry(self, max_attempts=3):
    for attempt in range(1, max_attempts + 1):
        try:
            self.connect()
            log.success("Connection", "Connected successfully", [
                f"→ Attempt: {attempt}/{max_attempts}"
            ])
            return True
            
        except Exception as e:
            if attempt < max_attempts:
                log.warning("Connection", f"Connection failed - retrying", [
                    f"→ Attempt: {attempt}/{max_attempts}",
                    f"→ Error: {e}",
                    f"→ Next retry in: {self.retry_delay}s"
                ])
                time.sleep(self.retry_delay)
            else:
                log.error("Connection", f"Connection failed after {max_attempts} attempts", [
                    f"→ Final error: {e}"
                ])
    
    return False
```

---

## Migration Guide

### Converting Existing Print Statements

**Old Style (Inconsistent):**
```python
print("✅ Pico TC-08 libraries available")
print("🔌 Connect button clicked")
print("   → Starting NI cDAQ service...")
print("📊 Starting CSV data logging...")
print("⏹️  Stop Test button clicked")
print("❌ Connection failed")
```

**New Style (Standardized):**
```python
log.success("Libraries", "Pico TC-08 library loaded")
log.info("UI", "Connect button clicked")
log.info("System", "Starting NI cDAQ service")
log.success("DataLogger", "CSV data logging started")
log.info("UI", "Stop Test button clicked")
log.error("Connection", "Connection failed")
```

### Step-by-Step Migration

1. **Add the import:**
   ```python
   from utils.logger import log
   ```

2. **Replace print statements:**
   - Identify the appropriate log level (info, success, warning, error)
   - Choose a consistent component name
   - Convert the message to be concise and clear

3. **Convert detailed output:**
   ```python
   # Old
   print("✅ Hardware connected")
   print("   • Sensors: 15 active")
   print("   • Storage: 2.5GB available") 
   
   # New
   log.success("Hardware", "Hardware connected", [
       "• Sensors: 15 active",
       "• Storage: 2.5GB available"
   ])
   ```

4. **Test the output** to ensure formatting looks correct

---

## Quick Reference

### Import
```python
from utils.logger import log
```

### Basic Methods
```python
log.info(component, message)
log.success(component, message)
log.warning(component, message)  
log.error(component, message)
```

### With Sublines
```python
log.level(component, message, [
    "→ Detail 1",
    "• Detail 2",
    "→ Summary"
])
```

### Common Component Names
| Component | Usage |
|-----------|-------|
| `"System"` | Overall system operations |
| `"Libraries"` | Library loading |
| `"ConfigLoader"` | Configuration operations |
| `"SessionMgr"` | Session management |
| `"DataLogger"` | CSV/data logging |
| `"DAQ"` | Data acquisition |
| `"TC08"` | Temperature monitoring |
| `"BGA244"` | Gas analysis |
| `"CVM24P"` | Cell voltage monitoring |
| `"UI"` | User interface |
| `"TestRunner"` | Test execution |
| `"PostProcessor"` | Analysis/plots |

### Subline Prefixes
- `"→"` - Process steps, actions, results
- `"•"` - List items, enumeration
- Custom prefixes for specific contexts

---

## Technical Details

### Logger Implementation
- Located in: `utils/logger.py`
- Class: `TestRigLogger`
- Instance: `log` (imported from `utils.logger`)

### Features
- **Automatic timestamps** in format `YYYY-MM-DD HH:MM:SS`
- **Color-coded output** using ANSI escape codes
- **Aligned columns** for consistent formatting
- **Optional sublines** for structured details
- **Thread-safe** operation

### Color Scheme
- **INFO:** Blue (`\033[94m`)
- **SUCCESS:** Green (`\033[92m`)  
- **WARNING:** Yellow (`\033[93m`)
- **ERROR:** Red (`\033[91m`)

---

*This documentation covers the standardized logging system implemented across the AWE Test Rig codebase. For questions or updates, please maintain consistency with these guidelines.* 
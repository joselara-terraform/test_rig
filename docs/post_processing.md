# AWE Test Rig Data Post-Processing

The AWE Test Rig includes comprehensive data post-processing capabilities that automatically generate analysis plots from CSV data collected during test sessions.

## Features

- **5 Standard Plots**: Pressure, Gas Purity, Temperature, Cell Voltage, Current
- **Consistent Formatting**: Same axis limits and styling as the live UI plots
- **Active Channel Tracking**: Only plots channels that were active during the test
- **JPEG Output**: High-quality 300 DPI JPEG files for reports and documentation
- **Dual Usage**: Can run automatically after tests or independently on existing data

## Generated Plots

1. **pressure.jpg** - Pressure sensors vs time (0-1 normalized, 0s to max time)
2. **gas_purity.jpg** - Gas concentrations vs time (0-100%, 0s to max time)  
3. **temperature.jpg** - Temperature sensors vs time (0-100°C, 0s to max time)
4. **cell_voltage.jpg** - Cell voltages vs time (0-5V, 0s to max time)
5. **current.jpg** - Stack current vs time (0-150A, 0s to max time)

## Automatic Integration

Post-processing runs automatically when you stop a test in the main application:

```python
# In the UI or controller
controller.stop_test("completed")  # Automatically runs post-processing
```

**What happens automatically:**
1. Test stops and CSV logging ends
2. Active channel settings are saved to session metadata
3. Post-processing runs on the CSV data
4. 5 plots are generated and saved to the session's `plots/` folder
5. Success/failure status is reported

## Standalone Usage

You can also run post-processing independently on any existing session folder:

### Command Line

```bash
# Run on a specific session folder
python data/post_processor.py path/to/session/folder

# Example
python data/post_processor.py data/sessions/2025-07-01_12-25-53_UI_Test_Session
```

### Python Code

```python
from data.post_processor import process_session_data

# Process with automatic channel detection
success = process_session_data("path/to/session/folder")

# Process with custom active channels
active_channels = {
    'pressure': [0, 1],        # Only pressure channels 0 and 1
    'gas': [0, 1, 2],          # All gas channels  
    'temperature': [0, 2, 4],  # Selected temperature channels
    'voltage': list(range(20)), # First 20 voltage channels
    'current': [0]             # Current channel
}

success = process_session_data("path/to/session/folder", active_channels)
```

### Test Script

Use the included test script for easy standalone processing:

```bash
python test_post_processor.py data/sessions/2025-07-01_12-25-53_UI_Test_Session
```

## Session Folder Structure

The post-processor expects this folder structure:

```
session_folder/
├── csv_data/
│   ├── YYYY-MM-DD_HH-MM-SS_sensors.csv
│   ├── YYYY-MM-DD_HH-MM-SS_gas_analysis.csv
│   ├── YYYY-MM-DD_HH-MM-SS_cell_voltages.csv
│   └── YYYY-MM-DD_HH-MM-SS_actuators.csv
├── plots/                    # Generated plots saved here
│   ├── pressure.jpg
│   ├── gas_purity.jpg
│   ├── temperature.jpg
│   ├── cell_voltage.jpg
│   └── current.jpg
└── session_metadata.json    # Contains active channel settings
```

## Active Channel Configuration

Active channels are automatically saved when tests end. The format is:

```json
{
  "active_channels": {
    "pressure": [0, 1, 2, 3, 4],
    "gas": [0, 1, 2], 
    "temperature": [0, 1, 2, 3, 4, 5, 6, 7],
    "voltage": [0, 1, 2, ...],
    "current": [0]
  }
}
```

## Error Handling

- **Missing CSV files**: Post-processing skips gracefully with warnings
- **Empty data**: Plots are not generated if no data is available
- **Emergency stops**: Post-processing is automatically skipped
- **Channel mismatches**: Default channels are used if metadata is missing

## Dependencies

Required packages (automatically installed with requirements.txt):

- `pandas>=2.0.0` - CSV data loading and manipulation
- `matplotlib>=3.7.0` - Plot generation and JPEG export
- `numpy>=1.24.0` - Numerical operations

## Integration Points

The post-processor integrates with:

- **Controller Manager**: Automatic execution after test completion
- **Session Manager**: Active channel tracking and metadata storage
- **Global State**: Channel visibility settings from the UI
- **CSV Logger**: Compatible with all logged data formats

## Examples

### Full Test Workflow

1. Start test: `controller.start_test("My_Test")`
2. Operate system and collect data
3. Stop test: `controller.stop_test("completed")`
4. **Automatic post-processing runs**
5. Check `data/sessions/YYYY-MM-DD_HH-MM-SS_My_Test/plots/` for results

### Reprocessing Old Data

```bash
# Find existing sessions
ls data/sessions/

# Reprocess with updated post-processor
python data/post_processor.py data/sessions/2025-07-01_12-25-53_UI_Test_Session

# Results overwrite existing plots
```

### Batch Processing

```python
from pathlib import Path
from data.post_processor import process_session_data

sessions_dir = Path("data/sessions")
for session_folder in sessions_dir.iterdir():
    if session_folder.is_dir() and "test" in session_folder.name.lower():
        print(f"Processing {session_folder.name}...")
        process_session_data(str(session_folder))
```

## Notes

- Plots use the same axis limits and styling as the live UI plots
- Only channels that were visible/active during the test are plotted
- Cell voltage plots are limited to 20 channels maximum for clarity
- Post-processing is automatically skipped for emergency stops
- Generated plots are high-quality (300 DPI) suitable for reports 
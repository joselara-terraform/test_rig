"""
CSV data logger for AWE test rig
Handles real-time logging of sensor data during test sessions
"""

import csv
import time
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from core.state import get_global_state
from data.session_manager import get_session_manager
import os


class CSVLogger:
    """Real-time CSV data logger for test sessions"""
    
    def __init__(self, log_interval: float = 1.0):
        self.state = get_global_state()
        self.session_manager = get_session_manager()
        self.log_interval = log_interval  # seconds between log entries
        
        # Logging control
        self.logging = False
        self.log_thread = None
        self.stop_event = threading.Event()
        
        # File paths and writers
        self.csv_files = {}
        self.csv_writers = {}
        self.file_handles = {}
        
        # Data counters for statistics
        self.log_count = 0
        self.start_time = None
        
        # Column definitions for different data types
        self.column_definitions = {
            'main_sensors': [
                'timestamp', 'elapsed_seconds',
                'pressure_h2_psi', 'pressure_o2_psi', 'current_a',
                'temp_inlet_c', 'temp_outlet_c', 'temp_stack1_c', 'temp_stack2_c',
                'temp_ambient_c', 'temp_cooling_c', 'temp_gas_c', 'temp_case_c'
            ],
            'gas_analysis': [
                'timestamp', 'elapsed_seconds',
                'bga1_primary_gas_pct', 'bga1_secondary_gas_pct', 'bga1_remaining_gas_pct', 
                'bga1_primary_gas_type', 'bga1_secondary_gas_type', 'bga1_remaining_gas_type',
                'bga2_primary_gas_pct', 'bga2_secondary_gas_pct', 'bga2_remaining_gas_pct',
                'bga2_primary_gas_type', 'bga2_secondary_gas_type', 'bga2_remaining_gas_type',
                'bga3_primary_gas_pct', 'bga3_secondary_gas_pct', 'bga3_remaining_gas_pct',
                'bga3_primary_gas_type', 'bga3_secondary_gas_type', 'bga3_remaining_gas_type',
                'purge_mode'
            ],
            'cell_voltages': [
                'timestamp', 'elapsed_seconds'
            ] + [f'cell_{i+1:03d}_v' for i in range(120)],  # cell_001_v to cell_120_v
            'actuator_states': [
                'timestamp', 'elapsed_seconds',
                'valve_koh_storage', 'valve_di_storage', 'valve_stack_drain', 'valve_n2_purge',
                'pump_main'
            ]
        }
    
    def start_logging(self) -> bool:
        """Start logging data to CSV files"""
        if self.logging:
            print("⚠️  CSV logging already running")
            return True
        
        # Check if there's an active session
        current_session = self.session_manager.get_current_session()
        if not current_session:
            print("❌ Cannot start logging - no active test session")
            print("   → Call session_manager.start_new_session() first")
            return False
        
        print("📊 Starting CSV data logging...")
        print(f"   → Session: {current_session['session_id']}")
        print(f"   → Session folder: {current_session['folder_path']}")
        
        try:
            # Initialize CSV files
            print("   → Initializing CSV files...")
            if not self._initialize_csv_files():
                print("❌ Failed to initialize CSV files")
                return False
            
            # Start logging thread
            self.logging = True
            self.stop_event.clear()
            self.log_count = 0
            self.start_time = time.time()
            
            self.log_thread = threading.Thread(target=self._logging_worker, daemon=True)
            self.log_thread.start()
            
            print(f"✅ CSV logging started successfully")
            print(f"   → Log interval: {self.log_interval}s")
            print(f"   → Files created: {len(self.csv_files)}")
            for file_type, file_path in self.csv_files.items():
                print(f"      • {file_type}: {Path(file_path).name}")
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to start CSV logging: {e}")
            import traceback
            print(f"   → Error details: {traceback.format_exc()}")
            self._cleanup_files()
            return False
    
    def stop_logging(self) -> Dict[str, Any]:
        """Stop logging and finalize CSV files"""
        if not self.logging:
            print("⚠️  CSV logging not running")
            return {}
        
        print("📊 Stopping CSV data logging...")
        
        # Signal stop and wait for thread
        self.stop_event.set()
        self.logging = False
        
        if self.log_thread and self.log_thread.is_alive():
            self.log_thread.join(timeout=5.0)
        
        # Finalize and close files
        stats = self._finalize_files()
        
        print(f"✅ CSV logging stopped")
        print(f"   → Log entries: {self.log_count}")
        print(f"   → Duration: {stats.get('duration_formatted', 'Unknown')}")
        
        return stats
    
    def _initialize_csv_files(self) -> bool:
        """Initialize CSV files with headers"""
        try:
            # Get base filename from session manager
            print("      → Getting base filename from session manager...")
            base_filename = self.session_manager.get_base_filename("data")
            print(f"      → Base filename: {base_filename}")
            
            # Create CSV files for different data types
            file_configs = {
                'main_sensors': f"{base_filename}_sensors.csv",
                'gas_analysis': f"{base_filename}_gas_analysis.csv", 
                'cell_voltages': f"{base_filename}_cell_voltages.csv",
                'actuator_states': f"{base_filename}_actuators.csv"
            }
            
            print(f"      → Creating {len(file_configs)} CSV files...")
            
            # Initialize each CSV file
            for file_type, filename in file_configs.items():
                print(f"         • Creating {file_type}: {filename}")
                
                # Register file with session manager
                file_path = self.session_manager.register_file(
                    filename, 
                    "csv", 
                    f"Real-time {file_type.replace('_', ' ')} data"
                )
                print(f"           → Full path: {file_path}")
                
                # Check if directory exists and is writable
                file_path_obj = Path(file_path)
                parent_dir = file_path_obj.parent
                
                if not parent_dir.exists():
                    print(f"           → Creating directory: {parent_dir}")
                    parent_dir.mkdir(parents=True, exist_ok=True)
                
                if not parent_dir.is_dir():
                    raise Exception(f"Parent directory is not a directory: {parent_dir}")
                
                # Test write permissions
                if not os.access(parent_dir, os.W_OK):
                    raise Exception(f"No write permission to directory: {parent_dir}")
                
                # Open file and create CSV writer
                print(f"           → Opening file for writing...")
                file_handle = open(file_path, 'w', newline='', encoding='utf-8')
                csv_writer = csv.writer(file_handle)
                
                # Write header row
                headers = self.column_definitions[file_type]
                print(f"           → Writing {len(headers)} column headers")
                csv_writer.writerow(headers)
                file_handle.flush()
                
                # Store references
                self.csv_files[file_type] = file_path
                self.file_handles[file_type] = file_handle
                self.csv_writers[file_type] = csv_writer
                
                print(f"           → ✅ {file_type} file created successfully")
            
            print(f"      → ✅ All {len(file_configs)} CSV files initialized")
            return True
            
        except Exception as e:
            print(f"❌ Error initializing CSV files: {e}")
            import traceback
            print(f"   → Error details: {traceback.format_exc()}")
            self._cleanup_files()
            return False
    
    def _logging_worker(self):
        """Main logging worker thread"""
        print(f"📊 CSV logging worker started (interval: {self.log_interval}s)")
        
        while self.logging and not self.stop_event.is_set():
            try:
                # Get current timestamp
                current_time = datetime.now()
                timestamp_str = current_time.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]  # millisecond precision
                elapsed_seconds = time.time() - self.start_time
                
                # Log different data types
                self._log_main_sensors(timestamp_str, elapsed_seconds)
                self._log_gas_analysis(timestamp_str, elapsed_seconds)
                self._log_cell_voltages(timestamp_str, elapsed_seconds)
                self._log_actuator_states(timestamp_str, elapsed_seconds)
                
                # Flush all files
                for file_handle in self.file_handles.values():
                    file_handle.flush()
                
                self.log_count += 1
                
                # Wait for next interval
                self.stop_event.wait(self.log_interval)
                
            except Exception as e:
                print(f"❌ CSV logging error: {e}")
                break
        
        print("📊 CSV logging worker stopped")
    
    def _log_main_sensors(self, timestamp: str, elapsed: float):
        """Log main sensor data (pressure, current, temperature)"""
        try:
            # Get current sensor values
            pressure_vals = self.state.pressure_values[:2]
            current_val = self.state.current_value
            temp_vals = self.state.temperature_values[:8]
            
            # Ensure we have the right number of values
            while len(pressure_vals) < 2:
                pressure_vals.append(0.0)
            while len(temp_vals) < 8:
                temp_vals.append(0.0)
            
            # Create row data
            row = [
                timestamp, round(elapsed, 3),
                round(pressure_vals[0], 3), round(pressure_vals[1], 3), round(current_val, 1),
                round(temp_vals[0], 1), round(temp_vals[1], 1), round(temp_vals[2], 1), round(temp_vals[3], 1),
                round(temp_vals[4], 1), round(temp_vals[5], 1), round(temp_vals[6], 1), round(temp_vals[7], 1)
            ]
            
            self.csv_writers['main_sensors'].writerow(row)
            
        except Exception as e:
            print(f"⚠️  Error logging main sensors: {e}")
    
    def _log_gas_analysis(self, timestamp: str, elapsed: float):
        """Log gas analysis data from BGA244 units with primary/secondary gas format"""
        try:
            # Get enhanced gas data from state (if available)
            enhanced_gas_data = getattr(self.state, 'enhanced_gas_data', [])
            purge_mode = self.state.purge_mode
            
            # Create row data with primary/secondary gas format
            row = [timestamp, round(elapsed, 3)]
            
            # If enhanced data is available, use it
            if enhanced_gas_data and len(enhanced_gas_data) >= 3:
                # Process each BGA unit using enhanced data
                for i in range(3):  # Only first 3 units
                    gas_reading = enhanced_gas_data[i]
                    
                    # Extract gas assignments and concentrations
                    primary_gas = gas_reading.get('primary_gas', 'H2')
                    secondary_gas = gas_reading.get('secondary_gas', 'O2')
                    remaining_gas = gas_reading.get('remaining_gas', 'N2')
                    
                    primary_pct = gas_reading.get('primary_gas_concentration', 0.0)
                    secondary_pct = gas_reading.get('secondary_gas_concentration', 0.0)
                    remaining_pct = gas_reading.get('remaining_gas_concentration', 0.0)
                    
                    # Add data to row
                    row.extend([
                        round(primary_pct, 3), round(secondary_pct, 3), round(remaining_pct, 3),
                        primary_gas, secondary_gas, remaining_gas
                    ])
            else:
                # Fallback to legacy data format
                from services.bga244 import BGA244Config
                gas_data = self.state.gas_concentrations[:3]
                
                # Ensure we have data for all 3 BGA units
                while len(gas_data) < 3:
                    gas_data.append({'H2': 0.0, 'O2': 0.0, 'N2': 0.0, 'other': 0.0})
                
                # Process each BGA unit using configuration and purge mode
                unit_ids = list(BGA244Config.BGA_UNITS.keys())
                for i, unit_id in enumerate(unit_ids[:3]):  # Only first 3 units
                    unit_config = BGA244Config.BGA_UNITS[unit_id]
                    gas_readings = gas_data[i]
                    
                    # Determine current gas assignments based on purge mode
                    if purge_mode:
                        if unit_config['name'] == 'H2 Header':
                            primary_gas = 'H2'
                            secondary_gas = 'N2'
                            remaining_gas = 'O2'
                        elif unit_config['name'] == 'O2 Header':
                            primary_gas = 'O2'
                            secondary_gas = 'N2'
                            remaining_gas = 'H2'
                        else:  # De-oxo
                            primary_gas = 'H2'
                            secondary_gas = 'N2'
                            remaining_gas = 'O2'
                    else:
                        # Normal mode
                        primary_gas = unit_config['primary_gas']
                        secondary_gas = unit_config['secondary_gas']
                        remaining_gas = 'N2'  # Typically N2 in normal mode
                    
                    # Extract concentrations
                    primary_pct = gas_readings.get(primary_gas, 0.0)
                    secondary_pct = gas_readings.get(secondary_gas, 0.0)
                    remaining_pct = gas_readings.get(remaining_gas, 0.0)
                    
                    # Add data to row
                    row.extend([
                        round(primary_pct, 3), round(secondary_pct, 3), round(remaining_pct, 3),
                        primary_gas, secondary_gas, remaining_gas
                    ])
            
            # Add purge mode flag
            row.append(purge_mode)
            
            self.csv_writers['gas_analysis'].writerow(row)
            
        except Exception as e:
            print(f"⚠️  Error logging gas analysis: {e}")
    
    def _log_cell_voltages(self, timestamp: str, elapsed: float):
        """Log cell voltage data from CVM24P"""
        try:
            # Get cell voltage data
            cell_voltages = self.state.cell_voltages[:120]
            
            # Ensure we have 120 voltage values
            while len(cell_voltages) < 120:
                cell_voltages.append(0.0)
            
            # Create row data
            row = [timestamp, round(elapsed, 3)] + [round(v, 3) for v in cell_voltages]
            
            self.csv_writers['cell_voltages'].writerow(row)
            
        except Exception as e:
            print(f"⚠️  Error logging cell voltages: {e}")
    
    def _log_actuator_states(self, timestamp: str, elapsed: float):
        """Log actuator states (valves and pump)"""
        try:
            # Get actuator states
            valve_states = self.state.valve_states[:4]
            pump_state = self.state.pump_state
            
            # Ensure we have 4 valve states
            while len(valve_states) < 4:
                valve_states.append(False)
            
            # Create row data (convert boolean to int for CSV)
            row = [
                timestamp, round(elapsed, 3),
                int(valve_states[0]), int(valve_states[1]), int(valve_states[2]), int(valve_states[3]),
                int(pump_state)
            ]
            
            self.csv_writers['actuator_states'].writerow(row)
            
        except Exception as e:
            print(f"⚠️  Error logging actuator states: {e}")
    
    def _finalize_files(self) -> Dict[str, Any]:
        """Close all CSV files and generate statistics"""
        stats = {
            'log_count': self.log_count,
            'files_created': len(self.csv_files),
            'file_paths': self.csv_files.copy()
        }
        
        if self.start_time:
            duration = time.time() - self.start_time
            stats['duration_seconds'] = duration
            stats['duration_formatted'] = f"{int(duration//60):02d}:{int(duration%60):02d}"
            stats['average_rate'] = self.log_count / duration if duration > 0 else 0
        
        # Close all file handles
        for file_handle in self.file_handles.values():
            try:
                file_handle.close()
            except Exception as e:
                print(f"⚠️  Error closing file: {e}")
        
        # Clear references
        self.csv_files.clear()
        self.csv_writers.clear()
        self.file_handles.clear()
        
        return stats
    
    def _cleanup_files(self):
        """Cleanup files in case of error during initialization"""
        for file_handle in self.file_handles.values():
            try:
                file_handle.close()
            except:
                pass
        
        self.csv_files.clear()
        self.csv_writers.clear()
        self.file_handles.clear()
    
    def get_status(self) -> Dict[str, Any]:
        """Get current logging status"""
        status = {
            'logging': self.logging,
            'log_interval': self.log_interval,
            'log_count': self.log_count,
            'files_active': len(self.csv_files)
        }
        
        if self.start_time:
            duration = time.time() - self.start_time
            status['duration_seconds'] = duration
            status['duration_formatted'] = f"{int(duration//60):02d}:{int(duration%60):02d}"
            status['average_rate'] = self.log_count / duration if duration > 0 else 0
        
        return status
    
    def set_log_interval(self, interval: float):
        """Update logging interval"""
        if interval > 0:
            self.log_interval = interval
            print(f"📊 CSV log interval updated to {interval}s")
        else:
            print("❌ Log interval must be positive")


# Global logger instance
_csv_logger = None
_logger_lock = threading.Lock()


def get_csv_logger() -> CSVLogger:
    """Get the global CSV logger instance"""
    global _csv_logger
    if _csv_logger is None:
        with _logger_lock:
            if _csv_logger is None:
                _csv_logger = CSVLogger()
    return _csv_logger


def start_data_logging(log_interval: float = 1.0) -> bool:
    """Convenience function to start CSV data logging"""
    logger = get_csv_logger()
    logger.set_log_interval(log_interval)
    return logger.start_logging()


def stop_data_logging() -> Dict[str, Any]:
    """Convenience function to stop CSV data logging"""
    logger = get_csv_logger()
    return logger.stop_logging() 
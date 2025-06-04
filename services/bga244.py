"""
BGA244 gas analyzer service for AWE test rig
Real hardware integration with 3 BGA244 units for gas concentration monitoring
"""

import serial
import time
import threading
import platform
from typing import Dict, Any, List, Optional
from core.state import get_global_state
from config.device_config import get_device_config


class BGA244Config:
    """Configuration constants for BGA244 Gas Analyzers"""
    
    # Serial communication settings
    BAUD_RATE = 9600
    DATA_BITS = 8
    STOP_BITS = 1
    PARITY = 'N'  # None
    TIMEOUT = 2.0  # seconds
    
    # Command settings
    COMMAND_DELAY = 0.1  # seconds between command and response
    RETRY_COUNT = 3
    
    # Gas analyzer configuration
    GAS_MODE_BINARY = 1  # Binary gas mode
    
    # Gas CAS numbers for configuration
    GAS_CAS_NUMBERS = {
        'H2': '1333-74-0',    # Hydrogen
        'O2': '7782-44-7',    # Oxygen  
        'N2': '7727-37-9',    # Nitrogen
        'He': '7440-59-7',    # Helium
        'Ar': '7440-37-1',    # Argon
        'CO2': '124-38-9'     # Carbon Dioxide
    }
    
    # Platform-specific serial port configurations
    SERIAL_PORTS = {
        'Windows': ['COM4', 'COM3', 'COM5', 'COM6', 'COM7', 'COM8'],
        'Linux': ['/dev/ttyUSB0', '/dev/ttyUSB1', '/dev/ttyUSB2', '/dev/ttyACM0'],
        'Darwin': ['/dev/tty.usbserial-A1', '/dev/tty.usbserial-A2', '/dev/tty.usbserial-A3']
    }
    
    # BGA Unit configurations for AWE test rig (as specified by user)
    BGA_UNITS = {
        'bga_1': {
            'name': 'H2 Header',
            'description': 'Gas analyzer on hydrogen header',
            'primary_gas': 'H2',     # H2 in O2 mixture
            'secondary_gas': 'O2',   # H2 in O2 mixture
            'expected_gases': ['H2', 'O2', 'N2']
        },
        'bga_2': {
            'name': 'O2 Header', 
            'description': 'Gas analyzer on oxygen header',
            'primary_gas': 'O2',     # O2 in H2 mixture
            'secondary_gas': 'H2',   # O2 in H2 mixture
            'expected_gases': ['O2', 'H2', 'N2']
        },
        'bga_3': {
            'name': 'De-oxo',
            'description': 'Gas analyzer on de-oxo unit',
            'primary_gas': 'H2',     # H2 in O2 mixture
            'secondary_gas': 'O2',   # H2 in O2 mixture
            'expected_gases': ['H2', 'O2', 'N2']
        }
    }


class BGA244Device:
    """Individual BGA244 Gas Analyzer Interface"""
    
    def __init__(self, port: str, unit_config: Dict[str, Any], unit_id: str):
        self.port = port
        self.unit_config = unit_config
        self.unit_id = unit_id
        self.serial_conn = None
        self.is_connected = False
        self.device_info = {}
        self.purge_mode = False
        
    def connect(self) -> bool:
        """Connect to BGA244 device"""
        try:
            print(f"🔌 Connecting to {self.unit_config['name']} on {self.port}...")
            
            self.serial_conn = serial.Serial(
                port=self.port,
                baudrate=BGA244Config.BAUD_RATE,
                bytesize=BGA244Config.DATA_BITS,
                stopbits=BGA244Config.STOP_BITS,
                parity=BGA244Config.PARITY,
                timeout=BGA244Config.TIMEOUT
            )
            
            # Clear buffers
            self.serial_conn.reset_input_buffer()
            self.serial_conn.reset_output_buffer()
            
            # Wait for device to be ready
            time.sleep(0.5)
            
            # Test communication
            response = self._send_command("*IDN?")
            if response:
                self.device_info['identity'] = response
                self.is_connected = True
                print(f"✅ Connected: {response}")
                return True
            else:
                print(f"❌ No response from device on {self.port}")
                self.disconnect()
                return False
                
        except Exception as e:
            print(f"❌ Connection failed on {self.port}: {e}")
            self.disconnect()
            return False
    
    def disconnect(self):
        """Disconnect from BGA244 device"""
        if self.serial_conn and self.serial_conn.is_open:
            try:
                self.serial_conn.close()
                self.is_connected = False
                print(f"✅ Disconnected from {self.port}")
            except Exception as e:
                print(f"⚠️  Error disconnecting from {self.port}: {e}")
    
    def configure_gases(self, purge_mode: bool = False) -> bool:
        """Configure gas analysis mode and target gases"""
        if not self.is_connected:
            return False
        
        try:
            print(f"⚙️  Configuring {self.unit_config['name']}...")
            
            # Set binary gas mode
            self._send_command(f"MSMD {BGA244Config.GAS_MODE_BINARY}")
            
            # Configure primary gas (always the same)
            primary_gas = self.unit_config['primary_gas']
            primary_cas = BGA244Config.GAS_CAS_NUMBERS[primary_gas]
            self._send_command(f"GASP {primary_cas}")
            print(f"   Primary gas: {primary_gas} ({primary_cas})")
            
            # Configure secondary gas (changes in purge mode)
            if purge_mode:
                secondary_gas = 'N2'  # All secondary gases become N2 in purge mode
                secondary_cas = BGA244Config.GAS_CAS_NUMBERS['N2']
                print(f"   PURGE MODE: Secondary gas changed to N2")
            else:
                secondary_gas = self.unit_config['secondary_gas']
                secondary_cas = BGA244Config.GAS_CAS_NUMBERS[secondary_gas]
            
            self._send_command(f"GASS {secondary_cas}")
            print(f"   Secondary gas: {secondary_gas} ({secondary_cas})")
            
            self.purge_mode = purge_mode
            print(f"✅ Gas configuration complete for {self.unit_config['name']}")
            return True
            
        except Exception as e:
            print(f"❌ Gas configuration failed: {e}")
            return False
    
    def read_measurements(self) -> Dict[str, Any]:
        """Read all available measurements from the BGA244"""
        if not self.is_connected:
            return {}
        
        measurements = {}
        
        try:
            # Read temperature
            temp_response = self._send_command("TCEL?")
            if temp_response:
                try:
                    measurements['temperature'] = float(temp_response)
                except ValueError:
                    measurements['temperature'] = None
            
            # Read pressure  
            pres_response = self._send_command("PRES?")
            if pres_response:
                try:
                    measurements['pressure'] = float(pres_response)
                except ValueError:
                    measurements['pressure'] = None
            
            # Read speed of sound
            sos_response = self._send_command("NSOS?")
            if sos_response:
                try:
                    measurements['speed_of_sound'] = float(sos_response)
                except ValueError:
                    measurements['speed_of_sound'] = None
            
            # Read primary gas concentration
            ratio_response = self._send_command("RATO? 1")
            if ratio_response:
                try:
                    measurements['primary_gas_concentration'] = float(ratio_response)
                    measurements['primary_gas'] = self.unit_config['primary_gas']
                except ValueError:
                    measurements['primary_gas_concentration'] = None
            
            # Read secondary gas concentration (if available)
            ratio2_response = self._send_command("RATO? 2")
            if ratio2_response:
                try:
                    measurements['secondary_gas_concentration'] = float(ratio2_response)
                    if self.purge_mode:
                        measurements['secondary_gas'] = 'N2'
                    else:
                        measurements['secondary_gas'] = self.unit_config['secondary_gas']
                except ValueError:
                    measurements['secondary_gas_concentration'] = None
            
            # Calculate remaining gas concentration
            if (measurements.get('primary_gas_concentration') is not None and 
                measurements.get('secondary_gas_concentration') is not None):
                primary_conc = measurements['primary_gas_concentration']
                secondary_conc = measurements['secondary_gas_concentration']
                remaining_conc = 100.0 - primary_conc - secondary_conc
                measurements['remaining_gas_concentration'] = max(0.0, remaining_conc)
                
                # Determine remaining gas based on configuration and purge mode
                if self.purge_mode:
                    # In purge mode, secondary is N2, so remaining is usually the other main gas
                    if self.unit_config['primary_gas'] == 'H2':
                        measurements['remaining_gas'] = 'O2'
                    else:
                        measurements['remaining_gas'] = 'H2'
                else:
                    # Normal mode - remaining is typically N2
                    measurements['remaining_gas'] = 'N2'
            
            return measurements
            
        except Exception as e:
            print(f"❌ Measurement reading error: {e}")
            return {}
    
    def _send_command(self, command: str) -> Optional[str]:
        """Send command to BGA244 and return response"""
        if not self.serial_conn or not self.serial_conn.is_open:
            return None
        
        try:
            # Send command
            command_bytes = (command + '\r\n').encode('ascii')
            self.serial_conn.write(command_bytes)
            
            # Wait for response
            time.sleep(BGA244Config.COMMAND_DELAY)
            
            # Read response
            response_bytes = self.serial_conn.read_all()
            response = response_bytes.decode('ascii', errors='ignore').strip()
            
            return response if response else None
            
        except Exception as e:
            print(f"⚠️  Command error ({command}): {e}")
            return None


class BGA244Service:
    """Service for BGA244 gas analyzer units with real hardware integration"""
    
    def __init__(self):
        self.connected = False
        self.polling = False
        self.poll_thread = None
        self.state = get_global_state()
        self.device_config = get_device_config()
        
        # Hardware interfaces
        self.devices = {}
        self.use_mock = False  # Will be set based on hardware availability
        self.purge_mode = False
        
        # Individual connection status for each BGA
        self.individual_connections = {
            'bga_1': False,
            'bga_2': False,
            'bga_3': False
        }
        
        # BGA244 configuration from device config
        self.device_name = "BGA244"
        self.sample_rate = self.device_config.get_sample_rate('bga244')
        self.num_units = len(BGA244Config.BGA_UNITS)
        
        # Platform detection for port selection
        self.system = platform.system()
        
        # Mock data for fallback
        self.mock_concentrations = [
            {'H2': 95.0, 'O2': 3.0, 'N2': 2.0},  # H2 Header
            {'O2': 95.0, 'H2': 3.0, 'N2': 2.0},  # O2 Header
            {'H2': 94.0, 'O2': 4.0, 'N2': 2.0}   # De-oxo
        ]
        
    def connect(self) -> bool:
        """Connect to BGA244 gas analyzers"""
        print("⚗️  Connecting to BGA244 gas analyzers...")
        
        try:
            # Try to connect to real hardware first
            print("   → Attempting hardware connection...")
            connected_count = self._connect_hardware()
            
            if connected_count > 0:
                print(f"✅ Connected {connected_count}/{self.num_units} BGA244 devices (HARDWARE)")
                self.use_mock = False
            else:
                print("⚠️  No hardware detected - falling back to MOCK mode")
                self.use_mock = True
                # Simulate all units connected in mock mode
                for unit_id in BGA244Config.BGA_UNITS.keys():
                    self.individual_connections[unit_id] = True
                connected_count = self.num_units
            
            # Update overall connection status (true if any BGA connected)
            overall_connected = connected_count > 0
            self.connected = overall_connected
            self.state.update_connection_status('bga244', overall_connected)
            
            mode_str = "MOCK" if self.use_mock else "HARDWARE"
            print(f"✅ BGA244 service ready ({mode_str} mode)")
            return True
            
        except Exception as e:
            print(f"❌ Failed to connect to BGA244: {e}")
            self.connected = False
            self.state.update_connection_status('bga244', False)
            return False
    
    def _connect_hardware(self) -> int:
        """Connect to real BGA244 hardware"""
        if self.system not in BGA244Config.SERIAL_PORTS:
            return 0
        
        ports_to_try = BGA244Config.SERIAL_PORTS[self.system]
        connected_count = 0
        
        for unit_id, unit_config in BGA244Config.BGA_UNITS.items():
            if connected_count < len(ports_to_try):
                port = ports_to_try[connected_count]
                
                try:
                    device = BGA244Device(port, unit_config, unit_id)
                    
                    if device.connect():
                        if device.configure_gases(self.purge_mode):
                            self.devices[unit_id] = device
                            self.individual_connections[unit_id] = True
                            connected_count += 1
                            print(f"✅ {unit_config['name']} ready on {port}")
                        else:
                            device.disconnect()
                            self.individual_connections[unit_id] = False
                            print(f"❌ Gas configuration failed for {unit_config['name']}")
                    else:
                        self.individual_connections[unit_id] = False
                        print(f"❌ Connection failed for {unit_config['name']} on {port}")
                        
                except Exception as e:
                    self.individual_connections[unit_id] = False
                    print(f"❌ Device error for {unit_config['name']}: {e}")
        
        return connected_count
    
    def disconnect(self):
        """Disconnect from BGA244 analyzers"""
        print("⚗️  Disconnecting from BGA244 analyzers...")
        
        # Stop polling first
        if self.polling:
            self.stop_polling()
        
        # Disconnect hardware devices
        if not self.use_mock:
            for unit_id, device in self.devices.items():
                device.disconnect()
                self.individual_connections[unit_id] = False
            self.devices.clear()
        
        # Reset all connection states
        for unit_id in self.individual_connections:
            self.individual_connections[unit_id] = False
        
        self.connected = False
        self.state.update_connection_status('bga244', False)
        
        print("✅ BGA244 analyzers disconnected")
    
    def start_polling(self) -> bool:
        """Start polling gas analysis data"""
        # Allow polling even if not all BGAs are connected
        if not self.connected and not any(self.individual_connections.values()):
            print("❌ Cannot start polling - No BGA244 devices connected")
            return False
        
        if self.polling:
            print("⚠️  BGA244 polling already running")
            return True
        
        connected_count = sum(1 for connected in self.individual_connections.values() if connected)
        mode_str = "MOCK" if self.use_mock else "HARDWARE"
        print(f"⚗️  Starting BGA244 polling at {self.sample_rate} Hz ({connected_count} devices, {mode_str})...")
        
        # Start hardware streaming if using real hardware
        if not self.use_mock:
            for unit_id, device in self.devices.items():
                device.configure_gases(self.purge_mode)
        
        self.polling = True
        self.poll_thread = threading.Thread(target=self._poll_data, daemon=True)
        self.poll_thread.start()
        
        print("✅ BGA244 polling started")
        return True
    
    def stop_polling(self):
        """Stop polling gas analysis data"""
        if not self.polling:
            return
        
        print("⚗️  Stopping BGA244 polling...")
        self.polling = False
        
        if self.poll_thread and self.poll_thread.is_alive():
            self.poll_thread.join(timeout=3.0)
        
        print("✅ BGA244 polling stopped")
    
    def set_purge_mode(self, purge_enabled: bool):
        """Set purge mode - changes all secondary gases to N2"""
        if self.purge_mode == purge_enabled:
            return  # No change needed
        
        self.purge_mode = purge_enabled
        mode_str = "ENABLED" if purge_enabled else "DISABLED"
        print(f"🔧 Purge mode {mode_str}")
        
        # Reconfigure all connected devices
        if not self.use_mock:
            for unit_id, device in self.devices.items():
                if device.is_connected:
                    device.configure_gases(self.purge_mode)
                    print(f"   → {device.unit_config['name']} reconfigured for purge mode")
    
    def _poll_data(self):
        """Polling thread function"""
        while self.polling and (self.connected or any(self.individual_connections.values())):
            try:
                if self.use_mock:
                    # Generate mock gas concentration readings
                    gas_readings = self._generate_mock_gas_data()
                else:
                    # Read from real hardware
                    gas_readings = self._read_hardware_gas_data()
                
                # Update global state
                self.state.update_sensor_values(gas_concentrations=gas_readings)
                
                # Sleep for sample rate (gas analysis is slow)
                time.sleep(1.0 / self.sample_rate)
                
            except Exception as e:
                print(f"❌ BGA244 polling error: {e}")
                break
    
    def _read_hardware_gas_data(self) -> List[Dict[str, float]]:
        """Read gas concentrations from real BGA244 hardware"""
        gas_readings = []
        
        unit_ids = list(BGA244Config.BGA_UNITS.keys())
        
        for i, unit_id in enumerate(unit_ids):
            if unit_id in self.devices and self.individual_connections[unit_id]:
                try:
                    device = self.devices[unit_id]
                    measurements = device.read_measurements()
                    
                    if measurements:
                        # Convert to standard format
                        gas_data = {}
                        
                        # Map measurements to gas concentrations
                        if measurements.get('primary_gas_concentration') is not None:
                            primary_gas = measurements['primary_gas']
                            gas_data[primary_gas] = measurements['primary_gas_concentration']
                        
                        if measurements.get('secondary_gas_concentration') is not None:
                            secondary_gas = measurements['secondary_gas']
                            gas_data[secondary_gas] = measurements['secondary_gas_concentration']
                        
                        if measurements.get('remaining_gas_concentration') is not None:
                            remaining_gas = measurements['remaining_gas']
                            gas_data[remaining_gas] = measurements['remaining_gas_concentration']
                        
                        # Apply calibrated zero offsets if configured
                        zero_offsets = self.device_config.get_bga_zero_offsets(unit_id)
                        for gas, concentration in gas_data.items():
                            offset = zero_offsets.get(gas, 0.0)
                            gas_data[gas] = concentration + offset
                        
                        gas_readings.append(gas_data)
                    else:
                        # No data from this device
                        gas_readings.append({'H2': 0.0, 'O2': 0.0, 'N2': 0.0})
                        
                except Exception as e:
                    print(f"⚠️  Hardware reading error for {unit_id}: {e}")
                    gas_readings.append({'H2': 0.0, 'O2': 0.0, 'N2': 0.0})
            else:
                # Device not connected
                gas_readings.append({'H2': 0.0, 'O2': 0.0, 'N2': 0.0})
        
        return gas_readings
    
    def _generate_mock_gas_data(self) -> List[Dict[str, float]]:
        """Generate realistic mock gas concentration readings"""
        import random
        
        gas_readings = []
        
        for i, base_concentrations in enumerate(self.mock_concentrations):
            readings = {}
            
            for gas, base_conc in base_concentrations.items():
                # Add realistic variation
                if gas == 'H2' or gas == 'O2':
                    variation = random.uniform(-1.0, 1.0)
                else:  # N2
                    variation = random.uniform(-0.2, 0.2)
                
                concentration = base_conc + variation
                concentration = max(0.0, min(100.0, concentration))
                readings[gas] = round(concentration, 2)
            
            # Normalize to 100%
            total = sum(readings.values())
            if total > 0:
                for gas in readings:
                    readings[gas] = round((readings[gas] / total) * 100.0, 2)
            
            gas_readings.append(readings)
        
        return gas_readings
    
    def get_status(self) -> Dict[str, Any]:
        """Get current service status"""
        return {
            'connected': self.connected,
            'polling': self.polling,
            'device': self.device_name,
            'sample_rate': f"{self.sample_rate} Hz",
            'units': self.num_units,
            'mode': 'MOCK' if self.use_mock else 'HARDWARE',
            'purge_mode': self.purge_mode,
            'individual_connections': self.individual_connections.copy(),
            'calibration_date': self.device_config.get_calibration_date()
        }
    
    def get_current_readings(self) -> Dict[str, Dict[str, float]]:
        """Get current gas readings with unit names"""
        readings = {}
        concentrations = self.state.gas_concentrations
        
        unit_ids = list(BGA244Config.BGA_UNITS.keys())
        
        for i, gas_data in enumerate(concentrations):
            if i < len(unit_ids):
                unit_id = unit_ids[i]
                unit_config = BGA244Config.BGA_UNITS[unit_id]
                unit_name = unit_config['name']
                readings[unit_name] = gas_data.copy()
        
        return readings
    
    def get_individual_connection_status(self) -> Dict[str, bool]:
        """Get individual connection status for each BGA unit"""
        return self.individual_connections.copy() 
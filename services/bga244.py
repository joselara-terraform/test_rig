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
        'Windows': ['COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8'],
        'Linux': ['/dev/ttyUSB0', '/dev/ttyUSB1', '/dev/ttyUSB2', '/dev/ttyACM0'],
        'Darwin': ['/dev/tty.usbserial-A1', '/dev/tty.usbserial-A2', '/dev/tty.usbserial-A3']
    }
    
    # BGA Unit configurations for AWE test rig (as specified by user)
    BGA_UNITS = {
        'bga_1': {
            'name': 'H2 Header',
            'description': 'BGA 1 - H2 Ratio 1: measures O2 in H2, H2 in N2 during purging',
            'primary_gas': 'O2',     # O2 in H2 - Primary measurement
            'secondary_gas': 'H2',   # H2 in mixture
            'expected_gases': ['H2', 'O2', 'N2']
        },
        'bga_2': {
            'name': 'O2 Header', 
            'description': 'BGA 2 - O2 Ratio 1: measures H2 in O2, O2 in N2 during purging',
            'primary_gas': 'H2',     # H2 in O2 - Primary measurement
            'secondary_gas': 'O2',   # O2 in mixture
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
        """Connect to BGA244 device with improved robustness"""
        try:
            print(f"🔌 Connecting to {self.unit_config['name']} on {self.port}...")
            
            self.serial_conn = serial.Serial(
                port=self.port,
                baudrate=BGA244Config.BAUD_RATE,
                bytesize=BGA244Config.DATA_BITS,
                stopbits=BGA244Config.STOP_BITS,
                parity=BGA244Config.PARITY,
                timeout=BGA244Config.TIMEOUT,
                xonxoff=False,    # Disable software flow control
                rtscts=False,     # Disable hardware flow control
                dsrdtr=False      # Disable DTR/DSR flow control
            )
            
            # Clear buffers and wait for device to be ready
            self.serial_conn.reset_input_buffer()
            self.serial_conn.reset_output_buffer()
            time.sleep(1.0)  # Increased wait time for BGA244 to be ready
            
            # Test communication with multiple attempts
            max_attempts = 3
            for attempt in range(max_attempts):
                print(f"   → Testing communication (attempt {attempt + 1}/{max_attempts})...")
                
                # Clear buffers before test
                self.serial_conn.reset_input_buffer()
                self.serial_conn.reset_output_buffer()
                time.sleep(0.1)
                
                response = self._send_command("*IDN?")
                if response and len(response) > 0:
                    self.device_info['identity'] = response
                    self.is_connected = True
                    print(f"✅ Connected: {response}")
                    return True
                else:
                    print(f"   ❌ Attempt {attempt + 1} failed - no valid response")
                    time.sleep(0.5)  # Wait before retry
            
            print(f"❌ No response from device on {self.port} after {max_attempts} attempts")
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
            
            # Store purge mode state for this device
            self.purge_mode = purge_mode
            
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
                    print(f"⚠️  Invalid primary gas response from {self.unit_config['name']}: '{ratio_response}'")
            else:
                print(f"⚠️  No primary gas response from {self.unit_config['name']}")
            
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
                    print(f"⚠️  Invalid secondary gas response from {self.unit_config['name']}: '{ratio2_response}'")
            else:
                print(f"⚠️  No secondary gas response from {self.unit_config['name']}")
            
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
                
                # Debug: Log successful readings occasionally
                if hasattr(self, '_debug_counter'):
                    self._debug_counter += 1
                else:
                    self._debug_counter = 1
                    
                if self._debug_counter % 50 == 0:  # Log every 50th reading
                    print(f"📊 {self.unit_config['name']}: {measurements['primary_gas']}={primary_conc:.2f}%, {measurements['secondary_gas']}={secondary_conc:.2f}%")
            
            return measurements
            
        except Exception as e:
            print(f"❌ Measurement reading error for {self.unit_config['name']}: {e}")
            return {}
    
    def _send_command(self, command: str) -> Optional[str]:
        """Send command to BGA244 and return response with improved robustness"""
        if not self.serial_conn or not self.serial_conn.is_open:
            return None
        
        try:
            # Clear buffers thoroughly before sending command
            self.serial_conn.reset_input_buffer()
            self.serial_conn.reset_output_buffer()
            time.sleep(0.05)  # Small delay after buffer clear
            
            # Send command
            command_bytes = (command + '\r\n').encode('ascii')
            self.serial_conn.write(command_bytes)
            self.serial_conn.flush()  # Ensure command is sent
            
            # Wait longer for response (BGA244 can be slow)
            time.sleep(0.2)  # Increased from 0.1 to 0.2 seconds
            
            # Read response with timeout
            response_bytes = b''
            start_time = time.time()
            
            while (time.time() - start_time) < 1.0:  # 1 second timeout
                if self.serial_conn.in_waiting > 0:
                    chunk = self.serial_conn.read(self.serial_conn.in_waiting)
                    response_bytes += chunk
                    
                    # Check if we have a complete response (ends with \r\n)
                    if b'\r\n' in response_bytes or b'\n' in response_bytes:
                        break
                        
                time.sleep(0.02)  # Small delay between checks
            
            # Decode and clean response
            response = response_bytes.decode('ascii', errors='ignore').strip()
            
            # Remove any non-printable characters and extra whitespace
            response = ''.join(char for char in response if char.isprintable()).strip()
            
            # Validate response format for numeric commands
            if command.startswith('RATO?') or command.startswith('TCEL?') or command.startswith('PRES?') or command.startswith('NSOS?'):
                # For numeric responses, validate format
                if response and not self._is_valid_numeric_response(response):
                    print(f"⚠️  Invalid response format from {self.unit_config['name']} for '{command}': '{response}'")
                    return None
            
            return response if response else None
            
        except Exception as e:
            print(f"⚠️  Command error for {self.unit_config['name']} ({command}): {e}")
            return None
    
    def _is_valid_numeric_response(self, response: str) -> bool:
        """Check if response is a valid numeric value"""
        try:
            # Try to convert to float
            float(response)
            return True
        except ValueError:
            return False


class BGA244Service:
    """Service for BGA244 gas analyzer units with real hardware integration only"""
    
    def __init__(self):
        self.connected = False
        self.polling = False
        self.poll_thread = None
        self.state = get_global_state()
        self.device_config = get_device_config()
        
        # Hardware interfaces
        self.devices = {}
        self.purge_mode = False
        
        # Individual connection status for each BGA
        self.individual_connections = {
            'bga_1': False,
            'bga_2': False,
            'bga_3': False
        }
        
        # BGA-to-port mapping to maintain consistent assignments
        self.bga_port_mapping = {
            'bga_1': None,
            'bga_2': None,
            'bga_3': None
        }
        
        # Persistent storage for last known good gas values (prevents step functions)
        self.last_known_values = {
            'bga_1': {'H2': 0.0, 'O2': 0.0, 'N2': 0.0, 'other': 0.0},
            'bga_2': {'H2': 0.0, 'O2': 0.0, 'N2': 0.0, 'other': 0.0},
            'bga_3': {'H2': 0.0, 'O2': 0.0, 'N2': 0.0, 'other': 0.0}
        }
        
        # BGA244 configuration from device config
        self.device_name = "BGA244"
        self.sample_rate = self.device_config.get_sample_rate('bga244')
        self.num_units = len(BGA244Config.BGA_UNITS)
        
        # Platform detection for port selection
        self.system = platform.system()
        
    def connect(self) -> bool:
        """Connect to BGA244 gas analyzers"""
        print("⚗️  Connecting to BGA244 gas analyzers...")
        
        try:
            # Try to connect to real hardware
            print("   → Attempting hardware connection...")
            connected_count = self._connect_hardware()
            
            # Report connection results
            if connected_count > 0:
                print(f"✅ Connected {connected_count}/{self.num_units} BGA244 devices")
                
                # Report individual connection status
                connected_units = [unit_id for unit_id, connected in self.individual_connections.items() if connected]
                disconnected_units = [unit_id for unit_id, connected in self.individual_connections.items() if not connected]
                
                if connected_units:
                    unit_names = [BGA244Config.BGA_UNITS[uid]['name'] for uid in connected_units]
                    print(f"   → Hardware connected: {', '.join(unit_names)}")
                
                if disconnected_units:
                    unit_names = [BGA244Config.BGA_UNITS[uid]['name'] for uid in disconnected_units]
                    print(f"   → Disconnected (no data): {', '.join(unit_names)}")
                
            else:
                print("⚠️  No BGA244 hardware detected")
                print("   → All BGAs will show no data until connected")
            
            # Update overall connection status (true if any BGA connected)
            overall_connected = connected_count > 0
            self.connected = overall_connected
            self.state.update_connection_status('bga244', overall_connected)
            
            print(f"✅ BGA244 service ready ({connected_count} devices connected)")
            return True
            
        except Exception as e:
            print(f"❌ Failed to connect to BGA244: {e}")
            self.connected = False
            self.state.update_connection_status('bga244', False)
            return False
    
    def _connect_hardware(self) -> int:
        """Connect to real BGA244 hardware with persistent port mapping"""
        if self.system not in BGA244Config.SERIAL_PORTS:
            return 0
        
        ports_to_try = BGA244Config.SERIAL_PORTS[self.system]
        connected_count = 0
        
        print("   → Attempting to reconnect BGAs to their assigned ports...")
        
        # Step 1: Try to reconnect BGAs to their previously assigned ports
        for unit_id, unit_config in BGA244Config.BGA_UNITS.items():
            if self.bga_port_mapping[unit_id] is not None:
                # This BGA had a port assigned before
                assigned_port = self.bga_port_mapping[unit_id]
                print(f"   → Trying to reconnect {unit_config['name']} to {assigned_port}...")
                
                if self._try_connect_bga_to_port(unit_id, unit_config, assigned_port):
                    connected_count += 1
                    print(f"   ✅ {unit_config['name']} reconnected to {assigned_port}")
                else:
                    print(f"   ❌ {unit_config['name']} failed to reconnect to {assigned_port}")
                    # Clear the mapping since this port is no longer working
                    self.bga_port_mapping[unit_id] = None
        
        # Step 2: For BGAs without port assignments, scan available ports
        unassigned_bgas = [uid for uid in BGA244Config.BGA_UNITS.keys() 
                          if not self.individual_connections[uid]]
        used_ports = [port for port in self.bga_port_mapping.values() if port is not None]
        available_ports = [port for port in ports_to_try if port not in used_ports]
        
        if unassigned_bgas and available_ports:
            print(f"   → Scanning {len(available_ports)} available ports for {len(unassigned_bgas)} unassigned BGAs...")
            
            for port in available_ports:
                if not unassigned_bgas:
                    break  # All BGAs assigned
                
                # Try to identify which BGA is on this port
                bga_unit_id = self._identify_bga_on_port(port, unassigned_bgas)
                
                if bga_unit_id:
                    unit_config = BGA244Config.BGA_UNITS[bga_unit_id]
                    if self._try_connect_bga_to_port(bga_unit_id, unit_config, port):
                        # Assign this port to this BGA permanently
                        self.bga_port_mapping[bga_unit_id] = port
                        connected_count += 1
                        unassigned_bgas.remove(bga_unit_id)
                        print(f"   ✅ {unit_config['name']} connected and assigned to {port}")
        
        return connected_count
    
    def _try_connect_bga_to_port(self, unit_id: str, unit_config: Dict[str, Any], port: str) -> bool:
        """Try to connect a specific BGA to a specific port"""
        try:
            device = BGA244Device(port, unit_config, unit_id)
            
            if device.connect():
                if device.configure_gases(self.purge_mode):
                    self.devices[unit_id] = device
                    self.individual_connections[unit_id] = True
                    return True
                else:
                    device.disconnect()
                    self.individual_connections[unit_id] = False
                    print(f"      ❌ Gas configuration failed for {unit_config['name']}")
            else:
                self.individual_connections[unit_id] = False
                
        except Exception as e:
            self.individual_connections[unit_id] = False
            print(f"      ❌ Device error for {unit_config['name']} on {port}: {e}")
        
        return False
    
    def _identify_bga_on_port(self, port: str, candidate_bgas: List[str]) -> Optional[str]:
        """Try to identify which BGA is connected to a specific port"""
        try:
            # Create a temporary connection to identify the device
            temp_serial = serial.Serial(
                port=port,
                baudrate=BGA244Config.BAUD_RATE,
                bytesize=BGA244Config.DATA_BITS,
                stopbits=BGA244Config.STOP_BITS,
                parity=BGA244Config.PARITY,
                timeout=BGA244Config.TIMEOUT
            )
            
            # Clear buffers
            temp_serial.reset_input_buffer()
            temp_serial.reset_output_buffer()
            time.sleep(0.2)
            
            # Send identification command
            command_bytes = '*IDN?\r\n'.encode('ascii')
            temp_serial.write(command_bytes)
            time.sleep(BGA244Config.COMMAND_DELAY)
            
            # Read response
            response_bytes = temp_serial.read_all()
            response = response_bytes.decode('ascii', errors='ignore').strip()
            
            temp_serial.close()
            
            if response:
                print(f"      → Device on {port} responds: {response}")
                
                # For now, assign to the first candidate BGA
                # In a real implementation, you might use the device serial number
                # or other identifying information from the response
                if candidate_bgas:
                    return candidate_bgas[0]
            else:
                print(f"      → No response from device on {port}")
                
        except Exception as e:
            print(f"      → Error identifying device on {port}: {e}")
        
        return None
    
    def disconnect(self):
        """Disconnect from BGA244 analyzers but preserve port mappings"""
        print("⚗️  Disconnecting from BGA244 analyzers...")
        
        # Stop polling first
        if self.polling:
            self.stop_polling()
        
        # Disconnect hardware devices but preserve port mappings for reconnection
        for unit_id, device in self.devices.items():
            device.disconnect()
            self.individual_connections[unit_id] = False
            # Reset persistent values for disconnected devices
            self.last_known_values[unit_id] = {'H2': 0.0, 'O2': 0.0, 'N2': 0.0, 'other': 0.0}
            # Keep self.bga_port_mapping[unit_id] intact for reconnection
        
        self.devices.clear()
        
        # Reset overall connection status but keep individual port mappings
        self.connected = False
        self.state.update_connection_status('bga244', False)
        
        print("✅ BGA244 analyzers disconnected (port mappings preserved for reconnection)")
    
    def reset_port_mappings(self):
        """Reset BGA-to-port mappings (for troubleshooting)"""
        print("🔧 Resetting BGA port mappings...")
        self.bga_port_mapping = {
            'bga_1': None,
            'bga_2': None,
            'bga_3': None
        }
        print("✅ Port mappings reset")
    
    def start_polling(self) -> bool:
        """Start polling gas analysis data"""
        if self.polling:
            print("⚠️  BGA244 polling already running")
            return True
        
        print(f"⚗️  Starting BGA244 polling at {self.sample_rate} Hz...")
        
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
            print(f"🔧 Purge mode already {'ENABLED' if purge_enabled else 'DISABLED'}")
            return  # No change needed
        
        self.purge_mode = purge_enabled
        mode_str = "ENABLED" if purge_enabled else "DISABLED"
        print(f"🔧 Purge mode {mode_str}")
        
        # Count connected devices
        connected_devices = [unit_id for unit_id, device in self.devices.items() if device.is_connected]
        
        if not connected_devices:
            print("   ⚠️  No connected BGA devices to reconfigure")
            return
        
        print(f"   → Reconfiguring {len(connected_devices)} connected BGA devices...")
        
        # Reconfigure all connected devices
        for unit_id, device in self.devices.items():
            if device.is_connected:
                unit_name = device.unit_config['name']
                print(f"   → Reconfiguring {unit_name}...")
                
                try:
                    success = device.configure_gases(self.purge_mode)
                    if success:
                        if purge_enabled:
                            print(f"     ✅ {unit_name}: Secondary gas → N2 (Nitrogen)")
                        else:
                            normal_secondary = device.unit_config['secondary_gas']
                            print(f"     ✅ {unit_name}: Secondary gas → {normal_secondary}")
                    else:
                        print(f"     ❌ {unit_name}: Configuration failed")
                except Exception as e:
                    print(f"     ❌ {unit_name}: Error during reconfiguration: {e}")
        
        print(f"   ✅ Purge mode reconfiguration complete")
        
        # Provide guidance on expected results
        if purge_enabled:
            print("   📊 Expected: All BGAs should now show N2 as secondary gas in readings")
        else:
            print("   📊 Expected: BGAs should show normal secondary gases (H2/O2) in readings")
    
    def _poll_data(self):
        """Polling thread function"""
        while self.polling and self.connected:
            try:
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
        """Read gas concentrations from real BGA244 hardware with persistent values"""
        gas_readings = []
        
        unit_ids = list(BGA244Config.BGA_UNITS.keys())
        
        for i, unit_id in enumerate(unit_ids):
            # Start with last known good values (persistent)
            gas_data = self.last_known_values[unit_id].copy()
            
            if unit_id in self.devices and self.individual_connections[unit_id]:
                # Read from real hardware
                try:
                    device = self.devices[unit_id]
                    measurements = device.read_measurements()
                    
                    if measurements:
                        # Successfully got new measurements - update values
                        new_gas_data = {'H2': 0.0, 'O2': 0.0, 'N2': 0.0, 'other': 0.0}
                        
                        # Map measurements to gas concentrations
                        if measurements.get('primary_gas_concentration') is not None:
                            primary_gas = measurements['primary_gas']
                            new_gas_data[primary_gas] = measurements['primary_gas_concentration']
                        
                        if measurements.get('secondary_gas_concentration') is not None:
                            secondary_gas = measurements['secondary_gas']
                            new_gas_data[secondary_gas] = measurements['secondary_gas_concentration']
                        
                        if measurements.get('remaining_gas_concentration') is not None:
                            remaining_gas = measurements['remaining_gas']
                            new_gas_data[remaining_gas] = measurements['remaining_gas_concentration']
                        
                        # Apply calibrated zero offsets if configured
                        zero_offsets = self.device_config.get_bga_zero_offsets(unit_id)
                        for gas, concentration in new_gas_data.items():
                            if gas != 'other':  # Don't apply offsets to 'other' category
                                offset = zero_offsets.get(gas, 0.0)
                                new_gas_data[gas] = concentration + offset
                        
                        # Update persistent storage with new valid values
                        self.last_known_values[unit_id] = new_gas_data.copy()
                        gas_data = new_gas_data
                        
                except Exception as e:
                    print(f"⚠️  Hardware reading error for {unit_id}: {e}")
                    # Keep last known good values instead of resetting to zeros
                    # gas_data already contains last known values from the copy above
            else:
                # Device not connected - reset to zeros only when actually disconnected
                if not self.individual_connections[unit_id]:
                    zero_data = {'H2': 0.0, 'O2': 0.0, 'N2': 0.0, 'other': 0.0}
                    self.last_known_values[unit_id] = zero_data.copy()
                    gas_data = zero_data
            
            # Always append the gas data (either new, last known, or zeros for disconnected)
            gas_readings.append(gas_data)
        
        return gas_readings
    
    def get_status(self) -> Dict[str, Any]:
        """Get current service status"""
        # Determine mode based on actual connections
        connected_count = sum(1 for connected in self.individual_connections.values() if connected)
        
        if connected_count == 0:
            # No connections at all
            mode = 'DISCONNECTED'
        else:
            # All hardware connected
            mode = 'HARDWARE'
        
        return {
            'connected': self.connected,
            'polling': self.polling,
            'device': self.device_name,
            'sample_rate': f"{self.sample_rate} Hz",
            'units': self.num_units,
            'mode': mode,
            'purge_mode': self.purge_mode,
            'individual_connections': self.individual_connections.copy(),
            'bga_port_mapping': self.bga_port_mapping.copy(),
            'connected_count': connected_count,
            'calibration_date': self.device_config.get_calibration_date()
        }
    
    def get_port_assignments(self) -> Dict[str, str]:
        """Get current BGA-to-port assignments for debugging"""
        assignments = {}
        for unit_id, port in self.bga_port_mapping.items():
            unit_name = BGA244Config.BGA_UNITS[unit_id]['name']
            assignments[unit_name] = port if port else "Not assigned"
        return assignments
    
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
    
    def clear_persistent_values(self):
        """Clear persistent gas concentration values (for troubleshooting)"""
        print("🔧 Clearing persistent gas concentration values...")
        self.last_known_values = {
            'bga_1': {'H2': 0.0, 'O2': 0.0, 'N2': 0.0, 'other': 0.0},
            'bga_2': {'H2': 0.0, 'O2': 0.0, 'N2': 0.0, 'other': 0.0},
            'bga_3': {'H2': 0.0, 'O2': 0.0, 'N2': 0.0, 'other': 0.0}
        }
        print("✅ Persistent values reset to zero") 
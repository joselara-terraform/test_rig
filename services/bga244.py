"""
BGA244 gas analyzer service for AWE test rig
Real hardware integration with 3 BGA244 units for gas concentration monitoring
"""

import serial
import time
import threading

from typing import Dict, Any, List, Optional
from core.state import get_global_state
from config.device_config import get_device_config
from utils.logger import log


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
    
    # BGA Unit configurations now loaded from devices.yaml
    # Gas pairs for normal and purge modes are defined in the configuration file


class BGA244Device:
    """Individual BGA244 Gas Analyzer Interface"""
    
    def __init__(self, port: str, unit_id: str, device_config):
        self.port = port
        self.unit_id = unit_id
        self.device_config = device_config
        self.unit_config = device_config.get_bga_unit_config(unit_id)
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
            
            # Store purge mode state for this device
            self.purge_mode = purge_mode
            
            # Set binary gas mode
            self._send_command(f"MSMD {BGA244Config.GAS_MODE_BINARY}")
            
            # Get gas configuration from device config based on mode
            primary_gas = self.device_config.get_bga_primary_gas(self.unit_id, purge_mode)
            secondary_gas = self.device_config.get_bga_secondary_gas(self.unit_id, purge_mode)
            
            # Configure primary gas
            primary_cas = BGA244Config.GAS_CAS_NUMBERS[primary_gas]
            self._send_command(f"GASP {primary_cas}")
            mode_str = "PURGE MODE" if purge_mode else "NORMAL MODE"
            print(f"   {mode_str}: Primary gas: {primary_gas} ({primary_cas})")
            
            # Configure secondary gas
            secondary_cas = BGA244Config.GAS_CAS_NUMBERS[secondary_gas]
            self._send_command(f"GASS {secondary_cas}")
            print(f"   {mode_str}: Secondary gas: {secondary_gas} ({secondary_cas})")
            
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
                    temp_val = float(temp_response)
                    # Check for overflow values
                    if temp_val > 1e30:  # Handle 9.9E37 and similar overflow values
                        measurements['temperature'] = None
                    else:
                        measurements['temperature'] = temp_val
                except ValueError:
                    measurements['temperature'] = None
            
            # Read pressure  
            pres_response = self._send_command("PRES?")
            if pres_response:
                try:
                    pres_val = float(pres_response)
                    # Check for overflow values
                    if pres_val > 1e30:  # Handle 9.9E37 and similar overflow values
                        measurements['pressure'] = None
                    else:
                        measurements['pressure'] = pres_val
                except ValueError:
                    measurements['pressure'] = None
            
            # Read speed of sound
            sos_response = self._send_command("NSOS?")
            if sos_response:
                try:
                    sos_val = float(sos_response)
                    # Check for overflow values
                    if sos_val > 1e30:  # Handle 9.9E37 and similar overflow values
                        measurements['speed_of_sound'] = None
                    else:
                        measurements['speed_of_sound'] = sos_val
                except ValueError:
                    measurements['speed_of_sound'] = None
            
            # Read primary gas concentration
            ratio_response = self._send_command("RATO? 1")
            if ratio_response:
                try:
                    primary_val = float(ratio_response)
                    # Check for overflow values - treat as 0 for gas concentrations
                    if primary_val > 1e30:  # Handle 9.9E37 and similar overflow values
                        measurements['primary_gas_concentration'] = 0.0
                        print(f"   ⚠️  {self.unit_config['name']}: Primary gas reading overflow ({ratio_response}) - treated as 0")
                    else:
                        measurements['primary_gas_concentration'] = primary_val
                    
                    # Set primary gas type from device config based on mode
                    measurements['primary_gas'] = self.device_config.get_bga_primary_gas(self.unit_id, self.purge_mode)
                except ValueError:
                    measurements['primary_gas_concentration'] = None
            
            # Read secondary gas concentration (if available)
            ratio2_response = self._send_command("RATO? 2")
            if ratio2_response:
                try:
                    secondary_val = float(ratio2_response)
                    # Check for overflow values - treat as 0 for gas concentrations
                    if secondary_val > 1e30:  # Handle 9.9E37 and similar overflow values
                        measurements['secondary_gas_concentration'] = 0.0
                        print(f"   ⚠️  {self.unit_config['name']}: Secondary gas reading overflow ({ratio2_response}) - treated as 0")
                    else:
                        measurements['secondary_gas_concentration'] = secondary_val
                    
                    # Set secondary gas type from device config based on mode
                    measurements['secondary_gas'] = self.device_config.get_bga_secondary_gas(self.unit_id, self.purge_mode)
                except ValueError:
                    measurements['secondary_gas_concentration'] = None
            
            # Calculate remaining gas concentration
            if (measurements.get('primary_gas_concentration') is not None and 
                measurements.get('secondary_gas_concentration') is not None):
                primary_conc = measurements['primary_gas_concentration']
                secondary_conc = measurements['secondary_gas_concentration']
                remaining_conc = 100.0 - primary_conc - secondary_conc
                measurements['remaining_gas_concentration'] = max(0.0, remaining_conc)
                
                # Get remaining gas from device config based on mode
                measurements['remaining_gas'] = self.device_config.get_bga_remaining_gas(self.unit_id, self.purge_mode)
            
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
        
        # BGA244 configuration from device config
        self.device_name = "BGA244"
        self.sample_rate = self.device_config.get_sample_rate('bga244')
        self.num_units = len(self.device_config.get_bga244_config().get('units', {}))
        

        
    def connect(self) -> bool:
        """Connect to BGA244 gas analyzers"""
        try:
            # Try to connect to real hardware
            connected_count = self._connect_hardware()
            
            # Prepare connection status details
            connection_details = []
            
            # Report connection results
            if connected_count > 0:
                # Report individual connection status
                connected_units = [unit_id for unit_id, connected in self.individual_connections.items() if connected]
                disconnected_units = [unit_id for unit_id, connected in self.individual_connections.items() if not connected]
                
                if connected_units:
                    unit_names = [self.device_config.get_bga_unit_config(uid).get('name', uid) for uid in connected_units]
                    connection_details.append(f"→ Hardware connected: {', '.join(unit_names)}")
                
                if disconnected_units:
                    unit_names = [self.device_config.get_bga_unit_config(uid).get('name', uid) for uid in disconnected_units]
                    connection_details.append(f"→ Disconnected (no data): {', '.join(unit_names)}")
                
                log.success("BGA244", f"Connected {connected_count}/{self.num_units} BGA244 devices", connection_details)
            else:
                log.warning("BGA244", "No BGA244 hardware detected", [
                    "→ All BGAs will show no data until connected"
                ])
            
            # Update overall connection status (true if any BGA connected)
            overall_connected = connected_count > 0
            self.connected = overall_connected
            self.state.update_connection_status('bga244', overall_connected)
            
            return True
            
        except Exception as e:
            log.error("BGA244", f"Failed to connect to BGA244: {e}")
            self.connected = False
            self.state.update_connection_status('bga244', False)
            return False
    
    def _connect_hardware(self) -> int:
        """Connect to real BGA244 hardware using configured ports only"""
        connected_count = 0
        
        print("   → Connecting BGAs to configured ports...")
        
        # Connect each BGA to its configured port
        bga_units = self.device_config.get_bga244_config().get('units', {})
        for unit_id, unit_config in bga_units.items():
            # Get the configured port for this unit from device config
            configured_port = unit_config.get('port')
            
            if configured_port:
                print(f"   → Trying to connect {unit_config['name']} to {configured_port}...")
                
                if self._try_connect_bga_to_port(unit_id, configured_port):
                    # Assign this port to this BGA
                    self.bga_port_mapping[unit_id] = configured_port
                    connected_count += 1
                    print(f"   ✅ {unit_config['name']} connected to {configured_port}")
                else:
                    print(f"   ❌ {unit_config['name']} failed to connect to {configured_port}")
            else:
                print(f"   ❌ No port configured for {unit_config['name']}")
        
        return connected_count
    
    def _try_connect_bga_to_port(self, unit_id: str, port: str) -> bool:
        """Try to connect a specific BGA to a specific port"""
        try:
            device = BGA244Device(port, unit_id, self.device_config)
            
            if device.connect():
                if device.configure_gases(self.purge_mode):
                    self.devices[unit_id] = device
                    self.individual_connections[unit_id] = True
                    return True
                else:
                    device.disconnect()
                    self.individual_connections[unit_id] = False
                    print(f"      ❌ Gas configuration failed for {device.unit_config['name']}")
            else:
                self.individual_connections[unit_id] = False
                
        except Exception as e:
            self.individual_connections[unit_id] = False
            unit_name = self.device_config.get_bga_unit_config(unit_id).get('name', unit_id)
            print(f"      ❌ Device error for {unit_name} on {port}: {e}")
        
        return False
    
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
            log.warning("BGA244", "BGA244 polling already running")
            return True
        
        self.polling = True
        self.poll_thread = threading.Thread(target=self._poll_data, daemon=True)
        self.poll_thread.start()
        
        log.success("BGA244", f"BGA244 polling started at {self.sample_rate} Hz")
        return True
    
    def stop_polling(self):
        """Stop polling gas analysis data"""
        if not self.polling:
            return
        
        self.polling = False
        
        if self.poll_thread and self.poll_thread.is_alive():
            self.poll_thread.join(timeout=3.0)
        
        log.success("BGA244", "BGA244 polling stopped")
    
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
                # Read from real hardware (returns new format with primary/secondary gas info)
                gas_readings = self._read_hardware_gas_data()
                
                # Extract legacy format for existing state structure
                legacy_readings = []
                for reading in gas_readings:
                    legacy_readings.append(reading.get('legacy', {'H2': 0.0, 'O2': 0.0, 'N2': 0.0, 'other': 0.0}))
                
                # Update global state with legacy format (for backward compatibility)
                self.state.update_sensor_values(gas_concentrations=legacy_readings)
                
                # Store enhanced gas data in state for new logging format
                self.state.enhanced_gas_data = gas_readings
                
                # Sleep for sample rate (gas analysis is slow)
                time.sleep(1.0 / self.sample_rate)
                
            except Exception as e:
                print(f"❌ BGA244 polling error: {e}")
                break
    
    def _read_hardware_gas_data(self) -> List[Dict[str, Any]]:
        """Read gas concentrations from real BGA244 hardware with primary/secondary gas format"""
        gas_readings = []
        
        unit_ids = list(self.device_config.get_bga244_config().get('units', {}).keys())
        
        for i, unit_id in enumerate(unit_ids):
            if unit_id in self.devices and self.individual_connections[unit_id]:
                # Read from real hardware
                try:
                    device = self.devices[unit_id]
                    measurements = device.read_measurements()
                    
                    if measurements:
                        # Keep raw measurement format with primary/secondary gas info
                        gas_data = {
                            'primary_gas': measurements.get('primary_gas', 'H2'),
                            'secondary_gas': measurements.get('secondary_gas', 'O2'),
                            'remaining_gas': measurements.get('remaining_gas', 'N2'),
                            'primary_gas_concentration': measurements.get('primary_gas_concentration', 0.0),
                            'secondary_gas_concentration': measurements.get('secondary_gas_concentration', 0.0),
                            'remaining_gas_concentration': measurements.get('remaining_gas_concentration', 0.0)
                        }
                        
                        # Also create legacy H2/O2/N2 format for backward compatibility
                        legacy_format = {'H2': 0.0, 'O2': 0.0, 'N2': 0.0, 'other': 0.0}
                        
                        # Map concentrations to legacy format
                        primary_gas = gas_data['primary_gas']
                        secondary_gas = gas_data['secondary_gas']
                        remaining_gas = gas_data['remaining_gas']
                        
                        if primary_gas in legacy_format:
                            legacy_format[primary_gas] = gas_data['primary_gas_concentration']
                        if secondary_gas in legacy_format:
                            legacy_format[secondary_gas] = gas_data['secondary_gas_concentration']
                        if remaining_gas in legacy_format:
                            legacy_format[remaining_gas] = gas_data['remaining_gas_concentration']
                        
                        # Apply calibrated zero offsets to legacy format
                        zero_offsets = self.device_config.get_bga_zero_offsets(unit_id)
                        for gas, concentration in legacy_format.items():
                            offset = zero_offsets.get(gas, 0.0)
                            legacy_format[gas] = concentration + offset
                        
                        # Store both formats
                        gas_data['legacy'] = legacy_format
                        gas_readings.append(gas_data)
                    else:
                        # No data from this device
                        gas_readings.append({
                            'primary_gas': 'H2', 'secondary_gas': 'O2', 'remaining_gas': 'N2',
                            'primary_gas_concentration': 0.0, 'secondary_gas_concentration': 0.0, 'remaining_gas_concentration': 0.0,
                            'legacy': {'H2': 0.0, 'O2': 0.0, 'N2': 0.0, 'other': 0.0}
                        })
                        
                except Exception as e:
                    print(f"⚠️  Hardware reading error for {unit_id}: {e}")
                    gas_readings.append({
                        'primary_gas': 'H2', 'secondary_gas': 'O2', 'remaining_gas': 'N2',
                        'primary_gas_concentration': 0.0, 'secondary_gas_concentration': 0.0, 'remaining_gas_concentration': 0.0,
                        'legacy': {'H2': 0.0, 'O2': 0.0, 'N2': 0.0, 'other': 0.0}
                    })
            else:
                # Device not connected - return zero data
                gas_readings.append({
                    'primary_gas': 'H2', 'secondary_gas': 'O2', 'remaining_gas': 'N2',
                    'primary_gas_concentration': 0.0, 'secondary_gas_concentration': 0.0, 'remaining_gas_concentration': 0.0,
                    'legacy': {'H2': 0.0, 'O2': 0.0, 'N2': 0.0, 'other': 0.0}
                })
        
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
            unit_name = self.device_config.get_bga_unit_config(unit_id).get('name', unit_id)
            assignments[unit_name] = port if port else "Not assigned"
        return assignments
    
    def get_current_readings(self) -> Dict[str, Dict[str, float]]:
        """Get current gas readings with unit names"""
        readings = {}
        concentrations = self.state.gas_concentrations
        
        unit_ids = list(self.device_config.get_bga244_config().get('units', {}).keys())
        
        for i, gas_data in enumerate(concentrations):
            if i < len(unit_ids):
                unit_id = unit_ids[i]
                unit_name = self.device_config.get_bga_unit_config(unit_id).get('name', unit_id)
                readings[unit_name] = gas_data.copy()
        
        return readings
    
    def get_individual_connection_status(self) -> Dict[str, bool]:
        """Get individual connection status for each BGA unit"""
        return self.individual_connections.copy() 
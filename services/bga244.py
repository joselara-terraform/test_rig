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


class BGA244Device:
    """Individual BGA244 Gas Analyzer Interface"""
    
    def __init__(self, port: str, unit_id: str, unit_config: dict):
        self.port = port
        self.unit_id = unit_id
        self.unit_config = unit_config
        self.serial_conn = None
        self.is_connected = False
        self.purge_mode = False
        
    def connect(self) -> bool:
        """Connect to BGA244 device"""
        try:
            log.info("BGA244", f"Connecting to {self.unit_config['name']} on {self.port}")
            
            self.serial_conn = serial.Serial(
                port=self.port,
                baudrate=9600,
                bytesize=8,
                stopbits=1,
                parity='N',
                timeout=2.0
            )
            
            # Clear buffers
            self.serial_conn.reset_input_buffer()
            self.serial_conn.reset_output_buffer()
            time.sleep(0.5)
            
            # Test communication
            response = self._send_command("*IDN?")
            if response:
                self.is_connected = True
                log.success("BGA244", f"Connected: {response}")
                return True
            else:
                log.error("BGA244", f"No response from device on {self.port}")
                self.disconnect()
                return False
                
        except Exception as e:
            log.error("BGA244", f"Connection failed on {self.port}: {e}")
            self.disconnect()
            return False
    
    def disconnect(self):
        """Disconnect from BGA244 device"""
        if self.serial_conn and self.serial_conn.is_open:
            try:
                self.serial_conn.close()
                self.is_connected = False
                log.success("BGA244", f"Disconnected from {self.port}")
            except Exception as e:
                log.error("BGA244", f"Error disconnecting from {self.port}: {e}")
    
    def configure_gases(self, gas_config: dict) -> bool:
        """Configure gas analysis mode and target gases"""
        if not self.is_connected:
            return False
        
        try:
            # Set binary gas mode
            self._send_command("MSMD 1")
            
            # Configure primary gas
            primary_gas = gas_config['primary_gas']
            primary_cas = self._get_cas_number(primary_gas)
            self._send_command(f"GASP {primary_cas}")
            
            # Configure secondary gas
            secondary_gas = gas_config['secondary_gas']
            secondary_cas = self._get_cas_number(secondary_gas)
            self._send_command(f"GASS {secondary_cas}")
            
            return True
            
        except Exception as e:
            log.error("BGA244", f"Gas configuration failed: {e}")
            return False
    
    def read_measurements(self) -> Dict[str, Any]:
        """Read gas concentration measurements"""
        if not self.is_connected:
            return {}
        
        try:
            measurements = {}
            
            # Read primary gas concentration
            primary_response = self._send_command("RATO? 1")
            if primary_response:
                primary_val = float(primary_response)
                measurements['primary'] = 0.0 if primary_val > 1e30 else primary_val
            
            # Read secondary gas concentration
            secondary_response = self._send_command("RATO? 2")
            if secondary_response:
                secondary_val = float(secondary_response)
                measurements['secondary'] = 0.0 if secondary_val > 1e30 else secondary_val
            
            # Calculate remaining gas concentration
            if 'primary' in measurements and 'secondary' in measurements:
                remaining = 100.0 - measurements['primary'] - measurements['secondary']
                measurements['remaining'] = max(0.0, remaining)
            
            return measurements
            
        except Exception as e:
            log.error("BGA244", f"Measurement reading error: {e}")
            return {}
    
    def _send_command(self, command: str) -> Optional[str]:
        """Send command to BGA244 and return response"""
        if not self.serial_conn or not self.serial_conn.is_open:
            return None
        
        try:
            self.serial_conn.write((command + '\r\n').encode('ascii'))
            time.sleep(0.1)
            response_bytes = self.serial_conn.read_all()
            response = response_bytes.decode('ascii', errors='ignore').strip()
            return response if response else None
            
        except Exception as e:
            log.error("BGA244", f"Command error ({command}): {e}")
            return None
    
    def _get_cas_number(self, gas: str) -> str:
        """Get CAS number for gas"""
        cas_numbers = {
            'H2': '1333-74-0',
            'O2': '7782-44-7',
            'N2': '7727-37-9',
            'He': '7440-59-7',
            'Ar': '7440-37-1',
            'CO2': '124-38-9'
        }
        return cas_numbers.get(gas, '')


class BGA244Service:
    """Service for BGA244 gas analyzer units"""
    
    def __init__(self):
        self.connected = False
        self.polling = False
        self.poll_thread = None
        self.state = get_global_state()
        self.device_config = get_device_config()
        self.devices = {}
        self.purge_mode = False
        
        # Get configuration
        self.bga_config = self.device_config.get_bga244_config()
        self.sample_rate = self.device_config.get_sample_rate('bga244')
        
    def connect(self) -> bool:
        """Connect to BGA244 gas analyzers"""
        try:
            connected_count = 0
            
            # Connect each BGA to its configured port
            for unit_id, unit_config in self.bga_config.get('units', {}).items():
                port = unit_config.get('port')
                if not port:
                    log.error("BGA244", f"No port configured for {unit_config['name']}")
                    continue
                
                device = BGA244Device(port, unit_id, unit_config)
                if device.connect():
                    gas_config = self.device_config.get_bga_gas_config(unit_id, self.purge_mode)
                    if device.configure_gases(gas_config):
                        self.devices[unit_id] = device
                        connected_count += 1
                        log.success("BGA244", f"{unit_config['name']} connected to {port}")
                    else:
                        device.disconnect()
                        log.error("BGA244", f"Gas configuration failed for {unit_config['name']}")
                else:
                    log.error("BGA244", f"{unit_config['name']} failed to connect to {port}")
            
            # Update connection status
            if connected_count > 0:
                log.success("BGA244", f"Connected {connected_count}/{len(self.bga_config.get('units', {}))} BGA244 devices")
                self.connected = True
            else:
                log.error("BGA244", "No BGA244 hardware detected")
                self.connected = False
            
            self.state.update_connection_status('bga244', self.connected)
            return True
            
        except Exception as e:
            log.error("BGA244", f"Failed to connect to BGA244: {e}")
            self.connected = False
            self.state.update_connection_status('bga244', False)
            return False
    
    def disconnect(self):
        """Disconnect from BGA244 analyzers"""
        log.info("BGA244", "Disconnecting from BGA244 analyzers")
        
        if self.polling:
            self.stop_polling()
        
        for device in self.devices.values():
            device.disconnect()
        
        self.devices.clear()
        self.connected = False
        self.state.update_connection_status('bga244', False)
        
        log.success("BGA244", "BGA244 analyzers disconnected")
    
    def start_polling(self) -> bool:
        """Start polling gas analysis data"""
        if self.polling:
            log.warning("BGA244", "BGA244 polling already running")
            return True
        
        if not self.devices:
            return False
        
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
        """Set purge mode - changes secondary gases to N2"""
        if self.purge_mode == purge_enabled:
            return
        
        self.purge_mode = purge_enabled
        log.info("BGA244", f"Purge mode {'ENABLED' if purge_enabled else 'DISABLED'}")
        
        # Reconfigure all connected devices
        for unit_id, device in self.devices.items():
            if device.is_connected:
                gas_config = self.device_config.get_bga_gas_config(unit_id, self.purge_mode)
                if device.configure_gases(gas_config):
                    log.success("BGA244", f"{device.unit_config['name']} reconfigured")
                else:
                    log.error("BGA244", f"{device.unit_config['name']} reconfiguration failed")
    
    def _poll_data(self):
        """Polling thread function"""
        while self.polling and self.connected:
            try:
                # Initialize data structures
                legacy_readings = []
                enhanced_readings = []
                
                # Read from each BGA unit
                for unit_id in ['bga_1', 'bga_2', 'bga_3']:
                    if unit_id in self.devices:
                        device = self.devices[unit_id]
                        measurements = device.read_measurements()
                        
                        if measurements:
                            # Get gas configuration
                            gas_config = self.device_config.get_bga_gas_config(unit_id, self.purge_mode)
                            
                            # Build enhanced format
                            enhanced_data = {
                                'primary_gas': gas_config['primary_gas'],
                                'secondary_gas': gas_config['secondary_gas'],
                                'remaining_gas': gas_config['remaining_gas'],
                                'primary_gas_concentration': measurements.get('primary', 0.0),
                                'secondary_gas_concentration': measurements.get('secondary', 0.0),
                                'remaining_gas_concentration': measurements.get('remaining', 0.0)
                            }
                            
                            # Build legacy format
                            legacy_data = {'H2': 0.0, 'O2': 0.0, 'N2': 0.0, 'other': 0.0}
                            legacy_data[gas_config['primary_gas']] = measurements.get('primary', 0.0)
                            legacy_data[gas_config['secondary_gas']] = measurements.get('secondary', 0.0)
                            legacy_data[gas_config['remaining_gas']] = measurements.get('remaining', 0.0)
                            
                            enhanced_readings.append(enhanced_data)
                            legacy_readings.append(legacy_data)
                        else:
                            # No data - add zeros
                            enhanced_readings.append({
                                'primary_gas': 'H2', 'secondary_gas': 'O2', 'remaining_gas': 'N2',
                                'primary_gas_concentration': 0.0, 'secondary_gas_concentration': 0.0, 
                                'remaining_gas_concentration': 0.0
                            })
                            legacy_readings.append({'H2': 0.0, 'O2': 0.0, 'N2': 0.0, 'other': 0.0})
                    else:
                        # Device not connected - add zeros
                        enhanced_readings.append({
                            'primary_gas': 'H2', 'secondary_gas': 'O2', 'remaining_gas': 'N2',
                            'primary_gas_concentration': 0.0, 'secondary_gas_concentration': 0.0, 
                            'remaining_gas_concentration': 0.0
                        })
                        legacy_readings.append({'H2': 0.0, 'O2': 0.0, 'N2': 0.0, 'other': 0.0})
                
                # Update state with both formats
                self.state.update_sensor_values(gas_concentrations=legacy_readings)
                self.state.enhanced_gas_data = enhanced_readings
                
                # Sleep for sample rate
                time.sleep(1.0 / self.sample_rate)
                
            except Exception as e:
                log.error("BGA244", f"BGA244 polling error: {e}")
                break
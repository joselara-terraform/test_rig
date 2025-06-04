#!/usr/bin/env python3
"""
Enhanced BGA244 Gas Analyzer Test Script
Cleaned and improved version with multi-device support and robust error handling.
Based on original BGA_test.py but significantly enhanced for production use.
"""

import serial
import time
import platform
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
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
    
    # BGA Unit configurations for AWE test rig
    BGA_UNITS = {
        'bga_1': {
            'name': 'Hydrogen Side Analyzer',
            'description': 'Gas analyzer on hydrogen product stream',
            'primary_gas': 'H2',
            'secondary_gas': 'O2',
            'expected_gases': ['H2', 'O2', 'N2']
        },
        'bga_2': {
            'name': 'Oxygen Side Analyzer', 
            'description': 'Gas analyzer on oxygen product stream',
            'primary_gas': 'O2',
            'secondary_gas': 'H2',
            'expected_gases': ['O2', 'H2', 'N2']
        },
        'bga_3': {
            'name': 'Mixed Stream Analyzer',
            'description': 'Gas analyzer on mixed product stream',
            'primary_gas': 'N2',
            'secondary_gas': 'O2',
            'expected_gases': ['H2', 'O2', 'N2']
        }
    }


class BGA244Device:
    """Individual BGA244 Gas Analyzer Interface"""
    
    def __init__(self, port: str, unit_config: Dict[str, Any]):
        self.port = port
        self.unit_config = unit_config
        self.serial_conn = None
        self.is_connected = False
        self.device_info = {}
        
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
    
    def configure_gases(self) -> bool:
        """Configure gas analysis mode and target gases"""
        if not self.is_connected:
            return False
        
        try:
            print(f"⚙️  Configuring {self.unit_config['name']}...")
            
            # Set binary gas mode
            self._send_command(f"MSMD {BGA244Config.GAS_MODE_BINARY}")
            
            # Configure primary gas
            primary_gas = self.unit_config['primary_gas']
            primary_cas = BGA244Config.GAS_CAS_NUMBERS[primary_gas]
            self._send_command(f"GASP {primary_cas}")
            print(f"   Primary gas: {primary_gas} ({primary_cas})")
            
            # Configure secondary gas
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
            
            # Read secondary gas concentration (if available)
            ratio2_response = self._send_command("RATO? 2")
            if ratio2_response:
                try:
                    measurements['secondary_gas_concentration'] = float(ratio2_response)
                    measurements['secondary_gas'] = self.unit_config['secondary_gas']
                except ValueError:
                    measurements['secondary_gas_concentration'] = None
            
            # Calculate remaining gas concentration (typically N2)
            if (measurements.get('primary_gas_concentration') is not None and 
                measurements.get('secondary_gas_concentration') is not None):
                primary_conc = measurements['primary_gas_concentration']
                secondary_conc = measurements['secondary_gas_concentration']
                remaining_conc = 100.0 - primary_conc - secondary_conc
                measurements['remaining_gas_concentration'] = max(0.0, remaining_conc)
                measurements['remaining_gas'] = 'N2'  # Assume nitrogen
            
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


class BGA244System:
    """BGA244 Multi-Unit Gas Analyzer System"""
    
    def __init__(self):
        self.devices = {}
        self.system = platform.system()
        self.available_ports = []
        
    def scan_ports(self) -> List[str]:
        """Scan for available serial ports"""
        available_ports = []
        
        if self.system in BGA244Config.SERIAL_PORTS:
            ports_to_try = BGA244Config.SERIAL_PORTS[self.system]
            
            for port in ports_to_try:
                try:
                    test_serial = serial.Serial(port, timeout=0.1)
                    test_serial.close()
                    available_ports.append(port)
                    print(f"✅ Found available port: {port}")
                except Exception:
                    continue
        
        self.available_ports = available_ports
        return available_ports
    
    def connect_devices(self, target_port: str = None) -> int:
        """Connect to BGA244 devices"""
        print(f"🔍 Scanning for BGA244 devices...")
        
        if target_port:
            # Connect to specific port only
            ports_to_try = [target_port]
        else:
            # Scan all available ports
            ports_to_try = self.scan_ports()
        
        connected_count = 0
        
        for unit_id, unit_config in BGA244Config.BGA_UNITS.items():
            if connected_count < len(ports_to_try):
                port = ports_to_try[connected_count] if target_port else ports_to_try[connected_count]
                
                device = BGA244Device(port, unit_config)
                
                if device.connect():
                    if device.configure_gases():
                        self.devices[unit_id] = device
                        connected_count += 1
                        print(f"✅ {unit_config['name']} ready on {port}")
                    else:
                        device.disconnect()
                        print(f"❌ Gas configuration failed for {unit_config['name']}")
                else:
                    print(f"❌ Connection failed for {unit_config['name']} on {port}")
        
        print(f"📊 Connected {connected_count}/{len(BGA244Config.BGA_UNITS)} BGA244 devices")
        return connected_count
    
    def read_all_measurements(self) -> Dict[str, Dict[str, Any]]:
        """Read measurements from all connected devices"""
        all_measurements = {}
        
        for unit_id, device in self.devices.items():
            measurements = device.read_measurements()
            if measurements:
                all_measurements[unit_id] = {
                    'name': device.unit_config['name'],
                    'port': device.port,
                    'measurements': measurements
                }
        
        return all_measurements
    
    def disconnect_all(self):
        """Disconnect from all devices"""
        print("🔌 Disconnecting from all BGA244 devices...")
        for unit_id, device in self.devices.items():
            device.disconnect()
        self.devices.clear()


def main():
    """Test the BGA244 gas analyzer system"""
    print("=" * 70)
    print("Enhanced BGA244 Gas Analyzer Test Script")
    print("Based on original BGA_test.py - Significantly Enhanced")
    print("=" * 70)
    
    bga_system = BGA244System()
    
    try:
        # Connect to devices (use COM4 as specified)
        print("\n🔌 STEP 1: Connecting to BGA244 devices...")
        connected_count = bga_system.connect_devices(target_port="COM4")
        
        if connected_count == 0:
            print("❌ No BGA244 devices connected")
            print("\n🔧 TROUBLESHOOTING:")
            print("   • Check BGA244 serial connections")
            print("   • Verify correct COM port (currently set to COM4)")
            print("   • Ensure devices are powered on")
            print("   • Check serial cable connections")
            return False
        
        # Read measurements
        print(f"\n📊 STEP 2: Reading measurements from {connected_count} device(s)...")
        print("Press Ctrl+C to stop\n")
        
        try:
            for i in range(10):  # Read for 10 cycles
                print(f"📈 Reading Cycle {i+1}:")
                
                measurements = bga_system.read_all_measurements()
                
                for unit_id, unit_data in measurements.items():
                    print(f"   {unit_data['name']} ({unit_data['port']}):")
                    
                    meas = unit_data['measurements']
                    
                    if meas.get('temperature') is not None:
                        print(f"     Temperature: {meas['temperature']:.2f}°C")
                    
                    if meas.get('pressure') is not None:
                        print(f"     Pressure: {meas['pressure']:.2f} PSI")
                    
                    if meas.get('speed_of_sound') is not None:
                        print(f"     Speed of Sound: {meas['speed_of_sound']:.1f} m/s")
                    
                    if meas.get('primary_gas_concentration') is not None:
                        primary_gas = meas.get('primary_gas', 'Unknown')
                        print(f"     {primary_gas}: {meas['primary_gas_concentration']:.2f}%")
                    
                    if meas.get('secondary_gas_concentration') is not None:
                        secondary_gas = meas.get('secondary_gas', 'Unknown')
                        print(f"     {secondary_gas}: {meas['secondary_gas_concentration']:.2f}%")
                    
                    if meas.get('remaining_gas_concentration') is not None:
                        remaining_gas = meas.get('remaining_gas', 'N2')
                        print(f"     {remaining_gas}: {meas['remaining_gas_concentration']:.2f}%")
                
                print()
                time.sleep(2)  # Wait between readings
                
        except KeyboardInterrupt:
            print("\n🔔 Interrupted by user")
        
        return True
        
    except Exception as e:
        print(f"❌ Test error: {e}")
        return False
    
    finally:
        # Cleanup
        print("\n🧹 CLEANUP:")
        bga_system.disconnect_all()
        print("✅ BGA244 test complete")


if __name__ == "__main__":
    success = main()
    
    print("\n" + "=" * 70)
    if success:
        print("✅ ENHANCED BGA244 TEST SCRIPT COMPLETE")
        print("\n📋 ENHANCEMENTS:")
        print("   ✅ Multi-device support (3 gas analyzers)")
        print("   ✅ Cross-platform serial port handling")
        print("   ✅ Robust error handling and cleanup")
        print("   ✅ Comprehensive gas analysis commands")
        print("   ✅ Individual device management")
        print("   ✅ Ready for service integration")
    else:
        print("ℹ️  Script test completed (hardware not available)")
        print("   Ready for use with real BGA244 devices on COM4")
    
    print("=" * 70) 
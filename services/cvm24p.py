"""
CVM-24P cell voltage monitor service
Interfaces with 5 CVM24P modules (120 channels total) via XC2 protocol
"""

import asyncio
import time
import threading
from typing import List, Optional
from core.state import get_global_state
from config.device_config import get_device_config
from utils.logger import log

# XC2 protocol imports
try:
    from xc2.bus import SerialBus
    from xc2.consts import ProtocolEnum
    from xc2.utils import discover_serial_ports, get_serial_from_port
    from xc2.xc2_dev_cvm24p import XC2Cvm24p
    XC2_AVAILABLE = True
except ImportError:
    XC2_AVAILABLE = False
    log.error("Libraries", "XC2 libraries not available - CVM24P hardware connection will fail")


class CVM24PService:
    """Service for CVM-24P cell voltage monitor"""
    
    CHANNELS_PER_MODULE = 24
    BAUD_RATE = 1000000
    
    def __init__(self):
        self.connected = False
        self.polling = False
        self.state = get_global_state()
        self.device_config = get_device_config()
        
        # Configuration
        self.sample_rate = self.device_config.get_sample_rate('cvm24p')
        self.module_mapping = self.device_config.get_cvm24p_module_mapping()
        self.expected_modules = self.device_config.get_cvm24p_expected_modules()
        self.total_channels = self.expected_modules * self.CHANNELS_PER_MODULE
        
        # Hardware
        self.bus = None
        self.devices = {}  # serial -> XC2Cvm24p device
        self.voltage_data = [0.0] * self.total_channels
        self.polling_thread = None
        
    def connect(self) -> bool:
        """Connect to CVM24P modules"""
        if not XC2_AVAILABLE:
            log.error("CVM24P", "XC2 libraries not available")
            return False
            
        if not self.module_mapping:
            log.error("CVM24P", "No module mapping found in configuration")
            return False
        
        try:
            # Find serial port
            ports = discover_serial_ports()
            if not ports:
                log.error("CVM24P", "No serial ports found")
                return False
            
            # Try each port
            for port in ports:
                if self._connect_to_port(port):
                    self.connected = True
                    self.state.update_connection_status('cvm24p', True)
                    log.success("CVM24P", f"Connected to {self.expected_modules} modules")
                    return True
                    
            log.error("CVM24P", "Failed to connect on any port")
            return False
            
        except Exception as e:
            log.error("CVM24P", f"Connection failed: {e}")
            return False
    
    def _connect_to_port(self, port: str) -> bool:
        """Connect to modules on specified port"""
        try:
            # Create and connect bus
            bus_sn = get_serial_from_port(port)
            self.bus = SerialBus(
                bus_sn, 
                port=port, 
                baud_rate=self.BAUD_RATE,
                protocol_type=ProtocolEnum.XC2
            )
            
            # Run async connection in sync context
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                loop.run_until_complete(self.bus.connect())
                
                # Initialize each module using cached addresses
                for serial, address in self.module_mapping.items():
                    device = XC2Cvm24p(self.bus, address)
                    loop.run_until_complete(device.initial_structure_reading())
                    self.devices[serial] = device
                
                # Verify we got all expected modules
                if len(self.devices) != self.expected_modules:
                    raise Exception(f"Expected {self.expected_modules} modules, got {len(self.devices)}")
                    
                return True
                
            finally:
                loop.close()
                
        except Exception as e:
            self.bus = None
            self.devices.clear()
            return False
    
    def disconnect(self):
        """Disconnect from CVM24P"""
        if self.polling:
            self.stop_polling()
            
        self.bus = None
        self.devices.clear()
        self.voltage_data = [0.0] * self.total_channels
        
        self.connected = False
        self.state.update_connection_status('cvm24p', False)
        log.success("CVM24P", "Disconnected")
    
    def start_polling(self) -> bool:
        """Start polling cell voltage data"""
        if not self.connected:
            log.error("CVM24P", "Cannot start polling - not connected")
            return False
            
        if self.polling:
            return True
            
        self.polling = True
        self.polling_thread = threading.Thread(target=self._poll_data, daemon=True)
        self.polling_thread.start()
        
        log.success("CVM24P", f"Polling started at {self.sample_rate} Hz")
        return True
    
    def stop_polling(self):
        """Stop polling cell voltage data"""
        if not self.polling:
            return
            
        self.polling = False
        if self.polling_thread:
            self.polling_thread.join(timeout=2.0)
        
        log.info("CVM24P", "Polling stopped")
    
    def _poll_data(self):
        """Polling thread - reads voltage data"""
        # Create event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            while self.polling and self.connected:
                try:
                    # Read all voltages
                    voltages = loop.run_until_complete(self._read_all_voltages())
                    
                    # Update state
                    self.voltage_data = voltages
                    self.state.update_sensor_values(cell_voltages=voltages)
                    
                    # Sleep for sample rate
                    time.sleep(1.0 / self.sample_rate)
                    
                except Exception as e:
                    log.error("CVM24P", f"Polling error: {e}")
                    break
        finally:
            loop.close()
    
    async def _read_all_voltages(self) -> List[float]:
        """Read voltages from all modules in physical order"""
        all_voltages = []
        
        # Read in physical connection order from config
        for serial in self.module_mapping.keys():
            if serial in self.devices:
                try:
                    device = self.devices[serial]
                    cell_voltages = await device.read_and_get_reg_by_name("ch_V")
                    
                    # Take first 24 channels
                    module_voltages = cell_voltages[:self.CHANNELS_PER_MODULE]
                    
                    # Pad if needed
                    while len(module_voltages) < self.CHANNELS_PER_MODULE:
                        module_voltages.append(0.0)
                        
                    all_voltages.extend(module_voltages)
                    
                except Exception as e:
                    # Return zeros for failed module
                    all_voltages.extend([0.0] * self.CHANNELS_PER_MODULE)
            else:
                # Module not found
                all_voltages.extend([0.0] * self.CHANNELS_PER_MODULE)
        
        return all_voltages
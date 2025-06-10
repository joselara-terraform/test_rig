"""
CVM-24P cell voltage monitor service for AWE test rig
Real hardware integration using XC2 protocol for electrolyzer cell voltage monitoring
"""

import asyncio
import time
import threading
import queue
from typing import Dict, Any, List, Optional
from core.state import get_global_state
from config.device_config import get_device_config

# XC2 protocol imports for CVM24P communication
try:
    from xc2.bus import SerialBus
    from xc2.bus_utils import get_broadcast_echo, get_serial_broadcast
    from xc2.consts import ProtocolEnum
    from xc2.utils import discover_serial_ports, get_serial_from_port
    from xc2.xc2_dev_cvm24p import XC2Cvm24p
    XC2_AVAILABLE = True
except ImportError:
    XC2_AVAILABLE = False
    print("⚠️  XC2 libraries not available - CVM24P will use mock mode")


class CVM24PConfig:
    """Configuration constants for CVM24P Cell Voltage Monitor"""
    
    # Serial communication settings
    BAUD_RATE = 1000000  # 1MHz - found to work best in CVM_test.py
    DISCOVERY_ATTEMPTS = 5
    DISCOVERY_DELAY = 1.0  # seconds between discovery attempts
    
    # Device specifications
    CHANNELS_PER_MODULE = 24  # 24 channels per CVM24P module
    VOLTAGE_RESOLUTION = 0.001  # 1mV resolution
    MIN_CELL_VOLTAGE = 2.0  # Minimum safe cell voltage
    MAX_CELL_VOLTAGE = 3.5  # Maximum cell voltage under load
    NOMINAL_CELL_VOLTAGE = 2.75  # Nominal cell voltage
    
    # Health monitoring thresholds
    VOLTAGE_DEVIATION_WARNING = 0.1  # 100mV deviation warning
    VOLTAGE_IMBALANCE_THRESHOLD = 0.05  # 50mV imbalance threshold


class AsyncCVMManager:
    """Async manager for CVM hardware operations - runs in dedicated thread"""
    
    def __init__(self, command_queue: queue.Queue, result_queue: queue.Queue):
        self.command_queue = command_queue
        self.result_queue = result_queue
        self.bus = None
        self.modules = {}  # Dict of serial -> device info
        self.initialized_devices = {}  # Dict of serial -> XC2Cvm24p device
        self.running = False
        
    async def run(self):
        """Main async loop - handles commands and polling"""
        self.running = True
        
        while self.running:
            try:
                # Check for commands (non-blocking)
                try:
                    command = self.command_queue.get_nowait()
                    await self._handle_command(command)
                except queue.Empty:
                    pass
                
                # If connected, read voltages and update result queue
                if self.bus and self.initialized_devices:
                    try:
                        voltages = await self._read_all_voltages()
                        self.result_queue.put(('voltages', voltages))
                    except Exception as e:
                        self.result_queue.put(('error', f"Read error: {e}"))
                
                # Sleep to control polling rate
                await asyncio.sleep(0.1)  # 10Hz check rate
                
            except Exception as e:
                print(f"❌ AsyncCVMManager error: {e}")
                self.result_queue.put(('error', str(e)))
                await asyncio.sleep(1.0)
    
    async def _handle_command(self, command):
        """Handle commands from main thread"""
        cmd_type, cmd_data = command
        
        if cmd_type == 'connect':
            port = cmd_data
            success = await self._connect_to_port(port)
            self.result_queue.put(('connect_result', success))
            
        elif cmd_type == 'disconnect':
            await self._disconnect()
            self.result_queue.put(('disconnect_result', True))
            
        elif cmd_type == 'stop':
            self.running = False
            await self._disconnect()
            self.result_queue.put(('stopped', True))
    
    async def _connect_to_port(self, port: str) -> bool:
        """Connect to CVM hardware on specified port (similar to CVM_test.py)"""
        try:
            bus_sn = get_serial_from_port(port)
            
            print(f"   → Connecting to {port} at {CVM24PConfig.BAUD_RATE} baud...")
            
            # Create bus connection (like CVM_test.py)
            self.bus = SerialBus(
                bus_sn, 
                port=port, 
                baud_rate=CVM24PConfig.BAUD_RATE,
                protocol_type=ProtocolEnum.XC2
            )
            
            # Connect to bus
            await self.bus.connect()
            print(f"      → Bus connected, discovering modules...")
            
            # Add stability pause (like CVM_test.py)
            await asyncio.sleep(3)
            
            # Discover modules
            discovered_modules = await self._discover_modules()
            
            if not discovered_modules:
                print(f"      → No CVM24P modules found")
                await self.bus.disconnect()
                self.bus = None
                return False
            
            # Initialize modules
            initialized_count = await self._initialize_modules(discovered_modules)
            
            if initialized_count == 0:
                print(f"      → No modules successfully initialized")
                await self.bus.disconnect()
                self.bus = None
                return False
            
            print(f"   → Success! {initialized_count}/{len(discovered_modules)} modules initialized")
            return True
            
        except Exception as e:
            print(f"      → Connection error: {e}")
            if self.bus:
                try:
                    await self.bus.disconnect()
                except:
                    pass
                self.bus = None
            return False
    
    async def _discover_modules(self) -> Dict[str, Dict]:
        """Discover CVM24P modules (similar to CVM_test.py pattern)"""
        found_modules = {}
        
        for attempt in range(CVM24PConfig.DISCOVERY_ATTEMPTS):
            await asyncio.sleep(CVM24PConfig.DISCOVERY_DELAY)
            
            try:
                # Get devices via broadcast echo
                devices = await get_broadcast_echo(bus=self.bus)
                print(f"      → Discovery attempt {attempt+1}: Found {len(devices)} devices")
                
                # Try to get device info
                try:
                    device_info = await get_serial_broadcast(bus=self.bus)
                    
                    # Add modules by serial number
                    for addr, info in device_info.items():
                        serial = info['dev_serial']
                        device_type = info['dev_type']
                        
                        # Check if it's a CVM24P
                        if 'CVM' in device_type or 'cvm' in device_type.lower():
                            if serial not in found_modules:
                                found_modules[serial] = {
                                    'address': addr,
                                    'type': device_type,
                                    'serial': serial
                                }
                except Exception:
                    pass
                
                # Try direct identification for devices that responded to echo
                for addr in devices:
                    found = any(module['address'] == addr for module in found_modules.values())
                    
                    if not found:
                        try:
                            device = XC2Cvm24p(self.bus, addr)
                            device_type, device_serial = await device.read_serial_number()
                            
                            if device_serial not in found_modules:
                                found_modules[device_serial] = {
                                    'address': addr,
                                    'type': device_type,
                                    'serial': device_serial
                                }
                        except Exception:
                            pass
                            
            except Exception as e:
                print(f"      → Discovery attempt {attempt+1} failed: {e}")
        
        self.modules = found_modules
        return found_modules
    
    async def _initialize_modules(self, discovered_modules: Dict) -> int:
        """Initialize discovered modules (like CVM_test.py)"""
        initialized_count = 0
        
        print(f"   → Initializing {len(discovered_modules)} modules...")
        
        for serial, info in discovered_modules.items():
            try:
                device = XC2Cvm24p(self.bus, info['address'])
                await device.initial_structure_reading()
                
                self.initialized_devices[serial] = device
                initialized_count += 1
                print(f"   ✅ Module {serial} (0x{info['address']:X}) initialized")
                
            except Exception as e:
                print(f"   ❌ Failed to initialize module {serial}: {e}")
        
        return initialized_count
    
    async def _read_all_voltages(self) -> List[float]:
        """Read voltages from all modules (like CVM_test.py pattern)"""
        all_voltages = []
        
        # Sort by address for consistent ordering  
        sorted_modules = sorted(self.modules.items(), key=lambda x: x[1]['address'])
        
        for serial, module_info in sorted_modules:
            try:
                if serial in self.initialized_devices:
                    device = self.initialized_devices[serial]
                    # Use same method as CVM_test.py
                    cell_voltages = await device.read_and_get_reg_by_name("ch_V")
                    
                    # Take expected number of channels
                    module_voltages = cell_voltages[:CVM24PConfig.CHANNELS_PER_MODULE]
                    
                    # Pad with zeros if needed
                    while len(module_voltages) < CVM24PConfig.CHANNELS_PER_MODULE:
                        module_voltages.append(0.0)
                    
                    all_voltages.extend(module_voltages)
                else:
                    # Add zeros for uninitialized module
                    all_voltages.extend([0.0] * CVM24PConfig.CHANNELS_PER_MODULE)
                    
            except Exception as e:
                print(f"⚠️  Error reading module {serial}: {e}")
                # Add zeros for failed module
                all_voltages.extend([0.0] * CVM24PConfig.CHANNELS_PER_MODULE)
        
        return all_voltages
    
    async def _disconnect(self):
        """Disconnect from hardware"""
        if self.bus:
            try:
                await self.bus.disconnect()
            except Exception as e:
                print(f"⚠️  Bus disconnect error: {e}")
            
        self.bus = None
        self.modules.clear()
        self.initialized_devices.clear()


class CVM24PService:
    """Service for CVM-24P cell voltage monitor with simplified async pattern"""
    
    def __init__(self):
        self.connected = False
        self.polling = False
        self.state = get_global_state()
        self.device_config = get_device_config()
        
        # Hardware communication - simplified
        self.use_mock = not XC2_AVAILABLE
        
        # CVM24P configuration from device config
        self.device_name = "CVM-24P"
        self.sample_rate = self.device_config.get_sample_rate('cvm24p')
        self.expected_modules = 5  # Expect 5 modules for 120 channels (5 * 24 = 120)
        self.total_channels = self.expected_modules * CVM24PConfig.CHANNELS_PER_MODULE
        
        # Mock data for when hardware unavailable
        self.mock_voltages = [CVM24PConfig.NOMINAL_CELL_VOLTAGE] * self.total_channels
        
        # Async communication - simplified pattern
        self.command_queue = queue.Queue()
        self.result_queue = queue.Queue()
        self.async_thread = None
        self.async_manager = None
        
        # Latest voltage readings
        self.latest_voltages = [0.0] * self.total_channels
        self.modules_info = {}
        
    def connect(self) -> bool:
        """Connect to CVM24P modules"""
        print("🔋 Connecting to CVM-24P cell voltage monitor...")
        
        if not XC2_AVAILABLE:
            return self._connect_mock()
        
        try:
            # Try to connect to real hardware
            print("   → Attempting hardware connection...")
            
            if self._connect_hardware():
                self.connected = True
                self.state.update_connection_status('cvm24p', True)
                print(f"✅ CVM-24P connected - Hardware mode with {len(self.modules_info)} modules")
                return True
            else:
                print("   → Hardware connection failed, falling back to mock mode")
                return self._connect_mock()
                
        except Exception as e:
            print(f"❌ Failed to connect to CVM-24P: {e}")
            print("   → Falling back to mock mode")
            return self._connect_mock()
    
    def _connect_hardware(self) -> bool:
        """Connect to real CVM24P hardware using simplified async pattern"""
        try:
            # Discover serial ports
            available_ports = discover_serial_ports()
            if not available_ports:
                print("   → No serial ports found")
                return False
            
            print(f"   → Found {len(available_ports)} available ports: {available_ports}")
            
            # Start async manager thread
            self.async_manager = AsyncCVMManager(self.command_queue, self.result_queue)
            self.async_thread = threading.Thread(
                target=lambda: asyncio.run(self.async_manager.run()), 
                daemon=True
            )
            self.async_thread.start()
            
            # Try each port until one works
            for port_index, selected_port in enumerate(available_ports):
                try:
                    print(f"   → Trying port {selected_port} ({port_index+1}/{len(available_ports)})...")
                    
                    # Send connect command to async manager
                    self.command_queue.put(('connect', selected_port))
                    
                    # Wait for result with timeout
                    try:
                        result_type, result_data = self.result_queue.get(timeout=15.0)
                        
                        if result_type == 'connect_result' and result_data:
                            print(f"   → Success on {selected_port}!")
                            self.use_mock = False
                            
                            # Get module info from async manager
                            self.modules_info = self.async_manager.modules.copy()
                            
                            return True
                        else:
                            print(f"      → Failed on {selected_port}")
                            continue
                            
                    except queue.Empty:
                        print(f"      → Timeout on {selected_port}")
                        continue
                        
                except Exception as e:
                    print(f"      → Error with port {selected_port}: {e}")
                    continue
            
            print("   → All ports failed")
            self._stop_async_manager()
            return False
            
        except Exception as e:
            print(f"   → Hardware connection error: {e}")
            self._stop_async_manager()
            return False
    
    def _stop_async_manager(self):
        """Stop the async manager thread"""
        if self.async_manager:
            try:
                self.command_queue.put(('stop', None))
                if self.async_thread and self.async_thread.is_alive():
                    self.async_thread.join(timeout=3.0)
            except Exception as e:
                print(f"⚠️  Error stopping async manager: {e}")
            
            self.async_manager = None
            self.async_thread = None
    
    def _connect_mock(self) -> bool:
        """Connect in mock mode"""
        print("   → Using mock mode (no hardware)")
        print(f"   → Mock device: {self.device_name}")
        print(f"   → Mock configuration:")
        print(f"     • {self.expected_modules} modules x {CVM24PConfig.CHANNELS_PER_MODULE} channels = {self.total_channels} total")
        print(f"     • Voltage range: {CVM24PConfig.MIN_CELL_VOLTAGE}V - {CVM24PConfig.MAX_CELL_VOLTAGE}V")
        print(f"     • Resolution: {CVM24PConfig.VOLTAGE_RESOLUTION*1000}mV")
        
        self.use_mock = True
        self.connected = True
        self.state.update_connection_status('cvm24p', True)
        
        print("✅ CVM-24P connected successfully (MOCK MODE)")
        return True
    
    def disconnect(self):
        """Disconnect from CVM24P"""
        print("🔋 Disconnecting from CVM-24P...")
        
        # Stop polling first
        if self.polling:
            self.stop_polling()
        
        # Stop async manager
        if not self.use_mock:
            self._stop_async_manager()
        
        # Clear state
        self.modules_info.clear()
        self.latest_voltages = [0.0] * self.total_channels
        
        self.connected = False
        self.state.update_connection_status('cvm24p', False)
        
        print("✅ CVM-24P disconnected")
    
    def start_polling(self) -> bool:
        """Start polling cell voltage data"""
        if not self.connected:
            print("❌ Cannot start polling - CVM-24P not connected")
            return False
        
        if self.polling:
            print("⚠️  CVM-24P polling already running")
            return True
        
        mode_str = "MOCK" if self.use_mock else "HARDWARE"
        print(f"🔋 Starting CVM-24P polling at {self.sample_rate} Hz ({mode_str})...")
        
        self.polling = True
        
        # Start polling thread
        polling_thread = threading.Thread(target=self._poll_data, daemon=True)
        polling_thread.start()
        
        print("✅ CVM-24P polling started")
        return True
    
    def stop_polling(self):
        """Stop polling cell voltage data"""
        if not self.polling:
            return
        
        print("🔋 Stopping CVM-24P polling...")
        self.polling = False
        
        print("✅ CVM-24P polling stopped")
    
    def _poll_data(self):
        """Simplified polling thread function"""
        while self.polling and self.connected:
            try:
                if self.use_mock:
                    voltage_readings = self._generate_mock_data()
                else:
                    voltage_readings = self._read_hardware_data()
                
                # Update global state
                self.state.update_sensor_values(cell_voltages=voltage_readings)
                self.latest_voltages = voltage_readings
                
                # Sleep for sample rate
                time.sleep(1.0 / self.sample_rate)
                
            except Exception as e:
                print(f"❌ CVM-24P polling error: {e}")
                break
    
    def _read_hardware_data(self) -> List[float]:
        """Read voltage data from hardware - simplified"""
        try:
            # Check for new voltage data from async manager
            while True:
                try:
                    result_type, result_data = self.result_queue.get_nowait()
                    
                    if result_type == 'voltages':
                        return result_data
                    elif result_type == 'error':
                        print(f"⚠️  Hardware reading error: {result_data}")
                        return self.latest_voltages
                        
                except queue.Empty:
                    break
            
            # No new data, return latest readings
            return self.latest_voltages
            
        except Exception as e:
            print(f"⚠️  Hardware reading error: {e}")
            return self.latest_voltages
    
    def _generate_mock_data(self) -> List[float]:
        """Generate realistic mock voltage data"""
        import random
        
        # Get current from state to simulate load effects
        current = self.state.current_value
        current_factor = min(current / 5.0, 1.0)  # Normalize to 5A max
        voltage_drop = current_factor * 0.2  # Up to 200mV drop under load
        
        voltages = []
        for i in range(self.total_channels):
            # Base voltage with slight cell variation
            base_voltage = CVM24PConfig.NOMINAL_CELL_VOLTAGE + random.uniform(-0.05, 0.05)
            
            # Apply load effects
            operating_voltage = base_voltage - voltage_drop
            
            # Add noise
            noise = random.uniform(-0.015, 0.015)  # ±15mV noise
            
            voltage = operating_voltage + noise
            
            # Clamp to realistic range
            voltage = max(CVM24PConfig.MIN_CELL_VOLTAGE, 
                         min(CVM24PConfig.MAX_CELL_VOLTAGE, voltage))
            
            # Round to resolution
            voltages.append(round(voltage, 3))
        
        return voltages
    
    def get_status(self) -> Dict[str, Any]:
        """Get current service status"""
        mode = 'MOCK' if self.use_mock else 'HARDWARE'
        
        return {
            'connected': self.connected,
            'polling': self.polling,
            'device': self.device_name,
            'sample_rate': f"{self.sample_rate} Hz",
            'mode': mode,
            'modules': len(self.modules_info),
            'channels': self.total_channels,
            'resolution': f"{CVM24PConfig.VOLTAGE_RESOLUTION*1000}mV",
            'voltage_range': f"{CVM24PConfig.MIN_CELL_VOLTAGE}V - {CVM24PConfig.MAX_CELL_VOLTAGE}V"
        }
    
    def get_module_info(self) -> Dict[str, Dict]:
        """Get information about connected modules"""
        module_info = {}
        
        for serial, module_data in self.modules_info.items():
            module_info[serial] = {
                'address': f"0x{module_data['address']:X}",
                'type': module_data.get('type', 'CVM24P'),
                'channels': CVM24PConfig.CHANNELS_PER_MODULE,
                'initialized': True  # If it's in modules_info, it was initialized
            }
        
        return module_info
    
    def get_voltage_statistics(self) -> Dict[str, float]:
        """Get voltage statistics for the cell stack"""
        voltages = self.latest_voltages
        
        if not voltages or all(v == 0.0 for v in voltages):
            return {'min': 0.0, 'max': 0.0, 'avg': 0.0, 'total': 0.0, 'std_dev': 0.0}
        
        min_v = min(voltages)
        max_v = max(voltages)
        avg_v = sum(voltages) / len(voltages)
        total_v = sum(voltages)
        
        # Calculate standard deviation
        variance = sum((v - avg_v) ** 2 for v in voltages) / len(voltages)
        std_dev = variance ** 0.5
        
        return {
            'min': round(min_v, 3),
            'max': round(max_v, 3),
            'avg': round(avg_v, 3),
            'total': round(total_v, 3),
            'std_dev': round(std_dev, 3)
        }
    
    def get_unbalanced_cells(self, threshold: float = CVM24PConfig.VOLTAGE_IMBALANCE_THRESHOLD) -> List[int]:
        """Get list of cell indices with voltage significantly different from average"""
        stats = self.get_voltage_statistics()
        avg_voltage = stats['avg']
        voltages = self.latest_voltages
        
        unbalanced = []
        
        for i, voltage in enumerate(voltages):
            if abs(voltage - avg_voltage) > threshold:
                unbalanced.append(i + 1)  # 1-indexed cell numbers
        
        return unbalanced 
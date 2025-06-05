"""
CVM-24P cell voltage monitor service for AWE test rig
Real hardware integration using XC2 protocol for electrolyzer cell voltage monitoring
"""

import asyncio
import time
import threading
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


class CVM24PModule:
    """Individual CVM24P module interface"""
    
    def __init__(self, bus, address: int, serial: str, module_id: int):
        self.bus = bus
        self.address = address
        self.serial = serial
        self.module_id = module_id
        self.device = XC2Cvm24p(bus, address) if XC2_AVAILABLE else None
        self.is_initialized = False
        self.channel_voltages = [0.0] * CVM24PConfig.CHANNELS_PER_MODULE
        
    async def initialize(self) -> bool:
        """Initialize the CVM24P module"""
        if not self.device:
            return False
        
        try:
            await self.device.initial_structure_reading()
            self.is_initialized = True
            print(f"   ✅ Module {self.serial} (0x{self.address:X}) initialized")
            return True
        except Exception as e:
            print(f"   ❌ Failed to initialize module {self.serial}: {e}")
            return False
    
    async def read_voltages(self) -> List[float]:
        """Read all channel voltages from this module"""
        if not self.device or not self.is_initialized:
            return self.channel_voltages
        
        try:
            # Read all channel voltages using the method from CVM_test.py
            cell_voltages = await self.device.read_and_get_reg_by_name("ch_V")
            self.channel_voltages = cell_voltages[:CVM24PConfig.CHANNELS_PER_MODULE]
            return self.channel_voltages
        except Exception as e:
            print(f"⚠️  Error reading voltages from module {self.serial}: {e}")
            return self.channel_voltages


class CVM24PService:
    """Service for CVM-24P cell voltage monitor with real hardware integration"""
    
    def __init__(self):
        self.connected = False
        self.polling = False
        self.poll_thread = None
        self.state = get_global_state()
        self.device_config = get_device_config()
        
        # Hardware communication
        self.bus = None
        self.modules = {}  # Dict of serial -> CVM24PModule
        self.use_mock = not XC2_AVAILABLE
        
        # CVM24P configuration from device config
        self.device_name = "CVM-24P"
        self.sample_rate = self.device_config.get_sample_rate('cvm24p')
        self.expected_modules = 5  # Expect 5 modules for 120 channels (5 * 24 = 120)
        self.total_channels = self.expected_modules * CVM24PConfig.CHANNELS_PER_MODULE
        
        # Mock data for when hardware unavailable
        self.mock_voltages = [CVM24PConfig.NOMINAL_CELL_VOLTAGE] * self.total_channels
        
        # Event loop management for asyncio integration
        self.loop = None
        self.async_task = None
        
    def connect(self) -> bool:
        """Connect to CVM24P modules"""
        print("🔋 Connecting to CVM-24P cell voltage monitor...")
        
        if not XC2_AVAILABLE:
            return self._connect_mock()
        
        try:
            # Try to connect to real hardware
            print("   → Attempting hardware connection...")
            
            # Run async connection in thread-safe way
            if self._connect_hardware():
                self.connected = True
                self.state.update_connection_status('cvm24p', True)
                print(f"✅ CVM-24P connected - {len(self.modules)} modules with {self.total_channels} channels")
                return True
            else:
                print("   → Hardware connection failed, falling back to mock mode")
                return self._connect_mock()
                
        except Exception as e:
            print(f"❌ Failed to connect to CVM-24P: {e}")
            print("   → Falling back to mock mode")
            return self._connect_mock()
    
    def _connect_hardware(self) -> bool:
        """Connect to real CVM24P hardware"""
        try:
            # Discover serial ports
            available_ports = discover_serial_ports()
            if not available_ports:
                print("   → No serial ports found")
                return False
            
            print(f"   → Found {len(available_ports)} available ports: {available_ports}")
            
            # Try each port until one works
            for port_index, selected_port in enumerate(available_ports):
                try:
                    bus_sn = get_serial_from_port(selected_port)
                    
                    print(f"   → Trying port {selected_port} ({port_index+1}/{len(available_ports)}) at {CVM24PConfig.BAUD_RATE} baud...")
                    
                    # Create bus connection
                    self.bus = SerialBus(
                        bus_sn, 
                        port=selected_port, 
                        baud_rate=CVM24PConfig.BAUD_RATE,
                        protocol_type=ProtocolEnum.XC2
                    )
                    
                    # Connect to bus (run in event loop) - match CVM_test.py pattern exactly
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    
                    # Just connect - don't check return value like CVM_test.py
                    loop.run_until_complete(self.bus.connect())
                    print(f"      → Bus connected on {selected_port}, discovering modules...")
                    
                    # Add bus stability pause like CVM_test.py
                    loop.run_until_complete(asyncio.sleep(3))
                    
                    # Discover modules
                    discovered_modules = loop.run_until_complete(self._discover_modules())
                    
                    if not discovered_modules:
                        print(f"      → No CVM24P modules found on {selected_port}")
                        try:
                            loop.run_until_complete(self.bus.disconnect())
                        except:
                            pass
                        continue
                    
                    # Initialize modules
                    initialized_count = loop.run_until_complete(self._initialize_modules(discovered_modules))
                    
                    if initialized_count == 0:
                        print(f"      → No modules successfully initialized on {selected_port}")
                        try:
                            loop.run_until_complete(self.bus.disconnect())
                        except:
                            pass
                        continue
                    
                    print(f"   → Success! {initialized_count}/{len(discovered_modules)} modules initialized on {selected_port}")
                    
                    # Store event loop for polling
                    self.loop = loop
                    self.use_mock = False
                    
                    return True
                    
                except PermissionError as e:
                    print(f"      → Port {selected_port} is already in use (Permission denied)")
                    continue
                except Exception as e:
                    print(f"      → Error with port {selected_port}: {e}")
                    continue
            
            print("   → All ports failed or already in use")
            return False
            
        except Exception as e:
            print(f"   → Hardware connection error: {e}")
            return False
    
    async def _discover_modules(self) -> Dict[str, Dict]:
        """Discover all CVM24P modules on the bus"""
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
        
        return found_modules
    
    async def _initialize_modules(self, discovered_modules: Dict) -> int:
        """Initialize all discovered modules"""
        initialized_count = 0
        
        print(f"   → Initializing {len(discovered_modules)} modules...")
        
        for i, (serial, info) in enumerate(discovered_modules.items()):
            module = CVM24PModule(self.bus, info['address'], serial, i)
            
            if await module.initialize():
                self.modules[serial] = module
                initialized_count += 1
        
        return initialized_count
    
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
        
        # Close hardware connections - SerialBus doesn't have disconnect method
        if self.bus and not self.use_mock:
            try:
                # Just close the event loop - let SerialBus clean up automatically
                if self.loop and not self.loop.is_closed():
                    # Cancel any pending tasks more gently
                    try:
                        pending = [task for task in asyncio.all_tasks(self.loop) if not task.done()]
                        if pending:
                            for task in pending:
                                task.cancel()
                            # Give tasks a moment to cancel
                            try:
                                self.loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                            except:
                                pass
                    except RuntimeError:
                        # Loop might already be closed
                        pass
                    
                    # Close the loop
                    if not self.loop.is_closed():
                        self.loop.close()
            except Exception as e:
                print(f"⚠️  Error cleaning up event loop: {e}")
        
        # Clear state
        self.modules.clear()
        self.bus = None
        self.loop = None
        
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
        self.poll_thread = threading.Thread(target=self._poll_data, daemon=True)
        self.poll_thread.start()
        
        print("✅ CVM-24P polling started")
        return True
    
    def stop_polling(self):
        """Stop polling cell voltage data"""
        if not self.polling:
            return
        
        print("🔋 Stopping CVM-24P polling...")
        self.polling = False
        
        if self.poll_thread and self.poll_thread.is_alive():
            self.poll_thread.join(timeout=3.0)
        
        print("✅ CVM-24P polling stopped")
    
    def _poll_data(self):
        """Polling thread function"""
        while self.polling and self.connected:
            try:
                if self.use_mock:
                    voltage_readings = self._generate_mock_data()
                else:
                    voltage_readings = self._read_hardware_data()
                
                # Update global state
                self.state.update_sensor_values(cell_voltages=voltage_readings)
                
                # Sleep for sample rate
                time.sleep(1.0 / self.sample_rate)
                
            except Exception as e:
                print(f"❌ CVM-24P polling error: {e}")
                break
    
    def _read_hardware_data(self) -> List[float]:
        """Read voltage data from real hardware"""
        all_voltages = []
        
        try:
            # Read from all modules in the event loop
            if self.loop and not self.loop.is_closed():
                try:
                    future = asyncio.run_coroutine_threadsafe(
                        self._async_read_all_modules(), self.loop
                    )
                    all_voltages = future.result(timeout=5.0)  # Increase timeout
                except asyncio.TimeoutError:
                    print("⚠️  Hardware reading timeout")
                    all_voltages = [0.0] * self.total_channels
                except Exception as e:
                    print(f"⚠️  Hardware reading error: {e}")
                    all_voltages = [0.0] * self.total_channels
            else:
                print("⚠️  Event loop not available for hardware reading")
                all_voltages = [0.0] * self.total_channels
            
        except Exception as e:
            print(f"⚠️  Hardware reading error: {e}")
            # Return previous values on error
            all_voltages = self.state.cell_voltages if self.state.cell_voltages else [0.0] * self.total_channels
        
        return all_voltages
    
    async def _async_read_all_modules(self) -> List[float]:
        """Async function to read from all modules"""
        all_voltages = []
        
        # Read from each module (sorted by module_id for consistent order)
        sorted_modules = sorted(self.modules.items(), key=lambda x: x[1].module_id)
        
        for serial, module in sorted_modules:
            try:
                if module.is_initialized and module.device:
                    # Read voltages using the same method as CVM_test.py
                    cell_voltages = await module.device.read_and_get_reg_by_name("ch_V")
                    # Take only the expected number of channels
                    module_voltages = cell_voltages[:CVM24PConfig.CHANNELS_PER_MODULE]
                    # Pad with zeros if we got fewer channels than expected
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
        
        # Pad to expected channel count
        while len(all_voltages) < self.total_channels:
            all_voltages.append(0.0)
        
        return all_voltages[:self.total_channels]
    
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
            'modules': len(self.modules),
            'channels': self.total_channels,
            'resolution': f"{CVM24PConfig.VOLTAGE_RESOLUTION*1000}mV",
            'voltage_range': f"{CVM24PConfig.MIN_CELL_VOLTAGE}V - {CVM24PConfig.MAX_CELL_VOLTAGE}V"
        }
    
    def get_module_info(self) -> Dict[str, Dict]:
        """Get information about connected modules"""
        module_info = {}
        
        for serial, module in self.modules.items():
            module_info[serial] = {
                'address': f"0x{module.address:X}",
                'module_id': module.module_id,
                'channels': CVM24PConfig.CHANNELS_PER_MODULE,
                'initialized': module.is_initialized
            }
        
        return module_info
    
    def get_voltage_statistics(self) -> Dict[str, float]:
        """Get voltage statistics for the cell stack"""
        voltages = self.state.cell_voltages
        
        if not voltages:
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
        voltages = self.state.cell_voltages
        
        unbalanced = []
        
        for i, voltage in enumerate(voltages):
            if abs(voltage - avg_voltage) > threshold:
                unbalanced.append(i + 1)  # 1-indexed cell numbers
        
        return unbalanced 
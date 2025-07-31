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
    print("❌ XC2 libraries not available - CVM24P hardware connection will fail")


class CVM24PConfig:
    """Configuration constants for CVM24P Cell Voltage Monitor"""
    
    # Serial communication settings
    BAUD_RATE = 1000000  # 1MHz - found to work best in CVM_test.py
    DISCOVERY_ATTEMPTS = 10  # Increased from 5 for more reliable discovery
    DISCOVERY_DELAY = 1.5  # Increased delay for better reliability
    MAX_DISCOVERY_TIME = 60  # Maximum time to spend on discovery (seconds)
    EXPECTED_MODULES = 5  # Expected number of modules to find
    
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
    
    def __init__(self, command_queue: queue.Queue, result_queue: queue.Queue, expected_modules: int = 5):
        self.command_queue = command_queue
        self.result_queue = result_queue
        self.bus = None
        self.modules = {}  # Dict of serial -> device info
        self.initialized_devices = {}  # Dict of serial -> XC2Cvm24p device
        self.running = False
        self.debug_channel_assignment_printed = False  # DEBUG: Flag to print channel assignment only once
        self.expected_modules = expected_modules  # Configurable expected modules count
        
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
    
    async def _try_cached_modules(self, cached_mapping: Dict[str, int]) -> Dict[str, Dict]:
        """Try to connect to modules using cached serial→address mapping (fast path)"""
        print(f"      → Attempting fast connection using cached addresses...")
        found_modules = {}
        
        for serial, cached_address in cached_mapping.items():
            try:
                # Try to connect directly to cached address
                device = XC2Cvm24p(self.bus, cached_address)
                actual_type, actual_serial = await device.read_serial_number()
                
                if actual_serial == serial:
                    found_modules[serial] = {
                        'address': cached_address,
                        'type': actual_type,
                        'serial': serial
                    }
                    print(f"      → ✅ {serial} found at cached address 0x{cached_address:X}")
                else:
                    print(f"      → ⚠️  Address 0x{cached_address:X} has different serial: {actual_serial}")
                    
            except Exception as e:
                print(f"      → ❌ Failed to reach {serial} at cached address 0x{cached_address:X}: {e}")
        
        success_count = len(found_modules)
        expected_count = len(cached_mapping)
        print(f"      → Fast connection result: {success_count}/{expected_count} modules found")
        
        return found_modules
    
    async def _connect_to_port(self, port: str) -> bool:
        """Connect to CVM hardware on specified port (similar to CVM_test.py)"""
        try:
            print(f"DEBUG: ===== Starting CVM24P connection debug session =====")
            
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
            print(f"      → Bus connected")
            
            # Add stability pause (like CVM_test.py)
            await asyncio.sleep(2)
            
            # Get cached mapping from service (passed via attribute)
            cached_mapping = getattr(self, 'cached_mapping', {})
            discovered_modules = {}
            
            # Ultra-Fast Path: Assume cached addresses are correct (ULTRA-FAST - 2-3 seconds)
            if cached_mapping:
                print(f"      → Using ultra-fast initialization with cached addresses...")
                # Create discovered_modules directly from cached mapping (skip verification)
                for serial, address in cached_mapping.items():
                    discovered_modules[serial] = {
                        'address': address,
                        'type': 'CVM24P',  # Assume type
                        'serial': serial
                    }
                print(f"      → ✅ Created module map for {len(discovered_modules)} cached modules - proceeding to initialization")
            else:
                print(f"      → No cached mapping available - using full discovery...")
                discovered_modules = await self._discover_modules()
            
            if not discovered_modules:
                print(f"      → No CVM24P modules found")
                # SerialBus doesn't have disconnect method - just clear reference
                self.bus = None
                return False
            
            # CRITICAL: Set self.modules for voltage reading to work
            self.modules = discovered_modules
            
            # Check module count
            expected_count = self.expected_modules
            found_count = len(discovered_modules)
            
            if found_count < expected_count:
                print(f"      → ⚠️  Warning: Found only {found_count}/{expected_count} expected modules")
                print(f"      → Proceeding with initialization of found modules...")
            
            # Initialize modules
            initialized_count = await self._initialize_modules(discovered_modules)
            
            if initialized_count == 0:
                # If ultra-fast path failed and we used cached mapping, try fallback
                if cached_mapping and len(discovered_modules) == len(cached_mapping):
                    print(f"      → Ultra-fast initialization failed - falling back to verification/discovery...")
                    
                    # Fallback: Try cached addresses with verification
                    discovered_modules = await self._try_cached_modules(cached_mapping)
                    
                    # If still missing modules, use full discovery
                    if len(discovered_modules) < self.expected_modules:
                        missing_count = self.expected_modules - len(discovered_modules)
                        print(f"      → ⚠️  {missing_count} modules still missing - using full discovery...")
                        missing_modules = await self._discover_modules()
                        discovered_modules.update(missing_modules)
                    
                    # Try initialization again with verified modules
                    if discovered_modules:
                        print(f"      → Retrying initialization with {len(discovered_modules)} verified modules...")
                        # CRITICAL: Update self.modules for fallback path too
                        self.modules = discovered_modules
                        initialized_count = await self._initialize_modules(discovered_modules)
                
                if initialized_count == 0:
                    print(f"      → No modules successfully initialized after fallback")
                    # SerialBus doesn't have disconnect method - just clear reference
                    self.bus = None
                    return False
            
            # Success criteria: at least some modules initialized
            final_found_count = len(discovered_modules)  # Update count in case fallback was used
            success_rate = initialized_count / final_found_count if final_found_count > 0 else 0
            
            # Determine which path was successful
            if cached_mapping and final_found_count == len(cached_mapping) and initialized_count > 0:
                path_used = "ultra-fast cached"
            elif cached_mapping:
                path_used = "cached with fallback"
            else:
                path_used = "full discovery"
            
            print(f"   → Success! {initialized_count}/{final_found_count} modules initialized via {path_used} path ({success_rate:.1%} success rate)")
            
            if final_found_count < expected_count:
                print(f"   → ⚠️  Note: Only {final_found_count}/{expected_count} expected modules were discovered")
            
            return True
            
        except Exception as e:
            print(f"      → Connection error: {e}")
            # SerialBus doesn't have disconnect method - just clear reference
            self.bus = None
            return False
    
    async def _discover_modules(self) -> Dict[str, Dict]:
        """Discover CVM24P modules with robust retry logic to ensure all 5 modules are found"""
        found_modules = {}
        discovery_start_time = asyncio.get_event_loop().time()
        attempt = 0
        consecutive_same_count = 0
        last_module_count = 0
        
        print(f"      → Starting robust discovery process (expecting {self.expected_modules} modules)...")
        
        while len(found_modules) < self.expected_modules:
            attempt += 1
            
            # Check maximum discovery time
            elapsed_time = asyncio.get_event_loop().time() - discovery_start_time
            if elapsed_time > CVM24PConfig.MAX_DISCOVERY_TIME:
                print(f"      → Discovery timeout after {elapsed_time:.1f}s - found {len(found_modules)}/{self.expected_modules} modules")
                break
            
            # Vary timing slightly to avoid sync issues
            delay_variation = 0.2 * (attempt % 3 - 1)  # -0.2, 0, +0.2 seconds variation
            discovery_delay = CVM24PConfig.DISCOVERY_DELAY + delay_variation
            await asyncio.sleep(discovery_delay)
            
            try:
                print(f"      → Discovery attempt {attempt}: ", end="", flush=True)
                
                # Get devices via broadcast echo
                devices = await get_broadcast_echo(bus=self.bus)
                print(f"echo found {len(devices)} devices, ", end="", flush=True)
                
                # Try to get device info via serial broadcast
                device_info = {}
                try:
                    device_info = await get_serial_broadcast(bus=self.bus)
                    print(f"serial broadcast got {len(device_info)} responses, ", end="", flush=True)
                    
                    # Add modules by serial number from broadcast response
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
                                print(f"new module {serial} at 0x{addr:X}, ", end="", flush=True)
                
                except Exception as e:
                    print(f"serial broadcast failed ({e}), ", end="", flush=True)
                
                # Try direct identification for devices that responded to echo but not serial broadcast
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
                                print(f"direct ID found {device_serial} at 0x{addr:X}, ", end="", flush=True)
                        except Exception:
                            pass  # Skip failed direct identification
                
                current_count = len(found_modules)
                print(f"total: {current_count}/{self.expected_modules} modules")
                
                # Track if we're making progress
                if current_count == last_module_count:
                    consecutive_same_count += 1
                else:
                    consecutive_same_count = 0
                    last_module_count = current_count
                
                # If we found all expected modules, we're done
                if current_count >= self.expected_modules:
                    print(f"      → ✅ Found all {self.expected_modules} expected modules after {attempt} attempts")
                    break
                
                # If we're stuck at the same count for too many attempts, try a longer delay
                if consecutive_same_count >= 3:
                    print(f"      → Stuck at {current_count} modules, trying extended discovery...")
                    await asyncio.sleep(3.0)  # Longer pause to let network settle
                    consecutive_same_count = 0
                
            except Exception as e:
                print(f"failed: {e}")
                continue
        
        # Final summary
        if len(found_modules) < self.expected_modules:
            print(f"      → ⚠️  Warning: Only found {len(found_modules)}/{self.expected_modules} expected modules")
            print(f"      → Discovered modules: {list(found_modules.keys())}")
        else:
            print(f"      → ✅ Successfully discovered all {len(found_modules)} modules")
        
        # DEBUG: Show discovery order
        print(f"      → DEBUG: Discovery order: {list(found_modules.keys())}")
        discovery_addresses = [(serial, f"0x{info['address']:X}") for serial, info in found_modules.items()]
        print(f"      → DEBUG: Discovery addresses: {discovery_addresses}")
        
        self.modules = found_modules
        return found_modules
    
    async def _initialize_modules(self, discovered_modules: Dict) -> int:
        """Initialize discovered modules (like CVM_test.py)"""
        initialized_count = 0
        
        print(f"   → Initializing {len(discovered_modules)} modules...")
        
        # DEBUG: Show initialization order
        init_order = list(discovered_modules.keys())
        print(f"   → DEBUG: Initialization order: {init_order}")
        
        for serial, info in discovered_modules.items():
            try:
                device = XC2Cvm24p(self.bus, info['address'])
                await device.initial_structure_reading()
                
                self.initialized_devices[serial] = device
                initialized_count += 1
                print(f"   ✅ Module {serial} (0x{info['address']:X}) initialized")
                
            except Exception as e:
                print(f"   ❌ Failed to initialize module {serial}: {e}")
        
        # DEBUG: Show final initialized modules
        initialized_serials = list(self.initialized_devices.keys())
        print(f"   → DEBUG: Successfully initialized modules: {initialized_serials}")
        
        return initialized_count
    
    async def _read_all_voltages(self) -> List[float]:
        """Read voltages from all modules (like CVM_test.py pattern)"""
        all_voltages = []
        
        # Sort by address for consistent ordering  
        sorted_modules = sorted(self.modules.items(), key=lambda x: x[1]['address'])
        
        # DEBUG: Show sorting and channel assignment
        if not self.debug_channel_assignment_printed:
            print(f"DEBUG: Voltage reading - module sorting and channel assignment:")
            channel_start = 0
            for i, (serial, module_info) in enumerate(sorted_modules):
                channel_end = channel_start + CVM24PConfig.CHANNELS_PER_MODULE - 1
                print(f"DEBUG:   Module {serial} (0x{module_info['address']:X}) → Channels {channel_start+1}-{channel_end+1}")
                channel_start += CVM24PConfig.CHANNELS_PER_MODULE
            self.debug_channel_assignment_printed = True
        
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
        # SerialBus doesn't have a disconnect() method
        # Just clear references and let it clean up automatically
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
        
        # CVM24P configuration from device config
        self.device_name = "CVM-24P"
        self.sample_rate = self.device_config.get_sample_rate('cvm24p')
        # Get expected modules count from devices.yaml (will be updated after module mapping is loaded)
        self.expected_modules = 5  # Default fallback
        self.total_channels = self.expected_modules * CVM24PConfig.CHANNELS_PER_MODULE
        
        # Get module mapping from devices.yaml (source of truth)
        self.cached_module_mapping = self.device_config.get_cvm24p_module_mapping()
        self.module_names = self.device_config.get_cvm24p_module_names()
        
        # Validate module configuration
        if not self.cached_module_mapping:
            print("⚠️  Warning: No CVM24P module mapping found in devices.yaml")
        else:
            expected_count = self.device_config.get_cvm24p_expected_modules()
            print(f"   → Loaded {len(self.cached_module_mapping)} module mappings from devices.yaml")
            
            # Debug: Show configured module mapping
            print(f"   → Physical connection order:")
            for serial, address in self.cached_module_mapping.items():
                module_name = self.module_names.get(serial, f'Module {serial}')
                print(f"      {module_name} - {serial} (0x{address:X})")
        
        # Update expected modules count based on devices.yaml
        self.expected_modules = self.device_config.get_cvm24p_expected_modules()
        self.total_channels = self.expected_modules * CVM24PConfig.CHANNELS_PER_MODULE
        
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
            print("❌ XC2 libraries not available - cannot connect to hardware")
            return False
        
        try:
            # Try to connect to hardware
            print("   → Attempting hardware connection...")
            
            if self._connect_hardware():
                self.connected = True
                self.state.update_connection_status('cvm24p', True)
                print(f"✅ CVM-24P connected - Hardware mode with {len(self.modules_info)} modules")
                return True
            else:
                print("❌ Hardware connection failed")
                return False
                
        except Exception as e:
            print(f"❌ Failed to connect to CVM-24P: {e}")
            return False
    
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
            self.async_manager = AsyncCVMManager(self.command_queue, self.result_queue, self.expected_modules)
            # Pass cached mapping to async manager for fast connection
            self.async_manager.cached_mapping = self.cached_module_mapping
            self.async_thread = threading.Thread(
                target=lambda: asyncio.run(self.async_manager.run()), 
                daemon=True
            )
            self.async_thread.start()
            
            # Clear any stale results from previous attempts
            while not self.result_queue.empty():
                try:
                    self.result_queue.get_nowait()
                except queue.Empty:
                    break
            
            # Try each port until one works
            for port_index, selected_port in enumerate(available_ports):
                try:
                    print(f"   → Trying port {selected_port} ({port_index+1}/{len(available_ports)})...")
                    
                    # Send connect command to async manager
                    self.command_queue.put(('connect', selected_port))
                    
                    # Wait for result with longer timeout (discovery + initialization can take 30+ seconds)
                    try:
                        result_type, result_data = self.result_queue.get(timeout=45.0)
                        
                        if result_type == 'connect_result' and result_data:
                            print(f"   → Success on {selected_port}!")
                            
                            # Wait a moment for async manager to finish updating modules
                            time.sleep(1.0)
                            
                            # Get module info from async manager
                            if self.async_manager:
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
    
    def disconnect(self):
        """Disconnect from CVM24P"""
        print("🔋 Disconnecting from CVM-24P...")
        
        # Stop polling first
        if self.polling:
            self.stop_polling()
        
        # Stop async manager
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
        
        print(f"🔋 Starting CVM-24P polling at {self.sample_rate} Hz...")
        
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
    
    def get_status(self) -> Dict[str, Any]:
        """Get current service status"""
        return {
            'connected': self.connected,
            'polling': self.polling,
            'device': self.device_name,
            'sample_rate': f"{self.sample_rate} Hz",
            'mode': 'Hardware',
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
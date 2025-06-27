"""
Pico TC-08 thermocouple logger service for AWE test rig
Real hardware integration for 8-channel temperature monitoring
"""

import time
import threading

from typing import List, Tuple, Dict, Any
from core.state import get_global_state
from config.device_config import get_device_config

# Try to import the required Pico libraries
try:
    import ctypes
    PICO_AVAILABLE = True
    print("✅ Pico TC-08 libraries available")
except ImportError:
    PICO_AVAILABLE = False
    print("❌ Pico TC-08 libraries not available - hardware connection will fail")


class PicoTC08Config:
    """Configuration constants for Pico TC-08 thermocouple logger"""
    
    # Windows DLL paths
    DLL_PATHS = [
        r"C:\Program Files\Pico Technology\SDK\lib\usbtc08.dll",
        r"C:\Program Files (x86)\Pico Technology\SDK\lib\usbtc08.dll",
        "usbtc08.dll"  # Try system PATH
    ]
    
    # Thermocouple configuration
    NUM_CHANNELS = 8  # 8 thermocouple channels
    TC_TYPE = 'K'  # K-type thermocouples
    COLD_JUNCTION_TYPE = 'C'  # Cold junction compensation
    
    # Sampling configuration
    SAMPLE_INTERVAL_MS = 1000  # TC-08 sampling rate
    
    # Temperature units (0 = Celsius, 1 = Fahrenheit, 2 = Kelvin, 3 = Rankine)
    TEMP_UNITS = 0  # Celsius
    
    # Channel names for clarity (matching device config)
    CHANNEL_NAMES = [
        "Inlet Temperature",
        "Outlet Temperature", 
        "Stack Temperature 1",
        "Stack Temperature 2",
        "Ambient Temperature",
        "Cooling System Temperature",
        "Gas Temperature",
        "Case Temperature"
    ]


class PicoTC08Hardware:
    """Low-level Pico TC-08 hardware interface"""
    
    def __init__(self):
        self.dll = None
        self.handle = None
        self.is_connected = False
        self.is_streaming = False
        
    def load_dll(self) -> bool:
        """Load the Windows TC-08 DLL"""        
        for dll_path in PicoTC08Config.DLL_PATHS:
            try:
                self.dll = ctypes.WinDLL(dll_path)
                self._setup_function_prototypes()
                print(f"   → TC-08 library loaded: {dll_path}")
                return True
                
            except Exception:
                continue
        
        print(f"   → TC-08 library not found in any of these paths:")
        for path in PicoTC08Config.DLL_PATHS:
            print(f"     • {path}")
        return False
    
    def _setup_function_prototypes(self):
        """Set up ctypes function prototypes for TC-08 API"""
        
        # usb_tc08_open_unit
        self.dll.usb_tc08_open_unit.restype = ctypes.c_int16
        self.dll.usb_tc08_open_unit.argtypes = []
        
        # usb_tc08_set_channel
        self.dll.usb_tc08_set_channel.argtypes = [
            ctypes.c_int16,    # handle
            ctypes.c_int16,    # channel number
            ctypes.c_char      # type char ('C', 'K', etc)
        ]
        self.dll.usb_tc08_set_channel.restype = ctypes.c_int16
        
        # usb_tc08_run
        self.dll.usb_tc08_run.argtypes = [
            ctypes.c_int16,    # handle
            ctypes.c_int32     # sample interval (ms)
        ]
        self.dll.usb_tc08_run.restype = ctypes.c_int32
        
        # usb_tc08_get_temp
        self.dll.usb_tc08_get_temp.argtypes = [
            ctypes.c_int16,                     # handle
            ctypes.POINTER(ctypes.c_float),     # temp buffer
            ctypes.POINTER(ctypes.c_int32),     # time buffer
            ctypes.c_int32,                     # number of readings
            ctypes.POINTER(ctypes.c_int16),     # overflow flag
            ctypes.c_int16,                     # channel to read
            ctypes.c_int16,                     # units
            ctypes.c_int16                      # trigger mode
        ]
        self.dll.usb_tc08_get_temp.restype = ctypes.c_int32
        
        # usb_tc08_stop
        self.dll.usb_tc08_stop.argtypes = [ctypes.c_int16]
        self.dll.usb_tc08_stop.restype = ctypes.c_int16
        
        # usb_tc08_close_unit
        self.dll.usb_tc08_close_unit.argtypes = [ctypes.c_int16]
        self.dll.usb_tc08_close_unit.restype = ctypes.c_int16
    
    def connect(self) -> bool:
        """Connect to the TC-08 device"""
        if not self.dll:
            return False
        
        try:
            self.handle = self.dll.usb_tc08_open_unit()
            
            if self.handle <= 0:
                print("   → No TC-08 device found")
                return False
            
            print(f"   → TC-08 device opened with handle: {self.handle}")
            self.is_connected = True
            return True
            
        except Exception as e:
            print(f"   → TC-08 connection error: {e}")
            return False
    
    def configure_channels(self) -> bool:
        """Configure cold junction and thermocouple channels"""
        if not self.is_connected:
            return False
        
        try:
            # Configure cold junction (channel 0)
            cold_junction_char = ctypes.c_char(PicoTC08Config.COLD_JUNCTION_TYPE.encode())
            self.dll.usb_tc08_set_channel(self.handle, 0, cold_junction_char)
            
            # Configure all thermocouple channels
            tc_type_char = ctypes.c_char(PicoTC08Config.TC_TYPE.encode())
            
            for ch in range(1, PicoTC08Config.NUM_CHANNELS + 1):
                result = self.dll.usb_tc08_set_channel(self.handle, ch, tc_type_char)
                if result == 0:
                    print(f"   → Failed to configure channel {ch}")
                    return False
            
            print(f"   → Configured {PicoTC08Config.NUM_CHANNELS} K-type thermocouple channels")
            return True
            
        except Exception as e:
            print(f"   → Channel configuration error: {e}")
            return False
    
    def start_streaming(self) -> bool:
        """Start temperature streaming"""
        if not self.is_connected:
            return False
        
        try:
            actual_interval = self.dll.usb_tc08_run(self.handle, PicoTC08Config.SAMPLE_INTERVAL_MS)
            
            if actual_interval <= 0:
                print("   → Failed to start TC-08 streaming")
                return False
            
            self.is_streaming = True
            print("   → TC-08 streaming started at 1Hz")
            return True
            
        except Exception as e:
            print(f"   → Error starting TC-08 streaming: {e}")
            return False
    
    def read_temperatures(self) -> List[Tuple[str, float, bool]]:
        """Read temperatures from all channels"""
        if not self.is_streaming:
            return []
        
        temperatures = []
        
        try:
            for ch in range(1, PicoTC08Config.NUM_CHANNELS + 1):
                # Prepare buffers
                temp_buffer = (ctypes.c_float * 1)()
                time_buffer = (ctypes.c_int32 * 1)()
                overflow = ctypes.c_int16(0)
                
                # Read temperature
                self.dll.usb_tc08_get_temp(
                    self.handle,
                    temp_buffer,
                    time_buffer,
                    1,  # One reading
                    ctypes.byref(overflow),
                    ctypes.c_int16(ch),
                    ctypes.c_int16(PicoTC08Config.TEMP_UNITS),
                    ctypes.c_int16(0)  # No trigger
                )
                
                channel_name = PicoTC08Config.CHANNEL_NAMES[ch-1]
                temperature = temp_buffer[0]
                
                # Check for valid reading (TC-08 returns very large negative values for disconnected)
                valid = temperature > -100.0  # Reasonable threshold
                
                temperatures.append((channel_name, temperature, valid))
            
            return temperatures
            
        except Exception:
            return []
    
    def stop_streaming(self):
        """Stop temperature streaming"""
        if self.is_streaming and self.handle:
            try:
                self.dll.usb_tc08_stop(self.handle)
                self.is_streaming = False
            except Exception:
                pass
    
    def disconnect(self):
        """Disconnect from the device"""
        self.stop_streaming()
        
        if self.is_connected and self.handle:
            try:
                self.dll.usb_tc08_close_unit(self.handle)
                self.is_connected = False
                self.handle = None
                print("   → TC-08 device closed")
            except Exception as e:
                print(f"   → Error closing TC-08: {e}")


class PicoTC08Service:
    """Service for Pico TC-08 thermocouple unit with real hardware integration"""
    
    def __init__(self):
        self.connected = False
        self.polling = False
        self.poll_thread = None
        self.state = get_global_state()
        self.device_config = get_device_config()
        
        # Hardware interface
        self.hardware = PicoTC08Hardware()
        
        # TC-08 configuration from device config
        tc_config = self.device_config.get_pico_tc08_config()
        self.device_name = "TC-08"
        self.sample_rate = self.device_config.get_sample_rate('pico_tc08')
        self.num_channels = PicoTC08Config.NUM_CHANNELS
        
        # Channel configuration with zero offsets
        self.channel_config = {}
        for i in range(self.num_channels):
            channel_key = f"channel_{i}"
            channel_config = self.device_config.get_temperature_channel_config(channel_key)
            
            self.channel_config[i] = {
                "name": channel_config.get('name', f'Temperature {i+1}'),
                "type": "K",
                "description": channel_config.get('description', f'Temperature channel {i+1}')
            }
        
    def connect(self) -> bool:
        """Connect to Pico TC-08 device"""
        print("🌡️  Connecting to Pico TC-08 thermocouple logger...")
        
        if not PICO_AVAILABLE:
            print("❌ Pico libraries not available - cannot connect to hardware")
            return False
        
        try:
            # Try to load DLL and connect to real hardware
            print("   → Loading TC-08 DLL...")
            if self.hardware.load_dll():
                print("   → DLL loaded successfully")
                print("   → Connecting to hardware...")
                
                if self.hardware.connect():
                    print(f"   → Hardware connected (handle: {self.hardware.handle})")
                    print("   → Configuring channels...")
                    
                    if self.hardware.configure_channels():
                        print(f"   → Configured {self.num_channels} thermocouple channels:")
                        
                        for ch, config in self.channel_config.items():
                            print(f"     • CH{ch}: {config['name']}")
                        
                        self.connected = True
                        self.state.update_connection_status('pico_tc08', True)
                        
                        print("✅ Pico TC-08 connected successfully")
                        return True
                    else:
                        print("❌ Hardware channel configuration failed")
                        self.hardware.disconnect()
                else:
                    print("❌ Hardware connection failed - no TC-08 device found")
            else:
                print("❌ TC-08 DLL not available")
            
            return False
            
        except Exception as e:
            print(f"❌ Failed to connect to Pico TC-08: {e}")
            self.connected = False
            self.state.update_connection_status('pico_tc08', False)
            return False
    
    def disconnect(self):
        """Disconnect from Pico TC-08"""
        print("🌡️  Disconnecting from Pico TC-08...")
        
        # Stop polling first
        if self.polling:
            self.stop_polling()
        
        # Disconnect hardware
        self.hardware.disconnect()
        
        self.connected = False
        self.state.update_connection_status('pico_tc08', False)
        
        print("✅ Pico TC-08 disconnected")
    
    def start_polling(self) -> bool:
        """Start polling thermocouple data"""
        if not self.connected:
            print("❌ Cannot start polling - Pico TC-08 not connected")
            return False
        
        if self.polling:
            print("⚠️  Pico TC-08 polling already running")
            return True
        
        print(f"🌡️  Starting Pico TC-08 polling at {self.sample_rate} Hz...")
        
        # Start hardware streaming
        if not self.hardware.start_streaming():
            print("❌ Failed to start hardware streaming")
            return False
        
        self.polling = True
        self.poll_thread = threading.Thread(target=self._poll_data, daemon=True)
        self.poll_thread.start()
        
        print("✅ Pico TC-08 polling started")
        return True
    
    def stop_polling(self):
        """Stop polling thermocouple data"""
        if not self.polling:
            return
        
        print("🌡️  Stopping Pico TC-08 polling...")
        self.polling = False
        
        # Stop hardware streaming
        self.hardware.stop_streaming()
        
        if self.poll_thread and self.poll_thread.is_alive():
            self.poll_thread.join(timeout=2.0)
        
        print("✅ Pico TC-08 polling stopped")
    
    def _poll_data(self):
        """Polling thread function"""
        while self.polling and self.connected:
            try:
                # Read from hardware
                temp_readings = self._read_hardware_temperature_data()
                
                # Update global state
                self.state.update_sensor_values(temperature_values=temp_readings)
                
                # Sleep for sample rate
                time.sleep(1.0 / self.sample_rate)
                
            except Exception as e:
                print(f"❌ Pico TC-08 polling error: {e}")
                break
    
    def _read_hardware_temperature_data(self) -> List[float]:
        """Read temperatures from real TC-08 hardware"""
        try:
            # Read from hardware
            raw_readings = self.hardware.read_temperatures()
            
            if not raw_readings:
                # Return zeros if no readings available
                return [0.0] * self.num_channels
            
            temperatures = []
            
            for i, (channel_name, raw_temp, valid) in enumerate(raw_readings):
                if valid:
                    temperatures.append(round(raw_temp, 2))
                else:
                    # Invalid reading (disconnected thermocouple)
                    temperatures.append(0.0)
            
            return temperatures
            
        except Exception as e:
            print(f"⚠️  Hardware temperature reading error: {e}")
            # Return zeros on error
            return [0.0] * self.num_channels
    
    def get_status(self) -> Dict[str, Any]:
        """Get current service status"""
        return {
            'connected': self.connected,
            'polling': self.polling,
            'device': self.device_name,
            'sample_rate': f"{self.sample_rate} Hz",
            'channels': self.num_channels,
            'mode': 'Hardware',
            'channel_config': self.channel_config,
            'calibration_date': self.device_config.get_calibration_date()
        }
    
    def get_current_readings(self) -> Dict[str, float]:
        """Get current temperature readings with channel names"""
        readings = {}
        temps = self.state.temperature_values
        
        for i, temp in enumerate(temps):
            if i < len(self.channel_config):
                channel_name = self.channel_config[i]['name']
                readings[channel_name] = temp
        
        return readings 
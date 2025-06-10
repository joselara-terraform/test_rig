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
    import ctypes.util
    PICO_AVAILABLE = True
    print("✅ Pico TC-08 libraries available")
except ImportError:
    PICO_AVAILABLE = False
    print("❌ Pico TC-08 libraries not available - hardware connection will fail")


class PicoTC08Config:
    """Configuration constants for Pico TC-08 thermocouple logger"""
    
    NUM_CHANNELS = 8  # 8 thermocouple channels
    TEMP_UNITS = 0  # 0 = Celsius, 1 = Fahrenheit, 2 = Kelvin
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
        self.handle = None
        self.dll = None
        self.is_streaming = False
        
    def connect(self) -> bool:
        """Connect to Pico TC-08 hardware"""
        try:
            # Load the TC-08 library
            if ctypes.util.find_library("usbtc08"):
                self.dll = ctypes.cdll.LoadLibrary("usbtc08")
            elif ctypes.util.find_library("libusbtc08"):
                self.dll = ctypes.cdll.LoadLibrary("libusbtc08") 
            else:
                print("   → TC-08 library not found")
                return False
            
            # Open the first available TC-08 device
            self.handle = self.dll.usb_tc08_open_unit()
            
            if self.handle <= 0:
                print("   → No TC-08 device found")
                return False
            
            print(f"   → TC-08 device opened with handle: {self.handle}")
            
            # Configure channels for K-type thermocouples
            for ch in range(1, PicoTC08Config.NUM_CHANNELS + 1):
                # Set channel to K-type thermocouple (TypeK = 75)
                result = self.dll.usb_tc08_set_channel(
                    self.handle,
                    ctypes.c_int16(ch),
                    ctypes.c_char(b'K')  # K-type thermocouple
                )
                
                if result == 0:
                    print(f"   → Failed to configure channel {ch}")
                    return False
            
            print(f"   → Configured {PicoTC08Config.NUM_CHANNELS} K-type thermocouple channels")
            return True
            
        except Exception as e:
            print(f"   → TC-08 connection error: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from TC-08 hardware"""
        if self.is_streaming:
            self.stop_streaming()
            
        if self.handle and self.dll:
            try:
                self.dll.usb_tc08_close_unit(self.handle)
                print("   → TC-08 device closed")
            except Exception as e:
                print(f"   → Error closing TC-08: {e}")
            
        self.handle = None
        self.dll = None
    
    def start_streaming(self) -> bool:
        """Start temperature streaming"""
        if not self.handle or not self.dll:
            return False
            
        try:
            # Start streaming mode (interval in ms, we'll use 1000ms = 1Hz)
            result = self.dll.usb_tc08_run(self.handle, ctypes.c_int32(1000))
            
            if result == 0:
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
            print("   → Attempting hardware connection...")
            
            # Try to connect to real hardware
            if self.hardware.connect():
                self.connected = True
                self.state.update_connection_status('pico_tc08', True)
                
                print(f"   → TC-08 device connected successfully")
                print(f"   → {self.num_channels} thermocouple channels configured:")
                
                for ch, config in self.channel_config.items():
                    print(f"     • CH{ch}: {config['name']}")
                
                print("✅ Pico TC-08 connected successfully")
                return True
            else:
                print("❌ Hardware connection failed")
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
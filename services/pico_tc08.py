"""
Pico TC-08 thermocouple service for AWE test rig
Simulates 8-channel temperature readings from thermocouples
"""

import time
import threading
import random
from typing import Dict, Any, List
from core.state import get_global_state


class PicoTC08Service:
    """Service for Pico TC-08 thermocouple unit"""
    
    def __init__(self):
        self.connected = False
        self.polling = False
        self.poll_thread = None
        self.state = get_global_state()
        
        # TC-08 configuration
        self.device_name = "TC-08"
        self.sample_rate = 1.0  # 1 Hz for thermocouples (slower than DAQ)
        self.num_channels = 8
        
        # Thermocouple channel configuration
        self.channel_config = {
            0: {"name": "inlet_temp", "type": "K", "range": [20, 30]},      # Inlet water temp
            1: {"name": "outlet_temp", "type": "K", "range": [35, 50]},    # Outlet water temp  
            2: {"name": "stack_temp_1", "type": "K", "range": [40, 80]},   # Stack temperature 1
            3: {"name": "stack_temp_2", "type": "K", "range": [40, 80]},   # Stack temperature 2
            4: {"name": "ambient_temp", "type": "K", "range": [20, 25]},   # Ambient temperature
            5: {"name": "cooling_temp", "type": "K", "range": [15, 35]},   # Cooling system temp
            6: {"name": "gas_temp", "type": "K", "range": [25, 45]},       # Gas output temp
            7: {"name": "case_temp", "type": "K", "range": [30, 50]}       # Electronics case temp
        }
        
        # Base temperatures for realistic drift
        self.base_temps = [25.0, 42.0, 60.0, 58.0, 22.0, 28.0, 35.0, 40.0]
        
    def connect(self) -> bool:
        """Connect to Pico TC-08 device"""
        print("🌡️  Connecting to Pico TC-08...")
        try:
            # Simulate connection process
            time.sleep(0.5)
            
            print(f"   → Detecting device: {self.device_name}")
            print(f"   → Configuring {self.num_channels} thermocouple channels:")
            
            for ch, config in self.channel_config.items():
                print(f"     • CH{ch}: {config['name']} (Type {config['type']})")
            
            print(f"   → Setting sample rate: {self.sample_rate} Hz")
            
            self.connected = True
            self.state.update_connection_status('pico_tc08', True)
            
            print("✅ Pico TC-08 connected successfully")
            return True
            
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
            print("⚠️  Pico TC-08 polling already stopped" if not self.polling else "")
            self.stop_polling()
        
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
        
        if self.poll_thread and self.poll_thread.is_alive():
            self.poll_thread.join(timeout=2.0)
        
        print("✅ Pico TC-08 polling stopped")
    
    def _poll_data(self):
        """Polling thread function"""
        while self.polling and self.connected:
            try:
                # Generate realistic temperature readings
                temp_readings = self._generate_temperature_data()
                
                # Update global state
                self.state.update_sensor_values(temperature_values=temp_readings)
                
                # Sleep for sample rate
                time.sleep(1.0 / self.sample_rate)
                
            except Exception as e:
                print(f"❌ Pico TC-08 polling error: {e}")
                break
    
    def _generate_temperature_data(self) -> List[float]:
        """Generate realistic temperature readings for all channels"""
        temperatures = []
        
        for i in range(self.num_channels):
            config = self.channel_config[i]
            base_temp = self.base_temps[i]
            
            # Add realistic variation based on channel type
            if "ambient" in config["name"]:
                # Ambient temperature changes slowly
                variation = random.uniform(-0.5, 0.5)
            elif "stack" in config["name"]:
                # Stack temperatures can vary more
                variation = random.uniform(-2.0, 2.0)
            elif "inlet" in config["name"]:
                # Inlet water temperature is relatively stable
                variation = random.uniform(-1.0, 1.0)
            elif "outlet" in config["name"]:
                # Outlet temperature depends on operation
                variation = random.uniform(-1.5, 3.0)
            else:
                # General variation for other channels
                variation = random.uniform(-1.0, 1.0)
            
            # Calculate final temperature
            temp = base_temp + variation
            
            # Clamp to realistic range
            min_temp, max_temp = config["range"]
            temp = max(min_temp, min(max_temp, temp))
            
            temperatures.append(round(temp, 2))
        
        return temperatures
    
    def get_status(self) -> Dict[str, Any]:
        """Get current service status"""
        return {
            'connected': self.connected,
            'polling': self.polling,
            'device': self.device_name,
            'sample_rate': f"{self.sample_rate} Hz",
            'channels': self.num_channels,
            'channel_config': self.channel_config
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
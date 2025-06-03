"""
CVM-24P cell voltage monitor service for AWE test rig
Simulates 24-channel cell voltage measurements for electrolyzer monitoring
"""

import time
import threading
import random
from typing import Dict, Any, List
from core.state import get_global_state


class CVM24PService:
    """Service for CVM-24P cell voltage monitor"""
    
    def __init__(self):
        self.connected = False
        self.polling = False
        self.poll_thread = None
        self.state = get_global_state()
        
        # CVM-24P configuration
        self.device_name = "CVM-24P"
        self.sample_rate = 10.0  # 10 Hz for voltage monitoring (faster than gas, slower than DAQ)
        self.num_channels = 24
        
        # Cell configuration for electrolyzer stack
        self.channel_config = {}
        for i in range(24):
            self.channel_config[i] = {
                "name": f"cell_{i+1:02d}",
                "description": f"Electrolyzer Cell {i+1}",
                "nominal_voltage": 2.1,  # Nominal 2.1V per cell
                "min_voltage": 1.8,      # Minimum safe voltage
                "max_voltage": 2.5       # Maximum voltage under load
            }
        
        # Base voltages for realistic variation (simulate slight cell differences)
        self.base_voltages = []
        for i in range(24):
            # Slight variation in cell characteristics
            base_v = 2.1 + random.uniform(-0.05, 0.05)  # ±50mV cell variation
            self.base_voltages.append(base_v)
        
        # Operating state simulation
        self.operating_current = 0.0  # Will affect voltage drop
        
    def connect(self) -> bool:
        """Connect to CVM-24P device"""
        print("🔋 Connecting to CVM-24P cell voltage monitor...")
        try:
            # Simulate connection process
            time.sleep(0.8)
            
            print(f"   → Detecting device: {self.device_name}")
            print(f"   → Configuring {self.num_channels} voltage channels:")
            print(f"     • Channels 1-24: Electrolyzer cell voltages")
            print(f"     • Voltage range: 1.8V - 2.5V per cell")
            print(f"     • Resolution: 1mV")
            
            print(f"   → Setting sample rate: {self.sample_rate} Hz")
            print(f"   → Calibrating voltage references...")
            time.sleep(0.3)
            
            self.connected = True
            self.state.update_connection_status('cvm24p', True)
            
            print("✅ CVM-24P connected successfully")
            return True
            
        except Exception as e:
            print(f"❌ Failed to connect to CVM-24P: {e}")
            self.connected = False
            self.state.update_connection_status('cvm24p', False)
            return False
    
    def disconnect(self):
        """Disconnect from CVM-24P"""
        print("🔋 Disconnecting from CVM-24P...")
        
        # Stop polling first
        if self.polling:
            print("⚠️  CVM-24P polling already stopped" if not self.polling else "")
            self.stop_polling()
        
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
            self.poll_thread.join(timeout=2.0)
        
        print("✅ CVM-24P polling stopped")
    
    def _poll_data(self):
        """Polling thread function"""
        while self.polling and self.connected:
            try:
                # Update operating current from global state (affects voltage)
                self.operating_current = self.state.current_value
                
                # Generate realistic voltage readings
                voltage_readings = self._generate_voltage_data()
                
                # Update global state
                self.state.update_sensor_values(cell_voltages=voltage_readings)
                
                # Sleep for sample rate
                time.sleep(1.0 / self.sample_rate)
                
            except Exception as e:
                print(f"❌ CVM-24P polling error: {e}")
                break
    
    def _generate_voltage_data(self) -> List[float]:
        """Generate realistic cell voltage readings"""
        voltages = []
        
        # Current affects voltage drop (simplified model)
        current_factor = min(self.operating_current / 5.0, 1.0)  # Normalize to 5A max
        voltage_drop = current_factor * 0.15  # Up to 150mV drop under load
        
        for i in range(self.num_channels):
            config = self.channel_config[i]
            base_voltage = self.base_voltages[i]
            
            # Apply load-dependent voltage drop
            operating_voltage = base_voltage - voltage_drop
            
            # Add realistic noise and variation
            noise = random.uniform(-0.01, 0.01)  # ±10mV noise
            drift = random.uniform(-0.005, 0.005)  # ±5mV slow drift
            
            # Calculate final voltage
            voltage = operating_voltage + noise + drift
            
            # Clamp to realistic cell voltage range
            voltage = max(config["min_voltage"], min(config["max_voltage"], voltage))
            
            # Round to 1mV resolution (CVM-24P spec)
            voltages.append(round(voltage, 3))
        
        return voltages
    
    def get_status(self) -> Dict[str, Any]:
        """Get current service status"""
        return {
            'connected': self.connected,
            'polling': self.polling,
            'device': self.device_name,
            'sample_rate': f"{self.sample_rate} Hz",
            'channels': self.num_channels,
            'resolution': "1mV",
            'voltage_range': "1.8V - 2.5V per cell"
        }
    
    def get_current_readings(self) -> Dict[str, float]:
        """Get current voltage readings with channel names"""
        readings = {}
        voltages = self.state.cell_voltages
        
        for i, voltage in enumerate(voltages):
            if i < len(self.channel_config):
                channel_name = self.channel_config[i]['name']
                readings[channel_name] = voltage
        
        return readings
    
    def get_stack_voltage(self) -> float:
        """Get total stack voltage (sum of all cells)"""
        return sum(self.state.cell_voltages)
    
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
    
    def check_cell_health(self) -> Dict[str, str]:
        """Check health status of each cell"""
        health_report = {}
        voltages = self.state.cell_voltages
        stats = self.get_voltage_statistics()
        avg_voltage = stats['avg']
        
        for i, voltage in enumerate(voltages):
            if i < len(self.channel_config):
                config = self.channel_config[i]
                cell_name = config['name']
                
                # Check voltage against thresholds
                if voltage < config['min_voltage']:
                    health_report[cell_name] = "Critical Low"
                elif voltage > config['max_voltage']:
                    health_report[cell_name] = "Critical High"
                elif abs(voltage - avg_voltage) > 0.1:  # >100mV deviation from average
                    health_report[cell_name] = "Warning"
                elif abs(voltage - config['nominal_voltage']) <= 0.05:  # Within 50mV of nominal
                    health_report[cell_name] = "Excellent"
                else:
                    health_report[cell_name] = "Good"
        
        return health_report
    
    def get_unbalanced_cells(self, threshold: float = 0.05) -> List[str]:
        """Get list of cells with voltage significantly different from average"""
        stats = self.get_voltage_statistics()
        avg_voltage = stats['avg']
        voltages = self.state.cell_voltages
        
        unbalanced = []
        
        for i, voltage in enumerate(voltages):
            if abs(voltage - avg_voltage) > threshold:
                cell_name = self.channel_config[i]['name']
                unbalanced.append(cell_name)
        
        return unbalanced 
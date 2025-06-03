"""
BGA244 gas analyzer service for AWE test rig
Simulates 3 BGA units measuring gas concentrations (H2, O2, N2, other)
"""

import time
import threading
import random
from typing import Dict, Any, List
from core.state import get_global_state


class BGA244Service:
    """Service for BGA244 gas analyzer units"""
    
    def __init__(self):
        self.connected = False
        self.polling = False
        self.poll_thread = None
        self.state = get_global_state()
        
        # BGA244 configuration
        self.device_name = "BGA244"
        self.sample_rate = 0.2  # 0.2 Hz (5 second intervals - gas analysis is slow)
        self.num_units = 3
        
        # BGA unit configuration for electrolyzer monitoring
        self.unit_config = {
            0: {
                "name": "hydrogen_side", 
                "location": "H2 outlet",
                "expected": {"H2": 95.0, "O2": 2.0, "N2": 2.5, "other": 0.5}
            },
            1: {
                "name": "oxygen_side", 
                "location": "O2 outlet", 
                "expected": {"H2": 1.0, "O2": 96.0, "N2": 2.5, "other": 0.5}
            },
            2: {
                "name": "mixed_gas", 
                "location": "Mixed stream",
                "expected": {"H2": 45.0, "O2": 48.0, "N2": 6.0, "other": 1.0}
            }
        }
        
    def connect(self) -> bool:
        """Connect to BGA244 gas analyzers"""
        print("⚗️  Connecting to BGA244 gas analyzers...")
        try:
            # Simulate connection process
            time.sleep(1.0)  # Gas analyzers take longer to initialize
            
            print(f"   → Detecting {self.num_units} BGA244 units")
            print(f"   → Configuring gas analysis channels:")
            
            for unit_id, config in self.unit_config.items():
                print(f"     • Unit {unit_id+1}: {config['name']} ({config['location']})")
            
            print(f"   → Setting sample rate: {self.sample_rate} Hz (gas analysis)")
            print(f"   → Calibrating analyzers...")
            time.sleep(0.5)
            
            self.connected = True
            self.state.update_connection_status('bga244', True)
            
            print("✅ BGA244 analyzers connected successfully")
            return True
            
        except Exception as e:
            print(f"❌ Failed to connect to BGA244: {e}")
            self.connected = False
            self.state.update_connection_status('bga244', False)
            return False
    
    def disconnect(self):
        """Disconnect from BGA244 analyzers"""
        print("⚗️  Disconnecting from BGA244 analyzers...")
        
        # Stop polling first
        if self.polling:
            print("⚠️  BGA244 polling already stopped" if not self.polling else "")
            self.stop_polling()
        
        self.connected = False
        self.state.update_connection_status('bga244', False)
        
        print("✅ BGA244 analyzers disconnected")
    
    def start_polling(self) -> bool:
        """Start polling gas analysis data"""
        if not self.connected:
            print("❌ Cannot start polling - BGA244 not connected")
            return False
        
        if self.polling:
            print("⚠️  BGA244 polling already running")
            return True
        
        print(f"⚗️  Starting BGA244 polling at {self.sample_rate} Hz...")
        
        self.polling = True
        self.poll_thread = threading.Thread(target=self._poll_data, daemon=True)
        self.poll_thread.start()
        
        print("✅ BGA244 polling started")
        return True
    
    def stop_polling(self):
        """Stop polling gas analysis data"""
        if not self.polling:
            return
        
        print("⚗️  Stopping BGA244 polling...")
        self.polling = False
        
        if self.poll_thread and self.poll_thread.is_alive():
            self.poll_thread.join(timeout=3.0)
        
        print("✅ BGA244 polling stopped")
    
    def _poll_data(self):
        """Polling thread function"""
        while self.polling and self.connected:
            try:
                # Generate realistic gas concentration readings
                gas_readings = self._generate_gas_data()
                
                # Update global state
                self.state.update_sensor_values(gas_concentrations=gas_readings)
                
                # Sleep for sample rate (gas analysis is slow)
                time.sleep(1.0 / self.sample_rate)
                
            except Exception as e:
                print(f"❌ BGA244 polling error: {e}")
                break
    
    def _generate_gas_data(self) -> List[Dict[str, float]]:
        """Generate realistic gas concentration readings for all units"""
        gas_readings = []
        
        for unit_id in range(self.num_units):
            config = self.unit_config[unit_id]
            expected = config["expected"]
            
            # Generate readings with realistic variation around expected values
            readings = {}
            
            for gas, expected_pct in expected.items():
                # Add realistic variation based on gas type and concentration
                if gas == "H2":
                    # Hydrogen can vary more during operation
                    variation = random.uniform(-2.0, 2.0)
                elif gas == "O2":
                    # Oxygen also varies during operation
                    variation = random.uniform(-1.5, 1.5)
                elif gas == "N2":
                    # Nitrogen contamination varies less
                    variation = random.uniform(-0.5, 0.5)
                else:  # other gases
                    # Trace gases have small variation
                    variation = random.uniform(-0.2, 0.2)
                
                # Calculate final concentration
                concentration = expected_pct + variation
                
                # Clamp to realistic ranges
                concentration = max(0.0, min(100.0, concentration))
                readings[gas] = round(concentration, 2)
            
            # Normalize to ensure total = 100%
            total = sum(readings.values())
            if total > 0:
                for gas in readings:
                    readings[gas] = round((readings[gas] / total) * 100.0, 2)
            
            gas_readings.append(readings)
        
        return gas_readings
    
    def get_status(self) -> Dict[str, Any]:
        """Get current service status"""
        return {
            'connected': self.connected,
            'polling': self.polling,
            'device': self.device_name,
            'sample_rate': f"{self.sample_rate} Hz",
            'units': self.num_units,
            'unit_config': self.unit_config
        }
    
    def get_current_readings(self) -> Dict[str, Dict[str, float]]:
        """Get current gas readings with unit names"""
        readings = {}
        concentrations = self.state.gas_concentrations
        
        for i, gas_data in enumerate(concentrations):
            if i < len(self.unit_config):
                unit_name = self.unit_config[i]['name']
                readings[unit_name] = gas_data.copy()
        
        return readings
    
    def get_gas_purity(self, unit_id: int, target_gas: str) -> float:
        """Get purity of target gas for a specific unit"""
        if 0 <= unit_id < len(self.state.gas_concentrations):
            concentrations = self.state.gas_concentrations[unit_id]
            return concentrations.get(target_gas, 0.0)
        return 0.0
    
    def check_gas_quality(self) -> Dict[str, str]:
        """Check gas quality for each unit"""
        quality_report = {}
        
        for unit_id, config in self.unit_config.items():
            unit_name = config['name']
            
            if unit_id < len(self.state.gas_concentrations):
                concentrations = self.state.gas_concentrations[unit_id]
                
                # Check quality based on primary gas
                if "hydrogen" in unit_name:
                    h2_purity = concentrations.get('H2', 0.0)
                    if h2_purity >= 99.0:
                        quality_report[unit_name] = "Excellent"
                    elif h2_purity >= 95.0:
                        quality_report[unit_name] = "Good"
                    elif h2_purity >= 90.0:
                        quality_report[unit_name] = "Fair"
                    else:
                        quality_report[unit_name] = "Poor"
                        
                elif "oxygen" in unit_name:
                    o2_purity = concentrations.get('O2', 0.0)
                    if o2_purity >= 99.0:
                        quality_report[unit_name] = "Excellent"
                    elif o2_purity >= 95.0:
                        quality_report[unit_name] = "Good"
                    elif o2_purity >= 90.0:
                        quality_report[unit_name] = "Fair"
                    else:
                        quality_report[unit_name] = "Poor"
                        
                else:  # mixed gas
                    total_primary = concentrations.get('H2', 0.0) + concentrations.get('O2', 0.0)
                    if total_primary >= 95.0:
                        quality_report[unit_name] = "Good"
                    elif total_primary >= 90.0:
                        quality_report[unit_name] = "Fair"
                    else:
                        quality_report[unit_name] = "Poor"
            else:
                quality_report[unit_name] = "No Data"
        
        return quality_report 
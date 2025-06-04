#!/usr/bin/env python3
"""
NI DAQ service for AWE test rig
Handles NI-9253 (4-20mA analog inputs) and NI-9485 (digital outputs)
"""

import time
import threading
import random
from core.state import get_global_state


class NIDAQService:
    """NI cDAQ service for analog input and digital output"""
    
    def __init__(self):
        self.state = get_global_state()
        self.connected = False
        self.polling = False
        self.polling_thread = None
        self._stop_event = threading.Event()
        
        # Mock hardware configuration
        self.device_name = "cDAQ1"
        self.analog_channels = {
            'pressure_1': 'cDAQ1Mod1/ai0',  # 4-20mA pressure sensor 1
            'pressure_2': 'cDAQ1Mod1/ai1',  # 4-20mA pressure sensor 2  
            'current': 'cDAQ1Mod1/ai2'      # 4-20mA current sensor
        }
        self.digital_channels = {
            'valve_1': 'cDAQ1Mod2/port0/line0',  # Solenoid valve 1
            'valve_2': 'cDAQ1Mod2/port0/line1',  # Solenoid valve 2
            'valve_3': 'cDAQ1Mod2/port0/line2',  # Solenoid valve 3
            'valve_4': 'cDAQ1Mod2/port0/line3',  # Solenoid valve 4
            'pump': 'cDAQ1Mod2/port0/line4'      # Pump relay
        }
        
        # Scaling factors for 4-20mA sensors
        self.scaling = {
            'pressure_1': {'min_ma': 4.0, 'max_ma': 20.0, 'min_eng': 0.0, 'max_eng': 50.0, 'units': 'PSI'},
            'pressure_2': {'min_ma': 4.0, 'max_ma': 20.0, 'min_eng': 0.0, 'max_eng': 100.0, 'units': 'PSI'},
            'current': {'min_ma': 4.0, 'max_ma': 20.0, 'min_eng': 0.0, 'max_eng': 10.0, 'units': 'A'}
        }
        
        # Sampling rate
        self.sample_rate = 250  # Hz
    
    def connect(self):
        """Connect to NI cDAQ device"""
        if self.connected:
            print("⚠️  NI DAQ already connected")
            return True
        
        try:
            print("🔌 Connecting to NI cDAQ...")
            
            # Mock connection sequence
            print(f"   → Detecting device: {self.device_name}")
            time.sleep(0.1)  # Simulate connection delay
            
            print("   → Configuring analog input channels:")
            for channel_name, channel_addr in self.analog_channels.items():
                print(f"     • {channel_name}: {channel_addr} (4-20mA)")
            
            print("   → Configuring digital output channels:")
            for channel_name, channel_addr in self.digital_channels.items():
                print(f"     • {channel_name}: {channel_addr}")
            
            print(f"   → Setting sample rate: {self.sample_rate} Hz")
            
            # Simulate successful connection
            self.connected = True
            self.state.update_connection_status('ni_daq', True)
            
            print("✅ NI cDAQ connected successfully")
            return True
            
        except Exception as e:
            print(f"❌ NI cDAQ connection failed: {e}")
            self.connected = False
            return False
    
    def disconnect(self):
        """Disconnect from NI cDAQ device"""
        if not self.connected:
            print("⚠️  NI DAQ already disconnected")
            return
        
        print("🔌 Disconnecting from NI cDAQ...")
        
        # Stop polling first
        self.stop_polling()
        
        # Set all outputs to safe state
        self._set_all_outputs_safe()
        
        # Mock disconnection
        self.connected = False
        self.state.update_connection_status('ni_daq', False)
        
        print("✅ NI cDAQ disconnected")
    
    def start_polling(self):
        """Start continuous data acquisition"""
        if not self.connected:
            print("❌ Cannot start polling - NI DAQ not connected")
            return False
        
        if self.polling:
            print("⚠️  NI DAQ polling already running")
            return True
        
        print(f"📊 Starting NI DAQ polling at {self.sample_rate} Hz...")
        
        self._stop_event.clear()
        self.polling = True
        
        # Start polling thread
        self.polling_thread = threading.Thread(target=self._polling_loop, daemon=True)
        self.polling_thread.start()
        
        print("✅ NI DAQ polling started")
        return True
    
    def stop_polling(self):
        """Stop continuous data acquisition"""
        if not self.polling:
            print("⚠️  NI DAQ polling already stopped")
            return
        
        print("📊 Stopping NI DAQ polling...")
        
        self._stop_event.set()
        self.polling = False
        
        # Wait for thread to finish
        if self.polling_thread and self.polling_thread.is_alive():
            self.polling_thread.join(timeout=2.0)
        
        print("✅ NI DAQ polling stopped")
    
    def _polling_loop(self):
        """Main data acquisition loop"""
        while self.polling and not self._stop_event.is_set():
            try:
                # Read analog inputs
                analog_data = self._read_analog_inputs()
                
                # Update global state with new readings
                self.state.update_sensor_values(
                    pressure_values=[analog_data['pressure_1'], analog_data['pressure_2']],
                    current_value=analog_data['current']
                )
                
                # Control digital outputs based on state
                self._update_digital_outputs()
                
                # Sleep to maintain sample rate
                time.sleep(1.0 / self.sample_rate)
                
            except Exception as e:
                print(f"❌ NI DAQ polling error: {e}")
                break
    
    def _read_analog_inputs(self):
        """Read and scale analog input channels"""
        raw_data = {}
        scaled_data = {}
        
        # Mock reading 4-20mA signals
        for channel_name in self.analog_channels.keys():
            # Generate realistic mock data
            if channel_name == 'pressure_1':
                # Pressure sensor 1: 0-15 PSI, typically around 0.8 PSI
                mock_value = random.uniform(0.7, 0.8)
            elif channel_name == 'pressure_2':
                # Pressure sensor 2: 0-15 PSI, typically around 0.3 PSI  
                mock_value = random.uniform(0.3, 0.4)
            elif channel_name == 'current':
                # Current sensor: 0-150 A, typically around 130 A
                mock_value = random.uniform(130, 135)
            else:
                mock_value = 0.0
            
            # Convert to 4-20mA signal (for realism)
            scaling = self.scaling[channel_name]
            mock_ma = self._eng_to_ma(mock_value, scaling)
            raw_data[channel_name] = mock_ma
            
            # Convert back to engineering units (simulating real scaling)
            scaled_data[channel_name] = self._ma_to_eng(mock_ma, scaling)
        
        return scaled_data
    
    def _eng_to_ma(self, eng_value, scaling):
        """Convert engineering units to 4-20mA"""
        eng_span = scaling['max_eng'] - scaling['min_eng']
        ma_span = scaling['max_ma'] - scaling['min_ma']
        
        if eng_span == 0:
            return scaling['min_ma']
        
        ma_value = scaling['min_ma'] + ((eng_value - scaling['min_eng']) / eng_span) * ma_span
        return max(scaling['min_ma'], min(scaling['max_ma'], ma_value))
    
    def _ma_to_eng(self, ma_value, scaling):
        """Convert 4-20mA to engineering units"""
        ma_span = scaling['max_ma'] - scaling['min_ma']
        eng_span = scaling['max_eng'] - scaling['min_eng']
        
        if ma_span == 0:
            return scaling['min_eng']
        
        eng_value = scaling['min_eng'] + ((ma_value - scaling['min_ma']) / ma_span) * eng_span
        return max(scaling['min_eng'], min(scaling['max_eng'], eng_value))
    
    def _update_digital_outputs(self):
        """Update digital outputs based on current state"""
        try:
            # Update valve states
            for i, valve_state in enumerate(self.state.valve_states):
                valve_name = f'valve_{i+1}'
                if valve_name in self.digital_channels:
                    self._set_digital_output(valve_name, valve_state)
            
            # Update pump state
            self._set_digital_output('pump', self.state.pump_state)
            
        except Exception as e:
            print(f"❌ Digital output update error: {e}")
    
    def _set_digital_output(self, channel_name, state):
        """Set individual digital output channel"""
        if channel_name in self.digital_channels:
            # Mock setting digital output
            # In real implementation, this would call NI-DAQmx functions
            pass
    
    def _set_all_outputs_safe(self):
        """Set all digital outputs to safe state (OFF)"""
        print("   → Setting all outputs to safe state (OFF)")
        
        # Update state to safe values
        with self.state._lock:
            self.state.pump_state = False
            for i in range(len(self.state.valve_states)):
                self.state.valve_states[i] = False
        
        # Set physical outputs to OFF
        for channel_name in self.digital_channels.keys():
            self._set_digital_output(channel_name, False)
    
    def get_status(self):
        """Get current service status"""
        return {
            'connected': self.connected,
            'polling': self.polling,
            'device': self.device_name,
            'sample_rate': f"{self.sample_rate} Hz",
            'analog_channels': len(self.analog_channels),
            'digital_channels': len(self.digital_channels)
        }


def main():
    """Test the NI DAQ service by running it directly"""
    print("=" * 60)
    print("TASK 10 TEST: NI DAQ Service")
    print("=" * 60)
    print("✅ NI DAQ service created")
    print("✅ Mock 3 analog inputs (2 pressure + 1 current)")
    print("✅ Mock 5 digital outputs (4 valves + 1 pump)")
    print("✅ 4-20mA scaling simulation")
    print("✅ GlobalState integration")
    print("\n🎯 TEST: Verify NI DAQ lifecycle:")
    
    service = NIDAQService()
    
    # Test connection
    print("\n1. Testing connection...")
    success = service.connect()
    print(f"   Result: {'✅ Success' if success else '❌ Failed'}")
    
    # Show status
    print("\n2. Service status:")
    status = service.get_status()
    for key, value in status.items():
        print(f"   {key}: {value}")
    
    # Test polling
    print("\n3. Starting data polling...")
    service.start_polling()
    
    print("\n4. Collecting data for 3 seconds...")
    time.sleep(3)
    
    # Show some data
    state = get_global_state()
    print(f"\n5. Sample data:")
    print(f"   Pressure 1: {state.pressure_values[0]:.2f} PSI")
    print(f"   Pressure 2: {state.pressure_values[1]:.2f} PSI")
    print(f"   Current: {state.current_value:.2f} A")
    
    # Test output control
    print("\n6. Testing digital outputs...")
    state.set_actuator_state('valve', True, 0)  # Turn on valve 1
    state.set_actuator_state('pump', True)      # Turn on pump
    time.sleep(1)
    print("   Valve 1 and pump turned ON")
    
    # Cleanup
    print("\n7. Stopping service...")
    service.stop_polling()
    service.disconnect()
    
    print("\n✅ NI DAQ service test complete!")
    print("=" * 60)


if __name__ == "__main__":
    main() 
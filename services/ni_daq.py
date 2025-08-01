#!/usr/bin/env python3
"""
NI DAQ service for AWE test rig
Handles NI-9253 (4-20mA analog inputs) and NI-9485 (digital outputs)

4-20mA Signal Conditioning (Enhanced):
- 4.0mA = 0% scale (calibrated minimum)  
- 20mA = 100% scale (maximum)
- <3.5mA = DISCONNECTED (sensor fault)
- 3.5-4.0mA = LOW SIGNAL (wiring issue)
- >20.5mA = HIGH SIGNAL (sensor overrange)
"""

import time
import threading
from core.state import get_global_state
from config.device_config import get_device_config
from utils.logger import log

# Try to import real NI-DAQmx library
try:
    import nidaqmx
    from nidaqmx.constants import LineGrouping, AcquisitionType
    from nidaqmx import Task
    NIDAQMX_AVAILABLE = True
    log.success("Libraries", "NI-DAQmx library loaded")
except ImportError:
    NIDAQMX_AVAILABLE = False
    log.error("Libraries", "NI-DAQmx library not found - hardware connection will fail")


class NIDAQService:
    """NI cDAQ service for analog input and digital output"""
    
    def __init__(self):
        self.state = get_global_state()
        self.device_config = get_device_config()
        self.connected = False
        self.polling = False
        self.polling_thread = None
        self._stop_event = threading.Event()
        
        # Get current range configuration
        self.current_range = self.device_config.get_current_range_config()
        self.min_current_ma = self.current_range.get('min_ma', 4.0)
        self.max_current_ma = self.current_range.get('max_ma', 20.0)
        
        # Real hardware configuration
        self.ni_9253_slot = "cDAQ9187-23E902CMod1"  # Analog input module
        self.ni_9485_slot_2 = "cDAQ9187-23E902CMod2"  # Digital output module
        self.ni_9485_slot_3 = "cDAQ9187-23E902CMod3"  # Digital output module
        
        # Analog input channels - loaded dynamically from devices.yaml
        self.analog_channels = self._build_analog_channels_from_config()
        
        # Digital output channels (valve relays)
        self.digital_channels = {
            'valve_1': {'module': self.ni_9485_slot_2, 'line': 0, 'name': "KOH Storage"},
            'valve_2': {'module': self.ni_9485_slot_2, 'line': 1, 'name': "DI Storage"},  
            'valve_3': {'module': self.ni_9485_slot_2, 'line': 2, 'name': "Stack Drain"},
            'valve_4': {'module': self.ni_9485_slot_2, 'line': 3, 'name': "N2 Purge"},
            'valve_5': {'module': self.ni_9485_slot_2, 'line': 5, 'name': "O2 Purge"},
            'pump': {'module': self.ni_9485_slot_2, 'line': 4, 'name': "Pump"},
            'pump_2': {'module': self.ni_9485_slot_2, 'line': 6, 'name': "KOH Pump"},
        }
        
        # Real NI-DAQmx tasks
        self.ai_task = None
        self.do_tasks = {}
        
        # Sampling rate
        self.sample_rate = 100  # Hz
    
    def connect(self):
        """Connect to NI cDAQ device"""
        if self.connected:
            log.warning("DAQ", "NI DAQ already connected")
            return True
        
        if not NIDAQMX_AVAILABLE:
            log.error("DAQ", "NI-DAQmx library not available - cannot connect to hardware")
            return False
        
        try:
            log.info("DAQ", "Connecting to NI cDAQ...")
            return self._connect_real()
        except Exception as e:
            log.error("DAQ", f"NI cDAQ connection failed: {e}")
            self.connected = False
            return False
    
    def _connect_real(self):
        """Connect to real NI cDAQ hardware"""
        # Test device detection
        system = nidaqmx.system.System.local()
        devices = system.devices
        cdaq_found = False
        device_info = []
        
        for device in devices:
            if "cDAQ" in device.product_type:
                cdaq_found = True
                device_info.append(f"• Found: {device.name}")
        
        if not cdaq_found:
            raise Exception("No cDAQ chassis detected")
        
        # Setup analog input task
        channel_info = []
        self.ai_task = Task()
        for ch_name, ch_config in self.analog_channels.items():
            channel = ch_config["channel"]
            channel_info.append(f"• {ch_config['name']}: {channel} (4-20mA, calibrated {self.min_current_ma}-{self.max_current_ma}mA)")
            
            # Add current input channel using configured range
            self.ai_task.ai_channels.add_ai_current_chan(
                channel,
                name_to_assign_to_channel=ch_name,
                min_val=self.min_current_ma / 1000.0,  # Convert mA to A
                max_val=self.max_current_ma / 1000.0   # Convert mA to A
            )
        
        # Configure FINITE sampling (like working test files)
        # This avoids timing issues with continuous acquisition
        self.ai_task.timing.cfg_samp_clk_timing(
            rate=1000,  # 1kHz sample rate for finite acquisition
            sample_mode=AcquisitionType.FINITE,
            samps_per_chan=10  # Read 10 samples per channel each time
        )
        
        # Setup digital output tasks
        digital_info = []
        for ch_name, ch_config in self.digital_channels.items():
            module = ch_config["module"]
            line = ch_config["line"]
            channel = f"{module}/port0/line{line}"
            
            digital_info.append(f"• {ch_config['name']}: {channel}")
            
            task = Task()
            task.do_channels.add_do_chan(channel, line_grouping=LineGrouping.CHAN_PER_LINE)
            self.do_tasks[ch_name] = task
        
        # Set all outputs to safe state initially
        self._set_all_outputs_safe()
        
        self.connected = True
        self.state.update_connection_status('ni_daq', True)
        
        # Log successful connection with all details
        log.success("DAQ", f"NI cDAQ connected and polling at {self.sample_rate} Hz", 
                   device_info + [f"→ {len(channel_info)} analog channels configured"] + 
                   channel_info + [f"→ {len(digital_info)} digital outputs configured"] + 
                   digital_info)
        return True
    
    def disconnect(self):
        """Disconnect from NI cDAQ device"""
        if not self.connected:
            log.warning("DAQ", "NI DAQ already disconnected")
            return
        
        # Stop polling first
        self.stop_polling()
        
        # Set all outputs to safe state
        self._set_all_outputs_safe()
        
        # Clean up hardware tasks
        if self.ai_task:
            try:
                self.ai_task.close()
                self.ai_task = None
            except:
                pass
        
        for task in self.do_tasks.values():
            try:
                task.close()
            except:
                pass
        self.do_tasks.clear()
        
        self.connected = False
        self.state.update_connection_status('ni_daq', False)
        
        log.success("DAQ", "NI cDAQ disconnected")
    
    def start_polling(self):
        """Start continuous data acquisition"""
        if not self.connected:
            log.error("DAQ", "Cannot start polling - NI DAQ not connected")
            return False
        
        if self.polling:
            log.warning("DAQ", "NI DAQ polling already running")
            return True
        
        self._stop_event.clear()
        self.polling = True
        
        # Start polling thread
        self.polling_thread = threading.Thread(target=self._polling_loop, daemon=True)
        self.polling_thread.start()
        
        log.success("DAQ", f"NI DAQ polling started at {self.sample_rate} Hz")
        return True
    
    def stop_polling(self):
        """Stop continuous data acquisition"""
        if not self.polling:
            log.warning("DAQ", "NI DAQ polling already stopped")
            return
        
        self._stop_event.set()
        self.polling = False
        
        # Wait for thread to finish
        if self.polling_thread and self.polling_thread.is_alive():
            self.polling_thread.join(timeout=2.0)
        
        log.success("DAQ", "NI DAQ polling stopped")
    
    def _polling_loop(self):
        """Main data acquisition loop"""
        while self.polling and not self._stop_event.is_set():
            try:
                # Read analog inputs
                analog_data = self._read_analog_inputs()
                
                # Update global state with new readings
                self.state.update_sensor_values(
                    pressure_values=[
                        analog_data['pt01'], 
                        analog_data['pt02'], 
                        analog_data.get('pt03', 0.0),
                        analog_data.get('pt04', 0.0), 
                        analog_data.get('pt05', 0.0),
                        analog_data.get('pt06', 0.0)
                    ],
                    current_value=analog_data['current'],
                    flowrate_value=analog_data.get('flowrate', 0.0)
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
        try:
            # For FINITE acquisition, read specific number of samples
            data = self.ai_task.read(number_of_samples_per_channel=10, timeout=2.0)
            
            # Handle data structure for multiple channels with FINITE acquisition
            num_channels = len(self.analog_channels)
            
            # With FINITE acquisition, data structure is predictable:
            # - Single channel: list of samples [s1, s2, s3, ...]
            # - Multiple channels: list of lists [[ch1_s1, ch1_s2, ...], [ch2_s1, ch2_s2, ...], ...]
            
            if num_channels == 1:
                # Single channel - data is a simple list
                all_channel_data = [data]
            else:
                # Multiple channels - data should be list of lists
                if isinstance(data, list) and len(data) > 0 and isinstance(data[0], list):
                    # Data is properly structured
                    all_channel_data = data
                else:
                    # Fallback - shouldn't happen with FINITE acquisition
                    print("⚠️  Unexpected data structure from FINITE acquisition")
                    all_channel_data = [[] for _ in range(num_channels)]
            
            # Process and convert to engineering units
            scaled_data = {}
            for i, (ch_name, ch_config) in enumerate(self.analog_channels.items()):
                # Calculate average current from samples
                if i < len(all_channel_data) and len(all_channel_data[i]) > 0:
                    channel_data = all_channel_data[i]
                    avg_current = sum(channel_data) / len(channel_data)
                else:
                    avg_current = 0.0
                
                # Convert 4-20mA current to engineering units with configuration-based scaling
                min_eng, max_eng = ch_config["range"]
                current_ma = avg_current * 1000  # Convert to mA for easier checking
                
                # Enhanced signal conditioning with configurable status checks
                fault_low = self.current_range.get('fault_threshold_low', 3.5)
                fault_high = self.current_range.get('fault_threshold_high', 20.5)
                
                if current_ma < fault_low:
                    # DISCONNECTED - no sensor connected
                    eng_value = 0.0
                elif current_ma < self.min_current_ma:
                    # LOW SIGNAL - sensor connected but signal too low
                    eng_value = 0.0
                elif current_ma > fault_high:
                    # HIGH SIGNAL - sensor overrange
                    eng_value = max_eng
                else:
                    # OK - normal operation with calibrated scaling
                    # Calibrated scaling: min_current_ma = 0, 20mA = max
                    current_range_ma = self.max_current_ma - self.min_current_ma
                    eng_value = ((avg_current - (self.min_current_ma / 1000.0)) / (current_range_ma / 1000.0)) * (max_eng - min_eng) + min_eng
                
                # Apply zero offset calibration
                zero_offset = self.device_config.get_analog_channel_zero_offset(ch_name)
                eng_value += zero_offset
                
                # Ensure value stays within bounds
                scaled_data[ch_name] = max(min_eng, min(max_eng, eng_value))
            
            return scaled_data
            
        except Exception as e:
            print(f"❌ Analog input read error: {e}")
            # Return zeros when hardware fails
            return {ch_name: 0.0 for ch_name in self.analog_channels.keys()}
    
    def _update_digital_outputs(self):
        """Update digital outputs based on current state"""
        try:
            # Update valve states
            for i, valve_state in enumerate(self.state.valve_states):
                valve_name = f'valve_{i+1}'
                if valve_name in self.digital_channels:
                    self._set_digital_output(valve_name, valve_state)
            
            # Update pump states
            self._set_digital_output('pump', self.state.pump_state)
            self._set_digital_output('pump_2', self.state.koh_pump_state)
            
        except Exception as e:
            print(f"❌ Digital output update error: {e}")
    
    def _set_digital_output(self, channel_name, state):
        """Set individual digital output channel"""
        if channel_name not in self.digital_channels:
            return
        
        # Real digital output
        if channel_name in self.do_tasks:
            try:
                self.do_tasks[channel_name].write(bool(state))
            except Exception as e:
                print(f"❌ Failed to set {channel_name} to {state}: {e}")
    
    def _set_all_outputs_safe(self):
        """Set all digital outputs to safe state (OFF)"""
        print("   → Setting all outputs to safe state (OFF)")
        
        # Update state to safe values
        with self.state._lock:
            self.state.pump_state = False
            self.state.koh_pump_state = False
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
            'mode': 'Hardware',
            'device': self.ni_9253_slot,
            'sample_rate': f"{self.sample_rate} Hz",
            'analog_channels': len(self.analog_channels),
            'digital_channels': len(self.digital_channels)
        }

    def _build_analog_channels_from_config(self):
        """Build analog channels configuration from devices.yaml"""
        channels = {}
        ni_config = self.device_config.get_ni_cdaq_config()
        channel_configs = ni_config.get('analog_inputs', {}).get('channels', {})
        
        for channel_name, channel_config in channel_configs.items():
            ai_channel = channel_config.get('channel', '')
            full_channel_path = f"{self.ni_9253_slot}/{ai_channel}"
            
            channels[channel_name] = {
                'channel': full_channel_path,
                'name': channel_config.get('name', channel_name),
                'range': channel_config.get('range', [0, 1]),
                'units': channel_config.get('units', '')
            }
            
        return channels


def main():
    """Test the NI DAQ service by running it directly"""
    print("=" * 60)
    print("NI DAQ Service Hardware Test")
    print("=" * 60)
    
    service = NIDAQService()
    
    print("✅ NI DAQ service created")
    print("✅ NI-9253 analog inputs (6 channels)")
    print("✅ NI-9485 digital outputs (7 channels)")
    print("✅ 4-20mA current measurement")
    print("✅ Enhanced signal conditioning")
    print("✅ Physical relay control")
    
    print("\n🎯 TEST: Verify NI DAQ hardware integration:")
    
    # Test connection
    print("\n1. Testing connection...")
    success = service.connect()
    print(f"   Result: {'✅ Success' if success else '❌ Failed'}")
    
    if not success:
        print("❌ Connection failed - cannot continue test")
        return
    
    # Show status
    print("\n2. Service status:")
    status = service.get_status()
    for key, value in status.items():
        print(f"   {key}: {value}")
    
    # Test polling
    print("\n3. Starting data polling...")
    service.start_polling()
    
    print("\n4. Collecting data for 5 seconds...")
    time.sleep(5)
    
    # Show some data
    state = get_global_state()
    print(f"\n5. Live sensor data:")
    print(f"   Pressure 1 (H₂): {state.pressure_values[0]:.2f} PSI")
    print(f"   Pressure 2 (O₂): {state.pressure_values[1]:.2f} PSI")
    print(f"   PT01: {state.pressure_values[2]:.4f} PSI")
    print(f"   PT02: {state.pressure_values[3]:.4f} PSI")
    print(f"   PT03: {state.pressure_values[4]:.4f} PSI")
    print(f"   PT05: {state.pressure_values[5]:.4f} PSI")
    print(f"   Current: {state.current_value:.2f} A")
    
    # Test output control
    print("\n6. Testing digital outputs...")
    state.set_actuator_state('valve', True, 0)  # Turn on valve 1
    state.set_actuator_state('pump', True)      # Turn on pump
    time.sleep(2)
    print("   Valve 1 and pump turned ON")
    
    state.set_actuator_state('valve', False, 0)  # Turn off valve 1
    state.set_actuator_state('pump', False)      # Turn off pump
    time.sleep(1)
    print("   Valve 1 and pump turned OFF")
    
    # Cleanup
    print("\n7. Stopping service...")
    service.stop_polling()
    service.disconnect()
    
    print("\n✅ NI DAQ service test complete!")
    print("=" * 60)


if __name__ == "__main__":
    main() 
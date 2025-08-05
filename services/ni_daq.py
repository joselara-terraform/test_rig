#!/usr/bin/env python3
"""
NI DAQ service for AWE test rig
Handles NI-9253 (4-20mA analog inputs) and NI-9485 (digital outputs)
"""

import time
import threading
from core.state import get_global_state
from config.device_config import get_device_config
from utils.logger import log

try:
    import nidaqmx
    from nidaqmx.constants import LineGrouping, AcquisitionType
    NIDAQMX_AVAILABLE = True
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
        
        # Configuration
        self.current_range = self.device_config.get_current_range_config()
        self.sample_rate = 100  # Hz
        
        # Hardware modules
        self.chassis = "cDAQ9187-23E902C"
        self.ai_module = f"{self.chassis}Mod1"
        self.do_module1 = f"{self.chassis}Mod2"
        self.do_module2 = f"{self.chassis}Mod3"
        
        # Tasks (initialized on connect)
        self.ai_task = None
        self.do_tasks = {}
    
    def connect(self):
        """Connect to NI cDAQ hardware"""
        if self.connected:
            return True
        
        if not NIDAQMX_AVAILABLE:
            return False
        
        try:
            # Get NI config first
            ni_config = self.device_config.get_ni_cdaq_config()
            
            # Setup analog inputs
            self._setup_analog_inputs()
            
            # Setup digital outputs  
            self._setup_digital_outputs()
            
            # Initialize safe state
            self._set_all_outputs_safe()
            
            self.connected = True
            self.state.update_connection_status('ni_daq', True)
            
            # Log connection with minimal details
            ai_count = len(self.device_config.get_ni_cdaq_config()['analog_inputs']['channels'])
            do_count = len(self.do_tasks)
            
            log.success("DAQ", f"NI cDAQ connected ({ai_count} AI, {do_count} DO)")
            return True
            
        except Exception as e:
            log.error("DAQ", f"NI cDAQ connection failed: {e}")
            self.disconnect()
            return False
    
    def disconnect(self):
        """Disconnect from NI cDAQ"""
        if not self.connected:
            return
        
        self.stop_polling()
        self._set_all_outputs_safe()
        
        # Close tasks
        if self.ai_task:
            try:
                self.ai_task.close()
            except:
                pass
            self.ai_task = None
        
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
        """Start data acquisition"""
        if not self.connected or self.polling:
            return False
        
        self._stop_event.clear()
        self.polling = True
        self.polling_thread = threading.Thread(target=self._polling_loop, daemon=True)
        self.polling_thread.start()
        
        log.success("DAQ", f"Polling started ({self.sample_rate} Hz)")
        return True
    
    def stop_polling(self):
        """Stop data acquisition"""
        if not self.polling:
            return
        
        self._stop_event.set()
        self.polling = False
        
        if self.polling_thread and self.polling_thread.is_alive():
            self.polling_thread.join(timeout=2.0)
        
        log.success("DAQ", "Polling stopped")
    
    def _setup_analog_inputs(self):
        """Configure analog input channels"""
        self.ai_task = nidaqmx.Task()
        
        # Get channel config from devices.yaml
        self.ai_channels = self.device_config.get_ni_cdaq_config()['analog_inputs']['channels']
        
        # Add each channel to task
        for ch_name, ch_config in self.ai_channels.items():
            channel_path = f"{self.ai_module}/{ch_config['channel']}"
            
            # Add as current channel (4-20mA)
            self.ai_task.ai_channels.add_ai_current_chan(
                channel_path,
                name_to_assign_to_channel=ch_name,
                min_val=self.current_range['min_ma'] / 1000.0,
                max_val=self.current_range['max_ma'] / 1000.0
            )
        
        # Use on-demand sampling (no clock, no buffer)
        # This is simpler and avoids buffer overflow issues
    
    def _setup_digital_outputs(self):
        """Configure digital output channels"""
        # Hardcoded digital outputs mapping (from original code)
        # This matches the known hardware configuration
        digital_channels = {
            'valve_1': {'module': self.do_module1, 'line': 0},
            'valve_2': {'module': self.do_module1, 'line': 1},
            'valve_3': {'module': self.do_module1, 'line': 2},
            'valve_4': {'module': self.do_module1, 'line': 3},
            'valve_5': {'module': self.do_module1, 'line': 5},
            'pump': {'module': self.do_module1, 'line': 4},
            'pump_2': {'module': self.do_module1, 'line': 6}
        }
        
        # Create tasks for each output
        for name, config in digital_channels.items():
            channel = f"{config['module']}/port0/line{config['line']}"
            
            task = nidaqmx.Task()
            task.do_channels.add_do_chan(channel, line_grouping=LineGrouping.CHAN_PER_LINE)
            self.do_tasks[name] = task
    
    def _polling_loop(self):
        """Main data acquisition loop"""
        while self.polling and not self._stop_event.is_set():
            try:
                # Read analog inputs
                analog_data = self._read_analog_inputs()
                
                # Update state
                self.state.update_sensor_values(
                    pressure_values=[
                        analog_data.get('pt01', 0.0),
                        analog_data.get('pt02', 0.0),
                        analog_data.get('pt03', 0.0),
                        analog_data.get('pt04', 0.0),
                        analog_data.get('pt05', 0.0),
                        analog_data.get('pt06', 0.0)
                    ],
                    current_value=analog_data.get('current', 0.0),
                    flowrate_value=analog_data.get('flowrate', 0.0)
                )
                
                # Update digital outputs
                self._update_digital_outputs()
                
                # Sleep for sample rate
                time.sleep(1.0 / self.sample_rate)
                
            except Exception as e:
                log.error("DAQ", f"Polling error: {e}")
                break
    
    def _read_analog_inputs(self):
        """Read and scale analog inputs"""
        try:
            # Read single sample per channel (on-demand)
            raw_data = self.ai_task.read()
            
            # Scale to engineering units
            scaled_data = {}
            channel_names = list(self.ai_channels.keys())
            
            # Ensure raw_data is a list
            if not isinstance(raw_data, list):
                raw_data = [raw_data]
            
            for i, ch_name in enumerate(channel_names):
                ch_config = self.ai_channels[ch_name]
                current_a = raw_data[i] if i < len(raw_data) else 0.0
                current_ma = current_a * 1000
                
                # Check signal validity
                fault_low = self.current_range.get('fault_threshold_low', 3.5)
                fault_high = self.current_range.get('fault_threshold_high', 20.5)
                
                if current_ma < fault_low or current_ma > fault_high:
                    # Sensor fault
                    scaled_data[ch_name] = 0.0
                else:
                    # Scale to engineering units
                    min_ma = self.current_range['min_ma']
                    max_ma = self.current_range['max_ma']
                    min_eng, max_eng = ch_config['range']
                    
                    # Linear scaling with calibrated range
                    normalized = (current_ma - min_ma) / (max_ma - min_ma)
                    eng_value = min_eng + normalized * (max_eng - min_eng)
                    
                    # Apply zero offset
                    offset = self.device_config.get_analog_channel_zero_offset(ch_name)
                    eng_value += offset
                    
                    # Clamp to range
                    scaled_data[ch_name] = max(min_eng, min(max_eng, eng_value))
            
            return scaled_data
            
        except Exception as e:
            log.error("DAQ", f"Read error: {e}")
            return {ch: 0.0 for ch in self.ai_channels.keys()}
    
    def _update_digital_outputs(self):
        """Update digital outputs from state"""
        try:
            # Update valves
            for i, state in enumerate(self.state.valve_states):
                key = f'valve_{i+1}'
                if key in self.do_tasks:
                    self.do_tasks[key].write(bool(state))
            
            # Update pumps
            if 'pump' in self.do_tasks:
                self.do_tasks['pump'].write(bool(self.state.pump_state))
            if 'pump_2' in self.do_tasks:
                self.do_tasks['pump_2'].write(bool(self.state.koh_pump_state))
                
        except Exception as e:
            log.error("DAQ", f"Output update error: {e}")
    
    def _set_all_outputs_safe(self):
        """Set all outputs to OFF"""
        # Update state
        with self.state._lock:
            self.state.pump_state = False
            self.state.koh_pump_state = False
            for i in range(len(self.state.valve_states)):
                self.state.valve_states[i] = False
        
        # Set physical outputs
        for task in self.do_tasks.values():
            try:
                task.write(False)
            except:
                pass
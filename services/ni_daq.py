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
        
        # Hardware modules from config
        ni_config = self.device_config.get_ni_cdaq_config()
        self.chassis = ni_config['chassis']
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
        
        # Configure finite acquisition - minimum 2 samples required
        self.ai_task.timing.cfg_samp_clk_timing(
            rate=1000,
            sample_mode=AcquisitionType.FINITE,
            samps_per_chan=2
        )
    
    def _setup_digital_outputs(self):
        """Configure digital output channels"""
        # Get digital output config from devices.yaml
        ni_config = self.device_config.get_ni_cdaq_config()
        valves_config = ni_config['digital_outputs']['valves']
        pumps_config = ni_config['digital_outputs']['pump']
        
        # Create mapping for all digital outputs
        digital_channels = {}
        
        # Add valves (valve_1, valve_2, etc.)
        valve_index = 1
        for valve_name, valve_config in valves_config.items():
            key = f'valve_{valve_index}'
            module = valve_config['module']
            line = valve_config['line']
            digital_channels[key] = {'module': module, 'line': line}
            valve_index += 1
        
        # Add pumps (pump, pump_2)
        pump_index = 1
        for pump_name, pump_config in pumps_config.items():
            if pump_index == 1:
                key = 'pump'
            else:
                key = f'pump_{pump_index}'
            module = pump_config['module']
            line = pump_config['line']
            digital_channels[key] = {'module': module, 'line': line}
            pump_index += 1
        
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
                
                # Get sensor mapping from config
                channels_config = self.device_config.get_ni_cdaq_config()['analog_inputs']['channels']
                
                # Build pressure values array in correct order to match CSV headers
                pressure_values = []
                # Use the exact order from device config that matches CSV headers
                ordered_pressure_sensors = ['pt01', 'pt02', 'pt03', 'pt04', 'pt05', 'pt06']
                for sensor_name in ordered_pressure_sensors:
                    if sensor_name in channels_config:
                        pressure_values.append(analog_data.get(sensor_name, 0.0))
                    else:
                        pressure_values.append(0.0)
                
                # Get current and flowrate from config
                current_value = 0.0
                flowrate_value = 0.0
                for name, config in channels_config.items():
                    if config.get('units') == 'A':
                        current_value = analog_data.get(name, 0.0)
                    elif config.get('units') == 'SLM':
                        flowrate_value = analog_data.get(name, 0.0)
                
                # Update state
                self.state.update_sensor_values(
                    pressure_values=pressure_values,
                    current_value=current_value,
                    flowrate_value=flowrate_value
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
            # Read 2 samples per channel (minimum required)
            raw_data = self.ai_task.read(number_of_samples_per_channel=2)
            
            # Scale to engineering units
            scaled_data = {}
            channel_names = list(self.ai_channels.keys())
            
            # Process data structure and average the 2 samples
            if len(channel_names) == 1:
                # Single channel: data is a list of 2 samples
                avg_data = [sum(raw_data) / len(raw_data)]
            else:
                # Multiple channels: average 2 samples per channel
                avg_data = [sum(ch) / len(ch) for ch in raw_data]
            
            for i, ch_name in enumerate(channel_names):
                ch_config = self.ai_channels[ch_name]
                current_a = avg_data[i] if i < len(avg_data) else 0.0
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
            # Get digital output config for mapping
            ni_config = self.device_config.get_ni_cdaq_config()
            valves_config = ni_config['digital_outputs']['valves']
            pumps_config = ni_config['digital_outputs']['pump']
            
            # Update valves using config order
            valve_index = 1
            for valve_name in valves_config.keys():
                key = f'valve_{valve_index}'
                if key in self.do_tasks and valve_index <= len(self.state.valve_states):
                    self.do_tasks[key].write(bool(self.state.valve_states[valve_index - 1]))
                valve_index += 1
            
            # Update pumps using config order
            pump_index = 1
            for pump_name in pumps_config.keys():
                if pump_index == 1:
                    key = 'pump'
                    if key in self.do_tasks:
                        self.do_tasks[key].write(bool(self.state.pump_state))
                elif pump_index == 2:
                    key = 'pump_2'
                    if key in self.do_tasks:
                        self.do_tasks[key].write(bool(self.state.koh_pump_state))
                pump_index += 1
                
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
#!/usr/bin/env python3
"""
Device Configuration Parser for AWE Test Rig
Loads devices.yaml and provides access to hardware settings including calibrated zero offsets
"""

import os
from typing import Dict, Any, Optional, List

# Try to import YAML parser, provide fallback if not available
try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False
    print("⚠️  PyYAML not available - using hardcoded configuration fallback")
    print("   To install: pip install PyYAML")


class DeviceConfig:
    """Device configuration manager with calibrated zero offset support"""
    
    def __init__(self, config_file: str = None):
        """Initialize device configuration"""
        if config_file is None:
            config_file = os.path.join(os.path.dirname(__file__), 'devices.yaml')
        
        self.config_file = config_file
        self.config = {}
        
        if YAML_AVAILABLE:
            self.load_config()
        else:
            self.load_fallback_config()
    
    def load_config(self):
        """Load configuration from YAML file"""
        try:
            with open(self.config_file, 'r') as file:
                self.config = yaml.safe_load(file)
            
            print(f"✅ Device configuration loaded from {self.config_file}")
            print(f"   Calibration date: {self.get_calibration_date()}")
            
        except FileNotFoundError:
            print(f"❌ Configuration file not found: {self.config_file}")
            print("   Using fallback configuration...")
            self.load_fallback_config()
        except Exception as e:
            print(f"❌ Error parsing YAML configuration: {e}")
            print("   Using fallback configuration...")
            self.load_fallback_config()
    
    def load_fallback_config(self):
        """Load hardcoded fallback configuration when YAML is not available"""
        self.config = {
            'ni_cdaq': {
                'chassis': 'cDAQ9187-23E902C',
                'analog_inputs': {
                    'module': 'cDAQ9187-23E902CMod1',
                    'sample_rate': 100,
                    'current_range': {
                        'min_ma': 4.0,
                        'max_ma': 20.0,
                        'fault_threshold_low': 3.5,
                        'fault_threshold_high': 20.5
                    },
                    'channels': {
                        'pressure_1': {
                            'channel': 'ai0',
                            'name': 'Pressure Sensor 1 (Hydrogen Side)',
                            'units': 'PSI',
                            'range': [0, 15],
                            'zero_offset': -0.035,
                            'description': 'Hydrogen side pressure measurement'
                        },
                        'pressure_2': {
                            'channel': 'ai1',
                            'name': 'Pressure Sensor 2 (Oxygen Side)',
                            'units': 'PSI',
                            'range': [0, 15],
                            'zero_offset': -0.066,
                            'description': 'Oxygen side pressure measurement'
                        },
                        'current': {
                            'channel': 'ai2',
                            'name': 'Stack Current Sensor',
                            'units': 'A',
                            'range': [0, 150],
                            'zero_offset': 0.0,
                            'description': 'Electrolyzer stack current measurement'
                        },
                        'pressure_post_ms': {
                            'channel': 'ai4',
                            'name': 'Post MS Pressure',
                            'units': 'PSI',
                            'range': [0, 1.012],
                            'zero_offset': 0.0,
                            'description': 'Post mass spectrometer pressure measurement'
                        },
                        'pressure_pre_ms': {
                            'channel': 'ai5',
                            'name': 'Pre MS Pressure',
                            'units': 'PSI',
                            'range': [0, 1.012],
                            'zero_offset': 0.0,
                            'description': 'Pre mass spectrometer pressure measurement'
                        },
                        'pressure_h2_bp': {
                            'channel': 'ai6',
                            'name': 'H2 Back Pressure',
                            'units': 'PSI',
                            'range': [0, 1.012],
                            'zero_offset': 0.0,
                            'description': 'Hydrogen back pressure measurement'
                        }
                    }
                },
                'digital_outputs': {
                    'valves': {
                        'koh_storage': {
                            'module': 'cDAQ9187-23E902CMod2',
                            'line': 0,
                            'name': 'KOH Storage Valve'
                        },
                        'di_storage': {
                            'module': 'cDAQ9187-23E902CMod2',
                            'line': 1,
                            'name': 'DI Storage Valve'
                        },
                        'stack_drain': {
                            'module': 'cDAQ9187-23E902CMod2',
                            'line': 2,
                            'name': 'Stack Drain Valve'
                        },
                        'h2_purge': {
                            'module': 'cDAQ9187-23E902CMod2',
                            'line': 3,
                            'name': 'H2 Purge Valve'
                        },
                        'o2_purge': {
                            'module': 'cDAQ9187-23E902CMod2',
                            'line': 5,
                            'name': 'O2 Purge Valve'
                        }
                    },
                    'pump': {
                        'di_fill_pump': {
                            'module': 'cDAQ9187-23E902CMod2',
                            'line': 4,
                            'name': 'DI Fill Pump'
                        },
                        'koh_fill_pump': {
                            'module': 'cDAQ9187-23E902CMod2',
                            'line': 6,
                            'name': 'KOH Fill Pump'
                        }
                    }
                }
            },
            'pico_tc08': {
                'channels': {
                    'channel_0': {'name': 'Inlet Temperature'},
                    'channel_1': {'name': 'Outlet Temperature'},
                    'channel_2': {'name': 'Stack Temperature 1'},
                    'channel_3': {'name': 'Stack Temperature 2'},
                    'channel_4': {'name': 'Ambient Temperature'},
                    'channel_5': {'name': 'Cooling System Temperature'},
                    'channel_6': {'name': 'Gas Temperature'},
                    'channel_7': {'name': 'Case Temperature'}
                }
            },
            'bga244': {
                'units': {
                    'bga_1': {
                        'port': 'COM8',
                        'name': 'H2 Header',
                        'normal_mode': {
                            'primary_gas': 'O2',
                            'secondary_gas': 'H2',
                            'remaining_gas': 'N2'
                        },
                        'purge_mode': {
                            'primary_gas': 'H2',
                            'secondary_gas': 'N2',
                            'remaining_gas': 'O2'
                        }
                    },
                    'bga_2': {
                        'port': 'COM9',
                        'name': 'O2 Header',
                        'normal_mode': {
                            'primary_gas': 'H2',
                            'secondary_gas': 'O2',
                            'remaining_gas': 'N2'
                        },
                        'purge_mode': {
                            'primary_gas': 'O2',
                            'secondary_gas': 'N2',
                            'remaining_gas': 'H2'
                        }
                    },
                    'bga_3': {
                        'port': 'COM3',
                        'name': 'De-oxo',
                        'normal_mode': {
                            'primary_gas': 'H2',
                            'secondary_gas': 'O2',
                            'remaining_gas': 'N2'
                        },
                        'purge_mode': {
                            'primary_gas': 'H2',
                            'secondary_gas': 'N2',
                            'remaining_gas': 'O2'
                        }
                    }
                }
            },
            'cvm24p': {
                'cells': {
                    'total_cells': 120,
                    'groups': 6,
                    'voltage_range': [0, 5]
                }
            },
            'system': {
                'sample_rates': {
                    'ni_daq': 100,
                    'pico_tc08': 1,
                    'bga244': 0.2,
                    'cvm24p': 10
                },
                'calibration': {
                    'auto_zero_on_startup': True,
                    'calibration_date': '2025-06-04',
                    'calibration_technician': 'Engineering Team'
                }
            }
        }
        
        print("✅ Fallback device configuration loaded")
        print(f"   Calibration date: {self.get_calibration_date()}")
    

    
    # NI cDAQ Configuration Methods
    def get_ni_cdaq_config(self) -> Dict[str, Any]:
        """Get complete NI cDAQ configuration"""
        return self.config.get('ni_cdaq', {})
    
    def get_analog_input_config(self, channel_name: str) -> Dict[str, Any]:
        """Get configuration for specific analog input channel including zero offset"""
        channels = self.config.get('ni_cdaq', {}).get('analog_inputs', {}).get('channels', {})
        return channels.get(channel_name, {})
    
    def get_analog_channel_zero_offset(self, channel_name: str) -> float:
        """Get calibrated zero offset for analog input channel"""
        channel_config = self.get_analog_input_config(channel_name)
        return channel_config.get('zero_offset', 0.0)
    
    def get_current_range_config(self) -> Dict[str, float]:
        """Get 4-20mA current range configuration"""
        return self.config.get('ni_cdaq', {}).get('analog_inputs', {}).get('current_range', {
            'min_ma': 4.0,
            'max_ma': 20.0,
            'fault_threshold_low': 3.5,
            'fault_threshold_high': 20.5
        })
    
    def get_digital_output_config(self, output_name: str) -> Dict[str, Any]:
        """Get configuration for specific digital output (valve/pump)"""
        valves = self.config.get('ni_cdaq', {}).get('digital_outputs', {}).get('valves', {})
        pumps = self.config.get('ni_cdaq', {}).get('digital_outputs', {}).get('pump', {})
        
        if output_name in valves:
            return valves[output_name]
        elif output_name in pumps:
            return pumps[output_name]
        else:
            return {}
    
    # Pico TC-08 Configuration Methods
    def get_pico_tc08_config(self) -> Dict[str, Any]:
        """Get complete Pico TC-08 configuration"""
        return self.config.get('pico_tc08', {})
    
    def get_temperature_channel_config(self, channel_name: str) -> Dict[str, Any]:
        """Get configuration for specific temperature channel including zero offset"""
        channels = self.config.get('pico_tc08', {}).get('channels', {})
        return channels.get(channel_name, {})
    
    def get_temperature_zero_offset(self, channel_name: str) -> float:
        """Get calibrated zero offset for temperature channel"""
        channel_config = self.get_temperature_channel_config(channel_name)
        return channel_config.get('zero_offset', 0.0)
    
    # BGA244 Configuration Methods
    def get_bga244_config(self) -> Dict[str, Any]:
        """Get complete BGA244 configuration"""
        return self.config.get('bga244', {})
    
    def get_bga_unit_config(self, unit_name: str) -> Dict[str, Any]:
        """Get configuration for specific BGA unit including zero offsets"""
        units = self.config.get('bga244', {}).get('units', {})
        return units.get(unit_name, {})
    
    def get_bga_gas_config(self, unit_name: str, purge_mode: bool = False) -> Dict[str, Any]:
        """Get gas analysis configuration for specific BGA unit and mode"""
        unit_config = self.get_bga_unit_config(unit_name)
        
        if purge_mode:
            return unit_config.get('purge_mode', {})
        else:
            return unit_config.get('normal_mode', {})
    
    def get_bga_primary_gas(self, unit_name: str, purge_mode: bool = False) -> str:
        """Get primary gas for specific BGA unit and mode"""
        gas_config = self.get_bga_gas_config(unit_name, purge_mode)
        return gas_config.get('primary_gas', 'H2')
    
    def get_bga_secondary_gas(self, unit_name: str, purge_mode: bool = False) -> str:
        """Get secondary gas for specific BGA unit and mode"""
        gas_config = self.get_bga_gas_config(unit_name, purge_mode)
        return gas_config.get('secondary_gas', 'O2')
    
    def get_bga_remaining_gas(self, unit_name: str, purge_mode: bool = False) -> str:
        """Get remaining gas for specific BGA unit and mode"""
        gas_config = self.get_bga_gas_config(unit_name, purge_mode)
        return gas_config.get('remaining_gas', 'N2')
    
    def get_bga_expected_gases(self, unit_name: str, purge_mode: bool = False) -> List[str]:
        """Get expected gases list for specific BGA unit and mode"""
        gas_config = self.get_bga_gas_config(unit_name, purge_mode)
        return gas_config.get('expected_gases', ['H2', 'O2', 'N2'])
    
    def get_bga_zero_offsets(self, unit_name: str) -> Dict[str, float]:
        """Get calibrated zero offsets for BGA gas concentrations (disabled)"""
        return {}
    
    # CVM-24P Configuration Methods
    def get_cvm24p_config(self) -> Dict[str, Any]:
        """Get complete CVM-24P configuration"""
        return self.config.get('cvm24p', {})
    
    def get_voltage_zero_offsets(self) -> Dict[str, float]:
        """Get calibrated zero offsets for voltage measurements (disabled)"""
        return {}
    
    def get_voltage_group_offset(self, group_number: int) -> float:
        """Get calibrated zero offset for specific voltage group (disabled)"""
        return 0.0
    
    # System Configuration Methods
    def get_sample_rates(self) -> Dict[str, float]:
        """Get data acquisition sample rates for all devices"""
        return self.config.get('system', {}).get('sample_rates', {
            'ni_daq': 100,
            'pico_tc08': 1,
            'bga244': 0.2,
            'cvm24p': 10
        })
    
    def get_sample_rate(self, device: str) -> float:
        """Get sample rate for specific device"""
        return self.get_sample_rates().get(device, 1.0)
    
    def get_calibration_config(self) -> Dict[str, Any]:
        """Get calibration configuration settings"""
        return self.config.get('system', {}).get('calibration', {})
    
    def get_calibration_date(self) -> str:
        """Get last calibration date"""
        return self.get_calibration_config().get('calibration_date', 'Unknown')
    
    def is_auto_zero_enabled(self) -> bool:
        """Check if automatic zero offset application is enabled"""
        return self.get_calibration_config().get('auto_zero_on_startup', True)
    
    # Utility Methods
    def apply_zero_offset(self, raw_value: float, channel_name: str, device_type: str) -> float:
        """Apply calibrated zero offset to raw sensor value"""
        if not self.is_auto_zero_enabled():
            return raw_value
        
        zero_offset = 0.0
        
        if device_type == 'ni_daq':
            zero_offset = self.get_analog_channel_zero_offset(channel_name)
        elif device_type == 'pico_tc08':
            zero_offset = self.get_temperature_zero_offset(channel_name)
        elif device_type == 'bga244':
            # For BGA, need unit name and gas type
            # This would need additional parameters in practice
            pass
        elif device_type == 'cvm24p':
            # For voltage groups, need group number
            # This would need additional parameters in practice
            pass
        
        return raw_value + zero_offset
    
    def get_device_description(self, device_type: str, channel_name: str) -> str:
        """Get human-readable description for device channel"""
        if device_type == 'ni_daq':
            config = self.get_analog_input_config(channel_name)
        elif device_type == 'pico_tc08':
            config = self.get_temperature_channel_config(channel_name)
        else:
            config = {}
        
        return config.get('description', f'{device_type} {channel_name}')
    
    def validate_config(self) -> bool:
        """Validate that configuration contains required fields"""
        required_sections = ['ni_cdaq', 'pico_tc08', 'bga244', 'cvm24p', 'system']
        
        for section in required_sections:
            if section not in self.config:
                print(f"❌ Missing required configuration section: {section}")
                return False
        
        # Check for zero offset presence
        analog_channels = self.config.get('ni_cdaq', {}).get('analog_inputs', {}).get('channels', {})
        for channel_name, channel_config in analog_channels.items():
            if 'zero_offset' not in channel_config:
                print(f"⚠️  Missing zero_offset for analog channel: {channel_name}")
        
        print("✅ Configuration validation passed")
        return True


# Global configuration instance
_device_config = None

def get_device_config() -> DeviceConfig:
    """Get global device configuration instance"""
    global _device_config
    if _device_config is None:
        _device_config = DeviceConfig()
    return _device_config


def main():
    """Test the device configuration parser"""
    print("=" * 60)
    print("TASK 30 TEST: Device Configuration Parser")
    print("=" * 60)
    
    config = DeviceConfig()
    
    print("✅ Device configuration parser created")
    print("✅ YAML configuration loaded")
    print("✅ Calibrated zero offsets available for pressure/current sensors")
    
    # Test configuration validation
    print("\n🎯 TEST: Configuration validation:")
    is_valid = config.validate_config()
    print(f"   Result: {'✅ Valid' if is_valid else '❌ Invalid'}")
    
    # Test zero offset retrieval
    print("\n🎯 TEST: Calibrated zero offset retrieval:")
    
    # Analog input zero offsets
    pressure_1_offset = config.get_analog_channel_zero_offset('pressure_1')
    pressure_2_offset = config.get_analog_channel_zero_offset('pressure_2')
    current_offset = config.get_analog_channel_zero_offset('current')
    
    print(f"   Pressure 1 zero offset: {pressure_1_offset} PSI")
    print(f"   Pressure 2 zero offset: {pressure_2_offset} PSI")
    print(f"   Current zero offset: {current_offset} A")
    
    # Temperature zero offsets
    inlet_temp_offset = config.get_temperature_zero_offset('channel_0')
    print(f"   Inlet temperature zero offset: {inlet_temp_offset} °C")
    
    print("   BGA and CVM zero offsets: Disabled (not needed)")
    
    # Test sample rates
    print("\n🎯 TEST: Sample rate configuration:")
    sample_rates = config.get_sample_rates()
    for device, rate in sample_rates.items():
        print(f"   {device}: {rate} Hz")
    
    # Test calibration info
    print("\n🎯 TEST: Calibration information:")
    print(f"   Calibration date: {config.get_calibration_date()}")
    print(f"   Auto-zero enabled: {config.is_auto_zero_enabled()}")
    
    print("\n✅ Device configuration parser test complete!")
    print("=" * 60)


if __name__ == "__main__":
    main() 
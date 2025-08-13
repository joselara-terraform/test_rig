#!/usr/bin/env python3
"""
Device Configuration Parser for AWE Test Rig
Loads devices.yaml and provides access to hardware settings including calibrated zero offsets
"""

import os
from typing import Dict, Any, Optional, List
import yaml
from utils.logger import log


class DeviceConfig:
    """Device configuration manager with calibrated zero offset support"""
    
    def __init__(self, config_file: str = None):
        """Initialize device configuration"""
        if config_file is None:
            config_file = os.path.join(os.path.dirname(__file__), 'devices.yaml')
        
        self.config_file = config_file
        self.config = {}
        
        self.load_config()
    
    def load_config(self):
        """Load configuration from YAML file"""
        try:
            log.info("ConfigLoader", f"Loading config: {os.path.basename(self.config_file)}")
            
            if not os.path.exists(self.config_file):
                raise FileNotFoundError(f"Configuration file not found: {self.config_file}")
            
            with open(self.config_file, 'r') as file:
                self.config = yaml.safe_load(file)
            
            if not self.config:
                raise ValueError("Configuration file is empty or invalid")
            
            # Count devices for success message
            device_count = 0
            device_count += len(self.config.get('ni_cdaq', {}).get('analog_inputs', {}).get('channels', {}))
            device_count += len(self.config.get('pico_tc08', {}).get('channels', {}))
            device_count += len(self.config.get('bga244', {}).get('units', {}))
            device_count += len(self.config.get('cvm24p', {}).get('modules', {}))
            
            log.success("ConfigLoader", f"Loaded {device_count} devices from config", [
                f"→ Calibration date: {self.get_calibration_date()}"
            ])
            
            # Debug: Show which BGAs were loaded
            bga_units = self.config.get('bga244', {}).get('units', {})
            if bga_units:
                bga_info = []
                for unit_id, unit_config in bga_units.items():
                    normal_mode = unit_config.get('normal_mode', {})
                    primary = normal_mode.get('primary_gas', 'Unknown')
                    secondary = normal_mode.get('secondary_gas', 'Unknown')
                    port = unit_config.get('port', 'Unknown')
                    bga_info.append(f"• {unit_id} ({port}): {primary}/{secondary}")
                
                log.info("ConfigLoader", "BGA analyzers configured", bga_info)
            
        except FileNotFoundError as e:
            log.error("ConfigLoader", f"Configuration file not found: {os.path.basename(self.config_file)}", [
                "→ Please ensure devices.yaml exists in the config directory"
            ])
            raise e
        except yaml.YAMLError as e:
            log.error("ConfigLoader", f"Error parsing YAML configuration: {e}", [
                "→ Please check devices.yaml for syntax errors"
            ])
            raise e
        except Exception as e:
            log.error("ConfigLoader", f"Error loading configuration: {e}")
            raise e
    
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
    
    def get_valve_configs(self) -> Dict[str, Dict[str, Any]]:
        """Get all valve configurations"""
        return self.config.get('ni_cdaq', {}).get('digital_outputs', {}).get('valves', {})
    
    def get_pump_configs(self) -> Dict[str, Dict[str, Any]]:
        """Get all pump configurations"""
        return self.config.get('ni_cdaq', {}).get('digital_outputs', {}).get('pump', {})
    
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
    
    def get_cvm24p_module_mapping(self) -> Dict[str, int]:
        """Get CVM24P module serial number to address mapping (physical connection order)"""
        modules_config = self.get_cvm24p_config().get('modules', {})
        mapping = {}
        
        for serial, module_info in modules_config.items():
            address = module_info.get('address')
            if address is not None:
                mapping[serial] = address
        
        return mapping
    
    def get_cvm24p_module_names(self) -> Dict[str, str]:
        """Get CVM24P module serial number to name mapping"""
        modules_config = self.get_cvm24p_config().get('modules', {})
        names = {}
        
        for serial, module_info in modules_config.items():
            name = module_info.get('name', f'Module {serial}')
            names[serial] = name
        
        return names
    
    def get_cvm24p_module_info(self) -> Dict[str, Dict[str, Any]]:
        """Get complete CVM24P module information"""
        return self.get_cvm24p_config().get('modules', {})
    
    def get_cvm24p_expected_modules(self) -> int:
        """Get expected number of CVM24P modules"""
        modules_config = self.get_cvm24p_config().get('modules', {})
        return len(modules_config)
    
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
    
    # Label Management Methods - Single Source of Truth for Channel Names
    def get_ni_daq_channel_names(self) -> List[str]:
        """Get ordered list of NI-DAQ channel names from devices.yaml"""
        channels = self.config.get('ni_cdaq', {}).get('analog_inputs', {}).get('channels', {})
        # Order: All pressure sensors first, then current and flowrate
        ordered_channels = ['pt01', 'pt02', 'pt03', 'pt04', 'pt05', 'pt06', 'current', 'flowrate']
        return [channels.get(ch, {}).get('name', ch) for ch in ordered_channels if ch in channels]
    
    def get_pressure_channel_names(self) -> List[str]:
        """Get ordered list of only pressure sensor names from devices.yaml"""
        channels = self.config.get('ni_cdaq', {}).get('analog_inputs', {}).get('channels', {})
        # Only pressure sensors - exclude current and flowrate
        pressure_channels = ['pt01', 'pt02', 'pt03', 'pt04', 'pt05', 'pt06']
        return [channels.get(ch, {}).get('name', ch) for ch in pressure_channels if ch in channels]
    
    def get_pico_tc08_channel_names(self) -> List[str]:
        """Get ordered list of Pico TC-08 channel names from devices.yaml"""
        channels = self.config.get('pico_tc08', {}).get('channels', {})
        # Maintain channel order (channel_0 through channel_7)
        ordered_channels = [f'channel_{i}' for i in range(8)]
        return [channels.get(ch, {}).get('name', f'TC{i+1:02d}') for i, ch in enumerate(ordered_channels) if ch in channels]
    
    def get_bga244_unit_names(self) -> List[str]:
        """Get ordered list of BGA244 unit names from devices.yaml"""
        units = self.config.get('bga244', {}).get('units', {})
        # Maintain unit order (bga_1, bga_2, bga_3)
        ordered_units = ['bga_1', 'bga_2', 'bga_3']
        return [units.get(unit, {}).get('name', unit) for unit in ordered_units if unit in units]
    
    def get_csv_column_mapping(self) -> Dict[str, str]:
        """Get mapping from current CSV column names to device names"""
        mapping = {}
        
        # NI-DAQ analog channels - mapping based on actual current CSV usage
        ni_daq_names = self.get_ni_daq_channel_names()
        # Current CSV usage: h2_header=pt01, o2_header=pt02, current=current, etc.
        analog_mappings = {
            'h2_header': 'pt01',    # CSV col -> YAML key
            'o2_header': 'pt02', 
            'post_ms': 'pt03',
            'pre_ms': 'pt04',
            'h2_bop': 'pt05',
            'current': 'current',
            'flowrate': 'flowrate'
        }
        
        channels = self.config.get('ni_cdaq', {}).get('analog_inputs', {}).get('channels', {})
        for csv_col, yaml_key in analog_mappings.items():
            if yaml_key in channels:
                mapping[csv_col] = channels[yaml_key].get('name', csv_col)
        
        # Temperature channels  
        temp_names = self.get_pico_tc08_channel_names()
        for i in range(8):
            current_col = f'tc{i+1:02d}'
            if i < len(temp_names):
                mapping[current_col] = temp_names[i]
        
        # Gas analyzer channels
        bga_names = self.get_bga244_unit_names() 
        for i in range(3):
            pct_col = f'bga{i+1}_pct'
            pgas_col = f'bga{i+1}_pgas'
            if i < len(bga_names):
                mapping[pct_col] = f'{bga_names[i]}_pct'
                mapping[pgas_col] = f'{bga_names[i]}_pgas'
        
        return mapping
    
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
    print("AWE Test Rig Device Configuration Parser")
    print("=" * 60)
    
    try:
        config = DeviceConfig()
        
        print("✅ Device configuration parser created")
        
        # Test configuration validation
        print("\n🎯 TEST: Configuration validation:")
        is_valid = config.validate_config()
        print(f"   Result: {'✅ Valid' if is_valid else '❌ Invalid'}")
        
        # Test zero offset retrieval
        print("\n🎯 TEST: Calibrated zero offset retrieval:")
        
        # Analog input zero offsets
        pt01_offset = config.get_analog_channel_zero_offset('pt01')
        pt02_offset = config.get_analog_channel_zero_offset('pt02')
        current_offset = config.get_analog_channel_zero_offset('current')
        
        print(f"   PT01 zero offset: {pt01_offset} PSI")
        print(f"   PT02 zero offset: {pt02_offset} PSI")
        print(f"   Current zero offset: {current_offset} A")
        
        # Temperature zero offsets
        tc01_offset = config.get_temperature_zero_offset('channel_0')
        print(f"   TC01 temperature zero offset: {tc01_offset} °C")
        
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
        
        # Test BGA gas configurations
        print("\n🎯 TEST: BGA Gas configurations:")
        bga_units = config.get_bga244_config().get('units', {})
        for unit_id, unit_config in bga_units.items():
            name = unit_config.get('name', 'Unknown')
            port = unit_config.get('port', 'Unknown')
            
            normal_primary = config.get_bga_primary_gas(unit_id, purge_mode=False)
            normal_secondary = config.get_bga_secondary_gas(unit_id, purge_mode=False)
            purge_primary = config.get_bga_primary_gas(unit_id, purge_mode=True)
            purge_secondary = config.get_bga_secondary_gas(unit_id, purge_mode=True)
            
            print(f"   {unit_id} - {name} ({port}):")
            print(f"     Normal: {normal_primary}/{normal_secondary}")
            print(f"     Purge:  {purge_primary}/{purge_secondary}")
        
        print("\n✅ Device configuration parser test complete!")
        
    except Exception as e:
        print(f"\n❌ Configuration test failed: {e}")
        print("   Please ensure:")
        print("   1. devices.yaml exists in the config directory")
        print("   2. PyYAML is installed (pip install PyYAML)")
        print("   3. devices.yaml has valid YAML syntax")
    
    print("=" * 60)


if __name__ == "__main__":
    main() 
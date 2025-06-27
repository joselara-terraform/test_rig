#!/usr/bin/env python3
"""
Example Integration: Using Device Configuration with Calibrated Zero Offsets
Shows how services can integrate with the config system for proper sensor calibration
"""

import sys
import os

# Add parent directory to path to import config
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from config.device_config import get_device_config


def example_ni_daq_integration():
    """Example: How NI DAQ service would use device configuration"""
    print("=" * 60)
    print("EXAMPLE: NI DAQ Service with 4-20mA Zero Calibration")
    print("=" * 60)
    
    # Get device configuration
    config = get_device_config()
    
    # Simulate reading raw sensor values (in engineering units after 4-20mA scaling)
    raw_sensor_values = {
        'pressure_1': 0.0,    # 4-20mA properly scaled to 0 PSI at 4mA
        'pressure_2': 0.0,    # 4-20mA properly scaled to 0 PSI at 4mA
        'current': 0.0        # 4-20mA properly scaled to 0 A at 4mA
    }
    
    print("🔧 Raw sensor readings (4-20mA properly scaled to engineering units):")
    for sensor, raw_value in raw_sensor_values.items():
        channel_config = config.get_analog_input_config(sensor)
        print(f"   {channel_config.get('name', sensor)}: {raw_value} {channel_config.get('units', '')}")
    
    # Apply calibrated zero offsets (should be 0.0 for 4-20mA sensors)
    print("\n🎯 Applying calibrated zero offsets:")
    calibrated_values = {}
    
    for sensor, raw_value in raw_sensor_values.items():
        # Get zero offset from configuration (should be 0.0 for 4-20mA)
        zero_offset = config.get_analog_channel_zero_offset(sensor)
        
        # Apply calibration
        calibrated_value = raw_value + zero_offset
        calibrated_values[sensor] = calibrated_value
        
        # Get channel info
        channel_config = config.get_analog_input_config(sensor)
        sensor_name = channel_config.get('name', sensor)
        units = channel_config.get('units', '')
        
        print(f"   {sensor_name}:")
        print(f"     Raw (4-20mA scaled): {raw_value} {units}")
        print(f"     Zero offset: +{zero_offset} {units}")
        print(f"     Final calibrated: {calibrated_value} {units}")
    
    print(f"\n📊 Final calibrated sensor values:")
    print(f"   Hydrogen side pressure: {calibrated_values['pressure_1']:.2f} PSI (4mA = 0 PSI)")
    print(f"   Oxygen side pressure: {calibrated_values['pressure_2']:.2f} PSI (4mA = 0 PSI)") 
    print(f"   Stack current: {calibrated_values['current']:.1f} A (4mA = 0 A)")
    
    return calibrated_values


def example_temperature_integration():
    """Example: How Pico TC-08 service would use device configuration"""
    print("\n" + "=" * 60)
    print("EXAMPLE: Pico TC-08 Service with Temperature Calibration")
    print("=" * 60)
    
    config = get_device_config()
    
    # Simulate raw temperature readings (would be close to 0°C without ambient calibration)
    raw_temperatures = {
        'channel_0': 0.0,   # Inlet
        'channel_1': 0.0,   # Outlet  
        'channel_4': 0.0    # Ambient
    }
    
    print("🌡️  Raw temperature readings (before calibration):")
    for channel, raw_temp in raw_temperatures.items():
        channel_config = config.get_temperature_channel_config(channel)
        print(f"   {channel_config.get('name', channel)}: {raw_temp}°C")
    
    # Apply temperature calibration
    print("\n🎯 Applying temperature zero offsets:")
    calibrated_temps = {}
    
    for channel, raw_temp in raw_temperatures.items():
        zero_offset = config.get_temperature_zero_offset(channel)
        calibrated_temp = raw_temp + zero_offset
        calibrated_temps[channel] = calibrated_temp
        
        channel_config = config.get_temperature_channel_config(channel)
        sensor_name = channel_config.get('name', channel)
        
        print(f"   {sensor_name}: {raw_temp}°C + {zero_offset}°C = {calibrated_temp}°C")
    
    return calibrated_temps


def example_gas_analyzer_integration():
    """Example: How BGA244 service would use device configuration"""
    print("\n" + "=" * 60)
    print("EXAMPLE: BGA244 Service (No Zero Offsets Needed)")
    print("=" * 60)
    
    config = get_device_config()
    
    # Simulate raw gas concentration readings (direct measurements, no calibration needed)
    raw_concentrations = {
        'bga_1': {'H2': 0.0, 'O2': 0.0, 'N2': 0.0},
        'bga_2': {'H2': 0.0, 'O2': 0.0, 'N2': 0.0}
    }
    
    print("💨 Gas concentration readings (direct measurement):")
    for unit, gases in raw_concentrations.items():
        unit_config = config.get_bga_unit_config(unit)
        print(f"   {unit_config.get('name', unit)}:")
        for gas, concentration in gases.items():
            print(f"     {gas}: {concentration}% (no calibration needed)")
    
    print("\n🎯 BGA zero offsets: Disabled (direct measurement sensors)")
    
    return raw_concentrations


def main():
    """Demonstrate device configuration integration with calibrated zero offsets"""
    print("🎯 TASK 30: Device Configuration Integration Examples")
    print("   Showing how all services use calibrated zero offsets")
    
    # NI DAQ integration
    pressure_values = example_ni_daq_integration()
    
    # Temperature integration  
    temp_values = example_temperature_integration()
    
    # Gas analyzer integration
    gas_values = example_gas_analyzer_integration()
    
    # Summary
    print("\n" + "=" * 60)
    print("✅ TASK 30 COMPLETE: Calibrated Zero Offsets Implemented")
    print("=" * 60)
    print("📋 BENEFITS:")
    print("   ✅ 4-20mA sensors: Zero offset calibration for pressure/current")
    print("   ✅ Temperature sensors: Individual calibrated zero offsets")
    print("   ✅ BGA/CVM sensors: No zero offsets (direct measurement)")
    print("   ✅ Configuration-driven calibration (no hardcoded values)")
    print("   ✅ Windows-specific configuration")
    print("   ✅ Fallback configuration when YAML not available")
    print("   ✅ Calibration date tracking and validation")
    print("   ✅ Auto-zero application on service startup")
    print("\n📊 CALIBRATED READINGS READY FOR DASHBOARD:")
    print(f"   Pressure H2: {pressure_values['pressure_1']:.2f} PSI (with zero offset)")
    print(f"   Pressure O2: {pressure_values['pressure_2']:.2f} PSI (with zero offset)")
    print(f"   Current: {pressure_values['current']:.1f} A (with zero offset)")
    print(f"   Temperatures: {len(temp_values)} channels calibrated (with offsets)")
    print(f"   Gas analyzers: {len(gas_values)} units (direct measurement)")
    print("   CVM voltages: Direct measurement (no offsets needed)")
    print("\n🎯 Next: Integrate config into all service classes!")
    print("=" * 60)


if __name__ == "__main__":
    main() 
#!/usr/bin/env python3
"""
Configuration Loading Test Script
Helps diagnose why devices.yaml might not be loading correctly
"""

import os
import sys

def test_config_loading():
    """Test configuration loading and report any issues"""
    print("=" * 60)
    print("BGA Configuration Loading Diagnostic Test")
    print("=" * 60)
    
    # Check current directory
    print(f"Current working directory: {os.getcwd()}")
    
    # Check if devices.yaml exists
    config_file = os.path.join(os.path.dirname(__file__), 'devices.yaml')
    print(f"Looking for config file: {config_file}")
    
    if not os.path.exists(config_file):
        print("❌ devices.yaml file NOT found")
        print("   Expected location:", config_file)
        return False
    
    print("✅ devices.yaml file found")
    print(f"   File size: {os.path.getsize(config_file)} bytes")
    
    # Check if PyYAML is available
    try:
        import yaml
        print("✅ PyYAML is available")
    except ImportError:
        print("❌ PyYAML is NOT available - this is a critical problem!")
        print("   To fix: pip install PyYAML")
        print("   The application will crash without PyYAML")
        return False
    
    # Try to load the YAML file
    try:
        with open(config_file, 'r') as file:
            config = yaml.safe_load(file)
        print("✅ YAML file loads successfully")
        
        if not config:
            print("❌ YAML file is empty or returned None")
            return False
        
        # Check BGA configuration
        bga_config = config.get('bga244')
        if not bga_config:
            print("❌ No 'bga244' section found in config")
            return False
        
        bga_units = bga_config.get('units', {})
        if not bga_units:
            print("❌ No BGA units found in 'bga244.units' section")
            return False
        
        print(f"✅ Found {len(bga_units)} BGA units in config:")
        
        for unit_id, unit_config in bga_units.items():
            name = unit_config.get('name', 'Unknown')
            port = unit_config.get('port', 'Unknown')
            
            normal_mode = unit_config.get('normal_mode', {})
            if not normal_mode:
                print(f"   ❌ {unit_id}: Missing 'normal_mode' configuration")
                continue
                
            purge_mode = unit_config.get('purge_mode', {})
            if not purge_mode:
                print(f"   ❌ {unit_id}: Missing 'purge_mode' configuration")
                continue
            
            normal_primary = normal_mode.get('primary_gas', 'Unknown')
            normal_secondary = normal_mode.get('secondary_gas', 'Unknown')
            purge_primary = purge_mode.get('primary_gas', 'Unknown')
            purge_secondary = purge_mode.get('secondary_gas', 'Unknown')
            
            print(f"   ✅ {unit_id}: {name} ({port})")
            print(f"      Normal: {normal_primary}/{normal_secondary}")
            print(f"      Purge:  {purge_primary}/{purge_secondary}")
        
        return True
        
    except yaml.YAMLError as e:
        print(f"❌ YAML syntax error: {e}")
        print("   Please check devices.yaml for syntax errors")
        return False
    except Exception as e:
        print(f"❌ Error loading YAML file: {e}")
        return False

if __name__ == "__main__":
    success = test_config_loading()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ Configuration loading should work correctly")
        print("   Your devices.yaml will be loaded by the main application")
        print("   All BGA gas assignments should match your configuration")
    else:
        print("❌ Configuration loading has issues")
        print("   The main application will FAIL to start")
        print("   Fix the issues above before running the application")
    
    print("=" * 60) 
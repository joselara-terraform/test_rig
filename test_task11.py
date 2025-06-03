#!/usr/bin/env python3
"""
Test file for Task 11: Pico TC-08 thermocouple service
Run with: python3 test_task11.py
"""

import time
from services.pico_tc08 import PicoTC08Service
from core.state import get_global_state


def test_pico_creation():
    """Test that Pico TC-08 service can be created"""
    print("Testing Pico TC-08 service creation...")
    try:
        service = PicoTC08Service()
        print("✅ PASS: Pico TC-08 service created successfully")
        return True, service
    except Exception as e:
        print(f"❌ FAIL: Could not create Pico TC-08 service: {e}")
        return False, None


def test_pico_connection(service):
    """Test Pico TC-08 connection"""
    print("\nTesting Pico TC-08 connection...")
    try:
        success = service.connect()
        if success and service.connected:
            print("✅ PASS: Pico TC-08 connected successfully")
            print("✅ PASS: Connection status updated")
            return True
        else:
            print("❌ FAIL: Pico TC-08 connection failed")
            return False
    except Exception as e:
        print(f"❌ FAIL: Connection error: {e}")
        return False


def test_pico_polling(service):
    """Test Pico TC-08 data polling"""
    print("\nTesting Pico TC-08 data polling...")
    state = get_global_state()
    
    try:
        # Record initial values
        initial_temps = state.temperature_values.copy()
        
        # Start polling
        success = service.start_polling()
        if not success:
            print("❌ FAIL: Could not start polling")
            return False
        
        print("✅ PASS: Polling started successfully")
        
        # Wait for data updates (thermocouples are slower, 1 Hz)
        time.sleep(2.5)
        
        # Check if data has been updated
        new_temps = state.temperature_values
        
        # Verify we have 8 temperature readings
        if len(new_temps) != 8:
            print(f"❌ FAIL: Expected 8 temperature readings, got {len(new_temps)}")
            return False
        
        print("✅ PASS: 8 temperature channels available")
        
        # Verify temperature values are realistic for each channel
        channel_tests = [
            ("Inlet temp", new_temps[0], 20.0, 30.0),
            ("Outlet temp", new_temps[1], 35.0, 50.0),
            ("Stack temp 1", new_temps[2], 40.0, 80.0),
            ("Stack temp 2", new_temps[3], 40.0, 80.0),
            ("Ambient temp", new_temps[4], 20.0, 25.0),
            ("Cooling temp", new_temps[5], 15.0, 35.0),
            ("Gas temp", new_temps[6], 25.0, 45.0),
            ("Case temp", new_temps[7], 30.0, 50.0)
        ]
        
        for name, temp, min_val, max_val in channel_tests:
            if min_val <= temp <= max_val:
                print(f"✅ PASS: {name} realistic ({temp:.2f}°C)")
            else:
                print(f"❌ FAIL: {name} unrealistic ({temp:.2f}°C, expected {min_val}-{max_val}°C)")
                return False
        
        # Check that values are changing (not static)
        if new_temps != initial_temps:
            print("✅ PASS: Temperature values are updating")
        else:
            print("❌ FAIL: Temperature values appear static")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ FAIL: Polling error: {e}")
        return False


def test_pico_state_integration(service):
    """Test GlobalState integration"""
    print("\nTesting GlobalState integration...")
    state = get_global_state()
    
    try:
        # Check connection status in state
        if state.connections['pico_tc08']:
            print("✅ PASS: GlobalState connection status correct")
        else:
            print("❌ FAIL: GlobalState connection status incorrect")
            return False
        
        # Test current readings method
        readings = service.get_current_readings()
        
        expected_channels = ['inlet_temp', 'outlet_temp', 'stack_temp_1', 'stack_temp_2', 
                           'ambient_temp', 'cooling_temp', 'gas_temp', 'case_temp']
        
        for channel in expected_channels:
            if channel in readings:
                temp = readings[channel]
                print(f"✅ PASS: {channel} reading available ({temp:.2f}°C)")
            else:
                print(f"❌ FAIL: {channel} reading missing")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ FAIL: State integration error: {e}")
        return False


def test_pico_configuration(service):
    """Test Pico TC-08 configuration"""
    print("\nTesting Pico TC-08 configuration...")
    
    try:
        # Check channel configuration
        if len(service.channel_config) == 8:
            print("✅ PASS: 8 thermocouple channels configured")
        else:
            print(f"❌ FAIL: Expected 8 channels, found {len(service.channel_config)}")
            return False
        
        # Check sample rate is appropriate for thermocouples
        if service.sample_rate == 1.0:
            print("✅ PASS: Sample rate appropriate for thermocouples (1 Hz)")
        else:
            print(f"❌ FAIL: Unexpected sample rate: {service.sample_rate} Hz")
            return False
        
        # Check thermocouple types
        for ch, config in service.channel_config.items():
            if config['type'] == 'K':
                print(f"✅ PASS: Channel {ch} configured as Type K thermocouple")
            else:
                print(f"❌ FAIL: Channel {ch} unexpected type: {config['type']}")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ FAIL: Configuration error: {e}")
        return False


def test_service_status(service):
    """Test service status reporting"""
    print("\nTesting service status...")
    try:
        status = service.get_status()
        
        required_keys = ['connected', 'polling', 'device', 'sample_rate', 'channels', 'channel_config']
        for key in required_keys:
            if key in status:
                print(f"✅ PASS: Status contains {key}: {status[key]}")
            else:
                print(f"❌ FAIL: Status missing {key}")
                return False
        
        # Check device name
        if status['device'] == 'TC-08':
            print("✅ PASS: Correct device identification")
        else:
            print(f"❌ FAIL: Incorrect device name: {status['device']}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ FAIL: Status error: {e}")
        return False


def test_pico_disconnection(service):
    """Test Pico TC-08 disconnection"""
    print("\nTesting Pico TC-08 disconnection...")
    state = get_global_state()
    
    try:
        # Stop polling
        service.stop_polling()
        if not service.polling:
            print("✅ PASS: Polling stopped successfully")
        else:
            print("❌ FAIL: Polling did not stop")
            return False
        
        # Disconnect
        service.disconnect()
        if not service.connected:
            print("✅ PASS: Service disconnected successfully")
        else:
            print("❌ FAIL: Service did not disconnect")
            return False
        
        # Check state was updated
        if not state.connections['pico_tc08']:
            print("✅ PASS: GlobalState connection status updated")
        else:
            print("❌ FAIL: GlobalState connection status not updated")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ FAIL: Disconnection error: {e}")
        return False


def test_temperature_ranges(service):
    """Test temperature range realism"""
    print("\nTesting temperature range realism...")
    
    try:
        # Connect and start polling for extended test
        service.connect()
        service.start_polling()
        
        # Collect multiple readings
        readings_over_time = []
        for i in range(5):
            time.sleep(1.2)  # Slightly longer than sample rate
            temps = service.state.temperature_values.copy()
            readings_over_time.append(temps)
        
        # Analyze temperature stability and variation
        for ch in range(8):
            temps_for_channel = [reading[ch] for reading in readings_over_time]
            min_temp = min(temps_for_channel)
            max_temp = max(temps_for_channel)
            variation = max_temp - min_temp
            
            channel_name = service.channel_config[ch]['name']
            
            # Check variation is reasonable (not too stable, not too wild)
            if 0.1 <= variation <= 5.0:
                print(f"✅ PASS: {channel_name} shows realistic variation ({variation:.2f}°C)")
            else:
                print(f"❌ FAIL: {channel_name} unrealistic variation ({variation:.2f}°C)")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ FAIL: Temperature range test error: {e}")
        return False


def main():
    """Run all tests"""
    print("=" * 60)
    print("TASK 11 TEST: Pico TC-08 Service")
    print("=" * 60)
    
    all_tests_passed = True
    service = None
    
    # Test 1: Service creation
    success, service = test_pico_creation()
    all_tests_passed &= success
    
    if not service:
        print("\n💥 Cannot continue tests - service creation failed")
        return
    
    # Test 2: Configuration
    success = test_pico_configuration(service)
    all_tests_passed &= success
    
    # Test 3: Connection
    success = test_pico_connection(service)
    all_tests_passed &= success
    
    if success:
        # Test 4: Polling
        success = test_pico_polling(service)
        all_tests_passed &= success
        
        # Test 5: State integration
        success = test_pico_state_integration(service)
        all_tests_passed &= success
        
        # Test 6: Status reporting
        success = test_service_status(service)
        all_tests_passed &= success
        
        # Test 7: Temperature ranges
        success = test_temperature_ranges(service)
        all_tests_passed &= success
        
        # Test 8: Disconnection
        success = test_pico_disconnection(service)
        all_tests_passed &= success
    
    print("\n" + "=" * 60)
    if all_tests_passed:
        print("🎉 ALL TESTS PASSED - Task 11 Complete!")
        print("✅ Pico TC-08 service fully functional")
        print("✅ 8 thermocouple channels (Type K)")
        print("✅ 1 Hz polling with realistic temperatures")
        print("✅ Electrolyzer-specific temperature monitoring")
        print("✅ GlobalState integration working")
        print("✅ Temperature ranges and variation realistic")
    else:
        print("💥 SOME TESTS FAILED - Task 11 Needs Fixes")
    print("=" * 60)


if __name__ == "__main__":
    main() 
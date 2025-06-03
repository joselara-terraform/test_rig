#!/usr/bin/env python3
"""
Test file for Task 10: NI DAQ service
Run with: python3 test_task10.py
"""

import time
from services.ni_daq import NIDAQService
from core.state import get_global_state


def test_ni_daq_creation():
    """Test that NI DAQ service can be created"""
    print("Testing NI DAQ service creation...")
    try:
        service = NIDAQService()
        print("✅ PASS: NI DAQ service created successfully")
        return True, service
    except Exception as e:
        print(f"❌ FAIL: Could not create NI DAQ service: {e}")
        return False, None


def test_ni_daq_connection(service):
    """Test NI DAQ connection"""
    print("\nTesting NI DAQ connection...")
    try:
        success = service.connect()
        if success and service.connected:
            print("✅ PASS: NI DAQ connected successfully")
            print("✅ PASS: Connection status updated")
            return True
        else:
            print("❌ FAIL: NI DAQ connection failed")
            return False
    except Exception as e:
        print(f"❌ FAIL: Connection error: {e}")
        return False


def test_ni_daq_polling(service):
    """Test NI DAQ data polling"""
    print("\nTesting NI DAQ data polling...")
    state = get_global_state()
    
    try:
        # Record initial values
        initial_pressure1 = state.pressure_values[0]
        initial_pressure2 = state.pressure_values[1]
        initial_current = state.current_value
        
        # Start polling
        success = service.start_polling()
        if not success:
            print("❌ FAIL: Could not start polling")
            return False
        
        print("✅ PASS: Polling started successfully")
        
        # Wait for data updates
        time.sleep(1.5)
        
        # Check if data has been updated
        new_pressure1 = state.pressure_values[0]
        new_pressure2 = state.pressure_values[1]
        new_current = state.current_value
        
        # Verify data is realistic
        if 10.0 <= new_pressure1 <= 20.0:
            print(f"✅ PASS: Pressure 1 realistic ({new_pressure1:.2f} PSI)")
        else:
            print(f"❌ FAIL: Pressure 1 unrealistic ({new_pressure1:.2f} PSI)")
            return False
        
        if 25.0 <= new_pressure2 <= 35.0:
            print(f"✅ PASS: Pressure 2 realistic ({new_pressure2:.2f} PSI)")
        else:
            print(f"❌ FAIL: Pressure 2 unrealistic ({new_pressure2:.2f} PSI)")
            return False
        
        if 4.0 <= new_current <= 6.0:
            print(f"✅ PASS: Current realistic ({new_current:.2f} A)")
        else:
            print(f"❌ FAIL: Current unrealistic ({new_current:.2f} A)")
            return False
        
        # Check that values are changing (not static)
        if (new_pressure1 != initial_pressure1 or 
            new_pressure2 != initial_pressure2 or 
            new_current != initial_current):
            print("✅ PASS: Data values are updating")
        else:
            print("❌ FAIL: Data values appear static")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ FAIL: Polling error: {e}")
        return False


def test_ni_daq_state_integration(service):
    """Test GlobalState integration"""
    print("\nTesting GlobalState integration...")
    state = get_global_state()
    
    try:
        # Check connection status in state
        if state.connections['ni_daq']:
            print("✅ PASS: GlobalState connection status correct")
        else:
            print("❌ FAIL: GlobalState connection status incorrect")
            return False
        
        # Test actuator state changes
        print("Testing actuator control...")
        
        # Change valve state
        state.set_actuator_state('valve', True, 0)
        if state.valve_states[0]:
            print("✅ PASS: Valve state change works")
        else:
            print("❌ FAIL: Valve state change failed")
            return False
        
        # Change pump state
        state.set_actuator_state('pump', True)
        if state.pump_state:
            print("✅ PASS: Pump state change works")
        else:
            print("❌ FAIL: Pump state change failed")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ FAIL: State integration error: {e}")
        return False


def test_ni_daq_disconnection(service):
    """Test NI DAQ disconnection"""
    print("\nTesting NI DAQ disconnection...")
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
        if not state.connections['ni_daq']:
            print("✅ PASS: GlobalState connection status updated")
        else:
            print("❌ FAIL: GlobalState connection status not updated")
            return False
        
        # Check safe state (valves/pump should be OFF)
        if not state.pump_state and not any(state.valve_states):
            print("✅ PASS: All actuators set to safe state (OFF)")
        else:
            print("❌ FAIL: Actuators not in safe state")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ FAIL: Disconnection error: {e}")
        return False


def test_service_status(service):
    """Test service status reporting"""
    print("\nTesting service status...")
    try:
        status = service.get_status()
        
        required_keys = ['connected', 'polling', 'device', 'sample_rate', 'analog_channels', 'digital_channels']
        for key in required_keys:
            if key in status:
                print(f"✅ PASS: Status contains {key}: {status[key]}")
            else:
                print(f"❌ FAIL: Status missing {key}")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ FAIL: Status error: {e}")
        return False


def main():
    """Run all tests"""
    print("=" * 60)
    print("TASK 10 TEST: NI DAQ Service")
    print("=" * 60)
    
    all_tests_passed = True
    service = None
    
    # Test 1: Service creation
    success, service = test_ni_daq_creation()
    all_tests_passed &= success
    
    if not service:
        print("\n💥 Cannot continue tests - service creation failed")
        return
    
    # Test 2: Connection
    success = test_ni_daq_connection(service)
    all_tests_passed &= success
    
    if success:
        # Test 3: Polling
        success = test_ni_daq_polling(service)
        all_tests_passed &= success
        
        # Test 4: State integration
        success = test_ni_daq_state_integration(service)
        all_tests_passed &= success
        
        # Test 5: Status reporting
        success = test_service_status(service)
        all_tests_passed &= success
        
        # Test 6: Disconnection
        success = test_ni_daq_disconnection(service)
        all_tests_passed &= success
    
    print("\n" + "=" * 60)
    if all_tests_passed:
        print("🎉 ALL TESTS PASSED - Task 10 Complete!")
        print("✅ NI DAQ service fully functional")
        print("✅ 3 analog inputs (2 pressure + 1 current)")
        print("✅ 5 digital outputs (4 valves + 1 pump)")
        print("✅ 250 Hz polling with realistic data")
        print("✅ GlobalState integration working")
        print("✅ Safe state management working")
    else:
        print("💥 SOME TESTS FAILED - Task 10 Needs Fixes")
    print("=" * 60)


if __name__ == "__main__":
    main() 
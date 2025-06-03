#!/usr/bin/env python3
"""
Test file for Task 3: GlobalState singleton
Run with: python3 test_task3.py
"""

from core.state import get_global_state


def test_singleton_pattern():
    """Test that get_global_state returns the same instance"""
    print("Testing singleton pattern...")
    s1 = get_global_state()
    s2 = get_global_state()
    
    if s1 is s2:
        print("✅ PASS: Singleton returns same instance")
    else:
        print("❌ FAIL: Singleton returns different instances")
        return False
    return True


def test_initial_state():
    """Test initial state values"""
    print("\nTesting initial state values...")
    state = get_global_state()
    
    tests = [
        (state.test_running == False, "test_running is False"),
        (state.test_paused == False, "test_paused is False"),
        (state.emergency_stop == False, "emergency_stop is False"),
        (state.timer_value == 0.0, "timer_value is 0.0"),
        (len(state.pressure_values) == 2, "2 pressure sensors"),
        (len(state.temperature_values) == 8, "8 temperature sensors"),
        (len(state.cell_voltages) == 24, "24 cell voltages"),
        (len(state.valve_states) == 4, "4 valve states"),
        (state.pump_state == False, "pump_state is False"),
        (len(state.connections) == 4, "4 device connections"),
        ('ni_daq' in state.connections, "ni_daq in connections"),
        ('pico_tc08' in state.connections, "pico_tc08 in connections"),
        ('bga244' in state.connections, "bga244 in connections"),
        ('cvm24p' in state.connections, "cvm24p in connections"),
    ]
    
    all_passed = True
    for test_result, description in tests:
        if test_result:
            print(f"✅ PASS: {description}")
        else:
            print(f"❌ FAIL: {description}")
            all_passed = False
    
    return all_passed


def test_state_updates():
    """Test state update methods"""
    print("\nTesting state update methods...")
    state = get_global_state()
    
    # Test connection update
    state.update_connection_status('ni_daq', True)
    test1 = state.connections['ni_daq'] == True
    
    # Test actuator updates
    state.set_actuator_state('pump', True)
    test2 = state.pump_state == True
    
    state.set_actuator_state('valve', True, 0)
    test3 = state.valve_states[0] == True
    
    # Test sensor updates
    state.update_sensor_values(current_value=5.5, timer_value=10.0)
    test4 = state.current_value == 5.5
    test5 = state.timer_value == 10.0
    
    tests = [
        (test1, "Connection status update"),
        (test2, "Pump state update"),
        (test3, "Valve state update"),
        (test4, "Current value update"),
        (test5, "Timer value update"),
    ]
    
    all_passed = True
    for test_result, description in tests:
        if test_result:
            print(f"✅ PASS: {description}")
        else:
            print(f"❌ FAIL: {description}")
            all_passed = False
    
    return all_passed


def main():
    """Run all tests"""
    print("=" * 50)
    print("TASK 3 TEST: GlobalState Singleton")
    print("=" * 50)
    
    all_tests_passed = True
    
    all_tests_passed &= test_singleton_pattern()
    all_tests_passed &= test_initial_state()
    all_tests_passed &= test_state_updates()
    
    print("\n" + "=" * 50)
    if all_tests_passed:
        print("🎉 ALL TESTS PASSED - Task 3 Complete!")
    else:
        print("💥 SOME TESTS FAILED - Task 3 Needs Fixes")
    print("=" * 50)


if __name__ == "__main__":
    main() 
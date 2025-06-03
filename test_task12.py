#!/usr/bin/env python3
"""
Test file for Task 12: BGA244 gas analyzer service
Run with: python3 test_task12.py
"""

import time
from services.bga244 import BGA244Service
from core.state import get_global_state


def test_bga_creation():
    """Test that BGA244 service can be created"""
    print("Testing BGA244 service creation...")
    try:
        service = BGA244Service()
        print("✅ PASS: BGA244 service created successfully")
        return True, service
    except Exception as e:
        print(f"❌ FAIL: Could not create BGA244 service: {e}")
        return False, None


def test_bga_connection(service):
    """Test BGA244 connection"""
    print("\nTesting BGA244 connection...")
    try:
        success = service.connect()
        if success and service.connected:
            print("✅ PASS: BGA244 connected successfully")
            print("✅ PASS: Connection status updated")
            return True
        else:
            print("❌ FAIL: BGA244 connection failed")
            return False
    except Exception as e:
        print(f"❌ FAIL: Connection error: {e}")
        return False


def test_bga_configuration(service):
    """Test BGA244 configuration"""
    print("\nTesting BGA244 configuration...")
    
    try:
        # Check number of units
        if service.num_units == 3:
            print("✅ PASS: 3 BGA analyzer units configured")
        else:
            print(f"❌ FAIL: Expected 3 units, found {service.num_units}")
            return False
        
        # Check sample rate is appropriate for gas analysis
        if service.sample_rate == 0.2:
            print("✅ PASS: Sample rate appropriate for gas analysis (0.2 Hz)")
        else:
            print(f"❌ FAIL: Unexpected sample rate: {service.sample_rate} Hz")
            return False
        
        # Check unit configuration
        expected_units = ['hydrogen_side', 'oxygen_side', 'mixed_gas']
        for unit_id, config in service.unit_config.items():
            unit_name = config['name']
            if unit_name in expected_units:
                print(f"✅ PASS: Unit {unit_id+1} configured as {unit_name}")
            else:
                print(f"❌ FAIL: Unit {unit_id+1} unexpected name: {unit_name}")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ FAIL: Configuration error: {e}")
        return False


def test_bga_polling(service):
    """Test BGA244 data polling"""
    print("\nTesting BGA244 data polling...")
    state = get_global_state()
    
    try:
        # Record initial values
        initial_concentrations = [unit.copy() for unit in state.gas_concentrations]
        
        # Start polling
        success = service.start_polling()
        if not success:
            print("❌ FAIL: Could not start polling")
            return False
        
        print("✅ PASS: Polling started successfully")
        
        # Wait for data updates (gas analysis is slow, 0.2 Hz = 5 seconds)
        time.sleep(7.0)
        
        # Check if data has been updated
        new_concentrations = state.gas_concentrations
        
        # Verify we have 3 gas analyzer readings
        if len(new_concentrations) != 3:
            print(f"❌ FAIL: Expected 3 gas analyzer readings, got {len(new_concentrations)}")
            return False
        
        print("✅ PASS: 3 gas analyzer units reporting")
        
        # Verify gas composition for each unit
        unit_tests = [
            ("Hydrogen side", new_concentrations[0], "H2", 90.0, 99.0),
            ("Oxygen side", new_concentrations[1], "O2", 90.0, 99.0),
            ("Mixed gas", new_concentrations[2], None, 80.0, 100.0)  # Combined H2+O2
        ]
        
        for name, concentrations, primary_gas, min_val, max_val in unit_tests:
            # Check that all gas percentages sum to ~100%
            total = sum(concentrations.values())
            if 99.0 <= total <= 101.0:
                print(f"✅ PASS: {name} total composition valid ({total:.2f}%)")
            else:
                print(f"❌ FAIL: {name} total composition invalid ({total:.2f}%)")
                return False
            
            # Check primary gas concentration
            if primary_gas:
                primary_conc = concentrations.get(primary_gas, 0.0)
                if min_val <= primary_conc <= max_val:
                    print(f"✅ PASS: {name} {primary_gas} realistic ({primary_conc:.2f}%)")
                else:
                    print(f"❌ FAIL: {name} {primary_gas} unrealistic ({primary_conc:.2f}%)")
                    return False
            else:
                # Mixed gas - check combined H2+O2
                combined = concentrations.get('H2', 0.0) + concentrations.get('O2', 0.0)
                if min_val <= combined <= max_val:
                    print(f"✅ PASS: {name} H2+O2 combined realistic ({combined:.2f}%)")
                else:
                    print(f"❌ FAIL: {name} H2+O2 combined unrealistic ({combined:.2f}%)")
                    return False
        
        # Check that values are changing (not static)
        if new_concentrations != initial_concentrations:
            print("✅ PASS: Gas concentration values are updating")
        else:
            print("❌ FAIL: Gas concentration values appear static")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ FAIL: Polling error: {e}")
        return False


def test_bga_state_integration(service):
    """Test GlobalState integration"""
    print("\nTesting GlobalState integration...")
    state = get_global_state()
    
    try:
        # Check connection status in state
        if state.connections['bga244']:
            print("✅ PASS: GlobalState connection status correct")
        else:
            print("❌ FAIL: GlobalState connection status incorrect")
            return False
        
        # Test current readings method
        readings = service.get_current_readings()
        
        expected_units = ['hydrogen_side', 'oxygen_side', 'mixed_gas']
        for unit_name in expected_units:
            if unit_name in readings:
                concentrations = readings[unit_name]
                print(f"✅ PASS: {unit_name} readings available:")
                for gas, conc in concentrations.items():
                    print(f"        {gas}: {conc:.2f}%")
            else:
                print(f"❌ FAIL: {unit_name} readings missing")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ FAIL: State integration error: {e}")
        return False


def test_gas_analysis_features(service):
    """Test gas analysis specific features"""
    print("\nTesting gas analysis features...")
    
    try:
        # Test gas purity method
        h2_purity = service.get_gas_purity(0, 'H2')  # Hydrogen side
        o2_purity = service.get_gas_purity(1, 'O2')  # Oxygen side
        
        if 90.0 <= h2_purity <= 99.0:
            print(f"✅ PASS: H2 purity reading realistic ({h2_purity:.2f}%)")
        else:
            print(f"❌ FAIL: H2 purity unrealistic ({h2_purity:.2f}%)")
            return False
        
        if 90.0 <= o2_purity <= 99.0:
            print(f"✅ PASS: O2 purity reading realistic ({o2_purity:.2f}%)")
        else:
            print(f"❌ FAIL: O2 purity unrealistic ({o2_purity:.2f}%)")
            return False
        
        # Test gas quality assessment
        quality_report = service.check_gas_quality()
        
        for unit_name, quality in quality_report.items():
            if quality in ['Excellent', 'Good', 'Fair', 'Poor']:
                print(f"✅ PASS: {unit_name} quality assessment: {quality}")
            else:
                print(f"❌ FAIL: {unit_name} invalid quality: {quality}")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ FAIL: Gas analysis features error: {e}")
        return False


def test_service_status(service):
    """Test service status reporting"""
    print("\nTesting service status...")
    try:
        status = service.get_status()
        
        required_keys = ['connected', 'polling', 'device', 'sample_rate', 'units', 'unit_config']
        for key in required_keys:
            if key in status:
                print(f"✅ PASS: Status contains {key}: {status[key]}")
            else:
                print(f"❌ FAIL: Status missing {key}")
                return False
        
        # Check device name
        if status['device'] == 'BGA244':
            print("✅ PASS: Correct device identification")
        else:
            print(f"❌ FAIL: Incorrect device name: {status['device']}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ FAIL: Status error: {e}")
        return False


def test_gas_composition_stability(service):
    """Test gas composition stability over time"""
    print("\nTesting gas composition stability...")
    
    try:
        # Collect multiple readings
        readings_over_time = []
        for i in range(3):
            time.sleep(6.0)  # Wait for new gas analysis reading
            concentrations = [unit.copy() for unit in service.state.gas_concentrations]
            readings_over_time.append(concentrations)
        
        # Check that readings are realistic and stable
        for unit_id in range(3):
            unit_name = service.unit_config[unit_id]['name']
            
            # Check stability of primary gas
            if "hydrogen" in unit_name:
                h2_values = [reading[unit_id]['H2'] for reading in readings_over_time]
                variation = max(h2_values) - min(h2_values)
                if variation <= 5.0:  # Should be relatively stable
                    print(f"✅ PASS: {unit_name} H2 stability good ({variation:.2f}% variation)")
                else:
                    print(f"❌ FAIL: {unit_name} H2 too variable ({variation:.2f}% variation)")
                    return False
                    
            elif "oxygen" in unit_name:
                o2_values = [reading[unit_id]['O2'] for reading in readings_over_time]
                variation = max(o2_values) - min(o2_values)
                if variation <= 5.0:  # Should be relatively stable
                    print(f"✅ PASS: {unit_name} O2 stability good ({variation:.2f}% variation)")
                else:
                    print(f"❌ FAIL: {unit_name} O2 too variable ({variation:.2f}% variation)")
                    return False
        
        return True
        
    except Exception as e:
        print(f"❌ FAIL: Gas composition stability error: {e}")
        return False


def test_bga_disconnection(service):
    """Test BGA244 disconnection"""
    print("\nTesting BGA244 disconnection...")
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
        if not state.connections['bga244']:
            print("✅ PASS: GlobalState connection status updated")
        else:
            print("❌ FAIL: GlobalState connection status not updated")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ FAIL: Disconnection error: {e}")
        return False


def main():
    """Run all tests"""
    print("=" * 60)
    print("TASK 12 TEST: BGA244 Gas Analyzer Service")
    print("=" * 60)
    
    all_tests_passed = True
    service = None
    
    # Test 1: Service creation
    success, service = test_bga_creation()
    all_tests_passed &= success
    
    if not service:
        print("\n💥 Cannot continue tests - service creation failed")
        return
    
    # Test 2: Configuration
    success = test_bga_configuration(service)
    all_tests_passed &= success
    
    # Test 3: Connection
    success = test_bga_connection(service)
    all_tests_passed &= success
    
    if success:
        # Test 4: Polling
        success = test_bga_polling(service)
        all_tests_passed &= success
        
        # Test 5: State integration
        success = test_bga_state_integration(service)
        all_tests_passed &= success
        
        # Test 6: Gas analysis features
        success = test_gas_analysis_features(service)
        all_tests_passed &= success
        
        # Test 7: Status reporting
        success = test_service_status(service)
        all_tests_passed &= success
        
        # Test 8: Gas composition stability
        success = test_gas_composition_stability(service)
        all_tests_passed &= success
        
        # Test 9: Disconnection
        success = test_bga_disconnection(service)
        all_tests_passed &= success
    
    print("\n" + "=" * 60)
    if all_tests_passed:
        print("🎉 ALL TESTS PASSED - Task 12 Complete!")
        print("✅ BGA244 gas analyzer service fully functional")
        print("✅ 3 gas analyzer units (H2 side, O2 side, mixed)")
        print("✅ 0.2 Hz polling with realistic gas compositions")
        print("✅ Gas purity and quality assessment working")
        print("✅ GlobalState integration working")
        print("✅ Electrolyzer gas monitoring ready")
    else:
        print("💥 SOME TESTS FAILED - Task 12 Needs Fixes")
    print("=" * 60)


if __name__ == "__main__":
    main() 
#!/usr/bin/env python3
"""
Test file for Task 13: CVM-24P cell voltage monitor service
Run with: python3 test_task13.py
"""

import time
from services.cvm24p import CVM24PService
from core.state import get_global_state


def test_cvm_creation():
    """Test that CVM-24P service can be created"""
    print("Testing CVM-24P service creation...")
    try:
        service = CVM24PService()
        print("✅ PASS: CVM-24P service created successfully")
        return True, service
    except Exception as e:
        print(f"❌ FAIL: Could not create CVM-24P service: {e}")
        return False, None


def test_cvm_connection(service):
    """Test CVM-24P connection"""
    print("\nTesting CVM-24P connection...")
    try:
        success = service.connect()
        if success and service.connected:
            print("✅ PASS: CVM-24P connected successfully")
            print("✅ PASS: Connection status updated")
            return True
        else:
            print("❌ FAIL: CVM-24P connection failed")
            return False
    except Exception as e:
        print(f"❌ FAIL: Connection error: {e}")
        return False


def test_cvm_configuration(service):
    """Test CVM-24P configuration"""
    print("\nTesting CVM-24P configuration...")
    
    try:
        # Check number of channels
        if service.num_channels == 24:
            print("✅ PASS: 24 voltage channels configured")
        else:
            print(f"❌ FAIL: Expected 24 channels, found {service.num_channels}")
            return False
        
        # Check sample rate is appropriate for voltage monitoring
        if service.sample_rate == 10.0:
            print("✅ PASS: Sample rate appropriate for voltage monitoring (10 Hz)")
        else:
            print(f"❌ FAIL: Unexpected sample rate: {service.sample_rate} Hz")
            return False
        
        # Check channel configuration
        for i in range(24):
            if i in service.channel_config:
                config = service.channel_config[i]
                expected_name = f"cell_{i+1:02d}"
                if config['name'] == expected_name:
                    print(f"✅ PASS: Channel {i+1} configured as {expected_name}")
                else:
                    print(f"❌ FAIL: Channel {i+1} unexpected name: {config['name']}")
                    return False
            else:
                print(f"❌ FAIL: Channel {i} configuration missing")
                return False
        
        # Check voltage parameters
        sample_config = service.channel_config[0]
        if sample_config['nominal_voltage'] == 2.1:
            print("✅ PASS: Nominal voltage set correctly (2.1V)")
        else:
            print(f"❌ FAIL: Incorrect nominal voltage: {sample_config['nominal_voltage']}V")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ FAIL: Configuration error: {e}")
        return False


def test_cvm_polling(service):
    """Test CVM-24P data polling"""
    print("\nTesting CVM-24P data polling...")
    state = get_global_state()
    
    try:
        # Record initial values
        initial_voltages = state.cell_voltages.copy()
        
        # Start polling
        success = service.start_polling()
        if not success:
            print("❌ FAIL: Could not start polling")
            return False
        
        print("✅ PASS: Polling started successfully")
        
        # Wait for data updates (10 Hz = 0.1s intervals)
        time.sleep(0.5)
        
        # Check if data has been updated
        new_voltages = state.cell_voltages
        
        # Verify we have 24 voltage readings
        if len(new_voltages) != 24:
            print(f"❌ FAIL: Expected 24 voltage readings, got {len(new_voltages)}")
            return False
        
        print("✅ PASS: 24 cell voltage channels reporting")
        
        # Verify voltage values are realistic for each cell
        for i, voltage in enumerate(new_voltages):
            if 1.8 <= voltage <= 2.5:
                print(f"✅ PASS: Cell {i+1:02d} voltage realistic ({voltage:.3f}V)")
            else:
                print(f"❌ FAIL: Cell {i+1:02d} voltage unrealistic ({voltage:.3f}V)")
                return False
            
            # Check resolution (should be 1mV = 0.001V)
            if len(str(voltage).split('.')[-1]) <= 3:
                print(f"✅ PASS: Cell {i+1:02d} voltage resolution appropriate")
            else:
                print(f"❌ FAIL: Cell {i+1:02d} voltage resolution too high")
                return False
        
        # Check that values are changing (not static)
        if new_voltages != initial_voltages:
            print("✅ PASS: Voltage values are updating")
        else:
            print("❌ FAIL: Voltage values appear static")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ FAIL: Polling error: {e}")
        return False


def test_cvm_state_integration(service):
    """Test GlobalState integration"""
    print("\nTesting GlobalState integration...")
    state = get_global_state()
    
    try:
        # Check connection status in state
        if state.connections['cvm24p']:
            print("✅ PASS: GlobalState connection status correct")
        else:
            print("❌ FAIL: GlobalState connection status incorrect")
            return False
        
        # Test current readings method
        readings = service.get_current_readings()
        
        if len(readings) == 24:
            print("✅ PASS: All 24 cell readings available")
        else:
            print(f"❌ FAIL: Expected 24 readings, got {len(readings)}")
            return False
        
        # Check specific cell readings
        for i in range(1, 25):
            cell_name = f"cell_{i:02d}"
            if cell_name in readings:
                voltage = readings[cell_name]
                print(f"✅ PASS: {cell_name} reading available ({voltage:.3f}V)")
            else:
                print(f"❌ FAIL: {cell_name} reading missing")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ FAIL: State integration error: {e}")
        return False


def test_voltage_analysis_features(service):
    """Test voltage analysis specific features"""
    print("\nTesting voltage analysis features...")
    
    try:
        # Test stack voltage calculation
        stack_voltage = service.get_stack_voltage()
        expected_range = (24 * 1.8, 24 * 2.5)  # 43.2V to 60V for 24 cells
        
        if expected_range[0] <= stack_voltage <= expected_range[1]:
            print(f"✅ PASS: Stack voltage realistic ({stack_voltage:.3f}V)")
        else:
            print(f"❌ FAIL: Stack voltage unrealistic ({stack_voltage:.3f}V)")
            return False
        
        # Test voltage statistics
        stats = service.get_voltage_statistics()
        required_stats = ['min', 'max', 'avg', 'total', 'std_dev']
        
        for stat in required_stats:
            if stat in stats:
                value = stats[stat]
                print(f"✅ PASS: {stat} statistic available: {value}")
            else:
                print(f"❌ FAIL: {stat} statistic missing")
                return False
        
        # Check statistical consistency
        if stats['min'] <= stats['avg'] <= stats['max']:
            print("✅ PASS: Voltage statistics consistent")
        else:
            print("❌ FAIL: Voltage statistics inconsistent")
            return False
        
        if abs(stats['total'] - stack_voltage) < 0.001:
            print("✅ PASS: Total voltage matches stack voltage")
        else:
            print("❌ FAIL: Total voltage doesn't match stack voltage")
            return False
        
        # Test cell health check
        health_report = service.check_cell_health()
        
        if len(health_report) == 24:
            print("✅ PASS: Health report covers all 24 cells")
        else:
            print(f"❌ FAIL: Health report missing cells ({len(health_report)}/24)")
            return False
        
        valid_health_states = ['Excellent', 'Good', 'Warning', 'Critical Low', 'Critical High']
        for cell_name, health in health_report.items():
            if health in valid_health_states:
                print(f"✅ PASS: {cell_name} health status valid: {health}")
            else:
                print(f"❌ FAIL: {cell_name} invalid health status: {health}")
                return False
        
        # Test unbalanced cells detection
        unbalanced = service.get_unbalanced_cells(threshold=0.05)
        print(f"✅ PASS: Unbalanced cells detection works ({len(unbalanced)} cells)")
        
        return True
        
    except Exception as e:
        print(f"❌ FAIL: Voltage analysis features error: {e}")
        return False


def test_current_voltage_relationship(service):
    """Test that voltage responds to current changes"""
    print("\nTesting current-voltage relationship...")
    state = get_global_state()
    
    try:
        # Set low current
        state.update_sensor_values(current_value=1.0)
        time.sleep(0.3)  # Wait for polling update
        low_current_voltages = state.cell_voltages.copy()
        
        # Set high current
        state.update_sensor_values(current_value=5.0)
        time.sleep(0.3)  # Wait for polling update
        high_current_voltages = state.cell_voltages.copy()
        
        # Check that higher current results in lower voltages (voltage drop)
        avg_low = sum(low_current_voltages) / len(low_current_voltages)
        avg_high = sum(high_current_voltages) / len(high_current_voltages)
        
        if avg_low > avg_high:
            voltage_drop = avg_low - avg_high
            print(f"✅ PASS: Voltage drop under load ({voltage_drop:.3f}V)")
        else:
            print("❌ FAIL: No voltage drop observed under increased current")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ FAIL: Current-voltage relationship error: {e}")
        return False


def test_service_status(service):
    """Test service status reporting"""
    print("\nTesting service status...")
    try:
        status = service.get_status()
        
        required_keys = ['connected', 'polling', 'device', 'sample_rate', 'channels', 'resolution', 'voltage_range']
        for key in required_keys:
            if key in status:
                print(f"✅ PASS: Status contains {key}: {status[key]}")
            else:
                print(f"❌ FAIL: Status missing {key}")
                return False
        
        # Check device name
        if status['device'] == 'CVM-24P':
            print("✅ PASS: Correct device identification")
        else:
            print(f"❌ FAIL: Incorrect device name: {status['device']}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ FAIL: Status error: {e}")
        return False


def test_cvm_disconnection(service):
    """Test CVM-24P disconnection"""
    print("\nTesting CVM-24P disconnection...")
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
        if not state.connections['cvm24p']:
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
    print("TASK 13 TEST: CVM-24P Cell Voltage Monitor Service")
    print("=" * 60)
    
    all_tests_passed = True
    service = None
    
    # Test 1: Service creation
    success, service = test_cvm_creation()
    all_tests_passed &= success
    
    if not service:
        print("\n💥 Cannot continue tests - service creation failed")
        return
    
    # Test 2: Configuration
    success = test_cvm_configuration(service)
    all_tests_passed &= success
    
    # Test 3: Connection
    success = test_cvm_connection(service)
    all_tests_passed &= success
    
    if success:
        # Test 4: Polling
        success = test_cvm_polling(service)
        all_tests_passed &= success
        
        # Test 5: State integration
        success = test_cvm_state_integration(service)
        all_tests_passed &= success
        
        # Test 6: Voltage analysis features
        success = test_voltage_analysis_features(service)
        all_tests_passed &= success
        
        # Test 7: Current-voltage relationship
        success = test_current_voltage_relationship(service)
        all_tests_passed &= success
        
        # Test 8: Status reporting
        success = test_service_status(service)
        all_tests_passed &= success
        
        # Test 9: Disconnection
        success = test_cvm_disconnection(service)
        all_tests_passed &= success
    
    print("\n" + "=" * 60)
    if all_tests_passed:
        print("🎉 ALL TESTS PASSED - Task 13 Complete!")
        print("✅ CVM-24P cell voltage monitor fully functional")
        print("✅ 24 individual cell voltage measurements")
        print("✅ 10 Hz polling with 1mV resolution")
        print("✅ Voltage statistics and health monitoring")
        print("✅ Current-dependent voltage modeling")
        print("✅ GlobalState integration working")
        print("✅ Electrolyzer cell monitoring ready")
    else:
        print("💥 SOME TESTS FAILED - Task 13 Needs Fixes")
    print("=" * 60)


if __name__ == "__main__":
    main() 
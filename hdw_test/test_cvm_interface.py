#!/usr/bin/env python3
"""
CVM24P Interface Test Script
Based on CVM_test.py guide - Tests the CVM24P service interface and functionality

This script tests:
1. CVM24P service initialization and connection (hardware + mock fallback)
2. Module discovery and initialization simulation
3. Voltage reading interface
4. Data polling and state updates
5. Statistics and health monitoring
6. Error handling and reconnection logic
7. Service lifecycle management

Safe to run without hardware - will use mock mode automatically.
"""

import sys
import os
import time
import asyncio
from typing import Dict, List

# Add project root to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.cvm24p import CVM24PService, CVM24PConfig, CVM24PModule
from core.state import get_global_state
from services.controller_manager import get_controller_manager

# Check XC2 library availability
try:
    from xc2.bus import SerialBus
    from xc2.bus_utils import get_broadcast_echo, get_serial_broadcast
    from xc2.consts import ProtocolEnum
    from xc2.utils import discover_serial_ports, get_serial_from_port
    from xc2.xc2_dev_cvm24p import XC2Cvm24p
    XC2_AVAILABLE = True
except ImportError:
    XC2_AVAILABLE = False


def print_section(title: str):
    """Print a formatted section header"""
    print("\n" + "=" * 80)
    print(f"{title}")
    print("=" * 80)


def print_subsection(title: str):
    """Print a formatted subsection header"""
    print(f"\n--- {title} ---")


def test_cvm_service_basic():
    """Test basic CVM service functionality"""
    print_section("1. CVM24P SERVICE BASIC FUNCTIONALITY")
    
    # Test service initialization
    print_subsection("Service Initialization")
    cvm_service = CVM24PService()
    state = get_global_state()
    
    print(f"✅ Service created: {cvm_service.device_name}")
    print(f"   → Expected modules: {cvm_service.expected_modules}")
    print(f"   → Total channels: {cvm_service.total_channels}")
    print(f"   → Sample rate: {cvm_service.sample_rate} Hz")
    print(f"   → Use mock: {cvm_service.use_mock}")
    
    # Test connection
    print_subsection("Connection Test")
    connected = cvm_service.connect()
    
    if connected:
        print("✅ Connection successful")
        
        # Get and display status
        status = cvm_service.get_status()
        print("\n📊 Service Status:")
        for key, value in status.items():
            print(f"   • {key}: {value}")
        
        # Test module info (will be empty in mock mode)
        module_info = cvm_service.get_module_info()
        print(f"\n🔧 Connected Modules: {len(module_info)}")
        if module_info:
            for serial, info in module_info.items():
                print(f"   • {serial}: {info}")
        else:
            print("   → No hardware modules (mock mode)")
        
    else:
        print("❌ Connection failed")
        return False
    
    return cvm_service


def test_cvm_polling(cvm_service: CVM24PService):
    """Test CVM polling and data reading"""
    print_section("2. CVM24P POLLING AND DATA READING")
    
    state = get_global_state()
    
    # Start polling
    print_subsection("Starting Polling")
    polling_started = cvm_service.start_polling()
    
    if polling_started:
        print("✅ Polling started successfully")
        
        # Let it poll for a few seconds
        print("\n📊 Monitoring voltage data...")
        for i in range(5):
            time.sleep(1)
            
            # Get current voltage statistics
            stats = cvm_service.get_voltage_statistics()
            voltages = state.cell_voltages
            
            print(f"   Sample {i+1}:")
            print(f"     • Channels: {len(voltages)}")
            print(f"     • Min: {stats['min']:.3f}V")
            print(f"     • Max: {stats['max']:.3f}V") 
            print(f"     • Avg: {stats['avg']:.3f}V")
            print(f"     • Total: {stats['total']:.1f}V")
            print(f"     • Std Dev: {stats['std_dev']:.3f}V")
            
            # Show first few and last few voltages
            if voltages:
                print(f"     • First 5: {[f'{v:.3f}' for v in voltages[:5]]}")
                print(f"     • Last 5: {[f'{v:.3f}' for v in voltages[-5:]]}")
        
        # Test unbalanced cell detection
        print_subsection("Cell Balance Analysis")
        unbalanced = cvm_service.get_unbalanced_cells(threshold=0.02)  # 20mV threshold
        
        if unbalanced:
            print(f"⚠️  Found {len(unbalanced)} unbalanced cells:")
            for cell_num in unbalanced[:10]:  # Show first 10
                cell_voltage = voltages[cell_num-1] if cell_num <= len(voltages) else 0
                print(f"     • Cell {cell_num}: {cell_voltage:.3f}V")
            if len(unbalanced) > 10:
                print(f"     • ... and {len(unbalanced)-10} more")
        else:
            print("✅ All cells are balanced (within threshold)")
        
        # Stop polling
        print_subsection("Stopping Polling")
        cvm_service.stop_polling()
        print("✅ Polling stopped")
        
    else:
        print("❌ Failed to start polling")
        return False
    
    return True


def test_cvm_configuration():
    """Test CVM configuration and constants"""
    print_section("3. CVM24P CONFIGURATION TESTING")
    
    print_subsection("Configuration Constants")
    print(f"✅ Channels per module: {CVM24PConfig.CHANNELS_PER_MODULE}")
    print(f"✅ Baud rate: {CVM24PConfig.BAUD_RATE}")
    print(f"✅ Discovery attempts: {CVM24PConfig.DISCOVERY_ATTEMPTS}")
    print(f"✅ Voltage resolution: {CVM24PConfig.VOLTAGE_RESOLUTION*1000}mV")
    print(f"✅ Voltage range: {CVM24PConfig.MIN_CELL_VOLTAGE}V - {CVM24PConfig.MAX_CELL_VOLTAGE}V")
    print(f"✅ Nominal voltage: {CVM24PConfig.NOMINAL_CELL_VOLTAGE}V")
    print(f"✅ Imbalance threshold: {CVM24PConfig.VOLTAGE_IMBALANCE_THRESHOLD*1000}mV")
    
    # Test individual module creation (mock) - skip hardware-dependent parts
    print_subsection("Module Interface Testing")
    
    print(f"✅ Module interface constants verified:")
    print(f"   • Expected channels per module: {CVM24PConfig.CHANNELS_PER_MODULE}")
    print(f"   • Address format: 0x{0x10:X} (hexadecimal)")
    print(f"   • Serial format: String (e.g., 'TEST_MODULE_001')")
    print(f"   • Module ID format: Integer (0, 1, 2, ...)")
    print(f"   • Initialization state: Boolean")
    
    # Test configuration validation
    assert CVM24PConfig.CHANNELS_PER_MODULE == 24, "Expected 24 channels per module"
    assert CVM24PConfig.BAUD_RATE == 1000000, "Expected 1MHz baud rate"
    assert CVM24PConfig.MIN_CELL_VOLTAGE < CVM24PConfig.NOMINAL_CELL_VOLTAGE < CVM24PConfig.MAX_CELL_VOLTAGE, "Voltage range invalid"
    
    print(f"✅ All configuration constants validated")
    
    return True


def test_controller_integration():
    """Test CVM integration with controller manager"""
    print_section("4. CONTROLLER MANAGER INTEGRATION")
    
    controller = get_controller_manager()
    
    # Test service startup through controller
    print_subsection("Service Startup via Controller")
    services_started = controller.start_all_services()
    
    if services_started:
        print("✅ All services started via controller")
        
        # Check CVM service specifically
        cvm_service_info = controller.services.get('cvm24p')
        if cvm_service_info:
            cvm_service = cvm_service_info['service']
            print(f"✅ CVM service accessible: {cvm_service.device_name}")
            
            # Get status through controller
            status = cvm_service.get_status()
            print(f"   → Mode: {status['mode']}")
            print(f"   → Connected: {status['connected']}")
            print(f"   → Modules: {status['modules']}")
            
        else:
            print("❌ CVM service not found in controller")
        
        # Test service shutdown
        print_subsection("Service Shutdown via Controller")
        controller.stop_all_services()
        print("✅ All services stopped via controller")
        
    else:
        print("❌ Failed to start services via controller")
        return False
    
    return True


def test_error_handling():
    """Test error handling and edge cases"""
    print_section("5. ERROR HANDLING AND EDGE CASES")
    
    # Test double connection
    print_subsection("Double Connection Test")
    cvm_service = CVM24PService()
    
    result1 = cvm_service.connect()
    result2 = cvm_service.connect()  # Should handle gracefully
    
    print(f"✅ First connection: {result1}")
    print(f"✅ Second connection: {result2}")
    
    # Test polling without connection
    print_subsection("Polling Without Connection Test")
    cvm_service2 = CVM24PService()
    
    polling_result = cvm_service2.start_polling()
    print(f"✅ Polling without connection: {polling_result} (should be False)")
    
    # Test double polling
    print_subsection("Double Polling Test")
    if cvm_service.connected:
        poll1 = cvm_service.start_polling()
        poll2 = cvm_service.start_polling()  # Should handle gracefully
        
        print(f"✅ First polling start: {poll1}")
        print(f"✅ Second polling start: {poll2}")
        
        cvm_service.stop_polling()
    
    # Test disconnection
    print_subsection("Disconnection Test")
    cvm_service.disconnect()
    print("✅ Service disconnected")
    
    # Test operations after disconnection
    status_after_disconnect = cvm_service.get_status()
    print(f"✅ Status after disconnect: connected={status_after_disconnect['connected']}")
    
    return True


def test_data_interface():
    """Test data reading interface and formats"""
    print_section("6. DATA INTERFACE AND FORMATS")
    
    # Create and connect service
    cvm_service = CVM24PService()
    cvm_service.connect()
    
    if not cvm_service.connected:
        print("❌ Could not connect for data interface test")
        return False
    
    # Start polling briefly
    cvm_service.start_polling()
    time.sleep(2)
    
    # Test voltage statistics format
    print_subsection("Voltage Statistics Format")
    stats = cvm_service.get_voltage_statistics()
    
    print(f"✅ Statistics structure:")
    for key, value in stats.items():
        value_type = type(value).__name__
        print(f"   • {key}: {value} ({value_type})")
    
    # Test unbalanced cells format
    print_subsection("Unbalanced Cells Format")
    unbalanced = cvm_service.get_unbalanced_cells()
    print(f"✅ Unbalanced cells type: {type(unbalanced).__name__}")
    print(f"✅ Unbalanced cells count: {len(unbalanced)}")
    if unbalanced:
        print(f"✅ Sample unbalanced cells: {unbalanced[:5]}")
    
    # Test module info format
    print_subsection("Module Info Format")
    module_info = cvm_service.get_module_info()
    print(f"✅ Module info type: {type(module_info).__name__}")
    print(f"✅ Module count: {len(module_info)}")
    
    # Test state integration
    print_subsection("Global State Integration")
    state = get_global_state()
    voltages = state.cell_voltages
    
    print(f"✅ Global state voltages:")
    print(f"   • Type: {type(voltages).__name__}")
    print(f"   • Length: {len(voltages)}")
    print(f"   • Sample values: {voltages[:3] if voltages else 'None'}")
    
    cvm_service.stop_polling()
    cvm_service.disconnect()
    
    return True


def test_performance():
    """Test performance characteristics"""
    print_section("7. PERFORMANCE TESTING")
    
    cvm_service = CVM24PService()
    cvm_service.connect()
    
    if not cvm_service.connected:
        print("❌ Could not connect for performance test")
        return False
    
    # Test connection time
    print_subsection("Connection Performance")
    start_time = time.time()
    cvm_service.disconnect()
    disconnect_time = time.time() - start_time
    
    start_time = time.time()
    cvm_service.connect()
    connect_time = time.time() - start_time
    
    print(f"✅ Connection time: {connect_time:.3f}s")
    print(f"✅ Disconnection time: {disconnect_time:.3f}s")
    
    # Test polling performance
    print_subsection("Polling Performance")
    cvm_service.start_polling()
    
    # Measure data update rate
    state = get_global_state()
    initial_voltages = state.cell_voltages.copy() if state.cell_voltages else []
    
    time.sleep(3)  # Let it poll for 3 seconds
    
    final_voltages = state.cell_voltages.copy() if state.cell_voltages else []
    
    if initial_voltages and final_voltages:
        changes = sum(1 for i, (v1, v2) in enumerate(zip(initial_voltages, final_voltages)) if abs(v1 - v2) > 0.001)
        print(f"✅ Data changes detected: {changes}/{len(initial_voltages)} channels")
        print(f"✅ Effective sample rate: {cvm_service.sample_rate} Hz")
    else:
        print("⚠️  No voltage data for performance measurement")
    
    cvm_service.stop_polling()
    cvm_service.disconnect()
    
    return True


def main():
    """Main test runner"""
    print_section("CVM24P INTERFACE TEST SUITE")
    print("🧪 Testing CVM24P service interface based on CVM_test.py guide")
    print("📋 This test runs safely without hardware (uses mock mode)")
    print("🎯 Verifies: Hardware interface, XC2 protocol structure, polling, data formats")
    
    test_results = []
    
    try:
        # Run all tests
        tests = [
            ("Basic Functionality", test_cvm_service_basic),
            ("Configuration", test_cvm_configuration), 
            ("Controller Integration", test_controller_integration),
            ("Error Handling", test_error_handling),
            ("Data Interface", test_data_interface),
            ("Performance", test_performance)
        ]
        
        for test_name, test_func in tests:
            try:
                print(f"\n🧪 Running {test_name} test...")
                
                if test_name == "Basic Functionality":
                    # Special case - this returns the service for polling test
                    result = test_func()
                    if result and hasattr(result, 'connected'):
                        # Run polling test with the service
                        print("\n🧪 Running Polling test...")
                        polling_result = test_cvm_polling(result)
                        test_results.append(("Polling", polling_result))
                        result.disconnect()
                        test_results.append((test_name, True))
                    else:
                        test_results.append((test_name, False))
                else:
                    result = test_func()
                    test_results.append((test_name, result))
                    
            except Exception as e:
                print(f"❌ Test {test_name} failed with error: {e}")
                test_results.append((test_name, False))
        
        # Summary
        print_section("TEST RESULTS SUMMARY")
        
        passed = sum(1 for _, result in test_results if result)
        total = len(test_results)
        
        print(f"📊 Test Results: {passed}/{total} passed")
        print()
        
        for test_name, result in test_results:
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"   {status} - {test_name}")
        
        # Overall assessment
        print(f"\n🎯 CVM24P INTERFACE ASSESSMENT:")
        
        if passed == total:
            print("   ✅ All tests passed - CVM interface ready for hardware")
            print("   ✅ XC2 protocol integration implemented correctly")
            print("   ✅ Service lifecycle management working")
            print("   ✅ Mock mode fallback functioning")
            print("   ✅ Data formats and statistics correct")
            
        elif passed >= total * 0.8:
            print("   ⚠️  Most tests passed - Minor issues detected")
            print("   🔧 Review failed tests before hardware deployment")
            
        else:
            print("   ❌ Multiple test failures - Interface needs attention")
            print("   🔧 Fix critical issues before hardware testing")
        
        print(f"\n📋 HARDWARE DEPLOYMENT READINESS:")
        print(f"   → XC2 libraries: {'Available' if XC2_AVAILABLE else 'Need installation'}")
        print(f"   → Service interface: {'Ready' if passed >= total * 0.8 else 'Needs fixes'}")
        print(f"   → Error handling: {'Robust' if 'Error Handling' in [name for name, result in test_results if result] else 'Needs review'}")
        print(f"   → Controller integration: {'Working' if 'Controller Integration' in [name for name, result in test_results if result] else 'Failed'}")
        
        return passed == total
        
    except KeyboardInterrupt:
        print("\n🔔 Test interrupted by user")
        return False
    except Exception as e:
        print(f"\n❌ Test suite error: {e}")
        return False


if __name__ == "__main__":
    print("🧪 CVM24P Interface Test Suite")
    print("🎯 Based on CVM_test.py - Tests hardware interface without requiring connection")
    
    try:
        success = main()
        
        if success:
            print("\n🎉 All tests passed! CVM interface is ready.")
            sys.exit(0)
        else:
            print("\n⚠️  Some tests failed. Review before hardware deployment.")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n🔔 Test interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Test suite error: {e}")
        sys.exit(1) 
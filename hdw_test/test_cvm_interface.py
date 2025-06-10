#!/usr/bin/env python3
"""
Task 30: CVM24P Service Integration Test
Tests CVM24P service functionality with real hardware

Real hardware required - no mock functionality available.
"""

import sys
import os
import time

# Add parent directory to path to import services
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.cvm24p import CVM24PService, CVM24PConfig

def test_service_creation():
    """Test CVM service creation and configuration"""
    print("=" * 60)
    print("TEST 1: Service Creation and Configuration")
    print("=" * 60)
    
    service = CVM24PService()
    
    print("✅ Service created successfully")
    print(f"   → Device name: {service.device_name}")
    print(f"   → Expected modules: {service.expected_modules}")
    print(f"   → Total channels: {service.total_channels}")
    print(f"   → Sample rate: {service.sample_rate} Hz")
    
    # Test configuration constants
    print(f"\n📋 Configuration Constants:")
    print(f"   → Baud rate: {CVM24PConfig.BAUD_RATE}")
    print(f"   → Channels per module: {CVM24PConfig.CHANNELS_PER_MODULE}")
    print(f"   → Expected modules: {CVM24PConfig.EXPECTED_MODULES}")
    print(f"   → Voltage range: {CVM24PConfig.MIN_CELL_VOLTAGE}V - {CVM24PConfig.MAX_CELL_VOLTAGE}V")
    print(f"   → Voltage resolution: {CVM24PConfig.VOLTAGE_RESOLUTION * 1000}mV")
    
    return service

def test_hardware_connection(service):
    """Test hardware connection"""
    print("\n" + "=" * 60)
    print("TEST 2: Hardware Connection")
    print("=" * 60)
    
    print("🔌 Attempting to connect to CVM hardware...")
    connected = service.connect()
    
    if connected:
        print("✅ Hardware connection successful!")
        
        # Get detailed status
        status = service.get_status()
        print(f"\n📊 Service Status:")
        for key, value in status.items():
            print(f"   → {key}: {value}")
        
        # Test module info
        module_info = service.get_module_info()
        if module_info:
            print(f"\n🔧 Module Information:")
            for serial, info in module_info.items():
                print(f"   → Module {serial}:")
                print(f"     • Address: {info['address']}")
                print(f"     • Type: {info['type']}")
                print(f"     • Channels: {info['channels']}")
                print(f"     • Initialized: {info['initialized']}")
        else:
            print("\n⚠️  No module information available")
        
        return True
    else:
        print("❌ Hardware connection failed!")
        print("   → Check that CVM hardware is connected")
        print("   → Verify no other programs are using the port")
        return False

def test_polling_functionality(service):
    """Test data polling"""
    print("\n" + "=" * 60)
    print("TEST 3: Data Polling")
    print("=" * 60)
    
    if not service.connected:
        print("❌ Cannot test polling - service not connected")
        return False
    
    print("📊 Starting data polling...")
    success = service.start_polling()
    
    if not success:
        print("❌ Failed to start polling")
        return False
    
    print("✅ Polling started successfully")
    print("📈 Collecting data for 5 seconds...")
    
    # Collect data for a few seconds
    for i in range(5):
        time.sleep(1)
        stats = service.get_voltage_statistics()
        
        print(f"   Second {i+1}: Min={stats['min']:.3f}V, "
              f"Max={stats['max']:.3f}V, Avg={stats['avg']:.3f}V")
    
    # Test final statistics
    final_stats = service.get_voltage_statistics()
    print(f"\n📊 Final Statistics:")
    print(f"   → Minimum voltage: {final_stats['min']:.3f}V")
    print(f"   → Maximum voltage: {final_stats['max']:.3f}V")
    print(f"   → Average voltage: {final_stats['avg']:.3f}V")
    print(f"   → Total voltage: {final_stats['total']:.3f}V")
    print(f"   → Standard deviation: {final_stats['std_dev']:.3f}V")
    
    # Test unbalanced cells
    unbalanced = service.get_unbalanced_cells()
    if unbalanced:
        print(f"   → Unbalanced cells: {unbalanced}")
    else:
        print(f"   → All cells balanced (within {CVM24PConfig.VOLTAGE_IMBALANCE_THRESHOLD*1000}mV)")
    
    # Stop polling
    service.stop_polling()
    print("✅ Polling stopped successfully")
    
    return True

def test_service_disconnection(service):
    """Test service disconnection"""
    print("\n" + "=" * 60)
    print("TEST 4: Service Disconnection")
    print("=" * 60)
    
    print("🔌 Disconnecting from CVM service...")
    service.disconnect()
    
    # Verify disconnection
    status = service.get_status()
    if not status['connected']:
        print("✅ Service disconnected successfully")
        return True
    else:
        print("❌ Service still shows as connected")
        return False

def run_comprehensive_test():
    """Run all tests in sequence"""
    print("🧪 CVM24P Service Comprehensive Test")
    print("🎯 Testing real hardware integration")
    print("=" * 60)
    
    test_results = []
    
    # Test 1: Service creation
    try:
        service = test_service_creation()
        test_results.append(("Service Creation", True))
    except Exception as e:
        print(f"❌ Service creation failed: {e}")
        test_results.append(("Service Creation", False))
        return test_results
    
    # Test 2: Hardware connection
    try:
        connection_success = test_hardware_connection(service)
        test_results.append(("Hardware Connection", connection_success))
        
        if not connection_success:
            print("\n⚠️  Skipping remaining tests - hardware not connected")
            return test_results
            
    except Exception as e:
        print(f"❌ Hardware connection test failed: {e}")
        test_results.append(("Hardware Connection", False))
        return test_results
    
    # Test 3: Polling functionality
    try:
        polling_success = test_polling_functionality(service)
        test_results.append(("Data Polling", polling_success))
    except Exception as e:
        print(f"❌ Polling test failed: {e}")
        test_results.append(("Data Polling", False))
    
    # Test 4: Service disconnection
    try:
        disconnection_success = test_service_disconnection(service)
        test_results.append(("Service Disconnection", disconnection_success))
    except Exception as e:
        print(f"❌ Disconnection test failed: {e}")
        test_results.append(("Service Disconnection", False))
    
    return test_results

def print_test_summary(test_results):
    """Print test results summary"""
    print("\n" + "=" * 60)
    print("TEST RESULTS SUMMARY")
    print("=" * 60)
    
    passed = 0
    total = len(test_results)
    
    for test_name, success in test_results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if success:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed!")
        return True
    else:
        print("⚠️  Some tests failed")
        return False

def main():
    """Main test execution"""
    print("📋 This test requires real CVM24P hardware to be connected")
    print("📋 Ensure no other programs are using the CVM ports")
    print()
    
    # Run comprehensive tests
    test_results = run_comprehensive_test()
    
    # Print summary
    all_passed = print_test_summary(test_results)
    
    if all_passed:
        print("\n✅ CVM24P service integration test complete - all functionality working!")
    else:
        print("\n❌ CVM24P service integration test completed with failures")
        print("   → Check hardware connections and port availability")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    main() 
#!/usr/bin/env python3
"""
Simple CVM Hardware Connection Test
Focuses specifically on testing the hardware connection logic
"""

import sys
import os

# Add project root to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.cvm24p import CVM24PService


def test_hardware_connection():
    """Test CVM hardware connection specifically"""
    print("🔧 CVM Hardware Connection Test")
    print("=" * 50)
    
    # Create service
    print("1. Creating CVM service...")
    cvm_service = CVM24PService()
    print(f"   → Service created: {cvm_service.device_name}")
    print(f"   → Use mock: {cvm_service.use_mock}")
    print(f"   → Expected modules: {cvm_service.expected_modules}")
    
    # Test connection
    print("\n2. Testing hardware connection...")
    try:
        connected = cvm_service.connect()
        
        if connected:
            print("✅ Connection successful!")
            
            # Get service status
            status = cvm_service.get_status()
            print(f"\n📊 Connection Results:")
            print(f"   → Mode: {status['mode']}")
            print(f"   → Connected: {status['connected']}")
            print(f"   → Modules found: {status['modules']}")
            print(f"   → Channels: {status['channels']}")
            
            # Show module details
            if status['modules'] > 0:
                module_info = cvm_service.get_module_info()
                print(f"\n🔧 Module Details:")
                for serial, info in module_info.items():
                    print(f"   → Module {serial}: Address {info['address']}, Initialized: {info['initialized']}")
                
                # Test a quick voltage reading
                print(f"\n📊 Testing voltage reading...")
                cvm_service.start_polling()
                import time
                time.sleep(2)
                
                stats = cvm_service.get_voltage_statistics()
                print(f"   → Statistics: Min={stats['min']:.3f}V, Max={stats['max']:.3f}V, Avg={stats['avg']:.3f}V")
                
                cvm_service.stop_polling()
            
            # Clean up
            cvm_service.disconnect()
            print("\n✅ Test completed successfully!")
            return True
            
        else:
            print("❌ Connection failed!")
            return False
            
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("🧪 Simple CVM Hardware Test")
    print("🎯 This will try to connect to real CVM hardware on COM5")
    print("📋 Make sure CVM_test.py is not running!")
    print()
    
    success = test_hardware_connection()
    
    if success:
        print("\n🎉 Hardware connection works!")
    else:
        print("\n⚠️ Hardware connection failed - check debug output above")
    
    input("\nPress Enter to exit...") 
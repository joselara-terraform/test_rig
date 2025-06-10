#!/usr/bin/env python3
"""
Simple CVM24P Hardware Test
Tests connection to real CVM24P hardware only - no mock functionality
"""

import sys
import os

# Add parent directory to path to import services
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.cvm24p import CVM24PService

def test_hardware_connection():
    """Test CVM hardware connection specifically"""
    print("🔋 Testing CVM24P Hardware Connection")
    print("=" * 50)
    
    cvm_service = CVM24PService()
    
    print(f"✅ CVM24P service created")
    print(f"   → Expected modules: {cvm_service.expected_modules}")
    print(f"   → Total channels: {cvm_service.total_channels}")
    print(f"   → Sample rate: {cvm_service.sample_rate} Hz")
    
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
    print("🧪 CVM24P Hardware Connection Test")
    print("🎯 This test requires real CVM hardware to be connected")
    print("📋 Make sure CVM_test.py is not running!")
    print()
    
    success = test_hardware_connection()
    
    if success:
        print("\n🎉 Hardware connection works!")
    else:
        print("\n⚠️ Hardware connection failed - check that CVM hardware is connected")
    
    input("\nPress Enter to exit...") 
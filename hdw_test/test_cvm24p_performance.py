#!/usr/bin/env python3
"""
CVM24P Performance Test Script
Tests the new high-speed voltage data collection capabilities
"""

import sys
import os
import time

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.device_config import get_device_config
from services.cvm24p import CVM24PService

def test_cvm24p_performance():
    """Test CVM24P performance optimizations"""
    print("🔋 Testing CVM24P Performance Optimizations")
    print("=" * 50)
    
    # Load configuration
    device_config = get_device_config()
    
    # Display configuration
    print(f"Configuration loaded:")
    print(f"  Target sample rate: {device_config.get_cvm24p_target_sample_rate()} Hz")
    print(f"  Max sample rate: {device_config.get_cvm24p_max_sample_rate()} Hz")
    print(f"  CSV log rate: {device_config.get_sample_rate('cvm24p')} Hz (matches CVM24P rate)")
    print(f"  Latency minimized: {device_config.is_cvm24p_latency_minimized()}")
    print(f"  Performance logging: {device_config.is_cvm24p_performance_logging_enabled()}")
    print()
    
    # Initialize service
    cvm_service = CVM24PService()
    
    print(f"🔌 Attempting CVM24P connection...")
    if cvm_service.connect():
        print("✅ Connected successfully!")
        
        # Display status
        status = cvm_service.get_status()
        print(f"\nStatus:")
        for key, value in status.items():
            if isinstance(value, dict):
                print(f"  {key}:")
                for subkey, subvalue in value.items():
                    print(f"    {subkey}: {subvalue}")
            else:
                print(f"  {key}: {value}")
        
        # Start polling for performance test
        if cvm_service.start_polling():
            print(f"\n🚀 Performance test running for 60 seconds...")
            print(f"   Monitor the console for performance reports every 30s")
            
            # Let it run for 60 seconds
            time.sleep(60)
            
            # Stop and show final status
            cvm_service.stop_polling()
            final_status = cvm_service.get_status()
            
            if 'actual_sample_rate' in final_status:
                print(f"\n📊 Final Performance Results:")
                print(f"   Target: {final_status['target_sample_rate']}")
                print(f"   Actual: {final_status['actual_sample_rate']}")
                print(f"   Efficiency: {final_status['efficiency']}")
                print(f"   Total samples: {final_status['total_samples']}")
        
        cvm_service.disconnect()
        print("✅ Test completed successfully!")
        
    else:
        print("❌ Connection failed - check hardware and COM ports")
        return False
    
    return True

if __name__ == "__main__":
    try:
        success = test_cvm24p_performance()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        sys.exit(1) 
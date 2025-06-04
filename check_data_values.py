"""
Simple script to continuously display current pressure values from GlobalState
"""

import time
from core.state import get_global_state
from services.ni_daq import NIDAQService


def main():
    print("=" * 50)
    print("PRESSURE DATA MONITOR")
    print("=" * 50)
    print("Monitoring live pressure values from NI DAQ service...")
    print("Press Ctrl+C to stop\n")
    
    # Start NI DAQ service
    daq_service = NIDAQService()
    if not daq_service.connect():
        print("❌ Failed to connect to NI DAQ service")
        return
    
    if not daq_service.start_polling():
        print("❌ Failed to start NI DAQ polling")
        return
    
    state = get_global_state()
    
    try:
        while True:
            # Get current values
            pressure1 = state.pressure_values[0] if len(state.pressure_values) > 0 else 0.0
            pressure2 = state.pressure_values[1] if len(state.pressure_values) > 1 else 0.0
            current = state.current_value
            
            # Clear line and print current values
            print(f"\rPressure 1: {pressure1:.3f} PSI  |  Pressure 2: {pressure2:.3f} PSI  |  Current: {current:.2f} A", end="", flush=True)
            
            time.sleep(0.5)  # Update every 500ms
            
    except KeyboardInterrupt:
        print("\n\nStopping...")
    finally:
        daq_service.disconnect()
        print("✅ NI DAQ service stopped")


if __name__ == "__main__":
    main() 
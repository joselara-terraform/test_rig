#!/usr/bin/env python3
"""
Continuous Pressure Sensor Reading Script
Reads 4-20mA pressure sensor (0-15 PSIG) from NI-9253 module on cDAQ-9187
Channel: AI0
Press Ctrl+C to stop
"""

import time
import sys
import signal

try:
    import nidaqmx
    from nidaqmx.constants import AcquisitionType
    from nidaqmx import Task
    print("✅ NI-DAQmx library imported successfully")
except ImportError:
    print("❌ NI-DAQmx library not found!")
    print("   Install with: pip install nidaqmx")
    sys.exit(1)

# Hardware Configuration
NI_9253_SLOT = "cDAQ9187-23E902CMod1"  # Analog input module
PRESSURE_CHANNEL = f"{NI_9253_SLOT}/ai0"  # AI0 channel

# Sensor Configuration
SENSOR_MIN_CURRENT = 0.004  # 4mA
SENSOR_MAX_CURRENT = 0.020  # 20mA
PRESSURE_MIN = 0.0  # 0 PSIG
PRESSURE_MAX = 15.0  # 15 PSIG

# Display Configuration
UPDATE_RATE = 10  # Hz (readings per second)
SAMPLES_PER_READ = 10  # Number of samples to average

# Global flag for clean shutdown
running = True

def signal_handler(sig, frame):
    """Handle Ctrl+C for clean shutdown"""
    global running
    print("\n\n⚠️  Stopping measurement...")
    running = False

def convert_current_to_pressure(current_ma):
    """
    Convert 4-20mA current to pressure (0-15 PSIG)
    
    Args:
        current_ma: Current in milliamps
    
    Returns:
        Pressure in PSIG
    """
    # Handle out-of-range values
    if current_ma < 4.0:
        return 0.0  # Below minimum
    elif current_ma > 20.0:
        return PRESSURE_MAX  # Above maximum
    
    # Linear scaling: (current - 4mA) / 16mA * 15 PSIG
    pressure = ((current_ma - 4.0) / 16.0) * PRESSURE_MAX
    return pressure

def main():
    """Main function to continuously read pressure sensor"""
    print("="*60)
    print("CONTINUOUS PRESSURE SENSOR READING")
    print("="*60)
    print(f"Hardware Configuration:")
    print(f"  • Module: {NI_9253_SLOT}")
    print(f"  • Channel: AI0")
    print(f"  • Sensor: 4-20mA, 0-15 PSIG")
    print(f"  • Update Rate: {UPDATE_RATE} Hz")
    print("="*60)
    print("\nPress Ctrl+C to stop\n")
    
    # Register signal handler for clean shutdown
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        # Create analog input task
        with Task() as task:
            # Add pressure sensor channel
            task.ai_channels.add_ai_current_chan(
                PRESSURE_CHANNEL,
                name_to_assign_to_channel="pressure_sensor",
                min_val=SENSOR_MIN_CURRENT,
                max_val=SENSOR_MAX_CURRENT
            )
            
            # Configure finite sampling instead of continuous
            # This avoids timeout issues when sensors are disconnected
            
            # Don't start the task - we'll read on demand
            print("📊 Started continuous pressure monitoring...\n")
            
            # Initialize statistics
            reading_count = 0
            min_pressure = float('inf')
            max_pressure = float('-inf')
            start_time = time.time()
            
            # Main reading loop
            while running:
                try:
                    # Read single sample (on-demand)
                    current_sample = task.read()
                    
                    # Convert to mA
                    current_ma = current_sample * 1000
                    
                    # Check if sensor is connected (should be between 4-20mA)
                    if current_ma < 3.5:
                        sensor_status = "⚠️  DISCONNECTED"
                        pressure_psig = 0.0
                    elif current_ma < 4.0:
                        sensor_status = "⚠️  LOW SIGNAL"
                        pressure_psig = 0.0
                    elif current_ma > 20.5:
                        sensor_status = "⚠️  HIGH SIGNAL"
                        pressure_psig = PRESSURE_MAX
                    else:
                        sensor_status = "✅ CONNECTED"
                        pressure_psig = convert_current_to_pressure(current_ma)
                    
                    # Update statistics
                    reading_count += 1
                    if sensor_status == "✅ CONNECTED":
                        min_pressure = min(min_pressure, pressure_psig)
                        max_pressure = max(max_pressure, pressure_psig)
                    
                    # Calculate runtime
                    elapsed_time = time.time() - start_time
                    hours = int(elapsed_time // 3600)
                    minutes = int((elapsed_time % 3600) // 60)
                    seconds = int(elapsed_time % 60)
                    
                    # Display reading with statistics
                    if sensor_status == "✅ CONNECTED":
                        print(f"\r⏱️  Runtime: {hours:02d}:{minutes:02d}:{seconds:02d} | "
                              f"📊 Pressure: {pressure_psig:6.2f} PSIG | "
                              f"⚡ Current: {current_ma:5.2f} mA | "
                              f"📈 Min: {min_pressure:5.2f} | "
                              f"📉 Max: {max_pressure:5.2f} | "
                              f"#️⃣  Readings: {reading_count}", 
                              end='', flush=True)
                    else:
                        print(f"\r⏱️  Runtime: {hours:02d}:{minutes:02d}:{seconds:02d} | "
                              f"{sensor_status} | "
                              f"⚡ Current: {current_ma:5.2f} mA | "
                              f"#️⃣  Readings: {reading_count}                    ", 
                              end='', flush=True)
                    
                    # Sleep to maintain update rate
                    time.sleep(1.0 / UPDATE_RATE)
                    
                except nidaqmx.errors.DaqError as e:
                    if "timeout" in str(e).lower():
                        print(f"\n⚠️  Read timeout - checking connection...")
                    else:
                        print(f"\n❌ DAQ Error: {e}")
                        break
                except Exception as e:
                    print(f"\n❌ Unexpected error: {e}")
                    break
            
            # Clean shutdown
            
            # Print final statistics
            print(f"\n\n{'='*60}")
            print("MEASUREMENT STATISTICS")
            print(f"{'='*60}")
            if reading_count > 0:
                print(f"Total Runtime: {hours:02d}:{minutes:02d}:{seconds:02d}")
                print(f"Total Readings: {reading_count:,}")
                print(f"Average Rate: {reading_count/elapsed_time:.1f} readings/second")
                if min_pressure != float('inf'):
                    print(f"Minimum Pressure: {min_pressure:.2f} PSIG")
                    print(f"Maximum Pressure: {max_pressure:.2f} PSIG")
                    print(f"Pressure Range: {max_pressure - min_pressure:.2f} PSIG")
                else:
                    print("No valid pressure readings (sensor disconnected)")
            else:
                print("No readings collected")
            print(f"{'='*60}")
            
    except nidaqmx.errors.DaqError as e:
        print(f"\n❌ Failed to initialize DAQ: {e}")
        print("\nTroubleshooting:")
        print("1. Check that the cDAQ-9187 is connected via USB")
        print("2. Verify the module name in NI MAX")
        print("3. Ensure NI-DAQmx drivers are installed")
        print("4. Check that the pressure sensor is connected to AI0")
        
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
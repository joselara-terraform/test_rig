#!/usr/bin/env python3
"""
Minimal NI cDAQ Current Monitor
Continuous raw current readings from ai0-ai5 of cDAQ9187-23E902CMod1
Press Ctrl+C to stop
"""

import time
import sys
import signal

try:
    import nidaqmx
    from nidaqmx.constants import AcquisitionType
    from nidaqmx import Task
except ImportError:
    print("❌ NI-DAQmx library not found!")
    print("   Install with: pip install nidaqmx")
    sys.exit(1)

# Hardware Configuration
MODULE = "cDAQ9187-23E902CMod1"
CHANNELS = [f"{MODULE}/ai{i}" for i in range(6)]  # ai0-ai5
UPDATE_RATE = 10  # Hz

# Global flag for clean shutdown
running = True

def signal_handler(sig, frame):
    global running
    print("\n\nStopping...")
    running = False

def main():
    print("="*50)
    print("MINIMAL CURRENT MONITOR")
    print("="*50)
    print(f"Module: {MODULE}")
    print(f"Channels: ai0-ai5")
    print(f"Update Rate: {UPDATE_RATE} Hz")
    print("Press Ctrl+C to stop\n")
    
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        with Task() as task:
            # Add current input channels
            for i, channel in enumerate(CHANNELS):
                task.ai_channels.add_ai_current_chan(
                    channel,
                    name_to_assign_to_channel=f"ai{i}",
                    min_val=0.0,     # 0mA
                    max_val=0.025    # 25mA
                )
            
            # Configure timing
            task.timing.cfg_samp_clk_timing(
                rate=1000,
                sample_mode=AcquisitionType.FINITE,
                samps_per_chan=10
            )
            
            print("📊 Reading current channels...\n")
            
            while running:
                try:
                    # Read all channels
                    data = task.read(number_of_samples_per_channel=10)
                    
                    # Calculate averages
                    readings = []
                    for i in range(6):
                        avg_current = sum(data[i]) / len(data[i])
                        current_ma = avg_current * 1000  # Convert to mA
                        readings.append(f"ai{i}: {current_ma:6.2f}mA")
                    
                    # Display
                    print(f"\r{' | '.join(readings)}", end='', flush=True)
                    
                    time.sleep(1.0 / UPDATE_RATE)
                    
                except Exception as e:
                    print(f"\n❌ Read error: {e}")
                    break
            
    except Exception as e:
        print(f"❌ Setup error: {e}")

if __name__ == "__main__":
    main() 
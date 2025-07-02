#!/usr/bin/env python3
"""
Minimal NI cDAQ Current Monitor
Continuous raw current readings from ai0-ai5 of cDAQ9187-23E902CMod1
Activates H2 and O2 purge valves (relays 3 and 5)
Press Ctrl+C to stop
"""

import time
import sys
import signal

try:
    import nidaqmx
    from nidaqmx.constants import AcquisitionType, LineGrouping
    from nidaqmx import Task
except ImportError:
    print("❌ NI-DAQmx library not found!")
    print("   Install with: pip install nidaqmx")
    sys.exit(1)

# Hardware Configuration
AI_MODULE = "cDAQ9187-23E902CMod1"  # Analog input module
DO_MODULE = "cDAQ9187-23E902CMod2"  # Digital output module
CHANNELS = [f"{AI_MODULE}/ai{i}" for i in range(6)]  # ai0-ai5
H2_PURGE_RELAY = f"{DO_MODULE}/port0/line3"  # Relay 3 - H2 purge valve
O2_PURGE_RELAY = f"{DO_MODULE}/port0/line5"  # Relay 5 - O2 purge valve
UPDATE_RATE = 10  # Hz

# Global flag for clean shutdown
running = True
do_task = None

def signal_handler(sig, frame):
    global running, do_task
    print("\n\nStopping...")
    running = False
    # Turn off relays on shutdown
    if do_task:
        try:
            do_task.write([False, False])  # Turn off both relays
            print("🔴 Purge valves OFF")
        except:
            pass

def main():
    global do_task
    
    print("="*50)
    print("MINIMAL CURRENT MONITOR + PURGE VALVES")
    print("="*50)
    print(f"AI Module: {AI_MODULE}")
    print(f"DO Module: {DO_MODULE}")
    print(f"Channels: ai0-ai5")
    print(f"Purge Valves: H2 (relay 3), O2 (relay 5)")
    print(f"Update Rate: {UPDATE_RATE} Hz")
    print("Press Ctrl+C to stop\n")
    
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        # Setup digital outputs for purge valves
        do_task = Task()
        do_task.do_channels.add_do_chan(
            f"{H2_PURGE_RELAY},{O2_PURGE_RELAY}",
            line_grouping=LineGrouping.CHAN_PER_LINE
        )
        
        # Turn on purge valves
        do_task.write([True, True])
        print("🟢 H2 and O2 purge valves ON\n")
        
        # Setup analog inputs
        with Task() as ai_task:
            # Add current input channels
            for i, channel in enumerate(CHANNELS):
                ai_task.ai_channels.add_ai_current_chan(
                    channel,
                    name_to_assign_to_channel=f"ai{i}",
                    min_val=0.0,     # 0mA
                    max_val=0.021    # 21mA (within NI-9253 limits)
                )
            
            # Configure timing
            ai_task.timing.cfg_samp_clk_timing(
                rate=1000,
                sample_mode=AcquisitionType.FINITE,
                samps_per_chan=10
            )
            
            print("📊 Reading current channels...\n")
            
            while running:
                try:
                    # Read all channels
                    data = ai_task.read(number_of_samples_per_channel=10)
                    
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
        
        # Turn off purge valves when done
        do_task.write([False, False])
        print("\n🔴 Purge valves OFF")
        do_task.close()
            
    except Exception as e:
        print(f"❌ Setup error: {e}")
        # Ensure valves are turned off on error
        if do_task:
            try:
                do_task.write([False, False])
                do_task.close()
                print("🔴 Purge valves OFF (error cleanup)")
            except:
                pass

if __name__ == "__main__":
    main() 
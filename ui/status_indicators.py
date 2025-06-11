#!/usr/bin/env python3
"""
Connection status indicators for AWE test rig hardware devices
"""

import tkinter as tk
from tkinter import ttk


class StatusIndicators:
    """Connection status indicators for all hardware devices"""
    
    def __init__(self, parent_frame):
        self.parent_frame = parent_frame
        
        # Device status (hardcoded as disconnected initially)
        self.device_status = {
            'ni_daq': False,
            'pico_tc08': False,
            'bga244_1': False,   # Individual BGA statuses
            'bga244_2': False,   # Individual BGA statuses  
            'bga244_3': False,   # Individual BGA statuses
            'cvm24p': False
        }
        
        # UI elements
        self.status_labels = {}
        self.status_indicators = {}
        
        self._create_indicators()
    
    def _create_indicators(self):
        """Create status indicator panel"""
        
        # Main status frame
        status_frame = ttk.LabelFrame(self.parent_frame, text="Hardware Connection Status", padding="10")
        status_frame.pack(fill='x', pady=5)
        
        # Create grid for device indicators
        devices = [
            ('ni_daq', 'NI cDAQ', 'Pressure/Current sensors + Valve/Pump control'),
            ('pico_tc08', 'Pico TC-08', '8-channel thermocouple logger'),
            ('bga244_1', 'BGA-1 (H2 Header)', 'Gas analyzer: H2 in O2 mixture'),
            ('bga244_2', 'BGA-2 (O2 Header)', 'Gas analyzer: O2 in H2 mixture'),
            ('bga244_3', 'BGA-3 (De-oxo)', 'Gas analyzer: H2 in O2 mixture'),
            ('cvm24p', 'CVM-24P', '24-channel cell voltage monitor')
        ]
        
        for i, (device_key, device_name, description) in enumerate(devices):
            # Device name label
            name_label = ttk.Label(status_frame, text=device_name, font=("Arial", 10, "bold"))
            name_label.grid(row=i, column=0, sticky='w', padx=5, pady=2)
            
            # Status indicator
            status_indicator = tk.Label(
                status_frame,
                text="❌ Disconnected",
                background="red",
                foreground="white",
                width=15,
                relief=tk.RAISED,
                font=("Arial", 9)
            )
            status_indicator.grid(row=i, column=1, padx=10, pady=2)
            self.status_indicators[device_key] = status_indicator
            
            # Description label
            desc_label = ttk.Label(status_frame, text=description, font=("Arial", 8), foreground="gray")
            desc_label.grid(row=i, column=2, sticky='w', padx=5, pady=2)
            
            # Polling rate/error info (placeholder)
            info_label = ttk.Label(status_frame, text="No data", font=("Arial", 8), foreground="gray")
            info_label.grid(row=i, column=3, sticky='w', padx=5, pady=2)
            self.status_labels[device_key] = info_label
    
    def update_device_status(self, device: str, connected: bool, info: str = ""):
        """Update the status of a specific device"""
        if device in self.device_status:
            self.device_status[device] = connected
            
            if connected:
                self.status_indicators[device].configure(
                    text="✅ Connected",
                    background="green",
                    foreground="white"
                )
                if info:
                    self.status_labels[device].configure(text=info, foreground="darkgreen")
                else:
                    self.status_labels[device].configure(text="Active", foreground="darkgreen")
            else:
                self.status_indicators[device].configure(
                    text="❌ Disconnected",
                    background="red",
                    foreground="white"
                )
                if info:
                    self.status_labels[device].configure(text=info, foreground="red")
                else:
                    self.status_labels[device].configure(text="No data", foreground="gray")
    
    def update_all_status(self, status_dict: dict):
        """Update status for all devices at once"""
        for device, connected in status_dict.items():
            self.update_device_status(device, connected)
    
    def get_connection_summary(self):
        """Get summary of connection status"""
        connected_count = sum(1 for status in self.device_status.values() if status)
        total_count = len(self.device_status)
        return f"{connected_count}/{total_count} devices connected"


def main():
    """Test the status indicators by running them directly"""
    root = tk.Tk()
    root.title("Test - Connection Status Indicators")
    root.geometry("800x300")
    
    print("=" * 60)
    print("TASK 7 TEST: Connection Status Indicators")
    print("=" * 60)
    print("✅ Status indicators created")
    print("✅ Four devices: NI DAQ, Pico TC-08, BGA244, CVM-24P")
    print("✅ All showing 'Disconnected' initially")
    print("\n🎯 TEST: Use buttons below to simulate connection changes")
    print("   - Each device shows: Name, Status, Description, Info")
    print("   - Status changes from ❌ Disconnected (red) to ✅ Connected (green)")
    print("\nClose window when done testing...")
    print("=" * 60)
    
    # Create status indicators
    status_indicators = StatusIndicators(root)
    
    # Add test buttons to simulate connection changes
    test_frame = ttk.LabelFrame(root, text="Test Controls", padding="5")
    test_frame.pack(fill='x', pady=10)
    
    def test_ni_daq():
        current = status_indicators.device_status['ni_daq']
        status_indicators.update_device_status('ni_daq', not current, "250 Hz" if not current else "")
        print(f"NI DAQ: {'Connected' if not current else 'Disconnected'}")
    
    def test_pico():
        current = status_indicators.device_status['pico_tc08']
        status_indicators.update_device_status('pico_tc08', not current, "1 Hz" if not current else "")
        print(f"Pico TC-08: {'Connected' if not current else 'Disconnected'}")
    
    def test_bga():
        current = status_indicators.device_status['bga244_1']
        status_indicators.update_device_status('bga244_1', not current, "0.5 Hz" if not current else "")
        print(f"BGA-1: {'Connected' if not current else 'Disconnected'}")
    
    def test_bga2():
        current = status_indicators.device_status['bga244_2']
        status_indicators.update_device_status('bga244_2', not current, "0.5 Hz" if not current else "")
        print(f"BGA-2: {'Connected' if not current else 'Disconnected'}")
    
    def test_bga3():
        current = status_indicators.device_status['bga244_3']
        status_indicators.update_device_status('bga244_3', not current, "0.5 Hz" if not current else "")
        print(f"BGA-3: {'Connected' if not current else 'Disconnected'}")
    
    def test_cvm():
        current = status_indicators.device_status['cvm24p']
        status_indicators.update_device_status('cvm24p', not current, "10 Hz" if not current else "")
        print(f"CVM-24P: {'Connected' if not current else 'Disconnected'}")
    
    def test_all():
        all_connected = all(status_indicators.device_status.values())
        new_status = not all_connected
        status_indicators.update_all_status({
            'ni_daq': new_status,
            'pico_tc08': new_status,
            'bga244_1': new_status,
            'bga244_2': new_status,
            'bga244_3': new_status,
            'cvm24p': new_status
        })
        if new_status:
            for device in status_indicators.device_status:
                rates = {'ni_daq': '250 Hz', 'pico_tc08': '1 Hz', 'bga244_1': '0.5 Hz', 'bga244_2': '0.5 Hz', 'bga244_3': '0.5 Hz', 'cvm24p': '10 Hz'}
                status_indicators.update_device_status(device, True, rates[device])
        print(f"All devices: {'Connected' if new_status else 'Disconnected'}")
        print(f"Summary: {status_indicators.get_connection_summary()}")
    
    # Test buttons
    ttk.Button(test_frame, text="Toggle NI DAQ", command=test_ni_daq).pack(side='left', padx=5)
    ttk.Button(test_frame, text="Toggle Pico TC-08", command=test_pico).pack(side='left', padx=5)
    ttk.Button(test_frame, text="Toggle BGA-1", command=test_bga).pack(side='left', padx=5)
    ttk.Button(test_frame, text="Toggle BGA-2", command=test_bga2).pack(side='left', padx=5)
    ttk.Button(test_frame, text="Toggle BGA-3", command=test_bga3).pack(side='left', padx=5)
    ttk.Button(test_frame, text="Toggle CVM-24P", command=test_cvm).pack(side='left', padx=5)
    ttk.Button(test_frame, text="Toggle All", command=test_all).pack(side='left', padx=10)
    
    root.mainloop()


if __name__ == "__main__":
    main() 
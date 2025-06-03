#!/usr/bin/env python3
"""
Control buttons for AWE test rig dashboard
"""

import tkinter as tk
from tkinter import ttk


class ControlPanel:
    """Control buttons for test operations"""
    
    def __init__(self, parent_frame):
        self.parent_frame = parent_frame
        self.is_connected = False
        self.test_running = False
        self.test_paused = False
        
        self._create_controls()
    
    def _create_controls(self):
        """Create control button panel"""
        
        # Main control frame
        control_frame = ttk.LabelFrame(self.parent_frame, text="Test Controls", padding="10")
        control_frame.pack(fill='x', pady=5)
        
        # Button frame for layout
        button_frame = ttk.Frame(control_frame)
        button_frame.pack()
        
        # Connect button
        self.connect_button = ttk.Button(
            button_frame,
            text="Connect to Hardware",
            command=self._on_connect_click,
            width=20
        )
        self.connect_button.grid(row=0, column=0, padx=5, pady=5)
        
        # Start Test button
        self.start_button = ttk.Button(
            button_frame,
            text="Start Test",
            command=self._on_start_click,
            width=15,
            state='disabled'
        )
        self.start_button.grid(row=0, column=1, padx=5, pady=5)
        
        # Pause/Resume button
        self.pause_button = ttk.Button(
            button_frame,
            text="Pause",
            command=self._on_pause_click,
            width=15,
            state='disabled'
        )
        self.pause_button.grid(row=0, column=2, padx=5, pady=5)
        
        # Emergency Stop button
        self.estop_button = ttk.Button(
            button_frame,
            text="EMERGENCY STOP",
            command=self._on_estop_click,
            width=20
        )
        self.estop_button.grid(row=0, column=3, padx=5, pady=5)
        
        # Style the emergency stop button
        style = ttk.Style()
        style.configure('Emergency.TButton', foreground='red')
        self.estop_button.configure(style='Emergency.TButton')
        
        # Status label
        self.status_label = ttk.Label(control_frame, text="Status: Disconnected", font=("Arial", 10))
        self.status_label.pack(pady=5)
    
    def _on_connect_click(self):
        """Handle Connect button click"""
        if not self.is_connected:
            print("🔌 Connect to Hardware button clicked")
            print("   → Attempting to connect to all devices...")
            self.is_connected = True
            self.connect_button.configure(text="Disconnect")
            self.start_button.configure(state='normal')
            self.status_label.configure(text="Status: Connected")
            print("   ✅ Connected (mocked)")
        else:
            print("🔌 Disconnect button clicked")
            print("   → Disconnecting from all devices...")
            self.is_connected = False
            self.test_running = False
            self.test_paused = False
            self.connect_button.configure(text="Connect to Hardware")
            self.start_button.configure(state='disabled', text="Start Test")
            self.pause_button.configure(state='disabled', text="Pause")
            self.status_label.configure(text="Status: Disconnected")
            print("   ✅ Disconnected")
    
    def _on_start_click(self):
        """Handle Start Test button click"""
        if not self.test_running:
            print("▶️  Start Test button clicked")
            print("   → Starting test sequence...")
            print("   → Timer started")
            print("   → Data logging started")
            self.test_running = True
            self.test_paused = False
            self.start_button.configure(text="Stop Test")
            self.pause_button.configure(state='normal', text="Pause")
            self.status_label.configure(text="Status: Test Running")
            print("   ✅ Test started")
        else:
            print("⏹️  Stop Test button clicked")
            print("   → Stopping test sequence...")
            print("   → Timer stopped")
            print("   → Data logging stopped")
            self.test_running = False
            self.test_paused = False
            self.start_button.configure(text="Start Test")
            self.pause_button.configure(state='disabled', text="Pause")
            self.status_label.configure(text="Status: Connected")
            print("   ✅ Test stopped")
    
    def _on_pause_click(self):
        """Handle Pause/Resume button click"""
        if not self.test_paused:
            print("⏸️  Pause button clicked")
            print("   → Pausing test...")
            print("   → Timer paused")
            print("   → Data logging paused")
            self.test_paused = True
            self.pause_button.configure(text="Resume")
            self.status_label.configure(text="Status: Test Paused")
            print("   ✅ Test paused")
        else:
            print("▶️  Resume button clicked")
            print("   → Resuming test...")
            print("   → Timer resumed")
            print("   → Data logging resumed")
            self.test_paused = False
            self.pause_button.configure(text="Pause")
            self.status_label.configure(text="Status: Test Running")
            print("   ✅ Test resumed")
    
    def _on_estop_click(self):
        """Handle Emergency Stop button click"""
        print("🚨 EMERGENCY STOP ACTIVATED! 🚨")
        print("   → All operations halted immediately")
        print("   → Valves closed")
        print("   → Pump stopped")
        print("   → Timer stopped")
        print("   → Data logging stopped")
        
        # Reset all states
        self.test_running = False
        self.test_paused = False
        
        # Update button states
        if self.is_connected:
            self.start_button.configure(text="Start Test")
            self.pause_button.configure(state='disabled', text="Pause")
            self.status_label.configure(text="Status: EMERGENCY STOP - Connected")
        else:
            self.start_button.configure(state='disabled')
            self.status_label.configure(text="Status: EMERGENCY STOP - Disconnected")
        
        print("   ✅ Emergency stop complete")


def main():
    """Test the control panel by running it directly"""
    root = tk.Tk()
    root.title("Test - Control Panel")
    root.geometry("600x200")
    
    print("=" * 50)
    print("TASK 6 TEST: Control Buttons")
    print("=" * 50)
    print("✅ Control panel created")
    print("✅ Buttons: Connect, Start Test, Pause/Resume, Emergency Stop")
    print("\n🎯 TEST: Click each button and check console output:")
    print("   1. Connect to Hardware (enables Start)")
    print("   2. Start Test (enables Pause, changes to Stop)")
    print("   3. Pause (changes to Resume)")
    print("   4. Resume (changes back to Pause)")
    print("   5. Emergency Stop (resets everything)")
    print("   6. Disconnect (disables Start)")
    print("\nClose window when done testing...")
    print("=" * 50)
    
    control_panel = ControlPanel(root)
    root.mainloop()


if __name__ == "__main__":
    main() 
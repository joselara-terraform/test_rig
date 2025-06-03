#!/usr/bin/env python3
"""
Control buttons for AWE test rig dashboard
"""

import tkinter as tk
from tkinter import ttk
from core.state import get_global_state
from core.timer import get_timer


class ControlPanel:
    """Control buttons for test operations"""
    
    def __init__(self, parent_frame):
        self.parent_frame = parent_frame
        self.state = get_global_state()
        self.timer = get_timer()
        
        # UI update timer
        self.update_job = None
        
        self._create_controls()
        self._start_ui_updates()
    
    def _create_controls(self):
        """Create control button panel"""
        
        # Main control frame
        control_frame = ttk.LabelFrame(self.parent_frame, text="Test Controls", padding="10")
        control_frame.pack(fill='x', pady=5)
        
        # Top row: buttons
        button_frame = ttk.Frame(control_frame)
        button_frame.pack()
        
        # Connect button
        self.connect_button = ttk.Button(
            button_frame,
            text="Connect",
            command=self._on_connect_click,
            width=15
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
        
        # Timer display
        self.timer_label = ttk.Label(
            button_frame,
            text="00:00:00",
            font=("Arial", 16, "bold"),
            foreground="blue"
        )
        self.timer_label.grid(row=0, column=4, padx=20, pady=5)
        
        # Style the emergency stop button
        style = ttk.Style()
        style.configure('Emergency.TButton', foreground='red')
        self.estop_button.configure(style='Emergency.TButton')
        
        # Bottom row: status
        status_frame = ttk.Frame(control_frame)
        status_frame.pack(pady=5)
        
        self.status_label = ttk.Label(status_frame, text="Status: Disconnected", font=("Arial", 10))
        self.status_label.pack()
    
    def _on_connect_click(self):
        """Handle Connect button click"""
        all_connected = all(self.state.connections.values())
        
        if not all_connected:
            print("🔌 Connect button clicked")
            print("   → Connecting to all devices...")
            
            # Update GlobalState connections (mocked as all successful)
            self.state.update_connection_status('ni_daq', True)
            self.state.update_connection_status('pico_tc08', True)
            self.state.update_connection_status('bga244', True)
            self.state.update_connection_status('cvm24p', True)
            
            print("   ✅ All devices connected (mocked)")
        else:
            print("🔌 Disconnect button clicked")
            print("   → Disconnecting from all devices...")
            
            # Stop any running test first
            if self.state.test_running:
                self._stop_test()
            
            # Update GlobalState connections
            self.state.update_connection_status('ni_daq', False)
            self.state.update_connection_status('pico_tc08', False)
            self.state.update_connection_status('bga244', False)
            self.state.update_connection_status('cvm24p', False)
            
            print("   ✅ All devices disconnected")
    
    def _on_start_click(self):
        """Handle Start Test button click"""
        if not self.state.test_running:
            print("▶️  Start Test button clicked")
            print("   → Starting test sequence...")
            
            # Update GlobalState and start timer
            with self.state._lock:
                self.state.test_running = True
                self.state.test_paused = False
                self.state.emergency_stop = False
            
            self.timer.start()
            print("   → Timer started")
            print("   → Data logging started (mocked)")
            print("   ✅ Test started")
        else:
            print("⏹️  Stop Test button clicked")
            self._stop_test()
    
    def _stop_test(self):
        """Stop the current test"""
        print("   → Stopping test sequence...")
        
        # Update GlobalState and stop timer
        with self.state._lock:
            self.state.test_running = False
            self.state.test_paused = False
        
        self.timer.stop()
        print("   → Timer stopped")
        print("   → Data logging stopped (mocked)")
        print("   ✅ Test stopped")
    
    def _on_pause_click(self):
        """Handle Pause/Resume button click"""
        if not self.state.test_paused:
            print("⏸️  Pause button clicked")
            print("   → Pausing test...")
            
            # Update GlobalState and pause timer
            with self.state._lock:
                self.state.test_paused = True
            
            self.timer.pause()
            print("   → Timer paused")
            print("   → Data logging paused (mocked)")
            print("   ✅ Test paused")
        else:
            print("▶️  Resume button clicked")
            print("   → Resuming test...")
            
            # Update GlobalState and resume timer
            with self.state._lock:
                self.state.test_paused = False
            
            self.timer.resume()
            print("   → Timer resumed")
            print("   → Data logging resumed (mocked)")
            print("   ✅ Test resumed")
    
    def _on_estop_click(self):
        """Handle Emergency Stop button click"""
        print("🚨 EMERGENCY STOP ACTIVATED! 🚨")
        print("   → All operations halted immediately")
        
        # Update GlobalState
        with self.state._lock:
            self.state.emergency_stop = True
            self.state.test_running = False
            self.state.test_paused = False
            # Reset all actuators to safe state
            self.state.pump_state = False
            for i in range(len(self.state.valve_states)):
                self.state.valve_states[i] = False
        
        # Stop timer
        self.timer.stop()
        
        print("   → Valves closed")
        print("   → Pump stopped")
        print("   → Timer stopped")
        print("   → Data logging stopped")
        print("   ✅ Emergency stop complete")
    
    def _start_ui_updates(self):
        """Start periodic UI updates"""
        self._update_ui()
    
    def _update_ui(self):
        """Update UI elements based on current state"""
        # Update button states based on GlobalState
        all_connected = all(self.state.connections.values())
        
        # Connect button
        if all_connected:
            self.connect_button.configure(text="Disconnect")
        else:
            self.connect_button.configure(text="Connect")
        
        # Start Test button
        if all_connected and not self.state.emergency_stop:
            self.start_button.configure(state='normal')
            if self.state.test_running:
                self.start_button.configure(text="Stop Test")
            else:
                self.start_button.configure(text="Start Test")
        else:
            self.start_button.configure(state='disabled', text="Start Test")
        
        # Pause button
        if self.state.test_running and not self.state.emergency_stop:
            self.pause_button.configure(state='normal')
            if self.state.test_paused:
                self.pause_button.configure(text="Resume")
            else:
                self.pause_button.configure(text="Pause")
        else:
            self.pause_button.configure(state='disabled', text="Pause")
        
        # Status label
        if self.state.emergency_stop:
            status_text = "Status: EMERGENCY STOP"
            if all_connected:
                status_text += " - Connected"
            else:
                status_text += " - Disconnected"
        elif not all_connected:
            status_text = "Status: Disconnected"
        elif self.state.test_running:
            if self.state.test_paused:
                status_text = "Status: Test Paused"
            else:
                status_text = "Status: Test Running"
        else:
            status_text = "Status: Connected"
        
        self.status_label.configure(text=status_text)
        
        # Timer display
        elapsed = self.state.timer_value
        hours = int(elapsed // 3600)
        minutes = int((elapsed % 3600) // 60)
        seconds = int(elapsed % 60)
        timer_text = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        self.timer_label.configure(text=timer_text)
        
        # Schedule next update
        self.update_job = self.parent_frame.after(100, self._update_ui)
    
    def cleanup(self):
        """Clean up resources"""
        if self.update_job:
            self.parent_frame.after_cancel(self.update_job)


def main():
    """Test the control panel by running it directly"""
    root = tk.Tk()
    root.title("Test - Control Panel with GlobalState")
    root.geometry("800x200")
    
    print("=" * 60)
    print("TASK 8 TEST: Controls Connected to GlobalState")
    print("=" * 60)
    print("✅ Control panel connected to GlobalState and Timer")
    print("✅ Timer display shows real elapsed time")
    print("✅ Buttons actually control state and timer")
    print("\n🎯 TEST: Click buttons and verify:")
    print("   1. Connect - updates GlobalState connections")
    print("   2. Start Test - actually starts Timer")
    print("   3. Pause - actually pauses Timer")
    print("   4. Timer display updates in real-time")
    print("   5. Emergency Stop - resets everything")
    print("\nTimer display format: HH:MM:SS")
    print("Close window when done testing...")
    print("=" * 60)
    
    control_panel = ControlPanel(root)
    
    def on_closing():
        control_panel.cleanup()
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()


if __name__ == "__main__":
    main() 
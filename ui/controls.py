#!/usr/bin/env python3
"""
Control buttons for AWE test rig dashboard
"""

import tkinter as tk
from tkinter import ttk
from core.state import get_global_state
from core.timer import get_timer
from services.controller_manager import get_controller_manager


class ControlPanel:
    """Control buttons for test operations"""
    
    def __init__(self, parent_frame, plot_reset_callback=None):
        self.parent_frame = parent_frame
        self.state = get_global_state()
        self.timer = get_timer()
        self.controller = get_controller_manager()
        
        # Callback to reset plots when starting a new test
        self.plot_reset_callback = plot_reset_callback
        
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
        self.estop_button = tk.Button(
            button_frame,
            text="EMERGENCY STOP",
            command=self._on_estop_click,
            width=20,
            background="red",
            foreground="white",
            font=("Arial", 10, "bold"),
            relief=tk.RAISED,
            borderwidth=2
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
        
        # Bottom row: status
        status_frame = ttk.Frame(control_frame)
        status_frame.pack(pady=5)
        
        self.status_label = ttk.Label(status_frame, text="Status: Disconnected", font=("Arial", 10))
        self.status_label.pack()
        
        # Manual Relay Controls - separate frame below main controls
        self._create_relay_controls()
    
    def _create_relay_controls(self):
        """Create manual relay control buttons for valves and pump"""
        
        # Manual controls frame
        relay_frame = ttk.LabelFrame(self.parent_frame, text="Manual Relay Controls", padding="10")
        relay_frame.pack(fill='x', pady=5)
        
        # Warning label
        warning_label = ttk.Label(
            relay_frame,
            text="⚠️ Manual overrides - Use only when necessary",
            font=("Arial", 9, "italic"),
            foreground="orange"
        )
        warning_label.pack(pady=(0, 5))
        
        # Controls grid
        controls_frame = ttk.Frame(relay_frame)
        controls_frame.pack()
        
        # Valve controls (4 valves in a row)
        valve_label = ttk.Label(controls_frame, text="Solenoid Valves:", font=("Arial", 10, "bold"))
        valve_label.grid(row=0, column=0, columnspan=4, pady=(0, 5), sticky='w')
        
        self.valve_buttons = []
        for i in range(4):
            # Valve label
            label = ttk.Label(controls_frame, text=f"Valve {i+1}:")
            label.grid(row=1, column=i, padx=5, pady=2, sticky='w')
            
            # Toggle button
            button = tk.Button(
                controls_frame,
                text="OFF",
                command=lambda v=i: self._toggle_valve(v),
                width=8,
                background="red",
                foreground="white",
                font=("Arial", 9, "bold"),
                relief=tk.RAISED
            )
            button.grid(row=2, column=i, padx=5, pady=2)
            self.valve_buttons.append(button)
        
        # Pump control (separate section)
        pump_label = ttk.Label(controls_frame, text="Pump:", font=("Arial", 10, "bold"))
        pump_label.grid(row=0, column=5, padx=(20, 5), pady=(0, 5), sticky='w')
        
        # Pump toggle button
        self.pump_button = tk.Button(
            controls_frame,
            text="OFF",
            command=self._toggle_pump,
            width=10,
            background="red",
            foreground="white",
            font=("Arial", 9, "bold"),
            relief=tk.RAISED
        )
        self.pump_button.grid(row=2, column=5, padx=(20, 5), pady=2)
        
        # All OFF button (emergency function)
        all_off_button = tk.Button(
            controls_frame,
            text="ALL OFF",
            command=self._all_relays_off,
            width=12,
            background="darkred",
            foreground="white",
            font=("Arial", 9, "bold"),
            relief=tk.RAISED
        )
        all_off_button.grid(row=2, column=6, padx=(20, 5), pady=2)
    
    def _on_connect_click(self):
        """Handle Connect button click"""
        if not self.controller.is_all_connected():
            print("🔌 Connect button clicked")
            
            # Use ControllerManager to start all services
            success = self.controller.start_all_services()
            
            if success:
                print("   ✅ All devices connected via ControllerManager")
            else:
                print("   ❌ Some devices failed to connect")
        else:
            print("🔌 Disconnect button clicked")
            
            # Stop any running test first
            if self.state.test_running:
                self._stop_test()
            
            # Use ControllerManager to stop all services
            self.controller.stop_all_services()
            print("   ✅ All devices disconnected via ControllerManager")
    
    def _on_start_click(self):
        """Handle Start Test button click"""
        if not self.state.test_running:
            print("▶️  Start Test button clicked")
            print("   → Starting test sequence...")
            
            # Reset timer and start fresh
            self.timer.reset()
            
            # Reset plots for new test
            if self.plot_reset_callback:
                self.plot_reset_callback()
                print("   → Plots reset for new test")
            
            # Update GlobalState and start timer
            with self.state._lock:
                self.state.test_running = True
                self.state.test_paused = False
                self.state.emergency_stop = False  # Clear any previous e-stop
            
            self.timer.start()
            print("   → Timer started from 0")
            print("   → Data logging started (mocked)")
            print("   ✅ Test started")
        else:
            print("⏹️  Stop Test button clicked")
            self._stop_test()
    
    def _stop_test(self):
        """Stop the current test (normal stop - timer resets, no valve/pump changes)"""
        print("   → Stopping test sequence...")
        
        # Update GlobalState and reset timer
        with self.state._lock:
            self.state.test_running = False
            self.state.test_paused = False
        
        self.timer.reset()  # Reset timer to 0 for next test
        print("   → Timer stopped and reset to 0")
        print("   → Data logging stopped (mocked)")
        print("   → CSV file generated (mocked)")
        print("   ✅ Test stopped - ready for new test")
    
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
        
        # Update GlobalState - emergency stop does more than regular stop
        with self.state._lock:
            self.state.test_running = False
            self.state.test_paused = False
            # Close all actuators to safe state (key difference from regular stop)
            self.state.pump_state = False
            for i in range(len(self.state.valve_states)):
                self.state.valve_states[i] = False
        
        # Reset timer
        self.timer.reset()
        
        print("   → Timer stopped and reset to 0")
        print("   → All valves closed (SAFE STATE)")
        print("   → Pump stopped (SAFE STATE)")
        print("   → Data logging stopped")
        print("   → CSV file generated (mocked)")
        print("   → Power systems ready for disconnect (future)")
        print("   ✅ Emergency stop complete - system in safe state")
        print("   ℹ️  Press Start Test to begin new test")
    
    def _start_ui_updates(self):
        """Start periodic UI updates"""
        self._update_ui()
    
    def _update_ui(self):
        """Update UI elements based on current state"""
        # Update button states based on ControllerManager and GlobalState
        all_connected = self.controller.is_all_connected()
        
        # Connect button
        if all_connected:
            self.connect_button.configure(text="Disconnect")
        else:
            self.connect_button.configure(text="Connect")
        
        # Start Test button - only enabled when connected
        if all_connected:
            self.start_button.configure(state='normal')
            if self.state.test_running:
                self.start_button.configure(text="Stop Test")
            else:
                self.start_button.configure(text="Start Test")
        else:
            self.start_button.configure(state='disabled', text="Start Test")
        
        # Pause button - only available during running test
        if self.state.test_running:
            self.pause_button.configure(state='normal')
            if self.state.test_paused:
                self.pause_button.configure(text="Resume")
            else:
                self.pause_button.configure(text="Pause")
        else:
            self.pause_button.configure(state='disabled', text="Pause")
        
        # Status label
        if not all_connected:
            status_text = "Status: Disconnected"
        elif self.state.test_running:
            if self.state.test_paused:
                status_text = "Status: Test Paused"
            else:
                status_text = "Status: Test Running"
        else:
            status_text = "Status: Connected - Ready"
        
        self.status_label.configure(text=status_text)
        
        # Timer display
        elapsed = self.state.timer_value
        hours = int(elapsed // 3600)
        minutes = int((elapsed % 3600) // 60)
        seconds = int(elapsed % 60)
        timer_text = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        self.timer_label.configure(text=timer_text)
        
        # Update relay control buttons (only if they exist)
        if hasattr(self, 'valve_buttons') and hasattr(self, 'pump_button'):
            self._update_relay_buttons(all_connected)
        
        # Schedule next update
        self.update_job = self.parent_frame.after(100, self._update_ui)
    
    def _update_relay_buttons(self, all_connected):
        """Update relay control button states and colors"""
        # Update valve buttons
        for i, button in enumerate(self.valve_buttons):
            valve_state = self.state.valve_states[i]
            
            if all_connected:
                button.configure(state='normal')
                if valve_state:
                    button.configure(text="ON", background="green")
                else:
                    button.configure(text="OFF", background="red")
            else:
                button.configure(state='disabled', text="OFF", background="gray")
        
        # Update pump button
        if all_connected:
            self.pump_button.configure(state='normal')
            if self.state.pump_state:
                self.pump_button.configure(text="ON", background="green")
            else:
                self.pump_button.configure(text="OFF", background="red")
        else:
            self.pump_button.configure(state='disabled', text="OFF", background="gray")
    
    def cleanup(self):
        """Clean up resources"""
        if self.update_job:
            self.parent_frame.after_cancel(self.update_job)
    
    def _toggle_valve(self, valve_index):
        """Toggle specific valve state"""
        if not self.controller.is_all_connected():
            print(f"❌ Cannot control Valve {valve_index+1} - System not connected")
            return
        
        current_state = self.state.valve_states[valve_index]
        new_state = not current_state
        
        # Update state via GlobalState (NI DAQ will pick this up automatically)
        self.state.set_actuator_state('valve', new_state, valve_index)
        
        print(f"🔧 Manual Control: Valve {valve_index+1} {'ON' if new_state else 'OFF'}")
        print(f"   → State updated in GlobalState")
        print(f"   → NI DAQ will update hardware output")
    
    def _toggle_pump(self):
        """Toggle pump state"""
        if not self.controller.is_all_connected():
            print("❌ Cannot control Pump - System not connected")
            return
        
        current_state = self.state.pump_state
        new_state = not current_state
        
        # Update state via GlobalState (NI DAQ will pick this up automatically)
        self.state.set_actuator_state('pump', new_state)
        
        print(f"🔧 Manual Control: Pump {'ON' if new_state else 'OFF'}")
        print(f"   → State updated in GlobalState")
        print(f"   → NI DAQ will update hardware output")
    
    def _all_relays_off(self):
        """Turn all relays OFF (emergency function)"""
        if not self.controller.is_all_connected():
            print("❌ Cannot control relays - System not connected")
            return
        
        print("🔧 Manual Control: ALL RELAYS OFF")
        
        # Turn off all valves
        for i in range(4):
            self.state.set_actuator_state('valve', False, i)
        
        # Turn off pump
        self.state.set_actuator_state('pump', False)
        
        print("   → All valve and pump states set to OFF")
        print("   → NI DAQ will update hardware outputs")


def main():
    """Test the control panel by running it directly"""
    root = tk.Tk()
    root.title("Test - Control Panel with Manual Relay Controls")
    root.geometry("900x300")
    
    print("=" * 70)
    print("TASK 18 TEST: Controls with Manual Relay Control Buttons")
    print("=" * 70)
    print("✅ Control panel connected to ControllerManager")
    print("✅ Manual relay control buttons added")
    print("✅ 4 valve toggle buttons + 1 pump toggle button")
    print("✅ Buttons update GlobalState and NI DAQ hardware")
    print("✅ Real-time button color updates (red=OFF, green=ON)")
    print("✅ Buttons disabled when system not connected")
    print("\n🎯 TEST: Click buttons and verify:")
    print("   1. Connect - enables relay control buttons")
    print("   2. Manual valve/pump buttons toggle states")
    print("   3. Button colors change: Red=OFF, Green=ON")
    print("   4. State updates are reflected in dashboard indicators")
    print("   5. Emergency Stop sets all relays to safe state")
    print("   6. 'ALL OFF' button turns off all relays")
    print("\n🔧 Manual Controls:")
    print("   • Valve 1-4: Individual solenoid valve control")
    print("   • Pump: Water circulation pump control")
    print("   • ALL OFF: Emergency relay shutdown")
    print("\n⚠️  Manual controls update hardware via NI DAQ service")
    print("Close window when done testing...")
    print("=" * 70)
    
    control_panel = ControlPanel(root)
    
    def on_closing():
        control_panel.cleanup()
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()


if __name__ == "__main__":
    main() 
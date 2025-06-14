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
        
        # Purge button
        self.purge_button = tk.Button(
            button_frame,
            text="PURGE OFF",
            command=self._on_purge_click,
            width=15,
            background="gray",
            foreground="white",
            font=("Arial", 9, "bold"),
            relief=tk.RAISED,
            borderwidth=2
        )
        self.purge_button.grid(row=0, column=4, padx=5, pady=5)
        
        # Timer display
        self.timer_label = ttk.Label(
            button_frame,
            text="00:00:00",
            font=("Arial", 16, "bold"),
            foreground="blue"
        )
        self.timer_label.grid(row=0, column=5, padx=20, pady=5)
        
        # Bottom row: status
        status_frame = ttk.Frame(control_frame)
        status_frame.pack(pady=5)
        
        self.status_label = ttk.Label(status_frame, text="Status: Disconnected", font=("Arial", 10))
        self.status_label.pack()
    
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
            
            # Reset plots for new test
            if self.plot_reset_callback:
                self.plot_reset_callback()
                print("   → Plots reset for new test")
            
            # Use controller manager to start test with real CSV logging
            success = self.controller.start_test("UI_Test_Session")
            
            if success:
                # Check if CSV logging actually started by looking at the logger status
                csv_logger_status = self.controller.csv_logger.get_status()
                if csv_logger_status.get('logging', False):
                    print("   ✅ Test started successfully with CSV data logging")
                    print("   → CSV files are being created in session folder")
                else:
                    print("   ✅ Test started successfully but CSV logging failed")
                    print("   → No data files will be created (check console for details)")
            else:
                print("   ❌ Failed to start test")
        else:
            print("⏹️  Stop Test button clicked")
            self._stop_test()
    
    def _stop_test(self):
        """Stop the current test using controller manager"""
        print("   → Stopping test sequence...")
        
        # Check if CSV logging was active before stopping
        csv_was_logging = self.controller.csv_logger.get_status().get('logging', False)
        
        # Use controller manager to stop test (this handles CSV logging and session finalization)
        final_session = self.controller.stop_test("completed")
        
        if csv_was_logging:
            print("   ✅ Test stopped - CSV data logging completed")
            if final_session:
                file_count = len(final_session.get('files', {}))
                print(f"   → {file_count} files saved in session folder")
        else:
            print("   ✅ Test stopped - no CSV data was logged")
            print("   → Session folder created but no data files")
    
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
        print("   → Emergency stop initiated via controller manager")
        
        # Use controller manager for emergency stop (handles CSV logging, sessions, and hardware safety)
        self.controller.emergency_stop()
        
        print("   ✅ Emergency stop complete - system in safe state")
        print("   ℹ️  Press Start Test to begin new test")
    
    def _on_purge_click(self):
        """Handle Purge button click"""
        current_purge = self.state.purge_mode
        new_purge = not current_purge
        
        print(f"🧹 PURGE button clicked")
        print(f"   → Changing purge mode: {'OFF' if current_purge else 'ON'} → {'ON' if new_purge else 'OFF'}")
        
        # Update GlobalState
        with self.state._lock:
            self.state.purge_mode = new_purge
        
        # Call BGA244 service to actually set purge mode
        try:
            # Fix: Access the actual service instance, not the service dict
            bga_service_info = self.controller.services.get('bga244')
            bga_service = bga_service_info['service'] if bga_service_info else None
            
            if bga_service and hasattr(bga_service, 'set_purge_mode'):
                bga_service.set_purge_mode(new_purge)
                if new_purge:
                    print("   → All BGA244 secondary gases changed to N2")
                    print("   → Hardware devices reconfigured for purge mode")
                else:
                    print("   → BGA244 secondary gases restored to normal configuration")
                    print("   → Hardware devices reconfigured for normal mode")
            else:
                print("   → BGA244 service not available (purge mode stored in state)")
        except Exception as e:
            print(f"   ⚠️  Error setting BGA purge mode: {e}")
        
        print(f"   ✅ Purge mode {'ENABLED' if new_purge else 'DISABLED'}")
    
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
        
        # Purge button - only enabled when BGA244 is connected
        bga_connected = self.controller.is_bga_connected() if hasattr(self.controller, 'is_bga_connected') else all_connected
        
        if bga_connected:
            self.purge_button.configure(state='normal')
            if self.state.purge_mode:
                self.purge_button.configure(
                    text="PURGE ON",
                    background="orange",
                    activebackground="darkorange"
                )
            else:
                self.purge_button.configure(
                    text="PURGE OFF",
                    background="gray",
                    activebackground="darkgray"
                )
        else:
            self.purge_button.configure(
                state='disabled',
                text="PURGE OFF",
                background="lightgray"
            )
        
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
    root.title("Test - Control Panel with ControllerManager")
    root.geometry("800x200")
    
    print("=" * 60)
    print("TASK 9 TEST: Controls with ControllerManager")
    print("=" * 60)
    print("✅ Control panel connected to ControllerManager")
    print("✅ Connect button uses real service coordination")
    print("✅ Timer display shows real elapsed time")
    print("✅ Buttons actually control state and timer")
    print("\n🎯 TEST: Click buttons and verify:")
    print("   1. Connect - actually starts all services via ControllerManager")
    print("   2. Status indicators should update automatically")
    print("   3. Start Test - actually starts Timer")
    print("   4. Pause - actually pauses Timer")
    print("   5. Timer display updates in real-time")
    print("   6. Emergency Stop - resets everything")
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
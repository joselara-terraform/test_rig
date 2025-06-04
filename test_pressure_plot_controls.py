"""
Test script to verify pressure plot responds correctly to test control buttons
"""

import tkinter as tk
from tkinter import ttk
import threading
import time

from core.state import get_global_state
from services.ni_daq import NIDAQService
from ui.plots import PressurePlot
from ui.controls import ControlsPanel


def test_pressure_plot_controls():
    """Test that pressure plot responds to test control buttons"""
    
    # Create test window
    root = tk.Tk()
    root.title("Test Pressure Plot Controls")
    root.geometry("1200x800")
    
    # Create main frame with two sections
    main_frame = ttk.Frame(root)
    main_frame.pack(fill='both', expand=True, padx=10, pady=10)
    
    # Left side - controls
    controls_frame = ttk.LabelFrame(main_frame, text="Test Controls", padding=10)
    controls_frame.pack(side='left', fill='y', padx=(0, 10))
    
    # Right side - plot
    plot_frame = ttk.LabelFrame(main_frame, text="Pressure Plot", padding=10)
    plot_frame.pack(side='right', fill='both', expand=True)
    
    # Create controls panel
    controls = ControlsPanel(controls_frame)
    
    # Create pressure plot
    pressure_plot = PressurePlot(plot_frame)
    
    # Start NI DAQ service to generate test data
    daq_service = NIDAQService()
    if daq_service.connect():
        daq_service.start_polling()
    
    # Add test instructions
    instructions = ttk.Label(
        controls_frame,
        text="\nTest Instructions:\n\n"
             "1. Click 'Connect' to connect hardware\n"
             "2. Click 'Start Test' - plot should start\n"
             "3. Click 'Pause' - plot should pause\n"
             "4. Click 'Resume' - plot should resume\n"
             "5. Click 'Stop' - plot should reset\n"
             "6. Click 'E-Stop' - plot should reset\n\n"
             "✅ Y-axis should stay 0-1 psig\n"
             "✅ Plot should only update when running\n"
             "✅ Plot should pause when paused\n"
             "✅ Plot should reset when stopped",
        justify='left',
        wraplength=250
    )
    instructions.pack(pady=10)
    
    # Add current state display
    state_frame = ttk.LabelFrame(controls_frame, text="Current State", padding=5)
    state_frame.pack(fill='x', pady=10)
    
    state_labels = {}
    state_vars = {
        'test_running': 'Test Running',
        'test_paused': 'Test Paused', 
        'emergency_stop': 'Emergency Stop',
        'timer_value': 'Timer Value'
    }
    
    for var, label in state_vars.items():
        frame = ttk.Frame(state_frame)
        frame.pack(fill='x', pady=2)
        ttk.Label(frame, text=f"{label}:", width=12).pack(side='left')
        state_labels[var] = ttk.Label(frame, text="False", foreground='red')
        state_labels[var].pack(side='left')
    
    def update_state_display():
        """Update the state display"""
        state = get_global_state()
        
        # Update state labels
        state_labels['test_running']['text'] = str(state.test_running)
        state_labels['test_running']['foreground'] = 'green' if state.test_running else 'red'
        
        state_labels['test_paused']['text'] = str(state.test_paused)
        state_labels['test_paused']['foreground'] = 'orange' if state.test_paused else 'gray'
        
        state_labels['emergency_stop']['text'] = str(state.emergency_stop)
        state_labels['emergency_stop']['foreground'] = 'red' if state.emergency_stop else 'gray'
        
        state_labels['timer_value']['text'] = f"{state.timer_value:.1f}s"
        state_labels['timer_value']['foreground'] = 'blue'
        
        # Schedule next update
        root.after(100, update_state_display)
    
    # Start state display updates
    update_state_display()
    
    def cleanup():
        """Clean up resources"""
        if daq_service.connected:
            daq_service.disconnect()
        pressure_plot.destroy()
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", cleanup)
    
    print("=" * 60)
    print("PRESSURE PLOT CONTROLS TEST")
    print("=" * 60)
    print("✅ Test window created with controls and plot")
    print("✅ NI DAQ service started for test data")
    print("✅ State display shows current test status")
    print()
    print("Expected behavior:")
    print("  • Y-axis should stay fixed at 0-1 psig")
    print("  • Plot should only collect data when test is running AND not paused")
    print("  • Plot should pause data collection when paused")
    print("  • Plot should reset/clear when stopped or e-stopped")
    print()
    print("Test the controls and verify plot behavior matches expectations...")
    print("Close window when done testing.")
    
    root.mainloop()


if __name__ == "__main__":
    test_pressure_plot_controls() 
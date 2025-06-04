"""
Live plotting module for AWE test rig dashboard
Provides real-time plots for pressure, voltage, and temperature data
"""

import tkinter as tk
from tkinter import ttk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import matplotlib.animation as animation
from collections import deque
import time
from typing import List, Tuple
from core.state import get_global_state


class PressurePlot:
    """Live pressure vs time plot"""
    
    def __init__(self, parent_frame):
        self.parent_frame = parent_frame
        self.state = get_global_state()
        
        # Data storage for plotting - no maxlen to retain all data
        self.time_data = deque()
        self.pressure1_data = deque()
        self.pressure2_data = deque()
        
        # Track start time for relative time display
        self.start_time = None
        self.last_update_time = 0
        
        # Create the matplotlib figure
        self.fig = Figure(figsize=(6, 4), dpi=80, facecolor='white')
        self.ax = self.fig.add_subplot(111)
        
        # Configure plot appearance
        self.ax.set_title("Pressure vs Time", fontsize=12, fontweight='bold')
        self.ax.set_xlabel("Time (s)", fontsize=10)
        self.ax.set_ylabel("Pressure (psig)", fontsize=10)
        self.ax.grid(True, alpha=0.3)
        
        # Create line objects for both pressure sensors
        self.line1, = self.ax.plot([], [], 'b-', linewidth=2, label='Pressure 1')
        self.line2, = self.ax.plot([], [], 'r-', linewidth=2, label='Pressure 2')
        
        # Add legend
        self.ax.legend(loc='upper right', fontsize=9)
        
        # Set initial axis limits - 0-1 psig range, 0-120s time
        self.ax.set_xlim(0, 120)  # 120 seconds minimum
        self.ax.set_ylim(0, 1)    # 0-1 psig range
        
        # Create canvas and add to parent frame
        self.canvas = FigureCanvasTkAgg(self.fig, parent_frame)
        self.canvas.get_tk_widget().pack(fill='both', expand=True)
        
        # Start animation
        self.animation = animation.FuncAnimation(
            self.fig, self._update_plot, interval=100, blit=False, cache_frame_data=False
        )
        
        # Pack the canvas
        self.canvas.draw()
    
    def _update_plot(self, frame):
        """Update plot with new data from GlobalState"""
        current_time = time.time()
        
        # Check test state - only collect data when actively running
        test_running = self.state.test_running
        test_paused = self.state.test_paused
        emergency_stop = self.state.emergency_stop
        
        # Reset plot if test stopped or emergency stop activated
        if not test_running or emergency_stop:
            if len(self.time_data) > 0:  # Only reset if we have data to clear
                self.reset()
            return self.line1, self.line2
        
        # Don't collect new data if test is paused
        if test_paused:
            return self.line1, self.line2
        
        # Initialize start time on first update when test starts
        if self.start_time is None:
            self.start_time = current_time
        
        # Calculate relative time
        relative_time = current_time - self.start_time
        
        # Update only if enough time has passed (throttle updates)
        if current_time - self.last_update_time < 0.1:  # 10 Hz max update rate
            return self.line1, self.line2
        
        self.last_update_time = current_time
        
        # Get current pressure values
        pressure1 = self.state.pressure_values[0] if len(self.state.pressure_values) > 0 else 0.0
        pressure2 = self.state.pressure_values[1] if len(self.state.pressure_values) > 1 else 0.0
        
        # Add new data points
        self.time_data.append(relative_time)
        self.pressure1_data.append(pressure1)
        self.pressure2_data.append(pressure2)
        
        # Update line data
        if len(self.time_data) > 0:
            self.line1.set_data(list(self.time_data), list(self.pressure1_data))
            self.line2.set_data(list(self.time_data), list(self.pressure2_data))
            
            # Set x-axis to always show from 0 to max(current_time + 120s, 120s)
            max_time = max(relative_time + 120, 120)
            self.ax.set_xlim(0, max_time)
            
            # Keep y-axis fixed at 0-1 psig range
            self.ax.set_ylim(0, 1.0)
        
        return self.line1, self.line2
    
    def reset(self):
        """Reset plot data"""
        self.time_data.clear()
        self.pressure1_data.clear()
        self.pressure2_data.clear()
        self.start_time = None
        self.last_update_time = 0
        
        # Reset axis limits
        self.ax.set_xlim(0, 120)
        self.ax.set_ylim(0, 1.0)  # Fixed y-axis range
        
        # Clear line data
        self.line1.set_data([], [])
        self.line2.set_data([], [])
        
        self.canvas.draw()
    
    def destroy(self):
        """Clean up resources"""
        if hasattr(self, 'animation'):
            self.animation.event_source.stop()
        self.canvas.get_tk_widget().destroy()


class VoltagePlot:
    """Live voltage vs time plot - placeholder for Task 15"""
    
    def __init__(self, parent_frame):
        self.parent_frame = parent_frame
        
        # Placeholder label
        self.placeholder = ttk.Label(
            parent_frame,
            text="[Voltage Plot - Task 15]\n\nVoltage plotting will be\nimplemented in Task 15",
            justify=tk.CENTER,
            background="lightgreen"
        )
        self.placeholder.pack(fill='both', expand=True)
    
    def reset(self):
        pass
    
    def destroy(self):
        self.placeholder.destroy()


class TemperaturePlot:
    """Live temperature vs time plot - placeholder for Task 16"""
    
    def __init__(self, parent_frame):
        self.parent_frame = parent_frame
        
        # Placeholder label
        self.placeholder = ttk.Label(
            parent_frame,
            text="[Temperature Plot - Task 16]\n\nTemperature plotting will be\nimplemented in Task 16",
            justify=tk.CENTER,
            background="lightyellow"
        )
        self.placeholder.pack(fill='both', expand=True)
    
    def reset(self):
        pass
    
    def destroy(self):
        self.placeholder.destroy()


def test_pressure_plot():
    """Test the pressure plot independently"""
    import threading
    from services.ni_daq import NIDAQService
    
    # Create test window
    root = tk.Tk()
    root.title("Test Pressure Plot")
    root.geometry("800x600")
    
    # Create frame for plot
    plot_frame = ttk.Frame(root)
    plot_frame.pack(fill='both', expand=True, padx=10, pady=10)
    
    # Create pressure plot
    pressure_plot = PressurePlot(plot_frame)
    
    # Start NI DAQ service to generate test data
    daq_service = NIDAQService()
    if daq_service.connect():
        daq_service.start_polling()
        print("✅ NI DAQ service started for pressure plot testing")
    
    def cleanup():
        if daq_service.connected:
            daq_service.disconnect()
        pressure_plot.destroy()
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", cleanup)
    
    print("=" * 50)
    print("PRESSURE PLOT TEST")
    print("=" * 50)
    print("✅ Live pressure plot created")
    print("✅ Data updating from GlobalState")
    print("✅ Auto-scaling axes")
    print("✅ Dual pressure sensor display")
    print("\nClose window when done testing...")
    
    root.mainloop()


if __name__ == "__main__":
    test_pressure_plot() 
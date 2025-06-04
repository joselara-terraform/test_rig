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
    """Live pressure and gas concentration vs time plot"""
    
    def __init__(self, parent_frame, max_points: int = 300):
        self.parent_frame = parent_frame
        self.state = get_global_state()
        self.max_points = max_points
        
        # Data storage for plotting - pressure data
        self.time_data = deque()
        self.pressure1_data = deque()
        self.pressure2_data = deque()
        
        # Data storage for gas concentrations (converted to 0-1 range)
        self.h2_hydrogen_side_data = deque()  # H2 from Unit 1 (hydrogen side)
        self.o2_oxygen_side_data = deque()    # O2 from Unit 2 (oxygen side)
        self.h2_mixed_data = deque()          # H2 from Unit 3 (mixed stream)
        self.o2_mixed_data = deque()          # O2 from Unit 3 (mixed stream)
        
        self.last_update_time = 0
        
        # Create the matplotlib figure
        self.fig = Figure(figsize=(6, 4), dpi=80, facecolor='white')
        self.ax = self.fig.add_subplot(111)
        
        # Configure plot appearance
        self.ax.set_title("Pressure & Gas Concentrations vs Time", fontsize=12, fontweight='bold')
        self.ax.set_xlabel("Time (s)", fontsize=10)
        self.ax.set_ylabel("Pressure (PSI) / Gas Fraction", fontsize=10)
        self.ax.grid(True, alpha=0.3)
        
        # Create line objects for pressure sensors
        self.line1, = self.ax.plot([], [], 'b-', linewidth=2, label='Pressure 1')
        self.line2, = self.ax.plot([], [], 'r-', linewidth=2, label='Pressure 2')
        
        # Create line objects for gas concentrations (using different colors and styles)
        self.line_h2_h_side, = self.ax.plot([], [], 'g--', linewidth=1.5, label='H₂ (H-side)', alpha=0.8)
        self.line_o2_o_side, = self.ax.plot([], [], 'm--', linewidth=1.5, label='O₂ (O-side)', alpha=0.8)
        self.line_h2_mixed, = self.ax.plot([], [], 'g:', linewidth=1.5, label='H₂ (mixed)', alpha=0.7)
        self.line_o2_mixed, = self.ax.plot([], [], 'm:', linewidth=1.5, label='O₂ (mixed)', alpha=0.7)
        
        # Add legend with smaller font to fit more entries
        self.ax.legend(loc='upper right', fontsize=8, ncol=2)
        
        # Set initial axis limits
        self.ax.set_xlim(0, 120)  # 120 seconds visible
        self.ax.set_ylim(0, 1)    # 0-1 range for both pressure (PSI) and gas fractions
        
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
        
        # Check test states
        if self.state.emergency_stop or not self.state.test_running:
            return (self.line1, self.line2, self.line_h2_h_side, 
                   self.line_o2_o_side, self.line_h2_mixed, self.line_o2_mixed)
        
        if self.state.test_paused:
            return (self.line1, self.line2, self.line_h2_h_side, 
                   self.line_o2_o_side, self.line_h2_mixed, self.line_o2_mixed)
        
        # Update only if enough time has passed (throttle updates)
        if current_time - self.last_update_time < 0.1:  # 10 Hz max update rate
            return (self.line1, self.line2, self.line_h2_h_side, 
                   self.line_o2_o_side, self.line_h2_mixed, self.line_o2_mixed)
        
        self.last_update_time = current_time
        
        # Use global timer
        relative_time = self.state.timer_value
        
        # Get current pressure values
        pressure1 = self.state.pressure_values[0] if len(self.state.pressure_values) > 0 else 0.0
        pressure2 = self.state.pressure_values[1] if len(self.state.pressure_values) > 1 else 0.0
        
        # Get gas concentration values and convert percentages to fractions (0-1 range)
        gas_concentrations = self.state.gas_concentrations
        
        # Unit 1: hydrogen_side (H2 outlet) - get H2 concentration
        h2_hydrogen_side = (gas_concentrations[0]['H2'] / 100.0) if len(gas_concentrations) > 0 else 0.0
        
        # Unit 2: oxygen_side (O2 outlet) - get O2 concentration  
        o2_oxygen_side = (gas_concentrations[1]['O2'] / 100.0) if len(gas_concentrations) > 1 else 0.0
        
        # Unit 3: mixed_gas (Mixed stream) - get both H2 and O2 concentrations
        h2_mixed = (gas_concentrations[2]['H2'] / 100.0) if len(gas_concentrations) > 2 else 0.0
        o2_mixed = (gas_concentrations[2]['O2'] / 100.0) if len(gas_concentrations) > 2 else 0.0
        
        # Add new data points
        self.time_data.append(relative_time)
        self.pressure1_data.append(pressure1)
        self.pressure2_data.append(pressure2)
        
        # Add gas concentration data points
        self.h2_hydrogen_side_data.append(h2_hydrogen_side)
        self.o2_oxygen_side_data.append(o2_oxygen_side)
        self.h2_mixed_data.append(h2_mixed)
        self.o2_mixed_data.append(o2_mixed)
        
        # Update line data for pressure
        if len(self.time_data) > 0:
            self.line1.set_data(list(self.time_data), list(self.pressure1_data))
            self.line2.set_data(list(self.time_data), list(self.pressure2_data))
            
            # Update line data for gas concentrations
            self.line_h2_h_side.set_data(list(self.time_data), list(self.h2_hydrogen_side_data))
            self.line_o2_o_side.set_data(list(self.time_data), list(self.o2_oxygen_side_data))
            self.line_h2_mixed.set_data(list(self.time_data), list(self.h2_mixed_data))
            self.line_o2_mixed.set_data(list(self.time_data), list(self.o2_mixed_data))
            
            # Always show 120 seconds window
            self.ax.set_xlim(0, max(relative_time + 120, 120))
            
            # Auto-scale y-axis based on data (considering both pressure and gas data)
            if len(self.time_data) > 5:  # Only auto-scale after some data
                all_values = (list(self.pressure1_data) + list(self.pressure2_data) + 
                             list(self.h2_hydrogen_side_data) + list(self.o2_oxygen_side_data) +
                             list(self.h2_mixed_data) + list(self.o2_mixed_data))
                
                if all_values:  # Make sure we have data
                    min_value = min(all_values)
                    max_value = max(all_values)
                    
                    # Add some margin
                    margin = (max_value - min_value) * 0.1
                    if margin < 0.05:  # Minimum margin 
                        margin = 0.05
                    
                    y_min = max(0, min_value - margin)
                    y_max = min(1.0, max_value + margin)  # Cap at 1.0 since that's 100%
                    
                    self.ax.set_ylim(y_min, y_max)
        
        return (self.line1, self.line2, self.line_h2_h_side, 
               self.line_o2_o_side, self.line_h2_mixed, self.line_o2_mixed)

    def reset(self):
        """Reset plot data"""
        self.time_data.clear()
        self.pressure1_data.clear()
        self.pressure2_data.clear()
        
        # Clear gas concentration data
        self.h2_hydrogen_side_data.clear()
        self.o2_oxygen_side_data.clear()
        self.h2_mixed_data.clear()
        self.o2_mixed_data.clear()

        self.last_update_time = 0
        
        # Reset axis limits
        self.ax.set_xlim(0, 120)
        self.ax.set_ylim(0, 1)
        
        # Clear line data for pressure
        self.line1.set_data([], [])
        self.line2.set_data([], [])
        
        # Clear line data for gas concentrations
        self.line_h2_h_side.set_data([], [])
        self.line_o2_o_side.set_data([], [])
        self.line_h2_mixed.set_data([], [])
        self.line_o2_mixed.set_data([], [])
        
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
    """Test the pressure and gas concentration plot independently"""
    import threading
    from services.controller_manager import get_controller_manager
    
    # Create test window
    root = tk.Tk()
    root.title("Test Pressure & Gas Concentration Plot")
    root.geometry("800x600")
    
    # Create frame for plot
    plot_frame = ttk.Frame(root)
    plot_frame.pack(fill='both', expand=True, padx=10, pady=10)
    
    # Create pressure plot
    pressure_plot = PressurePlot(plot_frame)
    
    # Start all services via ControllerManager to generate test data
    controller = get_controller_manager()
    if controller.start_all_services():
        print("✅ All services started for pressure & gas plot testing")
    
    def cleanup():
        if controller.is_all_connected():
            controller.stop_all_services()
        pressure_plot.destroy()
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", cleanup)
    
    print("=" * 50)
    print("PRESSURE & GAS CONCENTRATION PLOT TEST")
    print("=" * 50)
    print("✅ Live pressure & gas concentration plot created")
    print("✅ Data updating from GlobalState")
    print("✅ Auto-scaling axes")
    print("✅ Pressure sensors: Blue (P1) & Red (P2)")
    print("✅ Gas concentrations: Green (H₂) & Magenta (O₂)")
    print("✅ Multiple gas streams: H-side, O-side, Mixed")
    print("\nClose window when done testing...")
    
    root.mainloop()


if __name__ == "__main__":
    test_pressure_plot() 
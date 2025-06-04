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
        
        # Data storage for gas concentrations (converted to 0-1 range) - only 3 BGA series
        self.h2_hydrogen_side_data = deque()  # H2 from Unit 1 (hydrogen side)
        self.o2_oxygen_side_data = deque()    # O2 from Unit 2 (oxygen side)
        self.h2_mixed_data = deque()          # H2 from Unit 3 (mixed stream)
        
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
        
        # Create line objects for gas concentrations - only 3 BGA series
        self.line_h2_h_side, = self.ax.plot([], [], 'g--', linewidth=1.5, label='H₂ (H-side)', alpha=0.8)
        self.line_o2_o_side, = self.ax.plot([], [], 'm--', linewidth=1.5, label='O₂ (O-side)', alpha=0.8)
        self.line_h2_mixed, = self.ax.plot([], [], 'g:', linewidth=1.5, label='H₂ (mixed)', alpha=0.7)
        
        # Add legend with smaller font to fit entries
        self.ax.legend(loc='upper right', fontsize=8, ncol=2)
        
        # Set initial axis limits - static Y, dynamic X
        self.ax.set_xlim(0, 120)  # Initial X limit
        self.ax.set_ylim(0, 1)    # Static Y limit (0-1 range)
        
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
                   self.line_o2_o_side, self.line_h2_mixed)
        
        if self.state.test_paused:
            return (self.line1, self.line2, self.line_h2_h_side, 
                   self.line_o2_o_side, self.line_h2_mixed)
        
        # Update only if enough time has passed (throttle updates)
        if current_time - self.last_update_time < 0.1:  # 10 Hz max update rate
            return (self.line1, self.line2, self.line_h2_h_side, 
                   self.line_o2_o_side, self.line_h2_mixed)
        
        self.last_update_time = current_time
        
        # Use global timer
        relative_time = self.state.timer_value
        
        # Get current pressure values
        pressure1 = self.state.pressure_values[0] if len(self.state.pressure_values) > 0 else 0.0
        pressure2 = self.state.pressure_values[1] if len(self.state.pressure_values) > 1 else 0.0
        
        # Get gas concentration values and convert percentages to fractions (0-1 range)
        # Only 3 BGA series: H2 from hydrogen side, O2 from oxygen side, H2 from mixed
        gas_concentrations = self.state.gas_concentrations
        
        # Unit 1: hydrogen_side (H2 outlet) - get H2 concentration
        h2_hydrogen_side = (gas_concentrations[0]['H2'] / 100.0) if len(gas_concentrations) > 0 else 0.0
        
        # Unit 2: oxygen_side (O2 outlet) - get O2 concentration  
        o2_oxygen_side = (gas_concentrations[1]['O2'] / 100.0) if len(gas_concentrations) > 1 else 0.0
        
        # Unit 3: mixed_gas (Mixed stream) - get H2 concentration only
        h2_mixed = (gas_concentrations[2]['H2'] / 100.0) if len(gas_concentrations) > 2 else 0.0
        
        # Add new data points
        self.time_data.append(relative_time)
        self.pressure1_data.append(pressure1)
        self.pressure2_data.append(pressure2)
        
        # Add gas concentration data points - only 3 BGA series
        self.h2_hydrogen_side_data.append(h2_hydrogen_side)
        self.o2_oxygen_side_data.append(o2_oxygen_side)
        self.h2_mixed_data.append(h2_mixed)
        
        # Update line data
        if len(self.time_data) > 0:
            # Update pressure lines
            self.line1.set_data(list(self.time_data), list(self.pressure1_data))
            self.line2.set_data(list(self.time_data), list(self.pressure2_data))
            
            # Update gas concentration lines - only 3 BGA series
            self.line_h2_h_side.set_data(list(self.time_data), list(self.h2_hydrogen_side_data))
            self.line_o2_o_side.set_data(list(self.time_data), list(self.o2_oxygen_side_data))
            self.line_h2_mixed.set_data(list(self.time_data), list(self.h2_mixed_data))
            
            # Dynamic X-axis: [0, max(current_time * 1.2, 120)]
            # Static Y-axis: [0, 1] (no auto-scaling)
            self.ax.set_xlim(0, max(relative_time*1.2, 120))
        
        return (self.line1, self.line2, self.line_h2_h_side, 
               self.line_o2_o_side, self.line_h2_mixed)

    def reset(self):
        """Reset plot data"""
        self.time_data.clear()
        self.pressure1_data.clear()
        self.pressure2_data.clear()
        
        # Clear gas concentration data - only 3 BGA series
        self.h2_hydrogen_side_data.clear()
        self.o2_oxygen_side_data.clear()
        self.h2_mixed_data.clear()

        self.last_update_time = 0
        
        # Reset axis limits - static Y, initial X
        self.ax.set_xlim(0, 120)
        self.ax.set_ylim(0, 1)
        
        # Clear line data
        self.line1.set_data([], [])
        self.line2.set_data([], [])
        
        # Clear gas concentration lines - only 3 BGA series
        self.line_h2_h_side.set_data([], [])
        self.line_o2_o_side.set_data([], [])
        self.line_h2_mixed.set_data([], [])
        
        self.canvas.draw()
    
    def destroy(self):
        """Clean up resources"""
        if hasattr(self, 'animation'):
            self.animation.event_source.stop()
        self.canvas.get_tk_widget().destroy()


class VoltagePlot:
    """Live cell voltage vs time plot"""
    
    def __init__(self, parent_frame, max_points: int = 300):
        self.parent_frame = parent_frame
        self.state = get_global_state()
        self.max_points = max_points
        
        # Data storage for plotting - voltage data (6 groups of 20 cells each)
        self.time_data = deque()
        self.group1_data = deque()  # Cells 1-20 average
        self.group2_data = deque()  # Cells 21-40 average
        self.group3_data = deque()  # Cells 41-60 average
        self.group4_data = deque()  # Cells 61-80 average
        self.group5_data = deque()  # Cells 81-100 average
        self.group6_data = deque()  # Cells 101-120 average
        
        self.last_update_time = 0
        
        # Create the matplotlib figure
        self.fig = Figure(figsize=(6, 4), dpi=80, facecolor='white')
        self.ax = self.fig.add_subplot(111)
        
        # Configure plot appearance
        self.ax.set_title("Cell Voltages vs Time", fontsize=12, fontweight='bold')
        self.ax.set_xlabel("Time (s)", fontsize=10)
        self.ax.set_ylabel("Voltage (V)", fontsize=10)
        self.ax.grid(True, alpha=0.3)
        
        # Create line objects for voltage group averages
        self.line_group1, = self.ax.plot([], [], 'b-', linewidth=2, label='Group 1 (1-20)', alpha=0.9)
        self.line_group2, = self.ax.plot([], [], 'g-', linewidth=2, label='Group 2 (21-40)', alpha=0.9)
        self.line_group3, = self.ax.plot([], [], 'r-', linewidth=2, label='Group 3 (41-60)', alpha=0.9)
        self.line_group4, = self.ax.plot([], [], 'm-', linewidth=2, label='Group 4 (61-80)', alpha=0.9)
        self.line_group5, = self.ax.plot([], [], 'c-', linewidth=2, label='Group 5 (81-100)', alpha=0.9)
        self.line_group6, = self.ax.plot([], [], 'y-', linewidth=2, label='Group 6 (101-120)', alpha=0.9)
        
        # Add legend
        self.ax.legend(loc='upper right', fontsize=7, ncol=3)
        
        # Set initial axis limits - static Y (0-5V), dynamic X
        self.ax.set_xlim(0, 120)  # Initial X limit
        self.ax.set_ylim(0, 5)    # Static Y limit (0-5V range)
        
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
            return (self.line_group1, self.line_group2, self.line_group3, 
                   self.line_group4, self.line_group5, self.line_group6)
        
        if self.state.test_paused:
            return (self.line_group1, self.line_group2, self.line_group3, 
                   self.line_group4, self.line_group5, self.line_group6)
        
        # Update only if enough time has passed (throttle updates)
        if current_time - self.last_update_time < 0.1:  # 10 Hz max update rate
            return (self.line_group1, self.line_group2, self.line_group3, 
                   self.line_group4, self.line_group5, self.line_group6)
        
        self.last_update_time = current_time
        
        # Use global timer
        relative_time = self.state.timer_value
        
        # Get current cell voltage values and calculate group averages
        cell_voltages = self.state.cell_voltages
        
        if len(cell_voltages) >= 120:
            # Calculate group averages (20 cells per group)
            group1_avg = sum(cell_voltages[0:20]) / 20      # Cells 1-20
            group2_avg = sum(cell_voltages[20:40]) / 20     # Cells 21-40
            group3_avg = sum(cell_voltages[40:60]) / 20     # Cells 41-60
            group4_avg = sum(cell_voltages[60:80]) / 20     # Cells 61-80
            group5_avg = sum(cell_voltages[80:100]) / 20    # Cells 81-100
            group6_avg = sum(cell_voltages[100:120]) / 20   # Cells 101-120
        else:
            # No data available or insufficient data
            group1_avg = group2_avg = group3_avg = 0.0
            group4_avg = group5_avg = group6_avg = 0.0
        
        # Add new data points
        self.time_data.append(relative_time)
        self.group1_data.append(group1_avg)
        self.group2_data.append(group2_avg)
        self.group3_data.append(group3_avg)
        self.group4_data.append(group4_avg)
        self.group5_data.append(group5_avg)
        self.group6_data.append(group6_avg)
        
        # Update line data
        if len(self.time_data) > 0:
            self.line_group1.set_data(list(self.time_data), list(self.group1_data))
            self.line_group2.set_data(list(self.time_data), list(self.group2_data))
            self.line_group3.set_data(list(self.time_data), list(self.group3_data))
            self.line_group4.set_data(list(self.time_data), list(self.group4_data))
            self.line_group5.set_data(list(self.time_data), list(self.group5_data))
            self.line_group6.set_data(list(self.time_data), list(self.group6_data))
            
            # Dynamic X-axis: [0, max(current_time * 1.2, 120)]
            # Static Y-axis: [0, 5] (no auto-scaling)
            self.ax.set_xlim(0, max(relative_time*1.2, 120))
        
        return (self.line_group1, self.line_group2, self.line_group3, 
               self.line_group4, self.line_group5, self.line_group6)

    def reset(self):
        """Reset plot data"""
        self.time_data.clear()
        self.group1_data.clear()
        self.group2_data.clear()
        self.group3_data.clear()
        self.group4_data.clear()
        self.group5_data.clear()
        self.group6_data.clear()

        self.last_update_time = 0
        
        # Reset axis limits - static Y, initial X
        self.ax.set_xlim(0, 120)
        self.ax.set_ylim(0, 5)
        
        # Clear line data
        self.line_group1.set_data([], [])
        self.line_group2.set_data([], [])
        self.line_group3.set_data([], [])
        self.line_group4.set_data([], [])
        self.line_group5.set_data([], [])
        self.line_group6.set_data([], [])
        
        self.canvas.draw()
    
    def destroy(self):
        """Clean up resources"""
        if hasattr(self, 'animation'):
            self.animation.event_source.stop()
        self.canvas.get_tk_widget().destroy()


class TemperaturePlot:
    """Live temperature vs time plot - placeholder for Task 16"""
    
    def __init__(self, parent_frame):
        self.parent_frame = parent_frame
        
        # Placeholder label
        self.placeholder = ttk.Label(
            parent_frame,
            text="[Temperature Plot - Task 16]\n\nTemperature plotting will be\nimplemented in Task 16\n\n"
                 "Axis limits: Static Y, Dynamic X\nX = [0, max(time*1.2, 120)]",
            justify=tk.CENTER,
            background="lightyellow"
        )
        self.placeholder.pack(fill='both', expand=True)
    
    def reset(self):
        pass
    
    def destroy(self):
        self.placeholder.destroy()


def test_pressure_plot():
    """Test the pressure, gas concentration, and voltage plots independently"""
    import threading
    from services.controller_manager import get_controller_manager
    
    # Create test window
    root = tk.Tk()
    root.title("Test Pressure & Gas & Voltage Plots")
    root.geometry("1200x800")
    
    # Create frames for both plots side by side
    main_frame = ttk.Frame(root)
    main_frame.pack(fill='both', expand=True, padx=10, pady=10)
    
    # Left side: Pressure & Gas plot
    pressure_frame = ttk.LabelFrame(main_frame, text="Pressure & Gas Concentrations", padding="5")
    pressure_frame.pack(side='left', fill='both', expand=True, padx=(0, 5))
    
    # Right side: Voltage plot
    voltage_frame = ttk.LabelFrame(main_frame, text="Cell Voltages", padding="5")
    voltage_frame.pack(side='right', fill='both', expand=True, padx=(5, 0))
    
    # Create both plots
    pressure_plot = PressurePlot(pressure_frame)
    voltage_plot = VoltagePlot(voltage_frame)
    
    # Start all services via ControllerManager to generate test data
    controller = get_controller_manager()
    if controller.start_all_services():
        print("✅ All services started for plot testing")
    
    def cleanup():
        if controller.is_all_connected():
            controller.stop_all_services()
        pressure_plot.destroy()
        voltage_plot.destroy()
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", cleanup)
    
    print("=" * 60)
    print("PRESSURE & GAS & VOLTAGE PLOT TEST")
    print("=" * 60)
    print("✅ Live pressure & gas concentration plot created")
    print("✅ Live cell voltage plot created (120 cells, 6 groups)")
    print("✅ Data updating from GlobalState")
    print("✅ Static Y-axis, dynamic X-axis for both plots")
    print("\nPressure & Gas Plot (Y: 0-1):")
    print("   • Blue solid: Pressure 1")
    print("   • Red solid: Pressure 2")
    print("   • Green dashed: H₂ from hydrogen side")
    print("   • Magenta dashed: O₂ from oxygen side")
    print("   • Green dotted: H₂ from mixed stream")
    print("\nVoltage Plot (Y: 0-5V):")
    print("   • Blue solid: Group 1 (cells 1-20 avg)")
    print("   • Green solid: Group 2 (cells 21-40 avg)")
    print("   • Red solid: Group 3 (cells 41-60 avg)")
    print("   • Magenta solid: Group 4 (cells 61-80 avg)")
    print("   • Cyan solid: Group 5 (cells 81-100 avg)")
    print("   • Yellow solid: Group 6 (cells 101-120 avg)")
    print("\nClose window when done testing...")
    
    root.mainloop()


if __name__ == "__main__":
    test_pressure_plot() 
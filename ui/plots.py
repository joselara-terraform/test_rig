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
        
        # Data storage for plotting - voltage data
        self.time_data = deque()
        self.total_voltage_data = deque()     # Total stack voltage (normalized)
        self.avg_voltage_data = deque()       # Average cell voltage (normalized)
        self.min_voltage_data = deque()       # Minimum cell voltage (normalized)
        self.max_voltage_data = deque()       # Maximum cell voltage (normalized)
        
        self.last_update_time = 0
        
        # Voltage normalization constants
        self.max_cell_voltage = 2.5   # Maximum expected cell voltage
        self.max_stack_voltage = 60.0 # Maximum expected stack voltage (24 * 2.5V)
        
        # Create the matplotlib figure
        self.fig = Figure(figsize=(6, 4), dpi=80, facecolor='white')
        self.ax = self.fig.add_subplot(111)
        
        # Configure plot appearance
        self.ax.set_title("Cell Voltages vs Time", fontsize=12, fontweight='bold')
        self.ax.set_xlabel("Time (s)", fontsize=10)
        self.ax.set_ylabel("Normalized Voltage", fontsize=10)
        self.ax.grid(True, alpha=0.3)
        
        # Create line objects for voltage measurements
        self.line_total, = self.ax.plot([], [], 'b-', linewidth=2, label='Stack Total', alpha=0.9)
        self.line_avg, = self.ax.plot([], [], 'g-', linewidth=2, label='Cell Average', alpha=0.9)
        self.line_min, = self.ax.plot([], [], 'r--', linewidth=1.5, label='Cell Min', alpha=0.8)
        self.line_max, = self.ax.plot([], [], 'm--', linewidth=1.5, label='Cell Max', alpha=0.8)
        
        # Add legend
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
            return (self.line_total, self.line_avg, self.line_min, self.line_max)
        
        if self.state.test_paused:
            return (self.line_total, self.line_avg, self.line_min, self.line_max)
        
        # Update only if enough time has passed (throttle updates)
        if current_time - self.last_update_time < 0.1:  # 10 Hz max update rate
            return (self.line_total, self.line_avg, self.line_min, self.line_max)
        
        self.last_update_time = current_time
        
        # Use global timer
        relative_time = self.state.timer_value
        
        # Get current cell voltage values and calculate statistics
        cell_voltages = self.state.cell_voltages
        
        if len(cell_voltages) > 0:
            # Calculate voltage statistics
            total_voltage = sum(cell_voltages)
            avg_voltage = total_voltage / len(cell_voltages)
            min_voltage = min(cell_voltages)
            max_voltage = max(cell_voltages)
            
            # Normalize voltages to 0-1 range
            total_normalized = total_voltage / self.max_stack_voltage
            avg_normalized = avg_voltage / self.max_cell_voltage
            min_normalized = min_voltage / self.max_cell_voltage
            max_normalized = max_voltage / self.max_cell_voltage
        else:
            # No data available
            total_normalized = avg_normalized = min_normalized = max_normalized = 0.0
        
        # Add new data points
        self.time_data.append(relative_time)
        self.total_voltage_data.append(total_normalized)
        self.avg_voltage_data.append(avg_normalized)
        self.min_voltage_data.append(min_normalized)
        self.max_voltage_data.append(max_normalized)
        
        # Update line data
        if len(self.time_data) > 0:
            self.line_total.set_data(list(self.time_data), list(self.total_voltage_data))
            self.line_avg.set_data(list(self.time_data), list(self.avg_voltage_data))
            self.line_min.set_data(list(self.time_data), list(self.min_voltage_data))
            self.line_max.set_data(list(self.time_data), list(self.max_voltage_data))
            
            # Dynamic X-axis: [0, max(current_time * 1.2, 120)]
            # Static Y-axis: [0, 1] (no auto-scaling)
            self.ax.set_xlim(0, max(relative_time*1.2, 120))
        
        return (self.line_total, self.line_avg, self.line_min, self.line_max)

    def reset(self):
        """Reset plot data"""
        self.time_data.clear()
        self.total_voltage_data.clear()
        self.avg_voltage_data.clear()
        self.min_voltage_data.clear()
        self.max_voltage_data.clear()

        self.last_update_time = 0
        
        # Reset axis limits - static Y, initial X
        self.ax.set_xlim(0, 120)
        self.ax.set_ylim(0, 1)
        
        # Clear line data
        self.line_total.set_data([], [])
        self.line_avg.set_data([], [])
        self.line_min.set_data([], [])
        self.line_max.set_data([], [])
        
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
    print("✅ Live cell voltage plot created")
    print("✅ Data updating from GlobalState")
    print("✅ Static Y-axis (0-1), dynamic X-axis for both plots")
    print("\nPressure & Gas Plot:")
    print("   • Blue solid: Pressure 1")
    print("   • Red solid: Pressure 2")
    print("   • Green dashed: H₂ from hydrogen side")
    print("   • Magenta dashed: O₂ from oxygen side")
    print("   • Green dotted: H₂ from mixed stream")
    print("\nVoltage Plot:")
    print("   • Blue solid: Stack Total (normalized)")
    print("   • Green solid: Cell Average (normalized)")
    print("   • Red dashed: Cell Min (normalized)")
    print("   • Magenta dashed: Cell Max (normalized)")
    print("\nClose window when done testing...")
    
    root.mainloop()


if __name__ == "__main__":
    test_pressure_plot() 
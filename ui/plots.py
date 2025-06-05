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
        self.line1, = self.ax.plot([], [], 'b-', linewidth=2, label='H_2 Header')
        self.line2, = self.ax.plot([], [], 'r-', linewidth=2, label='O_2 Header')
        
        # Create line objects for gas concentrations - only 3 BGA series
        self.line_h2_h_side, = self.ax.plot([], [], 'g--', linewidth=1.5, label='H_2 Ratio 1', alpha=0.8)
        self.line_o2_o_side, = self.ax.plot([], [], 'm--', linewidth=1.5, label='O_2 Ratio 1', alpha=0.8)
        self.line_h2_mixed, = self.ax.plot([], [], 'g:', linewidth=1.5, label='H_2 Ratio 2', alpha=0.7)
        
        # Add legend with smaller font to fit entries
        self.ax.legend(loc='upper right', fontsize=10, ncol=1)
        
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
        self.ax.legend(loc='upper right', fontsize=10, ncol=1)
        
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
    """Live temperature vs time plot"""
    
    def __init__(self, parent_frame, max_points: int = 300):
        self.parent_frame = parent_frame
        self.state = get_global_state()
        self.max_points = max_points
        
        # Data storage for plotting - temperature data (8 thermocouple channels)
        self.time_data = deque()
        self.inlet_temp_data = deque()     # CH0: Inlet water temp
        self.outlet_temp_data = deque()    # CH1: Outlet water temp
        self.stack_temp1_data = deque()    # CH2: Stack temperature 1
        self.stack_temp2_data = deque()    # CH3: Stack temperature 2
        self.ambient_temp_data = deque()   # CH4: Ambient temperature
        self.cooling_temp_data = deque()   # CH5: Cooling system temp
        self.gas_temp_data = deque()       # CH6: Gas output temp
        self.case_temp_data = deque()      # CH7: Electronics case temp
        
        self.last_update_time = 0
        
        # Create the matplotlib figure
        self.fig = Figure(figsize=(6, 4), dpi=80, facecolor='white')
        self.ax = self.fig.add_subplot(111)
        
        # Configure plot appearance
        self.ax.set_title("Temperatures vs Time", fontsize=12, fontweight='bold')
        self.ax.set_xlabel("Time (s)", fontsize=10)
        self.ax.set_ylabel("Temperature (°C)", fontsize=10)
        self.ax.grid(True, alpha=0.3)
        
        # Create line objects for temperature channels
        self.line_TC1, = self.ax.plot([], [], 'b-', linewidth=2, label='Stack 1', alpha=0.9)
        self.line_TC2, = self.ax.plot([], [], 'r-', linewidth=2, label='Stack 2', alpha=0.9)
        self.line_TC3, = self.ax.plot([], [], 'g-', linewidth=2, label='Stack 3', alpha=0.9)
        self.line_TC4, = self.ax.plot([], [], 'm-', linewidth=2, label='Stack 4', alpha=0.9)
        self.line_TC5, = self.ax.plot([], [], 'c--', linewidth=1.5, label='H_2 Bubbler', alpha=0.8)
        self.line_TC6, = self.ax.plot([], [], 'y--', linewidth=1.5, label='O_2 Bubbler', alpha=0.8)
        self.line_TC7, = self.ax.plot([], [], 'orange', linewidth=1.5, label='H_2 Line HEX', alpha=0.8)
        self.line_TC8, = self.ax.plot([], [], 'brown', linewidth=1.5, label='O_2 Line HEX', alpha=0.8)
        
        # Add legend with smaller font to fit entries
        self.ax.legend(loc='upper right', fontsize=10, ncol=1)
        
        # Set initial axis limits - static Y (0-100°C), dynamic X
        self.ax.set_xlim(0, 120)   # Initial X limit
        self.ax.set_ylim(0, 100)   # Static Y limit (0-100°C range)
        
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
            return (self.line_TC1, self.line_TC2, self.line_TC3, self.line_TC4,
                   self.line_TC5, self.line_TC6, self.line_TC7, self.line_TC8)
        
        if self.state.test_paused:
            return (self.line_TC1, self.line_TC2, self.line_TC3, self.line_TC4,
                   self.line_TC5, self.line_TC6, self.line_TC7, self.line_TC8)
        
        # Update only if enough time has passed (throttle updates)
        if current_time - self.last_update_time < 0.1:  # 10 Hz max update rate
            return (self.line_TC1, self.line_TC2, self.line_TC3, self.line_TC4,
                   self.line_TC5, self.line_TC6, self.line_TC7, self.line_TC8)
        
        self.last_update_time = current_time
        
        # Use global timer
        relative_time = self.state.timer_value
        
        # Get current temperature values from the 8 thermocouple channels
        temp_values = self.state.temperature_values
        
        if len(temp_values) >= 8:
            # Extract temperature values for each channel
            inlet_temp = temp_values[0]     # CH0: Inlet water temp
            outlet_temp = temp_values[1]    # CH1: Outlet water temp
            stack_temp1 = temp_values[2]    # CH2: Stack temperature 1
            stack_temp2 = temp_values[3]    # CH3: Stack temperature 2
            ambient_temp = temp_values[4]   # CH4: Ambient temperature
            cooling_temp = temp_values[5]   # CH5: Cooling system temp
            gas_temp = temp_values[6]       # CH6: Gas output temp
            case_temp = temp_values[7]      # CH7: Electronics case temp
        else:
            # No data available or insufficient data
            inlet_temp = outlet_temp = stack_temp1 = stack_temp2 = 0.0
            ambient_temp = cooling_temp = gas_temp = case_temp = 0.0
        
        # Add new data points
        self.time_data.append(relative_time)
        self.inlet_temp_data.append(inlet_temp)
        self.outlet_temp_data.append(outlet_temp)
        self.stack_temp1_data.append(stack_temp1)
        self.stack_temp2_data.append(stack_temp2)
        self.ambient_temp_data.append(ambient_temp)
        self.cooling_temp_data.append(cooling_temp)
        self.gas_temp_data.append(gas_temp)
        self.case_temp_data.append(case_temp)
        
        # Update line data
        if len(self.time_data) > 0:
            self.line_TC1.set_data(list(self.time_data), list(self.inlet_temp_data))
            self.line_TC2.set_data(list(self.time_data), list(self.outlet_temp_data))
            self.line_TC3.set_data(list(self.time_data), list(self.stack_temp1_data))
            self.line_TC4.set_data(list(self.time_data), list(self.stack_temp2_data))
            self.line_TC5.set_data(list(self.time_data), list(self.ambient_temp_data))
            self.line_TC6.set_data(list(self.time_data), list(self.cooling_temp_data))
            self.line_TC7.set_data(list(self.time_data), list(self.gas_temp_data))
            self.line_TC8.set_data(list(self.time_data), list(self.case_temp_data))
            
            # Dynamic X-axis: [0, max(current_time * 1.2, 120)]
            # Static Y-axis: [0, 100] (no auto-scaling)
            self.ax.set_xlim(0, max(relative_time*1.2, 120))
        
        return (self.line_TC1, self.line_TC2, self.line_TC3, self.line_TC4,
               self.line_TC5, self.line_TC6, self.line_TC7, self.line_TC8)

    def reset(self):
        """Reset plot data"""
        self.time_data.clear()
        self.inlet_temp_data.clear()
        self.outlet_temp_data.clear()
        self.stack_temp1_data.clear()
        self.stack_temp2_data.clear()
        self.ambient_temp_data.clear()
        self.cooling_temp_data.clear()
        self.gas_temp_data.clear()
        self.case_temp_data.clear()

        self.last_update_time = 0
        
        # Reset axis limits - static Y, initial X
        self.ax.set_xlim(0, 120)
        self.ax.set_ylim(0, 100)
        
        # Clear line data
        self.line_TC1.set_data([], [])
        self.line_TC2.set_data([], [])
        self.line_TC3.set_data([], [])
        self.line_TC4.set_data([], [])
        self.line_TC5.set_data([], [])
        self.line_TC6.set_data([], [])
        self.line_TC7.set_data([], [])
        self.line_TC8.set_data([], [])
        
        self.canvas.draw()
    
    def destroy(self):
        """Clean up resources"""
        if hasattr(self, 'animation'):
            self.animation.event_source.stop()
        self.canvas.get_tk_widget().destroy()


def test_pressure_plot():
    """Test the pressure, gas concentration, voltage, and temperature plots independently"""
    import threading
    from services.controller_manager import get_controller_manager
    
    # Create test window
    root = tk.Tk()
    root.title("Test All Plots - Pressure, Gas, Voltage & Temperature")
    root.geometry("1600x900")
    
    # Create frames for all plots in a 2x2 grid
    main_frame = ttk.Frame(root)
    main_frame.pack(fill='both', expand=True, padx=10, pady=10)
    
    # Configure grid weights
    main_frame.columnconfigure(0, weight=1)
    main_frame.columnconfigure(1, weight=1)
    main_frame.rowconfigure(0, weight=1)
    main_frame.rowconfigure(1, weight=1)
    
    # Top-left: Pressure & Gas plot
    pressure_frame = ttk.LabelFrame(main_frame, text="Pressure & Gas Concentrations", padding="5")
    pressure_frame.grid(row=0, column=0, padx=(0, 5), pady=(0, 5), sticky='nsew')
    
    # Top-right: Voltage plot
    voltage_frame = ttk.LabelFrame(main_frame, text="Cell Voltages", padding="5")
    voltage_frame.grid(row=0, column=1, padx=(5, 0), pady=(0, 5), sticky='nsew')
    
    # Bottom-left: Temperature plot
    temperature_frame = ttk.LabelFrame(main_frame, text="Temperatures", padding="5")
    temperature_frame.grid(row=1, column=0, padx=(0, 5), pady=(5, 0), sticky='nsew')
    
    # Bottom-right: Info panel
    info_frame = ttk.LabelFrame(main_frame, text="Plot Information", padding="5")
    info_frame.grid(row=1, column=1, padx=(5, 0), pady=(5, 0), sticky='nsew')
    
    # Create all three plots
    pressure_plot = PressurePlot(pressure_frame)
    voltage_plot = VoltagePlot(voltage_frame)
    temperature_plot = TemperaturePlot(temperature_frame)
    
    # Create info display
    info_text = tk.Text(info_frame, wrap=tk.WORD, font=("Courier", 8))
    info_text.pack(fill='both', expand=True)
    
    info_content = """PLOT TESTING - ALL LIVE PLOTS
    
🔥 Pressure & Gas (Y: 0-1):
   • Blue solid: Pressure 1
   • Red solid: Pressure 2  
   • Green dashed: H₂ (H-side)
   • Magenta dashed: O₂ (O-side)
   • Green dotted: H₂ (mixed)

⚡ Cell Voltages (Y: 0-5V):
   • Blue: Group 1 (cells 1-20)
   • Green: Group 2 (cells 21-40)
   • Red: Group 3 (cells 41-60)
   • Magenta: Group 4 (cells 61-80)
   • Cyan: Group 5 (cells 81-100)
   • Yellow: Group 6 (cells 101-120)

🌡️  Temperatures (Y: 0-100°C):
   • Blue: Inlet water temp
   • Red: Outlet water temp
   • Green: Stack temp 1
   • Magenta: Stack temp 2
   • Cyan dashed: Ambient temp
   • Yellow dashed: Cooling temp
   • Orange: Gas output temp
   • Brown: Case temp

ARCHITECTURE:
✅ Static Y-axis, dynamic X-axis
✅ Same deque() storage pattern
✅ Same update throttling (10Hz)
✅ Same state checking logic
✅ Thread-safe operations
✅ Reset functionality

Close window when done testing..."""
    
    info_text.insert('1.0', info_content)
    info_text.config(state='disabled')
    
    # Start all services via ControllerManager to generate test data
    controller = get_controller_manager()
    if controller.start_all_services():
        print("✅ All services started for plot testing")
    
    def cleanup():
        if controller.is_all_connected():
            controller.stop_all_services()
        pressure_plot.destroy()
        voltage_plot.destroy()
        temperature_plot.destroy()
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", cleanup)
    
    print("=" * 70)
    print("ALL PLOTS TEST: PRESSURE, GAS, VOLTAGE & TEMPERATURE")
    print("=" * 70)
    print("✅ Live pressure & gas concentration plot created")
    print("✅ Live cell voltage plot created (120 cells, 6 groups)")
    print("✅ Live temperature plot created (8 thermocouples)")
    print("✅ Data updating from GlobalState")
    print("✅ Static Y-axis, dynamic X-axis for all plots")
    print("\nPressure & Gas Plot (Y: 0-1):")
    print("   • 2 pressure sensors + 3 gas concentrations")
    print("\nVoltage Plot (Y: 0-5V):")
    print("   • 6 group averages (20 cells each)")
    print("\nTemperature Plot (Y: 0-100°C):")
    print("   • 8 thermocouple channels")
    print("   • Inlet, outlet, stack, ambient, cooling, gas, case temps")
    print("\nAll plots follow same proven architecture!")
    print("Close window when done testing...")
    
    root.mainloop()


if __name__ == "__main__":
    test_pressure_plot() 
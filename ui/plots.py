"""
Real-time plotting components for AWE test rig dashboard
Includes pressure, gas concentration, voltage, and temperature plots

TEMPORARY MODIFICATION: VoltagePlot shows channels 96-110 individually
TO REVERT: Search for "TEMPORARY CHANGE" and "ORIGINAL CODE TO RESTORE" comments
and replace the modified sections with the original group averaging code.
"""

import tkinter as tk
from tkinter import ttk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import matplotlib.animation as animation
from collections import deque
import time
from typing import List, Tuple, Dict
from core.state import get_global_state


class PressurePlot:
    """Live pressure and gas concentration vs time plot"""
    
    def __init__(self, parent_frame, max_points: int = 300):
        self.parent_frame = parent_frame
        self.state = get_global_state()
        self.max_points = max_points
        
        # Data storage - store ALL pressure/gas data continuously
        self.time_data = deque()  # Store entire test history
        self.all_pressure_data = {}  # Store data for all 5 pressure sensors continuously
        self.all_gas_data = {}  # Store data for all 3 gas analyzers continuously
        
        # Initialize deques for all 5 pressure sensors
        for i in range(5):
            self.all_pressure_data[i] = deque()
            
        # Initialize deques for all 3 gas concentration channels
        for i in range(3):
            self.all_gas_data[i] = deque()
        
        self.last_update_time = 0
        
        # Create the matplotlib figure
        self.fig = Figure(figsize=(6, 4), dpi=80, facecolor='white')
        self.ax = self.fig.add_subplot(111)
        
        # Get colormaps for different data types
        self.pressure_colors = plt.cm.get_cmap('Set1', 5)  # 5 pressure channels
        self.gas_colors = plt.cm.get_cmap('Set2', 3)  # 3 gas channels
        
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
        """Update plot with new data from GlobalState based on visible channels."""
        current_time = time.time()
        
        # Throttle updates
        if current_time - self.last_update_time < 0.1:  # 10 Hz max update rate
            return
        self.last_update_time = current_time

        # Check test states
        if self.state.emergency_stop or not self.state.test_running or self.state.test_paused:
            return

        relative_time = self.state.timer_value
        self.time_data.append(relative_time)
        
        # CONTINUOUSLY store data for ALL pressure channels
        pressure_values = self.state.pressure_values
        for i in range(5):
            if len(pressure_values) > i:
                self.all_pressure_data[i].append(pressure_values[i])
            else:
                self.all_pressure_data[i].append(0.0)
        
        # CONTINUOUSLY store data for ALL gas concentration channels
        gas_concentrations = self.state.gas_concentrations
        enhanced_gas_data = getattr(self.state, 'enhanced_gas_data', [])
        
        # Store gas concentration data
        if enhanced_gas_data and len(enhanced_gas_data) >= 3:
            # Use primary gas concentrations (convert to 0-1 range)
            for i in range(3):
                primary_conc = enhanced_gas_data[i]['primary_gas_concentration'] if enhanced_gas_data[i]['primary_gas_concentration'] else 0.0
                self.all_gas_data[i].append(primary_conc / 100.0)  # Convert percentage to fraction
        else:
            # Fallback to legacy gas concentrations
            gas_values = [
                (gas_concentrations[0]['H2'] / 100.0) if len(gas_concentrations) > 0 else 0.0,
                (gas_concentrations[1]['O2'] / 100.0) if len(gas_concentrations) > 1 else 0.0,
                (gas_concentrations[2]['H2'] / 100.0) if len(gas_concentrations) > 2 else 0.0
            ]
            for i in range(3):
                self.all_gas_data[i].append(gas_values[i])
        
        # Get currently visible pressure channels
        visible_pressure_channels = sorted(list(self.state.visible_pressure_channels))
        visible_gas_channels = sorted(list(self.state.visible_gas_channels))
        
        # --- Redraw the entire plot for dynamic channel visibility ---
        self.ax.clear()
        
        # Configure plot appearance
        self.ax.set_title("Pressure & Gas Concentrations vs Time", fontsize=12, fontweight='bold')
        self.ax.set_xlabel("Time (s)", fontsize=10)
        self.ax.set_ylabel("Pressure (PSI) / Gas Fraction", fontsize=10)
        self.ax.grid(True, alpha=0.3)

        # Channel names
        pressure_names = ["H₂ Header", "O₂ Header", "Post MS", "Pre MS", "H₂ BP"]
        gas_names = ["BGA-H2", "BGA-O2", "BGA-DO"]
        
        has_visible_channels = False
        
        # Plot visible pressure channels
        for channel_idx in visible_pressure_channels:
            if self.time_data and self.all_pressure_data[channel_idx]:
                time_list = list(self.time_data)
                data_list = list(self.all_pressure_data[channel_idx])
                
                self.ax.plot(time_list, data_list, 
                             color=self.pressure_colors(channel_idx), 
                             linewidth=2, 
                             label=pressure_names[channel_idx],
                             linestyle='-')
                has_visible_channels = True
        
        # Plot visible gas channels
        for channel_idx in visible_gas_channels:
            if self.time_data and self.all_gas_data[channel_idx]:
                time_list = list(self.time_data)
                data_list = list(self.all_gas_data[channel_idx])
                
                self.ax.plot(time_list, data_list, 
                             color=self.gas_colors(channel_idx), 
                             linewidth=1.5, 
                             alpha=0.8,
                             label=gas_names[channel_idx],
                             linestyle='--')
                has_visible_channels = True

        if not has_visible_channels:
            self.ax.text(0.5, 0.5, "No channels selected", ha='center', va='center', transform=self.ax.transAxes)

        # Set axis limits
        self.ax.set_xlim(0, max(relative_time * 1.2, 120))
        self.ax.set_ylim(0, 1)  # 0-1 range for mixed pressure/gas display

        # Update legend
        if has_visible_channels:
            self.ax.legend(loc='upper right', fontsize=10, ncol=1)

    def reset(self):
        """Reset plot data"""
        self.time_data.clear()
        
        # Clear all pressure and gas data
        for i in range(5):
            self.all_pressure_data[i].clear()
        for i in range(3):
            self.all_gas_data[i].clear()

        self.last_update_time = 0
        
        # Clear the plot and redraw
        self.ax.clear()
        self.ax.set_title("Pressure & Gas Concentrations vs Time", fontsize=12, fontweight='bold')
        self.ax.set_xlabel("Time (s)", fontsize=10)
        self.ax.set_ylabel("Pressure (PSI) / Gas Fraction", fontsize=10)
        self.ax.grid(True, alpha=0.3)
        self.ax.set_xlim(0, 120)
        self.ax.set_ylim(0, 1)
        self.ax.text(0.5, 0.5, "Test not started", ha='center', va='center', transform=self.ax.transAxes)
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
        
        # Data storage - store ALL channel data continuously, regardless of visibility
        self.time_data = deque()  # Store entire test history
        self.all_channel_data = {}  # Store data for ALL 120 channels continuously
        
        # Initialize deques for all 120 channels
        for i in range(120):
            self.all_channel_data[i] = deque()

        # Plotting objects
        self.last_update_time = 0
        self.fig = Figure(figsize=(6, 4), dpi=80, facecolor='white')
        self.ax = self.fig.add_subplot(111)
        
        # Get a colormap
        self.colors = plt.cm.get_cmap('tab20', 120)

        # Create canvas and add to parent frame
        self.canvas = FigureCanvasTkAgg(self.fig, self.parent_frame)
        self.canvas.get_tk_widget().pack(fill='both', expand=True)
        
        # Start animation
        self.animation = animation.FuncAnimation(
            self.fig, self._update_plot, interval=100, blit=False, cache_frame_data=False
        )
        
        self.canvas.draw()
    
    def _update_plot(self, frame):
        """Update plot with new data from GlobalState based on visible channels."""
        current_time = time.time()
        
        # Throttle updates
        if current_time - self.last_update_time < 0.1:  # 10 Hz max update rate
            return
        self.last_update_time = current_time

        # Check test states
        if self.state.emergency_stop or not self.state.test_running or self.state.test_paused:
            return

        relative_time = self.state.timer_value
        self.time_data.append(relative_time)
        
        cell_voltages = self.state.cell_voltages
        
        # CONTINUOUSLY store data for ALL channels (background data collection)
        for channel_idx in range(120):
            if len(cell_voltages) > channel_idx:
                self.all_channel_data[channel_idx].append(cell_voltages[channel_idx])
            else:
                self.all_channel_data[channel_idx].append(0.0)
        
        # Get currently visible channels for display
        visible_channels = sorted(list(self.state.visible_voltage_channels))
        
        # --- Redraw the entire plot for dynamic channel visibility ---
        self.ax.clear()
        
        # Configure plot appearance
        self.ax.set_title("Cell Voltages vs Time", fontsize=12, fontweight='bold')
        self.ax.set_xlabel("Time (s)", fontsize=10)
        self.ax.set_ylabel("Voltage (V)", fontsize=10)
        self.ax.grid(True, alpha=0.3)

        if not visible_channels:
            # If no channels are selected, just show an empty plot
            self.ax.text(0.5, 0.5, "No channels selected", ha='center', va='center', transform=self.ax.transAxes)
        else:
            # Plot only the selected channels, but with their FULL historical data
            for channel_idx in visible_channels:
                if self.time_data and self.all_channel_data[channel_idx]:
                    # Use the complete historical data for this channel
                    time_list = list(self.time_data)
                    data_list = list(self.all_channel_data[channel_idx])
                    
                    self.ax.plot(time_list, data_list, 
                                 color=self.colors(channel_idx / 120.0), 
                                 linewidth=1.5, 
                                 label=f'Ch {channel_idx + 1}')

        # Set axis limits to show entire history
        self.ax.set_xlim(0, max(relative_time * 1.2, 120))
        self.ax.set_ylim(0, 5)

        # Update legend
        if visible_channels:
            # Adjust legend size and columns based on number of channels
            num_channels = len(visible_channels)
            if num_channels > 20:
                ncol = 2
                fontsize = 8
            else:
                ncol = 1
                fontsize = 10
            self.ax.legend(loc='upper right', fontsize=fontsize, ncol=ncol)

    def reset(self):
        """Reset plot data"""
        self.time_data.clear()
        
        # Clear all channel data
        for i in range(120):
            self.all_channel_data[i].clear()
            
        self.last_update_time = 0
        
        # Clear the plot and redraw
        self.ax.clear()
        self.ax.set_title("Cell Voltages vs Time", fontsize=12, fontweight='bold')
        self.ax.set_xlabel("Time (s)", fontsize=10)
        self.ax.set_ylabel("Voltage (V)", fontsize=10)
        self.ax.grid(True, alpha=0.3)
        self.ax.set_xlim(0, 120)
        self.ax.set_ylim(0, 5)
        self.ax.text(0.5, 0.5, "Test not started", ha='center', va='center', transform=self.ax.transAxes)
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
        
        # Data storage - store ALL temperature data continuously
        self.time_data = deque()  # Store entire test history
        self.all_temperature_data = {}  # Store data for all 8 temperature sensors continuously
        
        # Initialize deques for all 8 temperature sensors
        for i in range(8):
            self.all_temperature_data[i] = deque()
        
        self.last_update_time = 0
        
        # Create the matplotlib figure
        self.fig = Figure(figsize=(6, 4), dpi=80, facecolor='white')
        self.ax = self.fig.add_subplot(111)
        
        # Get colormap for temperature channels
        self.colors = plt.cm.get_cmap('tab10', 8)  # 8 temperature channels
        
        # Create canvas and add to parent frame
        self.canvas = FigureCanvasTkAgg(self.fig, parent_frame)
        self.canvas.get_tk_widget().pack(fill='both', expand=True)
        
        # Start animation
        self.animation = animation.FuncAnimation(
            self.fig, self._update_plot, interval=100, blit=False, cache_frame_data=False
        )
        
        self.canvas.draw()
    
    def _update_plot(self, frame):
        """Update plot with new data from GlobalState based on visible channels."""
        current_time = time.time()
        
        # Throttle updates
        if current_time - self.last_update_time < 0.1:  # 10 Hz max update rate
            return
        self.last_update_time = current_time

        # Check test states
        if self.state.emergency_stop or not self.state.test_running or self.state.test_paused:
            return

        relative_time = self.state.timer_value
        self.time_data.append(relative_time)
        
        # CONTINUOUSLY store data for ALL temperature channels
        temp_values = self.state.temperature_values
        for i in range(8):
            if len(temp_values) > i:
                self.all_temperature_data[i].append(temp_values[i])
            else:
                self.all_temperature_data[i].append(0.0)
        
        # Get currently visible temperature channels
        visible_temp_channels = sorted(list(self.state.visible_temperature_channels))
        
        # --- Redraw the entire plot for dynamic channel visibility ---
        self.ax.clear()
        
        # Configure plot appearance
        self.ax.set_title("Temperatures vs Time", fontsize=12, fontweight='bold')
        self.ax.set_xlabel("Time (s)", fontsize=10)
        self.ax.set_ylabel("Temperature (°C)", fontsize=10)
        self.ax.grid(True, alpha=0.3)

        # Temperature channel names
        temp_names = ["Stack 1", "Stack 2", "Stack 3", "Stack 4", "H₂ Bubbler", "O₂ Bubbler", "H₂ Line HEX", "O₂ Line HEX"]
        
        if not visible_temp_channels:
            # If no channels are selected, just show an empty plot
            self.ax.text(0.5, 0.5, "No channels selected", ha='center', va='center', transform=self.ax.transAxes)
        else:
            # Plot only the selected temperature channels with their FULL historical data
            for channel_idx in visible_temp_channels:
                if self.time_data and self.all_temperature_data[channel_idx]:
                    # Use the complete historical data for this channel
                    time_list = list(self.time_data)
                    data_list = list(self.all_temperature_data[channel_idx])
                    
                    # Choose line style based on channel type
                    if channel_idx < 4:  # Stack temperatures (0-3)
                        linestyle = '-'
                        linewidth = 2
                        alpha = 0.9
                    else:  # Other temperatures (4-7)
                        linestyle = '--'
                        linewidth = 1.5
                        alpha = 0.8
                    
                    self.ax.plot(time_list, data_list, 
                                 color=self.colors(channel_idx), 
                                 linewidth=linewidth, 
                                 linestyle=linestyle,
                                 alpha=alpha,
                                 label=temp_names[channel_idx])

        # Set axis limits
        self.ax.set_xlim(0, max(relative_time * 1.2, 120))
        self.ax.set_ylim(0, 100)  # 0-100°C range

        # Update legend
        if visible_temp_channels:
            # Adjust legend size based on number of channels
            num_channels = len(visible_temp_channels)
            if num_channels > 6:
                fontsize = 8
            else:
                fontsize = 10
            self.ax.legend(loc='upper right', fontsize=fontsize, ncol=1)

    def reset(self):
        """Reset plot data"""
        self.time_data.clear()
        
        # Clear all temperature data
        for i in range(8):
            self.all_temperature_data[i].clear()
            
        self.last_update_time = 0
        
        # Clear the plot and redraw
        self.ax.clear()
        self.ax.set_title("Temperatures vs Time", fontsize=12, fontweight='bold')
        self.ax.set_xlabel("Time (s)", fontsize=10)
        self.ax.set_ylabel("Temperature (°C)", fontsize=10)
        self.ax.grid(True, alpha=0.3)
        self.ax.set_xlim(0, 120)
        self.ax.set_ylim(0, 100)
        self.ax.text(0.5, 0.5, "Test not started", ha='center', va='center', transform=self.ax.transAxes)
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
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
from config.device_config import get_device_config


class PressurePlot:
    """Live pressure and gas concentration vs time plot"""
    
    def __init__(self, parent_frame, max_points: int = 300):
        self.parent_frame = parent_frame
        self.state = get_global_state()
        self.device_config = get_device_config()
        self.max_points = max_points
        
        # Data storage - store ALL pressure/gas data continuously
        self.time_data = deque()  # Store entire test history
        self.all_pressure_data = {}  # Store data for all 5 pressure sensors continuously
        self.all_gas_data = {}  # Store data for all 3 gas analyzers continuously
        
        # Initialize deques for all 6 pressure sensors
        for i in range(6):
            self.all_pressure_data[i] = deque()
            
        # Initialize deques for all 3 gas concentration channels
        for i in range(3):
            self.all_gas_data[i] = deque()
        
        self.last_update_time = 0
        
        # Create the matplotlib figure
        self.fig = Figure(figsize=(6, 4), dpi=80, facecolor='white')
        self.ax = self.fig.add_subplot(111)
        
        # Get colormaps for different data types
        self.pressure_colors = plt.cm.get_cmap('Set1', 6)  # 6 pressure channels
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
        for i in range(6):
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

        # Channel names (dynamically loaded from devices.yaml)
        pressure_names = self.device_config.get_pressure_channel_names()  # Only pressure sensors
        gas_names = self.device_config.get_bga244_unit_names()
        
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
        for i in range(6):
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
        self.device_config = get_device_config()
        self.max_points = max_points
        
        # Data storage - store ALL temperature and flowrate data continuously
        self.time_data = deque()  # Store entire test history
        self.all_temperature_data = {}  # Store data for all 8 temperature sensors continuously
        self.flowrate_data = deque()  # Store flowrate data
        
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
        
        # CONTINUOUSLY store flowrate data
        flowrate_val = self.state.flowrate_value
        self.flowrate_data.append(flowrate_val)
        
        # Get currently visible temperature and flowrate channels
        visible_temp_channels = sorted(list(self.state.visible_temperature_channels))
        visible_flowrate_channels = sorted(list(self.state.visible_flowrate_channels))
        
        # --- Redraw the entire plot for dynamic channel visibility ---
        self.ax.clear()
        
        # Configure plot appearance
        self.ax.set_title("Temperatures & Flowrate vs Time", fontsize=12, fontweight='bold')
        self.ax.set_xlabel("Time (s)", fontsize=10)
        self.ax.set_ylabel("Temperature (°C) / Flowrate (SLM)", fontsize=10)
        self.ax.grid(True, alpha=0.3)

        # Temperature channel names (dynamically loaded from devices.yaml)
        temp_names = self.device_config.get_pico_tc08_channel_names()
        
        has_visible_channels = False
        
        # Plot visible temperature channels
        if visible_temp_channels:
            # Plot only the selected temperature channels with their FULL historical data
            for channel_idx in visible_temp_channels:
                if self.time_data and self.all_temperature_data[channel_idx]:
                    # Use the complete historical data for this channel
                    time_list = list(self.time_data)
                    data_list = list(self.all_temperature_data[channel_idx])
                    
                    # Choose line style based on channel type
                    if channel_idx < 4:  # TC01-TC04 (0-3)
                        linestyle = '-'
                        linewidth = 2
                        alpha = 0.9
                    else:  # TC05-TC08 (4-7)
                        linestyle = '--'
                        linewidth = 1.5
                        alpha = 0.8
                    
                    self.ax.plot(time_list, data_list, 
                                 color=self.colors(channel_idx), 
                                 linewidth=linewidth, 
                                 linestyle=linestyle,
                                 alpha=alpha,
                                 label=temp_names[channel_idx])
                    has_visible_channels = True
        
        # Plot visible flowrate channels
        if visible_flowrate_channels and 0 in visible_flowrate_channels:
            if self.time_data and self.flowrate_data:
                time_list = list(self.time_data)
                data_list = list(self.flowrate_data)
                
                self.ax.plot(time_list, data_list, 
                             color='red', 
                             linewidth=2, 
                             linestyle='-',
                             alpha=1.0,
                             label="Flowrate")
                has_visible_channels = True
        
        if not has_visible_channels:
            # If no channels are selected, just show an empty plot
            self.ax.text(0.5, 0.5, "No channels selected", ha='center', va='center', transform=self.ax.transAxes)

        # Set axis limits
        self.ax.set_xlim(0, max(relative_time * 1.2, 120))
        self.ax.set_ylim(0, 150)

        # Update legend
        if has_visible_channels:
            # Adjust legend size based on number of channels
            total_channels = len(visible_temp_channels) + len(visible_flowrate_channels)
            if total_channels > 6:
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
            
        # Clear flowrate data
        self.flowrate_data.clear()
            
        self.last_update_time = 0
        
        # Clear the plot and redraw
        self.ax.clear()
        self.ax.set_title("Temperatures & Flowrate vs Time", fontsize=12, fontweight='bold')
        self.ax.set_xlabel("Time (s)", fontsize=10)
        self.ax.set_ylabel("Temperature (°C) / Flowrate (SLM)", fontsize=10)
        self.ax.grid(True, alpha=0.3)
        self.ax.set_xlim(0, 120)
        self.ax.set_ylim(0, 150)
        self.ax.text(0.5, 0.5, "Test not started", ha='center', va='center', transform=self.ax.transAxes)
        self.canvas.draw()
    
    def destroy(self):
        """Clean up resources"""
        if hasattr(self, 'animation'):
            self.animation.event_source.stop()
        self.canvas.get_tk_widget().destroy()


class CurrentPlot:
    """Live current vs time plot"""
    
    def __init__(self, parent_frame, max_points: int = 300):
        self.parent_frame = parent_frame
        self.state = get_global_state()
        self.max_points = max_points
        
        # Data storage - store current data continuously
        self.time_data = deque()  # Store entire test history
        self.current_data = deque()  # Store current sensor data
        
        self.last_update_time = 0
        
        # Create the matplotlib figure
        self.fig = Figure(figsize=(6, 4), dpi=80, facecolor='white')
        self.ax = self.fig.add_subplot(111)
        
        # Create canvas and add to parent frame
        self.canvas = FigureCanvasTkAgg(self.fig, parent_frame)
        self.canvas.get_tk_widget().pack(fill='both', expand=True)
        
        # Start animation
        self.animation = animation.FuncAnimation(
            self.fig, self._update_plot, interval=100, blit=False, cache_frame_data=False
        )
        
        self.canvas.draw()
    
    def _update_plot(self, frame):
        """Update plot with new data from GlobalState."""
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
        
        # Store current data continuously
        current_value = self.state.current_value
        self.current_data.append(current_value)
        
        # Check if current channel is visible (for future extensibility)
        visible_current = getattr(self.state, 'visible_current_channels', {0})
        show_current = 0 in visible_current
        
        # --- Redraw the entire plot ---
        self.ax.clear()
        
        # Configure plot appearance
        self.ax.set_title("Current vs Time", fontsize=12, fontweight='bold')
        self.ax.set_xlabel("Time (s)", fontsize=10)
        self.ax.set_ylabel("Current (A)", fontsize=10)
        self.ax.grid(True, alpha=0.3)

        if not show_current:
            # If current channel not selected, show empty plot
            self.ax.text(0.5, 0.5, "Current channel not selected", ha='center', va='center', transform=self.ax.transAxes)
        else:
            # Plot current data with full historical data
            if self.time_data and self.current_data:
                time_list = list(self.time_data)
                data_list = list(self.current_data)
                
                self.ax.plot(time_list, data_list, 
                             color='blue', 
                             linewidth=2, 
                             label='Stack Current')

        # Set axis limits
        self.ax.set_xlim(0, max(relative_time * 1.2, 120))
        self.ax.set_ylim(0, 110)

        # Update legend
        if show_current:
            self.ax.legend(loc='upper right', fontsize=10)

    def reset(self):
        """Reset plot data"""
        self.time_data.clear()
        self.current_data.clear()
        self.last_update_time = 0
        
        # Clear the plot and redraw
        self.ax.clear()
        self.ax.set_title("Current vs Time", fontsize=12, fontweight='bold')
        self.ax.set_xlabel("Time (s)", fontsize=10)
        self.ax.set_ylabel("Current (A)", fontsize=10)
        self.ax.grid(True, alpha=0.3)
        self.ax.set_xlim(0, 120)
        self.ax.set_ylim(0, 110)
        self.ax.text(0.5, 0.5, "Test not started", ha='center', va='center', transform=self.ax.transAxes)
        self.canvas.draw()
    
    def destroy(self):
        """Clean up resources"""
        if hasattr(self, 'animation'):
            self.animation.event_source.stop()
        self.canvas.get_tk_widget().destroy()


    test_pressure_plot() 
#!/usr/bin/env python3
"""
Dashboard window with 2x2 grid layout for AWE test rig

Valve mapping (matches NI cDAQ hardware configuration):
- Valve 1: KOH Storage    (cDAQ9187-23E902CMod2/port0/line0)
- Valve 2: DI Storage     (cDAQ9187-23E902CMod2/port0/line1)  
- Valve 3: Stack Drain    (cDAQ9187-23E902CMod2/port0/line2)
- Valve 4: N2 Purge       (cDAQ9187-23E902CMod2/port0/line3)
- Pump:    Pump           (cDAQ9187-23E902CMod2/port0/line4)
"""

import tkinter as tk
from tkinter import ttk, messagebox, PhotoImage
import os
from .controls import ControlPanel
from .status_indicators import StatusIndicators
from .plots import PressurePlot, VoltagePlot, TemperaturePlot, CurrentPlot
from core.state import get_global_state
from utils.logger import log


class Dashboard:
    """Main dashboard window with controls, status indicators, and 2x2 grid layout"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("AWE Electrolyzer Test Rig - Dashboard")
        
        # Set window icon
        self._set_window_icon()
        
        # Maximize the window - cross-platform approach
        self._maximize_window()
        
        # Get global state
        self.state = get_global_state()
        self.update_job = None
        
        # Plot objects
        self.pressure_plot = None
        self.voltage_plot = None
        self.temperature_plot = None
        self.current_plot = None
        
        # Set up window close protocol
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        
        # Create main container
        main_container = ttk.Frame(root, padding="5")
        main_container.pack(fill='both', expand=True)
        
        # Configure main container
        main_container.columnconfigure(0, weight=1)
        main_container.rowconfigure(2, weight=1)  # Give weight to the grid section
        
        # Add control panel at the top
        self.control_panel = ControlPanel(main_container, plot_reset_callback=self.reset_plots)
        
        # Create horizontal container for status indicators and actuator controls
        status_container = ttk.Frame(main_container)
        status_container.pack(fill='x', pady=5)
        
        # Configure columns for 50/50 split
        status_container.columnconfigure(0, weight=1)
        status_container.columnconfigure(1, weight=1)
        
        # Left side: Hardware Connection Status
        status_left_frame = ttk.Frame(status_container)
        status_left_frame.grid(row=0, column=0, sticky='nsew', padx=(0, 2))
        self.status_indicators = StatusIndicators(status_left_frame)
        
        # Right side: Actuator Controls (empty for now)
        status_right_frame = ttk.Frame(status_container)
        status_right_frame.grid(row=0, column=1, sticky='nsew', padx=(2, 0))
        
        # Create Actuator Controls section
        actuator_controls_frame = ttk.LabelFrame(status_right_frame, text="Actuator Controls", padding="10")
        actuator_controls_frame.pack(fill='both', expand=True)
        
        # Add actuator controls to this section
        self._create_actuator_controls(actuator_controls_frame)
        
        # Create main frame for 2x2 grid
        self.main_frame = ttk.Frame(main_container, padding="5")
        self.main_frame.pack(fill='both', expand=True, pady=(5, 0))
        
        # Configure grid weights for responsive resizing with uniform sizing
        self.main_frame.columnconfigure(0, weight=1, uniform="cols")
        self.main_frame.columnconfigure(1, weight=1, uniform="cols")
        self.main_frame.rowconfigure(0, weight=1, uniform="rows")
        self.main_frame.rowconfigure(1, weight=1, uniform="rows")
        
        # Set minimum size for uniform grid
        self.main_frame.grid_columnconfigure(0, minsize=200)
        self.main_frame.grid_columnconfigure(1, minsize=200)
        self.main_frame.grid_rowconfigure(0, minsize=150)
        self.main_frame.grid_rowconfigure(1, minsize=150)
        
        self._create_widgets()
        self._start_status_updates()
    
    def _maximize_window(self):
        """Maximize the window on Windows"""
        try:
            # Windows maximization
            self.root.state('zoomed')
            log.success("System", "Dashboard window maximized")
            
        except Exception as e:
            # Fallback to large window if maximization fails
            log.warning("System", f"Could not maximize window: {e}", [
                "→ Using fallback large window size"
            ])
            self.root.geometry("1400x900")
    
    def _set_window_icon(self):
        """Set the window icon using the favicon file"""
        try:
            # Get the path to the assets directory
            script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            
            # Method 1: For .ico files (Windows preferred)
            icon_path_ico = os.path.join(script_dir, "assets", "favicon.ico")
            if os.path.exists(icon_path_ico):
                self.root.iconbitmap(icon_path_ico)
                log.success("System", f"Window icon loaded: {icon_path_ico}")
                return
            
            # Method 2: For .png files (cross-platform)
            icon_path_png = os.path.join(script_dir, "assets", "favicon-32x32.png")
            if os.path.exists(icon_path_png):
                icon_image = PhotoImage(file=icon_path_png)
                self.root.iconphoto(True, icon_image)
                # Keep a reference to prevent garbage collection
                self.root.icon_image = icon_image
                log.success("System", f"Window icon loaded: {icon_path_png}")
                return
                
            # Method 3: Try other common names
            for filename in ["favicon-16x16.png", "android-chrome-192x192.png"]:
                icon_path = os.path.join(script_dir, "assets", filename)
                if os.path.exists(icon_path):
                    icon_image = PhotoImage(file=icon_path)
                    self.root.iconphoto(True, icon_image)
                    self.root.icon_image = icon_image
                    log.success("System", f"Window icon loaded: {icon_path}")
                    return
            
            log.warning("System", "No icon file found in assets/ directory")
            
        except Exception as e:
            log.error("System", f"Error loading window icon: {e}")
    
    def _on_closing(self):
        """Handle window close event with test running check"""
        if self.state.test_running:
            # Show confirmation dialog
            result = messagebox.askyesno(
                "Test Running",
                "A test is currently running!\n\n"
                "Closing the dashboard will stop the test and generate a final CSV file.\n\n"
                "Are you sure you want to stop the test and close the application?",
                icon="warning"
            )
            
            if result:
                log.info("System", "User confirmed closing during active test")
                # Stop the test gracefully
                if hasattr(self.control_panel, '_stop_test'):
                    self.control_panel._stop_test()
                log.info("System", "Test stopped due to application closure", [
                    "→ Final CSV generated"
                ])
                self._close_application()
            else:
                log.info("System", "User cancelled closing - test continues")
                # Don't close the window
                return
        else:
            # No test running, close normally
            self._close_application()
    
    def _close_application(self):
        """Clean up and close the application"""
        log.info("System", "Closing AWE Test Rig Dashboard")
        self.cleanup()
        self.root.destroy()
    
    def _create_widgets(self):
        """Create the 2x2 grid layout with actual plots"""
        
        # Top-left: Live Pressure and Gas Concentration vs Time plot
        self.pressure_frame = ttk.LabelFrame(
            self.main_frame, 
            text="Pressure & Gas Concentrations", 
            padding="2"
        )
        self.pressure_frame.grid(row=0, column=0, padx=2, pady=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.pressure_frame.columnconfigure(0, weight=1)
        self.pressure_frame.rowconfigure(0, weight=1)
        
        # Create actual pressure plot (now includes gas concentrations)
        self.pressure_plot = PressurePlot(self.pressure_frame)
        
        # Top-right: Live Cell Voltage vs Time plot
        self.voltage_frame = ttk.LabelFrame(
            self.main_frame, 
            text="Voltage vs Time", 
            padding="2"
        )
        self.voltage_frame.grid(row=0, column=1, padx=2, pady=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.voltage_frame.columnconfigure(0, weight=1)
        self.voltage_frame.rowconfigure(0, weight=1)
        
        # Create voltage plot
        self.voltage_plot = VoltagePlot(self.voltage_frame)
        
        # Bottom-left: Temperature vs Time plot (placeholder for Task 16)
        self.temperature_frame = ttk.LabelFrame(
            self.main_frame, 
            text="Temperature vs Time", 
            padding="2"
        )
        self.temperature_frame.grid(row=1, column=0, padx=2, pady=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.temperature_frame.columnconfigure(0, weight=1)
        self.temperature_frame.rowconfigure(0, weight=1)
        
        # Create temperature plot
        self.temperature_plot = TemperaturePlot(self.temperature_frame)
        
        # Bottom-right: Current vs Time plot
        self.current_frame = ttk.LabelFrame(
            self.main_frame, 
            text="Current vs Time", 
            padding="2"
        )
        self.current_frame.grid(row=1, column=1, padx=2, pady=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.current_frame.columnconfigure(0, weight=1)
        self.current_frame.rowconfigure(0, weight=1)
        
        # Create current plot
        self.current_plot = CurrentPlot(self.current_frame)
    
    def _create_actuator_controls(self, parent_frame):
        """Create actuator controls in 6-column grid layout with categories"""
        
        # Configure grid columns
        parent_frame.columnconfigure(0, weight=0)  # Fluid valve labels - fixed width
        parent_frame.columnconfigure(1, weight=0)  # Fluid valve buttons - fixed width
        parent_frame.columnconfigure(2, weight=0)  # Pump labels - fixed width
        parent_frame.columnconfigure(3, weight=0)  # Pump buttons - fixed width
        parent_frame.columnconfigure(4, weight=0)  # Purge valve labels - fixed width
        parent_frame.columnconfigure(5, weight=0)  # Purge valve buttons - fixed width
        
        # Column titles
        fluid_title = ttk.Label(parent_frame, text="Fluid Valves", font=("Arial", 10, "bold"))
        fluid_title.grid(row=0, column=0, sticky='w', padx=5, pady=2)
        
        pump_title = ttk.Label(parent_frame, text="Pumps", font=("Arial", 10, "bold"))
        pump_title.grid(row=0, column=2, sticky='w', padx=5, pady=2)
        
        purge_title = ttk.Label(parent_frame, text="Purge Valves", font=("Arial", 10, "bold"))
        purge_title.grid(row=0, column=4, sticky='w', padx=5, pady=2)
        
        # Fluid valve names (excluding purge valves)
        fluid_valve_names = ["KOH Storage", "DI Storage", "Stack Drain"]
        
        # Purge valve names  
        purge_valve_names = ["H2 Purge", "O2 Purge"]
        
        # Create fluid valve controls
        self.valve_labels = []
        
        # Fluid valves (indices 0, 1, 2)
        for i, valve_name in enumerate(fluid_valve_names):
            # Valve label
            valve_label = ttk.Label(parent_frame, text=valve_name, font=("Arial", 10))
            valve_label.grid(row=i+1, column=0, sticky='w', padx=5, pady=2)
            
            # Valve toggle button
            valve_button = tk.Button(
                parent_frame,
                text="OFF",
                background="red",
                foreground="white",
                width=12,
                relief=tk.RAISED,
                font=("Arial", 9),
                command=lambda valve_idx=i: self._toggle_valve(valve_idx),
                cursor="hand2"
            )
            valve_button.grid(row=i+1, column=1, padx=10, pady=2)
            self.valve_labels.append(valve_button)
        
        # Purge valves (indices 3, 4)
        for i, valve_name in enumerate(purge_valve_names):
            # Valve label
            valve_label = ttk.Label(parent_frame, text=valve_name, font=("Arial", 10))
            valve_label.grid(row=i+1, column=4, sticky='w', padx=5, pady=2)
            
            # Valve toggle button (original indices 3, 4)
            valve_button = tk.Button(
                parent_frame,
                text="OFF",
                background="red",
                foreground="white",
                width=12,
                relief=tk.RAISED,
                font=("Arial", 9),
                command=lambda valve_idx=i+3: self._toggle_valve(valve_idx),
                cursor="hand2"
            )
            valve_button.grid(row=i+1, column=5, padx=10, pady=2)
            self.valve_labels.append(valve_button)
        
        # Pump controls
        # DI Fill Pump
        di_pump_label = ttk.Label(parent_frame, text="DI Fill Pump", font=("Arial", 10))
        di_pump_label.grid(row=2, column=2, sticky='w', padx=5, pady=2)
        
        self.pump_state_label = tk.Button(
            parent_frame,
            text="OFF",
            background="red",
            foreground="white",
            width=12,
            relief=tk.RAISED,
            font=("Arial", 9),
            command=self._toggle_pump,
            cursor="hand2"
        )
        self.pump_state_label.grid(row=2, column=3, padx=10, pady=2)
        
        # KOH Fill Pump
        koh_pump_label = ttk.Label(parent_frame, text="KOH Fill Pump", font=("Arial", 10))
        koh_pump_label.grid(row=1, column=2, sticky='w', padx=5, pady=2)
        
        self.koh_pump_state_label = tk.Button(
            parent_frame,
            text="OFF",
            background="red",
            foreground="white",
            width=12,
            relief=tk.RAISED,
            font=("Arial", 9),
            command=self._toggle_koh_pump,
            cursor="hand2"
        )
        self.koh_pump_state_label.grid(row=1, column=3, padx=10, pady=2)
    
    def _create_valve_indicators(self):
        """Placeholder method - current sensor moved to plot, actuator controls moved to right side"""
        pass
    
    def _toggle_valve(self, valve_index):
        """Toggle valve state when clicked"""
        if not self.state.connections.get('ni_daq', False):
            valve_names = ["KOH Storage", "DI Storage", "Stack Drain", "H2 Purge", "O2 Purge"]
            log.warning("Actuators", f"Cannot control {valve_names[valve_index]} - NI DAQ not connected")
            return
        
        # Get current state and toggle it
        current_state = self.state.valve_states[valve_index]
        new_state = not current_state
        
        # Update state (NI DAQ service will automatically update hardware)
        self.state.set_actuator_state('valve', new_state, valve_index)
        
        valve_names = ["KOH Storage", "DI Storage", "Stack Drain", "H2 Purge", "O2 Purge"]
        log.info("Actuators", f"{valve_names[valve_index]} {'ON' if new_state else 'OFF'}")
    
    def _toggle_pump(self):
        """Toggle pump state when clicked"""
        if not self.state.connections.get('ni_daq', False):
            log.warning("Actuators", "Cannot control DI Fill Pump - NI DAQ not connected")
            return
        
        # Get current state and toggle it
        current_state = self.state.pump_state
        new_state = not current_state
        
        # Update state (NI DAQ service will automatically update hardware)
        self.state.set_actuator_state('pump', new_state)
        
        log.info("Actuators", f"DI Fill Pump {'ON' if new_state else 'OFF'}")
    
    def _toggle_koh_pump(self):
        """Toggle KOH pump state when clicked"""
        if not self.state.connections.get('ni_daq', False):
            log.warning("Actuators", "Cannot control KOH Fill Pump - NI DAQ not connected")
            return
        
        # Get current state and toggle it
        current_state = self.state.koh_pump_state
        new_state = not current_state
        
        # Update state (NI DAQ service will automatically update hardware)
        self.state.set_actuator_state('koh_pump', new_state)
        
        log.info("Actuators", f"KOH Fill Pump {'ON' if new_state else 'OFF'}")
    
    def reset_plots(self):
        """Reset all plots when starting a new test"""
        if self.pressure_plot:
            self.pressure_plot.reset()
        if self.voltage_plot:
            self.voltage_plot.reset()
        if self.temperature_plot:
            self.temperature_plot.reset()
        if self.current_plot:
            self.current_plot.reset()
    
    def _start_status_updates(self):
        """Start periodic status updates"""
        self._update_status_indicators()
    
    def _update_status_indicators(self):
        """Update status indicators based on GlobalState"""
        # Update connection status indicators
        connection_info = {
            'ni_daq': "250 Hz" if self.state.connections['ni_daq'] else "",
            'pico_tc08': "1 Hz" if self.state.connections['pico_tc08'] else "",
            'bga244_1': "0.2 Hz",
            'bga244_2': "0.2 Hz", 
            'bga244_3': "0.2 Hz",
            'cvm24p': "10 Hz" if self.state.connections['cvm24p'] else ""
        }
        
        # Get individual BGA connection statuses
        from services.controller_manager import get_controller_manager
        controller = get_controller_manager()
        
        # Fix: Access the actual service instance, not the service dict
        bga_service_info = controller.services.get('bga244')
        bga_service = bga_service_info['service'] if bga_service_info else None
        
        if bga_service and hasattr(bga_service, 'get_individual_connection_status'):
            individual_bga_status = bga_service.get_individual_connection_status()
            
            # Update individual BGA statuses
            for i, (bga_key, connected) in enumerate(individual_bga_status.items()):
                device_key = f'bga244_{i+1}'
                if device_key in self.status_indicators.device_status:
                    info = connection_info[device_key] if connected else ""
                    self.status_indicators.update_device_status(device_key, connected, info)
        else:
            # Fallback to combined BGA status if individual status not available
            bga_connected = self.state.connections.get('bga244', False)
            for i in range(1, 4):
                device_key = f'bga244_{i}'
                if device_key in self.status_indicators.device_status:
                    info = connection_info[device_key] if bga_connected else ""
                    self.status_indicators.update_device_status(device_key, bga_connected, info)
        
        # Update other devices normally
        for device in ['ni_daq', 'pico_tc08', 'cvm24p']:
            connected = self.state.connections[device]
            self.status_indicators.update_device_status(device, connected, connection_info[device])
        
        # Update valve button states and colors
        for i, valve_button in enumerate(self.valve_labels):
            valve_state = self.state.valve_states[i]
            if valve_state:
                valve_button.configure(text="ON", background="green", activebackground="lightgreen")
            else:
                valve_button.configure(text="OFF", background="red", activebackground="lightcoral")
            
            # Enable/disable based on NI DAQ connection
            if self.state.connections.get('ni_daq', False):
                valve_button.configure(state='normal')
            else:
                valve_button.configure(state='disabled')
        
        # Update pump button states and colors
        if self.state.pump_state:
            self.pump_state_label.configure(text="ON", background="green", activebackground="lightgreen")
        else:
            self.pump_state_label.configure(text="OFF", background="red", activebackground="lightcoral")
        
        # Enable/disable pump based on NI DAQ connection
        if self.state.connections.get('ni_daq', False):
            self.pump_state_label.configure(state='normal')
        else:
            self.pump_state_label.configure(state='disabled')
        
        # Update KOH pump button state and color
        if self.state.koh_pump_state:
            self.koh_pump_state_label.configure(text="ON", background="green", activebackground="lightgreen")
        else:
            self.koh_pump_state_label.configure(text="OFF", background="red", activebackground="lightcoral")
        
        # Enable/disable KOH pump based on NI DAQ connection
        if self.state.connections.get('ni_daq', False):
            self.koh_pump_state_label.configure(state='normal')
        else:
            self.koh_pump_state_label.configure(state='disabled')
        
        # Schedule next update
        self.update_job = self.root.after(100, self._update_status_indicators)
    
    def cleanup(self):
        """Clean up resources and stop all services"""
        log.info("System", "Cleaning up dashboard resources")
        
        cleanup_details = []
        
        # Cancel UI update timer
        if self.update_job:
            self.root.after_cancel(self.update_job)
            cleanup_details.append("→ UI update timer cancelled")
        
        # Stop all services through controller manager
        try:
            from services.controller_manager import get_controller_manager
            controller = get_controller_manager()
            if controller.services_running:
                controller.stop_all_services()
                cleanup_details.append("→ All hardware services stopped")
        except Exception as e:
            log.warning("System", f"Error stopping services: {e}")
        
        # Clean up plots
        if self.pressure_plot:
            try:
                self.pressure_plot.destroy()
                cleanup_details.append("→ Pressure plot destroyed")
            except Exception as e:
                log.warning("System", f"Error destroying pressure plot: {e}")
                
        if self.voltage_plot:
            try:
                self.voltage_plot.destroy()
                cleanup_details.append("→ Voltage plot destroyed")
            except Exception as e:
                log.warning("System", f"Error destroying voltage plot: {e}")
                
        if self.temperature_plot:
            try:
                self.temperature_plot.destroy()
                cleanup_details.append("→ Temperature plot destroyed")
            except Exception as e:
                log.warning("System", f"Error destroying temperature plot: {e}")
                
        if self.current_plot:
            try:
                self.current_plot.destroy()
                cleanup_details.append("→ Current plot destroyed")
            except Exception as e:
                log.warning("System", f"Error destroying current plot: {e}")
        
        # Clean up control panel
        if hasattr(self.control_panel, 'cleanup'):
            try:
                self.control_panel.cleanup()
                cleanup_details.append("→ Control panel cleaned up")
            except Exception as e:
                log.warning("System", f"Error cleaning up control panel: {e}")
        
        if cleanup_details:
            log.success("System", "Dashboard cleanup complete", cleanup_details)
        else:
            log.success("System", "Dashboard cleanup complete")


def main():
    """Test the dashboard by running it directly"""
    root = tk.Tk()
    
    print("=" * 70)
    print("DASHBOARD TEST: All Live Plots + Interactive Valve/Pump Controls")
    print("=" * 70)
    print("✅ Dashboard window opens MAXIMIZED")
    print("✅ Dashboard with live pressure & gas concentration plotting")
    print("✅ Dashboard with live cell voltage plotting (120 cells)")
    print("✅ Dashboard with live temperature plotting (8 thermocouples)")
    print("✅ All plots update from GlobalState")
    print("✅ Static Y-axis, dynamic X-axis for all plots")
    print("✅ Interactive valve/pump controls with relay outputs")
    
    dashboard = Dashboard(root)
    
    print("\nPressure & Gas Plot (Y: 0-1):")
    print("   • Blue: Pressure 1 | Red: Pressure 2")
    print("   • Green dashed: H₂ (H-side) | Magenta dashed: O₂ (O-side)")  
    print("   • Green dotted: H₂ (mixed stream)")
    print("\nVoltage Plot (Y: 0-5V):")
    print("   • Blue: Group 1 (1-20) | Green: Group 2 (21-40)")
    print("   • Red: Group 3 (41-60) | Magenta: Group 4 (61-80)")
    print("   • Cyan: Group 5 (81-100) | Yellow: Group 6 (101-120)")
    print("\nTemperature Plot (Y: 0-100°C):")
    print("   • Blue: Inlet | Red: Outlet | Green: Stack 1 | Magenta: Stack 2")
    print("   • Cyan dashed: Ambient | Yellow dashed: Cooling")
    print("   • Orange: Gas | Brown: Case")
    print("\nValve/Pump Controls:")
    print("   • 🔴 Red buttons = OFF | 🟢 Green buttons = ON")
    print("   • Click valve/pump buttons to toggle (when NI DAQ connected)")
    print("   • Buttons disabled when NI DAQ disconnected")
    print("   • KOH Storage, DI Storage, Stack Drain, H2 Purge, O2 Purge + Pumps")
    print("\n🎯 TEST: Verify all functionality:")
    print("   1. Click Connect - all services start, buttons enabled")
    print("   2. Click valve/pump buttons to control actuators")
    print("   3. Start Test - all plots begin updating")
    print("   4. Watch plots update and actuator control in real-time")
    print("   5. Emergency Stop turns off all actuators")
    print("\n🖥️  WINDOW: Dashboard opens as MAXIMIZED window!")
    print("Close window when done testing...")
    print("=" * 70)
    
    root.mainloop()


if __name__ == "__main__":
    main() 
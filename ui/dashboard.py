#!/usr/bin/env python3
"""
Dashboard window with 2x2 grid layout for AWE test rig
"""

import tkinter as tk
from tkinter import ttk, messagebox
from .controls import ControlPanel
from .status_indicators import StatusIndicators
from .plots import PressurePlot, VoltagePlot, TemperaturePlot
from core.state import get_global_state


class Dashboard:
    """Main dashboard window with controls, status indicators, and 2x2 grid layout"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("AWE Electrolyzer Test Rig - Dashboard")
        self.root.geometry("1400x900")
        
        # Get global state
        self.state = get_global_state()
        self.update_job = None
        
        # Plot objects
        self.pressure_plot = None
        self.voltage_plot = None
        self.temperature_plot = None
        
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
        
        # Add status indicators in the middle
        self.status_indicators = StatusIndicators(main_container)
        
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
                print("🔔 User confirmed closing during active test")
                # Stop the test gracefully
                if hasattr(self.control_panel, '_stop_test'):
                    self.control_panel._stop_test()
                print("   → Test stopped due to application closure")
                print("   → Final CSV generated")
                self._close_application()
            else:
                print("🔔 User cancelled closing - test continues")
                # Don't close the window
                return
        else:
            # No test running, close normally
            self._close_application()
    
    def _close_application(self):
        """Clean up and close the application"""
        print("🔔 Closing AWE Test Rig Dashboard...")
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
        
        # Bottom-right: Valve/Pump state indicators
        self.valve_frame = ttk.LabelFrame(
            self.main_frame, 
            text="Actuator States", 
            padding="5"
        )
        self.valve_frame.grid(row=1, column=1, padx=2, pady=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.valve_frame.columnconfigure(0, weight=1)
        self.valve_frame.rowconfigure(0, weight=1)
        
        # Create valve state indicators with toggle controls
        self._create_valve_indicators()
    
    def _create_valve_indicators(self):
        """Create valve and pump state indicators with toggle controls"""
        
        # Container frame to center content and control sizing
        container_frame = ttk.Frame(self.valve_frame)
        container_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Title
        title_label = ttk.Label(container_frame, text="Actuator Controls", font=("Arial", 12, "bold"))
        title_label.pack(pady=(10, 5))
        
        # Valve states (4 valves)
        valve_frame = ttk.Frame(container_frame)
        valve_frame.pack(pady=5)
        
        ttk.Label(valve_frame, text="Solenoid Valves:", font=("Arial", 10, "bold")).grid(row=0, column=0, columnspan=4, pady=5)
        
        self.valve_labels = []
        for i in range(4):
            valve_label = ttk.Label(valve_frame, text=f"Valve {i+1}:")
            valve_label.grid(row=1, column=i, padx=5, pady=2)
            
            # Clickable button instead of label
            valve_button = tk.Button(
                valve_frame, 
                text="OFF", 
                background="red", 
                foreground="white",
                width=6,
                relief=tk.RAISED,
                command=lambda valve_idx=i: self._toggle_valve(valve_idx),
                cursor="hand2"
            )
            valve_button.grid(row=2, column=i, padx=5, pady=2)
            self.valve_labels.append(valve_button)
        
        # Pump state
        pump_frame = ttk.Frame(container_frame)
        pump_frame.pack(pady=10)
        
        ttk.Label(pump_frame, text="Pump:", font=("Arial", 10, "bold")).pack()
        self.pump_state_label = tk.Button(
            pump_frame, 
            text="OFF", 
            background="red", 
            foreground="white",
            width=8,
            relief=tk.RAISED,
            font=("Arial", 10, "bold"),
            command=self._toggle_pump,
            cursor="hand2"
        )
        self.pump_state_label.pack(pady=5)
        
        # Current sensor display (read-only)
        current_frame = ttk.Frame(container_frame)
        current_frame.pack(pady=10)
        
        ttk.Label(current_frame, text="Current Sensor:", font=("Arial", 10, "bold")).pack()
        self.current_label = ttk.Label(current_frame, text="0.0 A", font=("Arial", 12))
        self.current_label.pack()
    
    def _toggle_valve(self, valve_index):
        """Toggle valve state when clicked"""
        if not self.state.connections.get('ni_daq', False):
            print(f"⚠️  Cannot control Valve {valve_index+1} - NI DAQ not connected")
            return
        
        # Get current state and toggle it
        current_state = self.state.valve_states[valve_index]
        new_state = not current_state
        
        # Update state (NI DAQ service will automatically update hardware)
        self.state.set_actuator_state('valve', new_state, valve_index)
        
        print(f"🔧 Valve {valve_index+1} {'ON' if new_state else 'OFF'}")
    
    def _toggle_pump(self):
        """Toggle pump state when clicked"""
        if not self.state.connections.get('ni_daq', False):
            print("⚠️  Cannot control Pump - NI DAQ not connected")
            return
        
        # Get current state and toggle it
        current_state = self.state.pump_state
        new_state = not current_state
        
        # Update state (NI DAQ service will automatically update hardware)
        self.state.set_actuator_state('pump', new_state)
        
        print(f"🔧 Pump {'ON' if new_state else 'OFF'}")
    
    def reset_plots(self):
        """Reset all plots when starting a new test"""
        if self.pressure_plot:
            self.pressure_plot.reset()
        if self.voltage_plot:
            self.voltage_plot.reset()
        if self.temperature_plot:
            self.temperature_plot.reset()
    
    def _start_status_updates(self):
        """Start periodic status updates"""
        self._update_status_indicators()
    
    def _update_status_indicators(self):
        """Update status indicators based on GlobalState"""
        # Update connection status indicators
        connection_info = {
            'ni_daq': "250 Hz" if self.state.connections['ni_daq'] else "",
            'pico_tc08': "1 Hz" if self.state.connections['pico_tc08'] else "",
            'bga244': "0.2 Hz" if self.state.connections['bga244'] else "",
            'cvm24p': "10 Hz" if self.state.connections['cvm24p'] else ""
        }
        
        for device, connected in self.state.connections.items():
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
        
        # Update pump button state and color
        if self.state.pump_state:
            self.pump_state_label.configure(text="ON", background="green", activebackground="lightgreen")
        else:
            self.pump_state_label.configure(text="OFF", background="red", activebackground="lightcoral")
        
        # Enable/disable pump based on NI DAQ connection
        if self.state.connections.get('ni_daq', False):
            self.pump_state_label.configure(state='normal')
        else:
            self.pump_state_label.configure(state='disabled')
        
        # Update current sensor
        self.current_label.configure(text=f"{self.state.current_value:.1f} A")
        
        # Schedule next update
        self.update_job = self.root.after(100, self._update_status_indicators)
    
    def cleanup(self):
        """Clean up resources"""
        if self.update_job:
            self.root.after_cancel(self.update_job)
        
        # Clean up plots
        if self.pressure_plot:
            self.pressure_plot.destroy()
        if self.voltage_plot:
            self.voltage_plot.destroy()
        if self.temperature_plot:
            self.temperature_plot.destroy()
        
        if hasattr(self.control_panel, 'cleanup'):
            self.control_panel.cleanup()


def main():
    """Test the dashboard by running it directly"""
    root = tk.Tk()
    dashboard = Dashboard(root)
    
    print("=" * 70)
    print("DASHBOARD TEST: All Live Plots + Interactive Valve/Pump Controls")
    print("=" * 70)
    print("✅ Dashboard with live pressure & gas concentration plotting")
    print("✅ Dashboard with live cell voltage plotting (120 cells)")
    print("✅ Dashboard with live temperature plotting (8 thermocouples)")
    print("✅ All plots update from GlobalState")
    print("✅ Static Y-axis, dynamic X-axis for all plots")
    print("✅ Interactive valve/pump controls with relay outputs")
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
    print("\n🎯 TEST: Verify all functionality:")
    print("   1. Click Connect - all services start, buttons enabled")
    print("   2. Click valve/pump buttons to control actuators")
    print("   3. Start Test - all plots begin updating")
    print("   4. Watch plots update and actuator control in real-time")
    print("   5. Emergency Stop turns off all actuators")
    print("\nFull AWE test rig control dashboard!")
    print("Close window when done testing...")
    print("=" * 70)
    
    root.mainloop()


if __name__ == "__main__":
    main() 
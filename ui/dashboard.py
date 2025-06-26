#!/usr/bin/env python3
"""
Dashboard window with 2x2 grid layout for AWE test rig

Actuator mapping (matches NI cDAQ hardware configuration):
- Line 0: KOH Storage Valve    (cDAQ9187-23E902CMod2/port0/line0)
- Line 1: DI Storage Valve     (cDAQ9187-23E902CMod2/port0/line1)  
- Line 2: Stack Drain Valve    (cDAQ9187-23E902CMod2/port0/line2)
- Line 3: H2 Purge Valve       (cDAQ9187-23E902CMod2/port0/line3)
- Line 4: DI Fill Pump         (cDAQ9187-23E902CMod2/port0/line4)
- Line 5: O2 Purge Valve       (cDAQ9187-23E902CMod2/port0/line5)
- Line 6: KOH Fill Pump        (cDAQ9187-23E902CMod2/port0/line6)
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
        
        # Maximize the window - cross-platform approach
        self._maximize_window()
        
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
    
    def _maximize_window(self):
        """Maximize the window - cross-platform approach"""
        try:
            # Try platform-specific maximization methods
            import platform
            system = platform.system()
            
            if system == "Windows":
                # Windows-specific maximization
                self.root.state('zoomed')
            elif system == "Linux":
                # Linux-specific maximization  
                self.root.attributes('-zoomed', True)
            else:
                # macOS and other platforms - use screen dimensions
                # Get screen dimensions
                screen_width = self.root.winfo_screenwidth()
                screen_height = self.root.winfo_screenheight()
                
                # Set window to full screen size
                self.root.geometry(f"{screen_width}x{screen_height}+0+0")
                
                # Try to remove window decorations for true full screen (optional)
                # self.root.overrideredirect(True)  # Uncomment for borderless
                
            print(f"✅ Dashboard window maximized ({platform.system()})")
            
        except Exception as e:
            # Fallback to large window if maximization fails
            print(f"⚠️  Could not maximize window: {e}")
            print("   → Using fallback large window size")
            self.root.geometry("1400x900")
    
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
        
        # Valve states (5 valves with real names)
        valve_frame = ttk.Frame(container_frame)
        valve_frame.pack(pady=5)
        
        ttk.Label(valve_frame, text="Valves & Pumps:", font=("Arial", 10, "bold")).grid(row=0, column=0, columnspan=4, pady=5)
        
        # All actuator names in the new structure - 7 total
        actuator_names = [
            "KOH Storage Valve",    # Index 0
            "DI Storage Valve",     # Index 1  
            "Stack Drain Valve",    # Index 2
            "H2 Purge Valve",       # Index 3
            "DI Fill Pump",         # Index 4
            "O2 Purge Valve",       # Index 5
            "KOH Fill Pump"         # Index 6
        ]
        
        self.actuator_labels = []
        
        # Create a grid layout for all 7 actuators (2 rows)
        for i, actuator_name in enumerate(actuator_names):
            row = 1 if i < 4 else 3  # First 4 in row 1, rest in row 3
            col = i if i < 4 else i - 4  # Column position
            
            # Label
            actuator_label = ttk.Label(valve_frame, text=f"{actuator_name}")
            actuator_label.grid(row=row, column=col, padx=3, pady=2)
            
            # Clickable button
            actuator_button = tk.Button(
                valve_frame, 
                text="OFF", 
                background="red", 
                foreground="white",
                width=10,  # Wider for longer names
                relief=tk.RAISED,
                command=lambda idx=i: self._toggle_actuator(idx),
                cursor="hand2"
            )
            actuator_button.grid(row=row+1, column=col, padx=3, pady=2)
            self.actuator_labels.append(actuator_button)
        
        # Current sensor display (read-only)
        current_frame = ttk.Frame(container_frame)
        current_frame.pack(pady=10)
        
        ttk.Label(current_frame, text="Current Sensor:", font=("Arial", 10, "bold")).pack()
        self.current_label = ttk.Label(current_frame, text="0.0 A", font=("Arial", 12))
        self.current_label.pack()
    
    def _toggle_actuator(self, actuator_index):
        """Toggle actuator state when clicked"""
        if not self.state.connections.get('ni_daq', False):
            actuator_names = [
                "KOH Storage Valve", "DI Storage Valve", "Stack Drain Valve", 
                "H2 Purge Valve", "DI Fill Pump", "O2 Purge Valve", "KOH Fill Pump"
            ]
            print(f"⚠️  Cannot control {actuator_names[actuator_index]} - NI DAQ not connected")
            return
        
        # Get current state and toggle it
        current_state = self.state.actuator_states[actuator_index]
        new_state = not current_state
        
        # Update state (NI DAQ service will automatically update hardware)
        self.state.set_actuator_state('actuator', new_state, actuator_index)
        
        actuator_names = [
            "KOH Storage Valve", "DI Storage Valve", "Stack Drain Valve", 
            "H2 Purge Valve", "DI Fill Pump", "O2 Purge Valve", "KOH Fill Pump"
        ]
        print(f"🔧 {actuator_names[actuator_index]} {'ON' if new_state else 'OFF'}")
    
    def _toggle_valve(self, valve_index):
        """Toggle valve state when clicked (backward compatibility)"""
        # Map old valve indices to new actuator indices
        valve_to_actuator_map = {0: 0, 1: 1, 2: 2, 3: 3, 4: 5}
        if valve_index in valve_to_actuator_map:
            actuator_index = valve_to_actuator_map[valve_index]
            self._toggle_actuator(actuator_index)
    
    def _toggle_pump(self):
        """Toggle DI Fill Pump state when clicked (backward compatibility)"""
        self._toggle_actuator(4)  # DI Fill Pump is at index 4
    
    def _toggle_koh_pump(self):
        """Toggle KOH Fill Pump state when clicked (backward compatibility)"""
        self._toggle_actuator(6)  # KOH Fill Pump is at index 6
    
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
        
        # Update actuator button states and colors (all 7 actuators)
        for i, actuator_button in enumerate(self.actuator_labels):
            actuator_state = self.state.actuator_states[i]
            if actuator_state:
                actuator_button.configure(text="ON", background="green", activebackground="lightgreen")
            else:
                actuator_button.configure(text="OFF", background="red", activebackground="lightcoral")
            
            # Enable/disable based on NI DAQ connection
            if self.state.connections.get('ni_daq', False):
                actuator_button.configure(state='normal')
            else:
                actuator_button.configure(state='disabled')
        
        # Update current sensor
        self.current_label.configure(text=f"{self.state.current_value:.1f} A")
        
        # Schedule next update
        self.update_job = self.root.after(100, self._update_status_indicators)
    
    def cleanup(self):
        """Clean up resources and stop all services"""
        print("🧹 Cleaning up dashboard resources...")
        
        # Cancel UI update timer
        if self.update_job:
            self.root.after_cancel(self.update_job)
            print("   → UI update timer cancelled")
        
        # Stop all services through controller manager
        try:
            from services.controller_manager import get_controller_manager
            controller = get_controller_manager()
            if controller.services_running:
                print("   → Stopping all hardware services...")
                controller.stop_all_services()
                print("   → All services stopped")
        except Exception as e:
            print(f"   ⚠️  Error stopping services: {e}")
        
        # Clean up plots
        if self.pressure_plot:
            try:
                self.pressure_plot.destroy()
                print("   → Pressure plot destroyed")
            except Exception as e:
                print(f"   ⚠️  Error destroying pressure plot: {e}")
                
        if self.voltage_plot:
            try:
                self.voltage_plot.destroy()
                print("   → Voltage plot destroyed")
            except Exception as e:
                print(f"   ⚠️  Error destroying voltage plot: {e}")
                
        if self.temperature_plot:
            try:
                self.temperature_plot.destroy()
                print("   → Temperature plot destroyed")
            except Exception as e:
                print(f"   ⚠️  Error destroying temperature plot: {e}")
        
        # Clean up control panel
        if hasattr(self.control_panel, 'cleanup'):
            try:
                self.control_panel.cleanup()
                print("   → Control panel cleaned up")
            except Exception as e:
                print(f"   ⚠️  Error cleaning up control panel: {e}")
        
        print("✅ Dashboard cleanup complete")


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
    print("   • KOH Storage, DI Storage, Stack Drain, H2 Purge, DI Fill Pump, O2 Purge, KOH Fill Pump")
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
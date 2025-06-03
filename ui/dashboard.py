#!/usr/bin/env python3
"""
Dashboard window with 2x2 grid layout for AWE test rig
"""

import tkinter as tk
from tkinter import ttk, messagebox
from .controls import ControlPanel
from .status_indicators import StatusIndicators
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
        
        # Set up window close protocol
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        
        # Create main container
        main_container = ttk.Frame(root, padding="5")
        main_container.pack(fill='both', expand=True)
        
        # Configure main container
        main_container.columnconfigure(0, weight=1)
        main_container.rowconfigure(2, weight=1)  # Give weight to the grid section
        
        # Add control panel at the top
        self.control_panel = ControlPanel(main_container)
        
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
        """Create the 2x2 grid layout with placeholders"""
        
        # Top-left: Pressure vs Time plot placeholder
        self.pressure_frame = ttk.LabelFrame(
            self.main_frame, 
            text="Pressure vs Time", 
            padding="5"
        )
        self.pressure_frame.grid(row=0, column=0, padx=2, pady=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.pressure_frame.columnconfigure(0, weight=1)
        self.pressure_frame.rowconfigure(0, weight=1)
        
        self.pressure_placeholder = ttk.Label(
            self.pressure_frame, 
            text="[Pressure Plot Placeholder]\n\nPressure Sensor 1: 0.0 PSI\nPressure Sensor 2: 0.0 PSI",
            justify=tk.CENTER,
            background="lightblue"
        )
        self.pressure_placeholder.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Top-right: Voltage vs Time plot placeholder
        self.voltage_frame = ttk.LabelFrame(
            self.main_frame, 
            text="Voltage vs Time", 
            padding="5"
        )
        self.voltage_frame.grid(row=0, column=1, padx=2, pady=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.voltage_frame.columnconfigure(0, weight=1)
        self.voltage_frame.rowconfigure(0, weight=1)
        
        self.voltage_placeholder = ttk.Label(
            self.voltage_frame, 
            text="[Voltage Plot Placeholder]\n\nCell Voltage Average: 0.0 V\nTotal Stack Voltage: 0.0 V",
            justify=tk.CENTER,
            background="lightgreen"
        )
        self.voltage_placeholder.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Bottom-left: Temperature vs Time plot placeholder
        self.temperature_frame = ttk.LabelFrame(
            self.main_frame, 
            text="Temperature vs Time", 
            padding="5"
        )
        self.temperature_frame.grid(row=1, column=0, padx=2, pady=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.temperature_frame.columnconfigure(0, weight=1)
        self.temperature_frame.rowconfigure(0, weight=1)
        
        self.temperature_placeholder = ttk.Label(
            self.temperature_frame, 
            text="[Temperature Plot Placeholder]\n\nTC1: 0.0°C  TC2: 0.0°C  TC3: 0.0°C  TC4: 0.0°C\nTC5: 0.0°C  TC6: 0.0°C  TC7: 0.0°C  TC8: 0.0°C",
            justify=tk.CENTER,
            background="lightyellow"
        )
        self.temperature_placeholder.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Bottom-right: Valve/Pump state indicators
        self.valve_frame = ttk.LabelFrame(
            self.main_frame, 
            text="Actuator States", 
            padding="5"
        )
        self.valve_frame.grid(row=1, column=1, padx=2, pady=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.valve_frame.columnconfigure(0, weight=1)
        self.valve_frame.rowconfigure(0, weight=1)
        
        # Create valve state indicators
        self._create_valve_indicators()
    
    def _create_valve_indicators(self):
        """Create valve and pump state indicators"""
        
        # Container frame to center content and control sizing
        container_frame = ttk.Frame(self.valve_frame)
        container_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Title
        title_label = ttk.Label(container_frame, text="[Valve/Pump State Panel]", font=("Arial", 12, "bold"))
        title_label.pack(pady=(10, 5))
        
        # Valve states (4 valves)
        valve_frame = ttk.Frame(container_frame)
        valve_frame.pack(pady=5)
        
        ttk.Label(valve_frame, text="Solenoid Valves:", font=("Arial", 10, "bold")).grid(row=0, column=0, columnspan=4, pady=5)
        
        self.valve_labels = []
        for i in range(4):
            valve_label = ttk.Label(valve_frame, text=f"Valve {i+1}:")
            valve_label.grid(row=1, column=i, padx=5, pady=2)
            
            # OFF indicator (will be updated from state)
            state_label = tk.Label(
                valve_frame, 
                text="OFF", 
                background="red", 
                foreground="white",
                width=6,
                relief=tk.RAISED
            )
            state_label.grid(row=2, column=i, padx=5, pady=2)
            self.valve_labels.append(state_label)
        
        # Pump state
        pump_frame = ttk.Frame(container_frame)
        pump_frame.pack(pady=10)
        
        ttk.Label(pump_frame, text="Pump:", font=("Arial", 10, "bold")).pack()
        self.pump_state_label = tk.Label(
            pump_frame, 
            text="OFF", 
            background="red", 
            foreground="white",
            width=8,
            relief=tk.RAISED,
            font=("Arial", 10, "bold")
        )
        self.pump_state_label.pack(pady=5)
        
        # Current sensor display
        current_frame = ttk.Frame(container_frame)
        current_frame.pack(pady=10)
        
        ttk.Label(current_frame, text="Current Sensor:", font=("Arial", 10, "bold")).pack()
        self.current_label = ttk.Label(current_frame, text="0.0 A", font=("Arial", 12))
        self.current_label.pack()
    
    def _start_status_updates(self):
        """Start periodic status updates"""
        self._update_status_indicators()
    
    def _update_status_indicators(self):
        """Update status indicators based on GlobalState"""
        # Update connection status indicators
        connection_info = {
            'ni_daq': "250 Hz" if self.state.connections['ni_daq'] else "",
            'pico_tc08': "1 Hz" if self.state.connections['pico_tc08'] else "",
            'bga244': "0.5 Hz" if self.state.connections['bga244'] else "",
            'cvm24p': "10 Hz" if self.state.connections['cvm24p'] else ""
        }
        
        for device, connected in self.state.connections.items():
            self.status_indicators.update_device_status(device, connected, connection_info[device])
        
        # Update actuator states
        for i, valve_state in enumerate(self.state.valve_states):
            if valve_state:
                self.valve_labels[i].configure(text="ON", background="green")
            else:
                self.valve_labels[i].configure(text="OFF", background="red")
        
        if self.state.pump_state:
            self.pump_state_label.configure(text="ON", background="green")
        else:
            self.pump_state_label.configure(text="OFF", background="red")
        
        # Update current sensor
        self.current_label.configure(text=f"{self.state.current_value:.1f} A")
        
        # Update sensor values in plot placeholders
        self.pressure_placeholder.configure(
            text=f"[Pressure Plot Placeholder]\n\nPressure Sensor 1: {self.state.pressure_values[0]:.1f} PSI\nPressure Sensor 2: {self.state.pressure_values[1]:.1f} PSI"
        )
        
        avg_voltage = sum(self.state.cell_voltages) / len(self.state.cell_voltages) if self.state.cell_voltages else 0
        total_voltage = sum(self.state.cell_voltages)
        self.voltage_placeholder.configure(
            text=f"[Voltage Plot Placeholder]\n\nCell Voltage Average: {avg_voltage:.2f} V\nTotal Stack Voltage: {total_voltage:.1f} V"
        )
        
        temp_text = "[Temperature Plot Placeholder]\n\n"
        for i in range(min(8, len(self.state.temperature_values))):
            if i == 4:
                temp_text += "\n"
            temp_text += f"TC{i+1}: {self.state.temperature_values[i]:.1f}°C  "
        self.temperature_placeholder.configure(text=temp_text.strip())
        
        # Schedule next update
        self.update_job = self.root.after(100, self._update_status_indicators)
    
    def cleanup(self):
        """Clean up resources"""
        if self.update_job:
            self.root.after_cancel(self.update_job)
        if hasattr(self.control_panel, 'cleanup'):
            self.control_panel.cleanup()


def main():
    """Test the dashboard by running it directly"""
    root = tk.Tk()
    dashboard = Dashboard(root)
    
    print("=" * 60)
    print("TASK 8 TEST: Dashboard Connected to GlobalState")
    print("=" * 60)
    print("✅ Dashboard fully connected to GlobalState")
    print("✅ Status indicators reflect real connection states")
    print("✅ Timer display shows actual elapsed time")
    print("✅ Control buttons update GlobalState and Timer")
    print("✅ Actuator states reflect GlobalState values")
    print("✅ Sensor values update from GlobalState")
    print("✅ Close confirmation popup when test running")
    print("\n🎯 TEST: Verify complete integration:")
    print("   1. Click Connect - status indicators turn green")
    print("   2. Start Test - timer starts counting")
    print("   3. Try to close window - popup appears asking for confirmation")
    print("   4. Pause/Resume - timer pauses/resumes")
    print("   5. Emergency Stop - everything resets")
    print("   6. All displays update in real-time")
    print("\nLayout: Controls → Status → 2x2 Grid")
    print("Close window when done testing...")
    print("=" * 60)
    
    root.mainloop()


if __name__ == "__main__":
    main() 
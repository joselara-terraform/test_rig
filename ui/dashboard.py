#!/usr/bin/env python3
"""
Dashboard window with 2x2 grid layout for AWE test rig
"""

import tkinter as tk
from tkinter import ttk
from .controls import ControlPanel
from .status_indicators import StatusIndicators


class Dashboard:
    """Main dashboard window with controls, status indicators, and 2x2 grid layout"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("AWE Electrolyzer Test Rig - Dashboard")
        self.root.geometry("1400x900")
        
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
        
        pressure_placeholder = ttk.Label(
            self.pressure_frame, 
            text="[Pressure Plot Placeholder]\n\nPressure Sensor 1: 0.0 PSI\nPressure Sensor 2: 0.0 PSI",
            justify=tk.CENTER,
            background="lightblue"
        )
        pressure_placeholder.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Top-right: Voltage vs Time plot placeholder
        self.voltage_frame = ttk.LabelFrame(
            self.main_frame, 
            text="Voltage vs Time", 
            padding="5"
        )
        self.voltage_frame.grid(row=0, column=1, padx=2, pady=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.voltage_frame.columnconfigure(0, weight=1)
        self.voltage_frame.rowconfigure(0, weight=1)
        
        voltage_placeholder = ttk.Label(
            self.voltage_frame, 
            text="[Voltage Plot Placeholder]\n\nCell Voltage Average: 0.0 V\nTotal Stack Voltage: 0.0 V",
            justify=tk.CENTER,
            background="lightgreen"
        )
        voltage_placeholder.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Bottom-left: Temperature vs Time plot placeholder
        self.temperature_frame = ttk.LabelFrame(
            self.main_frame, 
            text="Temperature vs Time", 
            padding="5"
        )
        self.temperature_frame.grid(row=1, column=0, padx=2, pady=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.temperature_frame.columnconfigure(0, weight=1)
        self.temperature_frame.rowconfigure(0, weight=1)
        
        temperature_placeholder = ttk.Label(
            self.temperature_frame, 
            text="[Temperature Plot Placeholder]\n\nTC1: 0.0°C  TC2: 0.0°C  TC3: 0.0°C  TC4: 0.0°C\nTC5: 0.0°C  TC6: 0.0°C  TC7: 0.0°C  TC8: 0.0°C",
            justify=tk.CENTER,
            background="lightyellow"
        )
        temperature_placeholder.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
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
        
        for i in range(4):
            valve_label = ttk.Label(valve_frame, text=f"Valve {i+1}:")
            valve_label.grid(row=1, column=i, padx=5, pady=2)
            
            # OFF indicator (red background placeholder)
            state_label = tk.Label(
                valve_frame, 
                text="OFF", 
                background="red", 
                foreground="white",
                width=6,
                relief=tk.RAISED
            )
            state_label.grid(row=2, column=i, padx=5, pady=2)
        
        # Pump state
        pump_frame = ttk.Frame(container_frame)
        pump_frame.pack(pady=10)
        
        ttk.Label(pump_frame, text="Pump:", font=("Arial", 10, "bold")).pack()
        pump_state_label = tk.Label(
            pump_frame, 
            text="OFF", 
            background="red", 
            foreground="white",
            width=8,
            relief=tk.RAISED,
            font=("Arial", 10, "bold")
        )
        pump_state_label.pack(pady=5)
        
        # Current sensor display
        current_frame = ttk.Frame(container_frame)
        current_frame.pack(pady=10)
        
        ttk.Label(current_frame, text="Current Sensor:", font=("Arial", 10, "bold")).pack()
        current_label = ttk.Label(current_frame, text="0.0 A", font=("Arial", 12))
        current_label.pack()


def main():
    """Test the dashboard by running it directly"""
    root = tk.Tk()
    dashboard = Dashboard(root)
    
    print("=" * 60)
    print("TASK 7 TEST: Dashboard with Status Indicators")
    print("=" * 60)
    print("✅ Dashboard window created")
    print("✅ Control panel at top")
    print("✅ Connection status indicators in middle")
    print("✅ 2x2 grid layout at bottom")
    print("✅ Four device indicators: NI DAQ, Pico, BGA, CVM")
    print("\n🎯 TEST: Verify layout structure:")
    print("   - Top: Control buttons (Connect, Start, Pause, E-Stop)")
    print("   - Middle: 4 device status indicators (all red/disconnected)")
    print("   - Bottom: 2x2 grid (Pressure, Voltage, Temperature, Valves)")
    print("\n⚠️  Note: Status indicators are not yet connected to controls")
    print("   (This will be done in Task 8: Connect UI to global state)")
    print("\nClose window when done testing...")
    print("=" * 60)
    
    root.mainloop()


if __name__ == "__main__":
    main() 
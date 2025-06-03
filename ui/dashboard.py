#!/usr/bin/env python3
"""
Dashboard window with 2x2 grid layout for AWE test rig
"""

import tkinter as tk
from tkinter import ttk


class Dashboard:
    """Main dashboard window with 2x2 grid layout"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("AWE Electrolyzer Test Rig - Dashboard")
        self.root.geometry("1000x700")
        
        # Create main frame
        self.main_frame = ttk.Frame(root, padding="10")
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights for responsive resizing
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)
        self.main_frame.columnconfigure(0, weight=1)
        self.main_frame.columnconfigure(1, weight=1)
        self.main_frame.rowconfigure(0, weight=1)
        self.main_frame.rowconfigure(1, weight=1)
        
        self._create_widgets()
    
    def _create_widgets(self):
        """Create the 2x2 grid layout with placeholders"""
        
        # Top-left: Pressure vs Time plot placeholder
        self.pressure_frame = ttk.LabelFrame(
            self.main_frame, 
            text="Pressure vs Time", 
            padding="5"
        )
        self.pressure_frame.grid(row=0, column=0, padx=5, pady=5, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        pressure_placeholder = ttk.Label(
            self.pressure_frame, 
            text="[Pressure Plot Placeholder]\n\nPressure Sensor 1: 0.0 PSI\nPressure Sensor 2: 0.0 PSI",
            justify=tk.CENTER,
            background="lightblue"
        )
        pressure_placeholder.pack(expand=True, fill='both')
        
        # Top-right: Voltage vs Time plot placeholder
        self.voltage_frame = ttk.LabelFrame(
            self.main_frame, 
            text="Voltage vs Time", 
            padding="5"
        )
        self.voltage_frame.grid(row=0, column=1, padx=5, pady=5, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        voltage_placeholder = ttk.Label(
            self.voltage_frame, 
            text="[Voltage Plot Placeholder]\n\nCell Voltage Average: 0.0 V\nTotal Stack Voltage: 0.0 V",
            justify=tk.CENTER,
            background="lightgreen"
        )
        voltage_placeholder.pack(expand=True, fill='both')
        
        # Bottom-left: Temperature vs Time plot placeholder
        self.temperature_frame = ttk.LabelFrame(
            self.main_frame, 
            text="Temperature vs Time", 
            padding="5"
        )
        self.temperature_frame.grid(row=1, column=0, padx=5, pady=5, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        temperature_placeholder = ttk.Label(
            self.temperature_frame, 
            text="[Temperature Plot Placeholder]\n\nTC1: 0.0°C  TC2: 0.0°C  TC3: 0.0°C  TC4: 0.0°C\nTC5: 0.0°C  TC6: 0.0°C  TC7: 0.0°C  TC8: 0.0°C",
            justify=tk.CENTER,
            background="lightyellow"
        )
        temperature_placeholder.pack(expand=True, fill='both')
        
        # Bottom-right: Valve/Pump state indicators
        self.valve_frame = ttk.LabelFrame(
            self.main_frame, 
            text="Actuator States", 
            padding="5"
        )
        self.valve_frame.grid(row=1, column=1, padx=5, pady=5, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Create valve state indicators
        self._create_valve_indicators()
    
    def _create_valve_indicators(self):
        """Create valve and pump state indicators"""
        
        # Title
        title_label = ttk.Label(self.valve_frame, text="[Valve/Pump State Panel]", font=("Arial", 12, "bold"))
        title_label.pack(pady=5)
        
        # Valve states (4 valves)
        valve_frame = ttk.Frame(self.valve_frame)
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
        pump_frame = ttk.Frame(self.valve_frame)
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
        current_frame = ttk.Frame(self.valve_frame)
        current_frame.pack(pady=10)
        
        ttk.Label(current_frame, text="Current Sensor:", font=("Arial", 10, "bold")).pack()
        current_label = ttk.Label(current_frame, text="0.0 A", font=("Arial", 12))
        current_label.pack()


def main():
    """Test the dashboard by running it directly"""
    root = tk.Tk()
    dashboard = Dashboard(root)
    
    print("=" * 50)
    print("TASK 5 TEST: Dashboard Window")
    print("=" * 50)
    print("✅ Dashboard window created")
    print("✅ 2x2 grid layout established")
    print("✅ Plot placeholders: Pressure, Voltage, Temperature")
    print("✅ Valve/pump state indicators created")
    print("\n🎯 TEST: Check that window shows 2x2 grid with:")
    print("   - Top-left: Pressure plot (blue)")
    print("   - Top-right: Voltage plot (green)")  
    print("   - Bottom-left: Temperature plot (yellow)")
    print("   - Bottom-right: Valve states (4 valves + pump)")
    print("\nClose window when done testing...")
    print("=" * 50)
    
    root.mainloop()


if __name__ == "__main__":
    main() 
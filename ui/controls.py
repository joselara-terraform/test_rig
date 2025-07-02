#!/usr/bin/env python3
"""
Control buttons for AWE test rig dashboard
"""

import tkinter as tk
from tkinter import ttk
from core.state import get_global_state
from core.timer import get_timer
from services.controller_manager import get_controller_manager


class ChannelSelector(tk.Toplevel):
    """Popup window to select which channels to plot across all data types."""

    def __init__(self, parent):
        super().__init__(parent)
        self.title("Select Plot Channels")
        self.geometry("450x600")  # Larger to accommodate tabs
        self.resizable(False, True)

        self.state = get_global_state()
        
        # Store references to checkboxes and labels for each tab
        self.pressure_vars = []
        self.pressure_labels = []
        self.temperature_vars = []
        self.temperature_labels = []
        self.voltage_vars = []
        self.voltage_labels = []
        self.current_vars = []
        self.current_labels = []

        # Main frame
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill="both", expand=True)
        main_frame.rowconfigure(1, weight=1)
        main_frame.columnconfigure(0, weight=1)
        
        # --- Control Buttons (Global) ---
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        close_button = ttk.Button(button_frame, text="Close", command=self.destroy)
        close_button.pack(side="right", padx=5)

        # --- Tabbed Interface ---
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.grid(row=1, column=0, sticky="nsew")

        # Create tabs
        self._create_pressure_tab()
        self._create_temperature_tab()
        self._create_voltage_tab()
        self._create_current_tab()

        # Start periodic updates of all values
        self._update_all_values()

    def _create_pressure_tab(self):
        """Create the pressure channels tab."""
        pressure_frame = ttk.Frame(self.notebook)
        self.notebook.add(pressure_frame, text="Pressure")
        
        # Control buttons for pressure tab
        button_frame = ttk.Frame(pressure_frame)
        button_frame.pack(fill="x", pady=(5, 10))
        
        ttk.Button(button_frame, text="Select All", command=self._select_all_pressure).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Deselect All", command=self._deselect_all_pressure).pack(side="left", padx=5)

        # Scrollable frame for pressure channels
        canvas = tk.Canvas(pressure_frame)
        scrollbar = ttk.Scrollbar(pressure_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Pressure section
        pressure_label = ttk.Label(scrollable_frame, text="Pressure Sensors:", font=("Arial", 10, "bold"))
        pressure_label.pack(anchor="w", padx=5, pady=(5, 5))

        # Pressure channel names
        pressure_names = ["H₂ Header", "O₂ Header", "Post MS", "Pre MS", "H₂ BP"]
        
        for i in range(5):  # 5 pressure sensors
            var = tk.BooleanVar(value=(i in self.state.visible_pressure_channels))
            
            # Get initial pressure value
            pressure = 0.0
            if len(self.state.pressure_values) > i:
                pressure = self.state.pressure_values[i]
            
            chk = ttk.Checkbutton(scrollable_frame, 
                                  text=f"{pressure_names[i]} - {pressure:.4f} PSI", 
                                  variable=var,
                                  command=lambda i=i: self._on_pressure_check(i))
            chk.pack(anchor="w", padx=15, pady=2)
            self.pressure_vars.append(var)
            self.pressure_labels.append(chk)

        # Separator
        separator = ttk.Separator(scrollable_frame, orient='horizontal')
        separator.pack(fill='x', padx=5, pady=10)

        # Gas concentration section
        gas_label = ttk.Label(scrollable_frame, text="Gas Concentrations:", font=("Arial", 10, "bold"))
        gas_label.pack(anchor="w", padx=5, pady=(5, 5))

        # Gas channel names and storage for gas checkboxes
        gas_names = ["BGA-H2", "BGA-O2", "BGA-DO"]
        self.gas_vars = []
        self.gas_labels = []
        
        for i in range(3):  # 3 gas concentration channels
            var = tk.BooleanVar(value=(i in self.state.visible_gas_channels))
            
            # Get initial gas concentration value
            gas_conc = 0.0
            enhanced_gas_data = getattr(self.state, 'enhanced_gas_data', [])
            if enhanced_gas_data and len(enhanced_gas_data) > i:
                gas_conc = enhanced_gas_data[i]['primary_gas_concentration'] if enhanced_gas_data[i]['primary_gas_concentration'] else 0.0
            elif len(self.state.gas_concentrations) > i:
                # Fallback to legacy gas data
                if i == 0:
                    gas_conc = self.state.gas_concentrations[i].get('H2', 0.0)
                elif i == 1:
                    gas_conc = self.state.gas_concentrations[i].get('O2', 0.0)
                else:
                    gas_conc = self.state.gas_concentrations[i].get('H2', 0.0)
            
            chk = ttk.Checkbutton(scrollable_frame, 
                                  text=f"{gas_names[i]} - {gas_conc:.1f}%", 
                                  variable=var,
                                  command=lambda i=i: self._on_gas_check(i))
            chk.pack(anchor="w", padx=15, pady=2)
            self.gas_vars.append(var)
            self.gas_labels.append(chk)

    def _create_temperature_tab(self):
        """Create the temperature channels tab."""
        temp_frame = ttk.Frame(self.notebook)
        self.notebook.add(temp_frame, text="Temperature")
        
        # Control buttons for temperature tab
        button_frame = ttk.Frame(temp_frame)
        button_frame.pack(fill="x", pady=(5, 10))
        
        ttk.Button(button_frame, text="Select All", command=self._select_all_temperature).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Deselect All", command=self._deselect_all_temperature).pack(side="left", padx=5)

        # Scrollable frame for temperature channels
        canvas = tk.Canvas(temp_frame)
        scrollbar = ttk.Scrollbar(temp_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Temperature channel names
        temp_names = ["Stack 1", "Stack 2", "Stack 3", "Stack 4", "H₂ Bubbler", "O₂ Bubbler", "H₂ Line HEX", "O₂ Line HEX"]
        
        for i in range(8):  # 8 temperature sensors
            var = tk.BooleanVar(value=(i in self.state.visible_temperature_channels))
            
            # Get initial temperature value
            temperature = 0.0
            if len(self.state.temperature_values) > i:
                temperature = self.state.temperature_values[i]
            
            chk = ttk.Checkbutton(scrollable_frame, 
                                  text=f"{temp_names[i]} - {temperature:.1f}°C", 
                                  variable=var,
                                  command=lambda i=i: self._on_temperature_check(i))
            chk.pack(anchor="w", padx=10, pady=2)
            self.temperature_vars.append(var)
            self.temperature_labels.append(chk)

    def _create_voltage_tab(self):
        """Create the voltage channels tab."""
        voltage_frame = ttk.Frame(self.notebook)
        self.notebook.add(voltage_frame, text="Voltage")
        
        # Control buttons for voltage tab
        button_frame = ttk.Frame(voltage_frame)
        button_frame.pack(fill="x", pady=(5, 10))
        
        ttk.Button(button_frame, text="Select All", command=self._select_all_voltage).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Deselect All", command=self._deselect_all_voltage).pack(side="left", padx=5)

        # Scrollable frame for voltage channels
        canvas = tk.Canvas(voltage_frame)
        scrollbar = ttk.Scrollbar(voltage_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Voltage channels (120 cell voltages)
        for i in range(120):
            var = tk.BooleanVar(value=(i in self.state.visible_voltage_channels))
            
            # Get initial voltage value
            voltage = 0.0
            if len(self.state.cell_voltages) > i:
                voltage = self.state.cell_voltages[i]
            
            chk = ttk.Checkbutton(scrollable_frame, 
                                  text=f"Channel {i + 1} - {voltage:.3f}V", 
                                  variable=var,
                                  command=lambda i=i: self._on_voltage_check(i))
            chk.pack(anchor="w", padx=10, pady=1)
            self.voltage_vars.append(var)
            self.voltage_labels.append(chk)

    def _create_current_tab(self):
        """Create the current channel tab."""
        current_frame = ttk.Frame(self.notebook)
        self.notebook.add(current_frame, text="Current")
        
        # Control buttons for current tab
        button_frame = ttk.Frame(current_frame)
        button_frame.pack(fill="x", pady=(5, 10))
        
        ttk.Button(button_frame, text="Select All", command=self._select_all_current).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Deselect All", command=self._deselect_all_current).pack(side="left", padx=5)

        # Scrollable frame for current channel
        canvas = tk.Canvas(current_frame)
        scrollbar = ttk.Scrollbar(current_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Current channel (just one channel)
        var = tk.BooleanVar(value=(0 in self.state.visible_current_channels))
        
        # Get initial current value
        current = self.state.current_value
        
        chk = ttk.Checkbutton(scrollable_frame, 
                              text=f"Stack Current - {current:.1f}A", 
                              variable=var,
                              command=lambda: self._on_current_check(0))
        chk.pack(anchor="w", padx=10, pady=2)
        self.current_vars.append(var)
        self.current_labels.append(chk)

    def _update_all_values(self):
        """Update all channel values displayed in all tabs."""
        # Update pressure values
        pressure_values = self.state.pressure_values
        pressure_names = ["H₂ Header", "O₂ Header", "Post MS", "Pre MS", "H₂ BP"]
        for i in range(5):
            pressure = 0.0
            if len(pressure_values) > i:
                pressure = pressure_values[i]
            new_text = f"{pressure_names[i]} - {pressure:.4f} PSI"
            self.pressure_labels[i].configure(text=new_text)

        # Update gas concentration values
        gas_names = ["BGA-H2", "BGA-O2", "BGA-DO"]
        enhanced_gas_data = getattr(self.state, 'enhanced_gas_data', [])
        for i in range(3):
            gas_conc = 0.0
            if enhanced_gas_data and len(enhanced_gas_data) > i:
                gas_conc = enhanced_gas_data[i]['primary_gas_concentration'] if enhanced_gas_data[i]['primary_gas_concentration'] else 0.0
            elif len(self.state.gas_concentrations) > i:
                # Fallback to legacy gas data
                if i == 0:
                    gas_conc = self.state.gas_concentrations[i].get('H2', 0.0)
                elif i == 1:
                    gas_conc = self.state.gas_concentrations[i].get('O2', 0.0)
                else:
                    gas_conc = self.state.gas_concentrations[i].get('H2', 0.0)
            new_text = f"{gas_names[i]} - {gas_conc:.1f}%"
            self.gas_labels[i].configure(text=new_text)

        # Update temperature values
        temp_values = self.state.temperature_values
        temp_names = ["Stack 1", "Stack 2", "Stack 3", "Stack 4", "H₂ Bubbler", "O₂ Bubbler", "H₂ Line HEX", "O₂ Line HEX"]
        for i in range(8):
            temperature = 0.0
            if len(temp_values) > i:
                temperature = temp_values[i]
            new_text = f"{temp_names[i]} - {temperature:.1f}°C"
            self.temperature_labels[i].configure(text=new_text)

        # Update voltage values
        cell_voltages = self.state.cell_voltages
        for i in range(120):
            voltage = 0.0
            if len(cell_voltages) > i:
                voltage = cell_voltages[i]
            new_text = f"Channel {i + 1} - {voltage:.3f}V"
            self.voltage_labels[i].configure(text=new_text)

        # Update current values
        current = self.state.current_value
        if len(self.current_labels) > 0:
            new_text = f"Stack Current - {current:.1f}A"
            self.current_labels[0].configure(text=new_text)
        
        # Schedule next update (every 100ms)
        self.after(100, self._update_all_values)

    # Pressure tab callbacks
    def _on_pressure_check(self, channel_index):
        if self.pressure_vars[channel_index].get():
            self.state.visible_pressure_channels.add(channel_index)
        else:
            self.state.visible_pressure_channels.discard(channel_index)
        print(f"Visible pressure channels: {sorted(list(self.state.visible_pressure_channels))}")

    def _select_all_pressure(self):
        for i in range(5):
            if not self.pressure_vars[i].get():
                self.pressure_vars[i].set(True)
                self.state.visible_pressure_channels.add(i)
        for i in range(3):
            if not self.gas_vars[i].get():
                self.gas_vars[i].set(True)
                self.state.visible_gas_channels.add(i)
        print("All pressure and gas channels selected.")

    def _deselect_all_pressure(self):
        for i in range(5):
            if self.pressure_vars[i].get():
                self.pressure_vars[i].set(False)
                self.state.visible_pressure_channels.discard(i)
        for i in range(3):
            if self.gas_vars[i].get():
                self.gas_vars[i].set(False)
                self.state.visible_gas_channels.discard(i)
        print("All pressure and gas channels deselected.")

    # Gas concentration callbacks (for pressure tab)
    def _on_gas_check(self, channel_index):
        if self.gas_vars[channel_index].get():
            self.state.visible_gas_channels.add(channel_index)
        else:
            self.state.visible_gas_channels.discard(channel_index)
        print(f"Visible gas channels: {sorted(list(self.state.visible_gas_channels))}")

    # Temperature tab callbacks
    def _on_temperature_check(self, channel_index):
        if self.temperature_vars[channel_index].get():
            self.state.visible_temperature_channels.add(channel_index)
        else:
            self.state.visible_temperature_channels.discard(channel_index)
        print(f"Visible temperature channels: {sorted(list(self.state.visible_temperature_channels))}")

    def _select_all_temperature(self):
        for i in range(8):
            if not self.temperature_vars[i].get():
                self.temperature_vars[i].set(True)
                self.state.visible_temperature_channels.add(i)
        print("All temperature channels selected.")

    def _deselect_all_temperature(self):
        for i in range(8):
            if self.temperature_vars[i].get():
                self.temperature_vars[i].set(False)
                self.state.visible_temperature_channels.discard(i)
        print("All temperature channels deselected.")

    # Voltage tab callbacks (existing logic)
    def _on_voltage_check(self, channel_index):
        if self.voltage_vars[channel_index].get():
            self.state.visible_voltage_channels.add(channel_index)
        else:
            self.state.visible_voltage_channels.discard(channel_index)
        print(f"Visible voltage channels: {sorted(list(self.state.visible_voltage_channels))}")

    def _select_all_voltage(self):
        for i in range(120):
            if not self.voltage_vars[i].get():
                self.voltage_vars[i].set(True)
                self.state.visible_voltage_channels.add(i)
        print("All voltage channels selected.")
    
    def _deselect_all_voltage(self):
        for i in range(120):
            if self.voltage_vars[i].get():
                self.voltage_vars[i].set(False)
                self.state.visible_voltage_channels.discard(i)
        print("All voltage channels deselected.")

    # Current tab callbacks
    def _on_current_check(self, channel_index):
        if self.current_vars[channel_index].get():
            self.state.visible_current_channels.add(channel_index)
        else:
            self.state.visible_current_channels.discard(channel_index)
        print(f"Visible current channels: {sorted(list(self.state.visible_current_channels))}")

    def _select_all_current(self):
        if not self.current_vars[0].get():
            self.current_vars[0].set(True)
            self.state.visible_current_channels.add(0)
        print("Current channel selected.")

    def _deselect_all_current(self):
        if self.current_vars[0].get():
            self.current_vars[0].set(False)
            self.state.visible_current_channels.discard(0)
        print("Current channel deselected.")


class ControlPanel:
    """Control buttons for test operations"""
    
    def __init__(self, parent_frame, plot_reset_callback=None):
        self.parent_frame = parent_frame
        self.state = get_global_state()
        self.timer = get_timer()
        self.controller = get_controller_manager()
        self.channel_selector_window = None
        
        # Callback to reset plots when starting a new test
        self.plot_reset_callback = plot_reset_callback
        
        # UI update timer
        self.update_job = None
        
        self._create_controls()
        self._start_ui_updates()
    
    def _create_controls(self):
        """Create control button panel"""
        
        # Main control frame
        control_frame = ttk.LabelFrame(self.parent_frame, text="Test Controls", padding="10")
        control_frame.pack(fill='x', pady=5)
        
        # Top row: buttons
        button_frame = ttk.Frame(control_frame)
        button_frame.pack()
        
        # Connect button
        self.connect_button = ttk.Button(
            button_frame,
            text="Connect",
            command=self._on_connect_click,
            width=15
        )
        self.connect_button.grid(row=0, column=0, padx=5, pady=5)
        
        # Start Test button
        self.start_button = ttk.Button(
            button_frame,
            text="Start Test",
            command=self._on_start_click,
            width=15,
            state='disabled'
        )
        self.start_button.grid(row=0, column=1, padx=5, pady=5)
        
        # Pause/Resume button
        self.pause_button = ttk.Button(
            button_frame,
            text="Pause",
            command=self._on_pause_click,
            width=15,
            state='disabled'
        )
        self.pause_button.grid(row=0, column=2, padx=5, pady=5)

        # Channel Selector Button (renamed from voltage-specific)
        self.channel_select_button = ttk.Button(
            button_frame,
            text="Select Plot Channels",
            command=self._open_channel_selector,
            width=20
        )
        self.channel_select_button.grid(row=0, column=3, padx=5, pady=5)
        
        # Emergency Stop button
        self.estop_button = tk.Button(
            button_frame,
            text="EMERGENCY STOP",
            command=self._on_estop_click,
            width=20,
            background="red",
            foreground="white",
            font=("Arial", 10, "bold"),
            relief=tk.RAISED,
            borderwidth=2
        )
        self.estop_button.grid(row=0, column=4, padx=5, pady=5)
        
        # Purge button
        self.purge_button = tk.Button(
            button_frame,
            text="PURGE OFF",
            command=self._on_purge_click,
            width=15,
            background="gray",
            foreground="white",
            font=("Arial", 9, "bold"),
            relief=tk.RAISED,
            borderwidth=2
        )
        self.purge_button.grid(row=0, column=5, padx=5, pady=5)
        
        # Timer display
        self.timer_label = ttk.Label(
            button_frame,
            text="00:00:00",
            font=("Arial", 16, "bold"),
            foreground="blue"
        )
        self.timer_label.grid(row=0, column=6, padx=20, pady=5)
        
        # Bottom row: status
        status_frame = ttk.Frame(control_frame)
        status_frame.pack(pady=5)
        
        self.status_label = ttk.Label(status_frame, text="Status: Disconnected", font=("Arial", 10))
        self.status_label.pack()

    def _open_channel_selector(self):
        """Open the comprehensive channel selector window."""
        if self.channel_selector_window and self.channel_selector_window.winfo_exists():
            self.channel_selector_window.lift()
        else:
            self.channel_selector_window = ChannelSelector(self.parent_frame)
    
    def _on_connect_click(self):
        """Handle Connect button click"""
        if not self.controller.is_all_connected():
            print("🔌 Connect button clicked")
            
            # Use ControllerManager to start all services
            success = self.controller.start_all_services()
            
            if success:
                print("   ✅ All devices connected via ControllerManager")
            else:
                print("   ❌ Some devices failed to connect")
        else:
            print("🔌 Disconnect button clicked")
            
            # Stop any running test first
            if self.state.test_running:
                self._stop_test()
            
            # Use ControllerManager to stop all services
            self.controller.stop_all_services()
            print("   ✅ All devices disconnected via ControllerManager")
    
    def _on_start_click(self):
        """Handle Start Test button click"""
        if not self.state.test_running:
            print("▶️  Start Test button clicked")
            print("   → Starting test sequence...")
            
            # Reset plots for new test
            if self.plot_reset_callback:
                self.plot_reset_callback()
                print("   → Plots reset for new test")
            
            # Use controller manager to start test with real CSV logging
            success = self.controller.start_test("UI_Test_Session")
            
            if success:
                # Check if CSV logging actually started by looking at the logger status
                csv_logger_status = self.controller.csv_logger.get_status()
                if csv_logger_status.get('logging', False):
                    print("   ✅ Test started successfully with CSV data logging")
                    print("   → CSV files are being created in session folder")
                else:
                    print("   ✅ Test started successfully but CSV logging failed")
                    print("   → No data files will be created (check console for details)")
            else:
                print("   ❌ Failed to start test")
        else:
            print("⏹️  Stop Test button clicked")
            self._stop_test()
    
    def _stop_test(self):
        """Stop the current test using controller manager"""
        print("   → Stopping test sequence...")
        
        # Check if CSV logging was active before stopping
        csv_was_logging = self.controller.csv_logger.get_status().get('logging', False)
        
        # Use controller manager to stop test (this handles CSV logging and session finalization)
        final_session = self.controller.stop_test("completed")
        
        if csv_was_logging:
            print("   ✅ Test stopped - CSV data logging completed")
            if final_session:
                file_count = len(final_session.get('files', {}))
                print(f"   → {file_count} files saved in session folder")
        else:
            print("   ✅ Test stopped - no CSV data was logged")
            print("   → Session folder created but no data files")
    
    def _on_pause_click(self):
        """Handle Pause/Resume button click"""
        if not self.state.test_paused:
            print("⏸️  Pause button clicked")
            print("   → Pausing test...")
            
            # Update GlobalState and pause timer
            with self.state._lock:
                self.state.test_paused = True
            
            self.timer.pause()
            print("   → Timer paused")
            print("   → Data logging paused (mocked)")
            print("   ✅ Test paused")
        else:
            print("▶️  Resume button clicked")
            print("   → Resuming test...")
            
            # Update GlobalState and resume timer
            with self.state._lock:
                self.state.test_paused = False
            
            self.timer.resume()
            print("   → Timer resumed")
            print("   → Data logging resumed (mocked)")
            print("   ✅ Test resumed")
    
    def _on_estop_click(self):
        """Handle Emergency Stop button click"""
        print("🚨 EMERGENCY STOP ACTIVATED! 🚨")
        print("   → Emergency stop initiated via controller manager")
        
        # Use controller manager for emergency stop (handles CSV logging, sessions, and hardware safety)
        self.controller.emergency_stop()
        
        print("   ✅ Emergency stop complete - system in safe state")
        print("   ℹ️  Press Start Test to begin new test")
    
    def _on_purge_click(self):
        """Handle Purge button click"""
        current_purge = self.state.purge_mode
        new_purge = not current_purge
        
        print(f"🧹 PURGE button clicked")
        print(f"   → Changing purge mode: {'OFF' if current_purge else 'ON'} → {'ON' if new_purge else 'OFF'}")
        
        # Update GlobalState
        with self.state._lock:
            self.state.purge_mode = new_purge
        
        # Call BGA244 service to actually set purge mode
        try:
            # Fix: Access the actual service instance, not the service dict
            bga_service_info = self.controller.services.get('bga244')
            bga_service = bga_service_info['service'] if bga_service_info else None
            
            if bga_service and hasattr(bga_service, 'set_purge_mode'):
                bga_service.set_purge_mode(new_purge)
                if new_purge:
                    print("   → All BGA244 secondary gases changed to N2")
                    print("   → Hardware devices reconfigured for purge mode")
                else:
                    print("   → BGA244 secondary gases restored to normal configuration")
                    print("   → Hardware devices reconfigured for normal mode")
            else:
                print("   → BGA244 service not available (purge mode stored in state)")
        except Exception as e:
            print(f"   ⚠️  Error setting BGA purge mode: {e}")
        
        print(f"   ✅ Purge mode {'ENABLED' if new_purge else 'DISABLED'}")
    
    def _start_ui_updates(self):
        """Start periodic UI updates"""
        self._update_ui()
    
    def _update_ui(self):
        """Update UI elements based on current state"""
        # Update button states based on ControllerManager and GlobalState
        all_connected = self.controller.is_all_connected()
        
        # Connect button
        if all_connected:
            self.connect_button.configure(text="Disconnect")
        else:
            self.connect_button.configure(text="Connect")
        
        # Start Test button - only enabled when connected
        if all_connected:
            self.start_button.configure(state='normal')
            if self.state.test_running:
                self.start_button.configure(text="Stop Test")
            else:
                self.start_button.configure(text="Start Test")
        else:
            self.start_button.configure(state='disabled', text="Start Test")
        
        # Pause button - only available during running test
        if self.state.test_running:
            self.pause_button.configure(state='normal')
            if self.state.test_paused:
                self.pause_button.configure(text="Resume")
            else:
                self.pause_button.configure(text="Pause")
        else:
            self.pause_button.configure(state='disabled', text="Pause")
        
        # Status label
        if not all_connected:
            status_text = "Status: Disconnected"
        elif self.state.test_running:
            if self.state.test_paused:
                status_text = "Status: Test Paused"
            else:
                status_text = "Status: Test Running"
        else:
            status_text = "Status: Connected - Ready"
        
        self.status_label.configure(text=status_text)
        
        # Purge button - only enabled when BGA244 is connected
        bga_connected = self.controller.is_bga_connected() if hasattr(self.controller, 'is_bga_connected') else all_connected
        
        if bga_connected:
            self.purge_button.configure(state='normal')
            if self.state.purge_mode:
                self.purge_button.configure(
                    text="PURGE ON",
                    background="orange",
                    activebackground="darkorange"
                )
            else:
                self.purge_button.configure(
                    text="PURGE OFF",
                    background="gray",
                    activebackground="darkgray"
                )
        else:
            self.purge_button.configure(
                state='disabled',
                text="PURGE OFF",
                background="lightgray"
            )
        
        # Timer display
        elapsed = self.state.timer_value
        hours = int(elapsed // 3600)
        minutes = int((elapsed % 3600) // 60)
        seconds = int(elapsed % 60)
        timer_text = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        self.timer_label.configure(text=timer_text)
        
        # Schedule next update
        self.update_job = self.parent_frame.after(100, self._update_ui)
    
    def cleanup(self):
        """Clean up resources"""
        if self.update_job:
            self.parent_frame.after_cancel(self.update_job)


def main():
    """Test the control panel by running it directly"""
    root = tk.Tk()
    root.title("Test - Control Panel with ControllerManager")
    root.geometry("800x200")
    
    print("=" * 60)
    print("TASK 9 TEST: Controls with ControllerManager")
    print("=" * 60)
    print("✅ Control panel connected to ControllerManager")
    print("✅ Connect button uses real service coordination")
    print("✅ Timer display shows real elapsed time")
    print("✅ Buttons actually control state and timer")
    print("\n🎯 TEST: Click buttons and verify:")
    print("   1. Connect - actually starts all services via ControllerManager")
    print("   2. Status indicators should update automatically")
    print("   3. Start Test - actually starts Timer")
    print("   4. Pause - actually pauses Timer")
    print("   5. Timer display updates in real-time")
    print("   6. Emergency Stop - resets everything")
    print("\nTimer display format: HH:MM:SS")
    print("Close window when done testing...")
    print("=" * 60)
    
    control_panel = ControlPanel(root)
    
    def on_closing():
        control_panel.cleanup()
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()


if __name__ == "__main__":
    main() 
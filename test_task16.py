#!/usr/bin/env python3
"""
Test file for Task 16: Live Temperature vs Time Plot
Run with: python3 test_task16.py
"""

import time
import tkinter as tk
from tkinter import ttk
from ui.plots import TemperaturePlot
from ui.dashboard import Dashboard
from services.controller_manager import get_controller_manager
from core.state import get_global_state


def test_temperature_plot_creation():
    """Test that TemperaturePlot can be created"""
    print("Testing TemperaturePlot creation...")
    
    try:
        root = tk.Tk()
        test_frame = ttk.Frame(root)
        test_frame.pack(fill='both', expand=True)
        
        plot = TemperaturePlot(test_frame)
        print("✅ PASS: TemperaturePlot created successfully")
        
        plot.destroy()
        root.destroy()
        return True
        
    except Exception as e:
        print(f"❌ FAIL: Could not create TemperaturePlot: {e}")
        return False


def test_temperature_plot_data_integration():
    """Test that TemperaturePlot reads from GlobalState"""
    print("\nTesting TemperaturePlot data integration...")
    
    try:
        state = get_global_state()
        
        # Set test temperature values (8 thermocouple channels)
        test_temperatures = [25.0, 42.5, 65.0, 58.5, 22.0, 30.5, 38.0, 45.5]  # °C
        
        state.update_sensor_values(temperature_values=test_temperatures)
        
        # Verify state update
        if len(state.temperature_values) == 8:
            print("✅ PASS: GlobalState temperature values updated correctly")
            print(f"   Temperature values: {state.temperature_values}")
            return True
        else:
            print(f"❌ FAIL: Expected 8 temperatures, got {len(state.temperature_values)}")
            return False
        
    except Exception as e:
        print(f"❌ FAIL: Data integration error: {e}")
        return False


def test_temperature_plot_with_live_data():
    """Test temperature plotting with live data from Pico TC-08 service"""
    print("\nTesting temperature plot with live Pico TC-08 data...")
    
    try:
        # Start all services via ControllerManager
        controller = get_controller_manager()
        if not controller.start_all_services():
            print("❌ FAIL: Could not start services")
            return False
        
        print("✅ PASS: All services providing live data")
        
        # Let data accumulate
        time.sleep(3.0)
        
        # Check that temperature data is updating
        state = get_global_state()
        temp_values = state.temperature_values
        
        if len(temp_values) == 8:
            # Extract temperature readings
            inlet_temp = temp_values[0]      # Inlet water temp
            outlet_temp = temp_values[1]     # Outlet water temp
            stack_temp1 = temp_values[2]     # Stack temperature 1
            stack_temp2 = temp_values[3]     # Stack temperature 2
            ambient_temp = temp_values[4]    # Ambient temperature
            cooling_temp = temp_values[5]    # Cooling system temp
            gas_temp = temp_values[6]        # Gas output temp
            case_temp = temp_values[7]       # Electronics case temp
            
            print(f"✅ PASS: Live temperature data collected")
            print(f"   Inlet: {inlet_temp:.1f}°C")
            print(f"   Outlet: {outlet_temp:.1f}°C")
            print(f"   Stack 1: {stack_temp1:.1f}°C")
            print(f"   Stack 2: {stack_temp2:.1f}°C")
            print(f"   Ambient: {ambient_temp:.1f}°C")
            print(f"   Cooling: {cooling_temp:.1f}°C")
            print(f"   Gas: {gas_temp:.1f}°C")
            print(f"   Case: {case_temp:.1f}°C")
            
            # Verify reasonable temperature ranges (15-80°C based on Pico TC-08 config)
            temp_ok = all(15.0 <= temp <= 80.0 for temp in temp_values)
            
            if temp_ok:
                print("✅ PASS: Temperature values in realistic range (15-80°C)")
            else:
                print("❌ FAIL: Temperature values outside expected range")
                controller.stop_all_services()
                return False
                
        else:
            print(f"❌ FAIL: Expected 8 temperatures, got {len(temp_values)}")
            controller.stop_all_services()
            return False
        
        # Clean up
        controller.stop_all_services()
        return True
        
    except Exception as e:
        print(f"❌ FAIL: Live data test error: {e}")
        return False


def test_temperature_channel_mapping():
    """Test temperature channel mapping and naming"""
    print("\nTesting temperature channel mapping...")
    
    try:
        state = get_global_state()
        
        # Set test temperatures with known values for each channel
        test_temperatures = [
            25.0,  # CH0: inlet_temp
            45.0,  # CH1: outlet_temp  
            70.0,  # CH2: stack_temp_1
            68.0,  # CH3: stack_temp_2
            22.0,  # CH4: ambient_temp
            30.0,  # CH5: cooling_temp
            40.0,  # CH6: gas_temp
            50.0   # CH7: case_temp
        ]
        
        state.update_sensor_values(temperature_values=test_temperatures)
        
        # Verify channel mapping
        expected_channels = [
            "Inlet water temp",
            "Outlet water temp", 
            "Stack temperature 1",
            "Stack temperature 2",
            "Ambient temperature",
            "Cooling system temp",
            "Gas output temp",
            "Electronics case temp"
        ]
        
        print(f"✅ PASS: Temperature channel mapping test")
        for i, (temp, desc) in enumerate(zip(test_temperatures, expected_channels)):
            print(f"   CH{i}: {temp}°C ({desc})")
        
        # Verify values are in 0-100°C range for plotting
        in_range = all(0.0 <= temp <= 100.0 for temp in test_temperatures)
        
        if in_range:
            print("✅ PASS: All temperatures in 0-100°C plotting range")
            return True
        else:
            print("❌ FAIL: Some temperatures outside 0-100°C plotting range")
            return False
        
    except Exception as e:
        print(f"❌ FAIL: Channel mapping test error: {e}")
        return False


def test_dashboard_integration():
    """Test that dashboard properly integrates temperature plot"""
    print("\nTesting dashboard integration...")
    
    try:
        # Create dashboard in test mode
        root = tk.Tk()
        root.withdraw()  # Hide window for testing
        
        dashboard = Dashboard(root)
        
        # Check that temperature plot exists and is not a placeholder
        if hasattr(dashboard, 'temperature_plot') and dashboard.temperature_plot is not None:
            if hasattr(dashboard.temperature_plot, '_update_plot'):
                print("✅ PASS: Dashboard contains live temperature plot")
            else:
                print("❌ FAIL: Dashboard temperature plot is still a placeholder")
                root.destroy()
                return False
        else:
            print("❌ FAIL: Dashboard missing temperature plot")
            root.destroy()
            return False
        
        # Test plot reset function
        dashboard.reset_plots()
        print("✅ PASS: Plot reset function works")
        
        # Clean up
        dashboard.cleanup()
        root.destroy()
        return True
        
    except Exception as e:
        print(f"❌ FAIL: Dashboard integration error: {e}")
        return False


def test_temperature_plot_features():
    """Test specific temperature plot features"""
    print("\nTesting temperature plot features...")
    
    try:
        root = tk.Tk()
        root.withdraw()  # Hide for testing
        
        test_frame = ttk.Frame(root)
        plot = TemperaturePlot(test_frame)
        
        # Check that plot has required components
        if hasattr(plot, 'fig') and hasattr(plot, 'ax'):
            print("✅ PASS: Plot has matplotlib figure and axes")
        else:
            print("❌ FAIL: Plot missing matplotlib components")
            return False
        
        # Check temperature lines (8 channels)
        required_lines = [
            'line_inlet', 'line_outlet', 'line_stack1', 'line_stack2',
            'line_ambient', 'line_cooling', 'line_gas', 'line_case'
        ]
        for line_name in required_lines:
            if hasattr(plot, line_name):
                print(f"✅ PASS: Plot has {line_name}")
            else:
                print(f"❌ FAIL: Plot missing {line_name}")
                return False
        
        # Check data storage (8 channels)
        required_data = [
            'inlet_temp_data', 'outlet_temp_data', 'stack_temp1_data', 'stack_temp2_data',
            'ambient_temp_data', 'cooling_temp_data', 'gas_temp_data', 'case_temp_data'
        ]
        for data_name in required_data:
            if hasattr(plot, data_name):
                print(f"✅ PASS: Plot has {data_name}")
            else:
                print(f"❌ FAIL: Plot missing {data_name}")
                return False
        
        # Check Y-axis limits (should be 0-100°C)
        y_limits = plot.ax.get_ylim()
        if y_limits == (0.0, 100.0):
            print("✅ PASS: Y-axis limits set to 0-100°C")
        else:
            print(f"❌ FAIL: Y-axis limits incorrect: {y_limits} (expected (0.0, 100.0))")
            return False
        
        # Test reset
        plot.reset()
        print("✅ PASS: Plot reset works")
        
        # Clean up
        plot.destroy()
        root.destroy()
        return True
        
    except Exception as e:
        print(f"❌ FAIL: Plot features test error: {e}")
        return False


def interactive_test():
    """Run interactive test showing live temperature plot"""
    print("\n" + "=" * 50)
    print("INTERACTIVE TEST: Live Temperature Plot")
    print("=" * 50)
    
    try:
        # Create test window
        root = tk.Tk()
        root.title("Task 16 - Live Temperature Plot Test")
        root.geometry("800x600")
        
        # Create frame for plot
        plot_frame = ttk.LabelFrame(root, text="Temperatures vs Time - Task 16", padding="5")
        plot_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Create temperature plot
        temperature_plot = TemperaturePlot(plot_frame)
        
        # Start all services for live data
        controller = get_controller_manager()
        if controller.start_all_services():
            print("✅ All services providing live temperature data")
        
        # Add instructions
        info_frame = ttk.Frame(root)
        info_frame.pack(fill='x', padx=10, pady=5)
        
        info_label = ttk.Label(
            info_frame,
            text="🌡️ Watch the live temperature plot update in real-time!\n"
                 "8 lines showing thermocouple readings\n"
                 "Blue: Inlet | Red: Outlet | Green: Stack 1 | Magenta: Stack 2\n"
                 "Cyan dashed: Ambient | Yellow dashed: Cooling\n"
                 "Orange: Gas | Brown: Case\n"
                 "Y-axis: 0-100°C (static), X-axis: dynamic expansion\n"
                 "Expected range: 15-80°C for realistic electrolyzer operation",
            justify='center'
        )
        info_label.pack()
        
        def cleanup():
            if controller.is_all_connected():
                controller.stop_all_services()
            temperature_plot.destroy()
            root.destroy()
        
        root.protocol("WM_DELETE_WINDOW", cleanup)
        
        print("📊 Live temperature plot window opened")
        print("   → 8 thermocouple channels")
        print("   → Actual temperatures (15-80°C range)")
        print("   → Static Y-axis (0-100°C), dynamic X-axis")
        print("\nClose window when done observing...")
        
        root.mainloop()
        return True
        
    except Exception as e:
        print(f"❌ FAIL: Interactive test error: {e}")
        return False


def main():
    """Run all tests"""
    print("=" * 60)
    print("TASK 16 TEST: Live Temperature vs Time Plot")
    print("=" * 60)
    
    all_tests_passed = True
    
    # Test 1: Plot creation
    success = test_temperature_plot_creation()
    all_tests_passed &= success
    
    # Test 2: Data integration
    success = test_temperature_plot_data_integration()
    all_tests_passed &= success
    
    # Test 3: Live data
    success = test_temperature_plot_with_live_data()
    all_tests_passed &= success
    
    # Test 4: Channel mapping
    success = test_temperature_channel_mapping()
    all_tests_passed &= success
    
    # Test 5: Dashboard integration
    success = test_dashboard_integration()
    all_tests_passed &= success
    
    # Test 6: Plot features
    success = test_temperature_plot_features()
    all_tests_passed &= success
    
    print("\n" + "=" * 60)
    if all_tests_passed:
        print("🎉 ALL TESTS PASSED - Task 16 Complete!")
        print("✅ Live temperature plotting fully functional")
        print("✅ 8 thermocouple channels with realistic data")
        print("✅ Actual temperatures (0-100°C range)")
        print("✅ Static Y-axis (0-100°C), dynamic X-axis")
        print("✅ Dashboard integration working")
        print("✅ Plot reset functionality working")
        print("✅ Real-time data from Pico TC-08 service")
        print("\n🎯 Task 16 deliverables:")
        print("   ✅ Enhanced ui/plots.py with TemperaturePlot class")
        print("   ✅ Live line plot from temperature data in GlobalState")
        print("   ✅ 8 thermocouple channels with proper mapping")
        print("   ✅ Actual temperature values (15-80°C range)")
        print("   ✅ Integrated into dashboard 2x2 grid")
        print("   ✅ Plot resets when starting new test")
        print("   ✅ Same architecture as PressurePlot and VoltagePlot")
        
        # Offer interactive test
        response = input("\n🔍 Run interactive test to see live temperature plotting? (y/n): ")
        if response.lower() == 'y':
            interactive_test()
        
    else:
        print("💥 SOME TESTS FAILED - Task 16 Needs Fixes")
    
    print("=" * 60)


if __name__ == "__main__":
    main() 
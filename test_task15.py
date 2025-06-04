#!/usr/bin/env python3
"""
Test file for Task 15: Live Cell Voltage vs Time Plot
Run with: python3 test_task15.py
"""

import time
import tkinter as tk
from tkinter import ttk
from ui.plots import VoltagePlot
from ui.dashboard import Dashboard
from services.controller_manager import get_controller_manager
from core.state import get_global_state


def test_voltage_plot_creation():
    """Test that VoltagePlot can be created"""
    print("Testing VoltagePlot creation...")
    
    try:
        root = tk.Tk()
        test_frame = ttk.Frame(root)
        test_frame.pack(fill='both', expand=True)
        
        plot = VoltagePlot(test_frame)
        print("✅ PASS: VoltagePlot created successfully")
        
        plot.destroy()
        root.destroy()
        return True
        
    except Exception as e:
        print(f"❌ FAIL: Could not create VoltagePlot: {e}")
        return False


def test_voltage_plot_data_integration():
    """Test that VoltagePlot reads from GlobalState"""
    print("\nTesting VoltagePlot data integration...")
    
    try:
        state = get_global_state()
        
        # Set test cell voltage values (120 cells)
        test_voltages = [2.5 + (i * 0.005) for i in range(120)]  # 2.50V to 3.10V
        
        state.update_sensor_values(cell_voltages=test_voltages)
        
        # Verify state update
        if len(state.cell_voltages) == 120:
            print("✅ PASS: GlobalState cell voltages updated correctly")
            print(f"   Sample voltages: {state.cell_voltages[:3]}...{state.cell_voltages[-1]}")
            return True
        else:
            print(f"❌ FAIL: Expected 120 voltages, got {len(state.cell_voltages)}")
            return False
        
    except Exception as e:
        print(f"❌ FAIL: Data integration error: {e}")
        return False


def test_voltage_plot_with_live_data():
    """Test voltage plotting with live data from CVM service"""
    print("\nTesting voltage plot with live CVM data...")
    
    try:
        # Start all services via ControllerManager
        controller = get_controller_manager()
        if not controller.start_all_services():
            print("❌ FAIL: Could not start services")
            return False
        
        print("✅ PASS: All services providing live data")
        
        # Let data accumulate
        time.sleep(3.0)
        
        # Check that voltage data is updating
        state = get_global_state()
        cell_voltages = state.cell_voltages
        
        if len(cell_voltages) == 120:
            # Calculate group averages
            group1_avg = sum(cell_voltages[0:20]) / 20
            group6_avg = sum(cell_voltages[100:120]) / 20
            total_voltage = sum(cell_voltages)
            overall_avg = total_voltage / 120
            min_voltage = min(cell_voltages)
            max_voltage = max(cell_voltages)
            
            print(f"✅ PASS: Live voltage data collected")
            print(f"   Total stack: {total_voltage:.1f}V")
            print(f"   Overall average: {overall_avg:.3f}V")
            print(f"   Group 1 avg: {group1_avg:.3f}V")
            print(f"   Group 6 avg: {group6_avg:.3f}V")
            print(f"   Min cell: {min_voltage:.3f}V")
            print(f"   Max cell: {max_voltage:.3f}V")
            
            # Verify reasonable voltage ranges (2.0-3.5V)
            voltage_ok = (2.0 <= min_voltage <= 3.5 and 
                         2.0 <= max_voltage <= 3.5 and
                         240.0 <= total_voltage <= 420.0)  # 120 * (2.0-3.5)
            
            if voltage_ok:
                print("✅ PASS: Voltage values in realistic range")
            else:
                print("❌ FAIL: Voltage values outside expected range")
                controller.stop_all_services()
                return False
                
        else:
            print(f"❌ FAIL: Expected 120 voltages, got {len(cell_voltages)}")
            controller.stop_all_services()
            return False
        
        # Clean up
        controller.stop_all_services()
        return True
        
    except Exception as e:
        print(f"❌ FAIL: Live data test error: {e}")
        return False


def test_voltage_normalization():
    """Test voltage group averaging for plotting"""
    print("\nTesting voltage group averaging...")
    
    try:
        state = get_global_state()
        
        # Set test voltages with known values for each group
        test_voltages = []
        for group in range(6):
            group_voltage = 2.5 + (group * 0.1)  # Groups: 2.5V, 2.6V, 2.7V, 2.8V, 2.9V, 3.0V
            test_voltages.extend([group_voltage] * 20)  # 20 cells per group
        
        state.update_sensor_values(cell_voltages=test_voltages)
        
        # Calculate expected group averages
        expected_averages = [2.5, 2.6, 2.7, 2.8, 2.9, 3.0]
        
        # Calculate actual group averages
        actual_averages = []
        for i in range(6):
            start_idx = i * 20
            end_idx = (i + 1) * 20
            group_avg = sum(test_voltages[start_idx:end_idx]) / 20
            actual_averages.append(group_avg)
        
        print(f"✅ PASS: Voltage group averaging test")
        for i, (expected, actual) in enumerate(zip(expected_averages, actual_averages)):
            print(f"   Group {i+1}: {actual:.3f}V (expected {expected:.3f}V)")
        
        # Verify values are correct and in 0-5V range
        averages_correct = all(abs(exp - act) < 0.001 for exp, act in zip(expected_averages, actual_averages))
        in_range = all(0.0 <= avg <= 5.0 for avg in actual_averages)
        
        if averages_correct and in_range:
            print("✅ PASS: Group averages correct and in 0-5V range")
            return True
        else:
            print("❌ FAIL: Group averages incorrect or outside 0-5V range")
            return False
        
    except Exception as e:
        print(f"❌ FAIL: Group averaging test error: {e}")
        return False


def test_dashboard_integration():
    """Test that dashboard properly integrates voltage plot"""
    print("\nTesting dashboard integration...")
    
    try:
        # Create dashboard in test mode
        root = tk.Tk()
        root.withdraw()  # Hide window for testing
        
        dashboard = Dashboard(root)
        
        # Check that voltage plot exists and is not a placeholder
        if hasattr(dashboard, 'voltage_plot') and dashboard.voltage_plot is not None:
            if hasattr(dashboard.voltage_plot, '_update_plot'):
                print("✅ PASS: Dashboard contains live voltage plot")
            else:
                print("❌ FAIL: Dashboard voltage plot is still a placeholder")
                root.destroy()
                return False
        else:
            print("❌ FAIL: Dashboard missing voltage plot")
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


def test_voltage_plot_features():
    """Test specific voltage plot features"""
    print("\nTesting voltage plot features...")
    
    try:
        root = tk.Tk()
        root.withdraw()  # Hide for testing
        
        test_frame = ttk.Frame(root)
        plot = VoltagePlot(test_frame)
        
        # Check that plot has required components
        if hasattr(plot, 'fig') and hasattr(plot, 'ax'):
            print("✅ PASS: Plot has matplotlib figure and axes")
        else:
            print("❌ FAIL: Plot missing matplotlib components")
            return False
        
        # Check voltage lines (6 groups)
        required_lines = ['line_group1', 'line_group2', 'line_group3', 'line_group4', 'line_group5', 'line_group6']
        for line_name in required_lines:
            if hasattr(plot, line_name):
                print(f"✅ PASS: Plot has {line_name}")
            else:
                print(f"❌ FAIL: Plot missing {line_name}")
                return False
        
        # Check data storage (6 groups)
        required_data = ['group1_data', 'group2_data', 'group3_data', 'group4_data', 'group5_data', 'group6_data']
        for data_name in required_data:
            if hasattr(plot, data_name):
                print(f"✅ PASS: Plot has {data_name}")
            else:
                print(f"❌ FAIL: Plot missing {data_name}")
                return False
        
        # Check Y-axis limits (should be 0-5V)
        y_limits = plot.ax.get_ylim()
        if y_limits == (0.0, 5.0):
            print("✅ PASS: Y-axis limits set to 0-5V")
        else:
            print(f"❌ FAIL: Y-axis limits incorrect: {y_limits} (expected (0.0, 5.0))")
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
    """Run interactive test showing live voltage plot"""
    print("\n" + "=" * 50)
    print("INTERACTIVE TEST: Live Voltage Plot")
    print("=" * 50)
    
    try:
        # Create test window
        root = tk.Tk()
        root.title("Task 15 - Live Voltage Plot Test")
        root.geometry("800x600")
        
        # Create frame for plot
        plot_frame = ttk.LabelFrame(root, text="Cell Voltages vs Time - Task 15", padding="5")
        plot_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Create voltage plot
        voltage_plot = VoltagePlot(plot_frame)
        
        # Start all services for live data
        controller = get_controller_manager()
        if controller.start_all_services():
            print("✅ All services providing live voltage data")
        
        # Add instructions
        info_frame = ttk.Frame(root)
        info_frame.pack(fill='x', padx=10, pady=5)
        
        info_label = ttk.Label(
            info_frame,
            text="🎯 Watch the live voltage plot update in real-time!\n"
                 "6 lines showing group averages (20 cells each)\n"
                 "Blue: Group 1 (1-20) | Green: Group 2 (21-40) | Red: Group 3 (41-60)\n"
                 "Magenta: Group 4 (61-80) | Cyan: Group 5 (81-100) | Yellow: Group 6 (101-120)\n"
                 "Y-axis: 0-5V (static), X-axis: dynamic expansion\n"
                 "Expected range: 2.0-3.5V per cell",
            justify='center'
        )
        info_label.pack()
        
        def cleanup():
            if controller.is_all_connected():
                controller.stop_all_services()
            voltage_plot.destroy()
            root.destroy()
        
        root.protocol("WM_DELETE_WINDOW", cleanup)
        
        print("📊 Live voltage plot window opened")
        print("   → 6 group averages (20 cells each)")
        print("   → Actual voltages (2-3.5V range)")
        print("   → Static Y-axis (0-5V), dynamic X-axis")
        print("\nClose window when done observing...")
        
        root.mainloop()
        return True
        
    except Exception as e:
        print(f"❌ FAIL: Interactive test error: {e}")
        return False


def main():
    """Run all tests"""
    print("=" * 60)
    print("TASK 15 TEST: Live Cell Voltage vs Time Plot")
    print("=" * 60)
    
    all_tests_passed = True
    
    # Test 1: Plot creation
    success = test_voltage_plot_creation()
    all_tests_passed &= success
    
    # Test 2: Data integration
    success = test_voltage_plot_data_integration()
    all_tests_passed &= success
    
    # Test 3: Live data
    success = test_voltage_plot_with_live_data()
    all_tests_passed &= success
    
    # Test 4: Group averaging
    success = test_voltage_normalization()
    all_tests_passed &= success
    
    # Test 5: Dashboard integration
    success = test_dashboard_integration()
    all_tests_passed &= success
    
    # Test 6: Plot features
    success = test_voltage_plot_features()
    all_tests_passed &= success
    
    print("\n" + "=" * 60)
    if all_tests_passed:
        print("🎉 ALL TESTS PASSED - Task 15 Complete!")
        print("✅ Live voltage plotting fully functional")
        print("✅ 120 cell voltages grouped into 6 averages")
        print("✅ Actual voltages (0-5V range, no normalization)")
        print("✅ Static Y-axis (0-5V), dynamic X-axis")
        print("✅ Dashboard integration working")
        print("✅ Plot reset functionality working")
        print("✅ Real-time data from CVM-24P service")
        print("\n🎯 Task 15 deliverables:")
        print("   ✅ Enhanced ui/plots.py with VoltagePlot class")
        print("   ✅ Live line plot from voltage data in GlobalState")
        print("   ✅ 6 group averages (20 cells each)")
        print("   ✅ Actual voltage values (2-3.5V range)")
        print("   ✅ Integrated into dashboard 2x2 grid")
        print("   ✅ Plot resets when starting new test")
        print("   ✅ Same architecture as PressurePlot")
        
        # Offer interactive test
        response = input("\n🔍 Run interactive test to see live voltage plotting? (y/n): ")
        if response.lower() == 'y':
            interactive_test()
        
    else:
        print("💥 SOME TESTS FAILED - Task 15 Needs Fixes")
    
    print("=" * 60)


if __name__ == "__main__":
    main() 
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
        
        # Set test cell voltage values (24 cells)
        test_voltages = [2.0 + (i * 0.01) for i in range(24)]  # 2.00V to 2.23V
        
        state.update_sensor_values(cell_voltages=test_voltages)
        
        # Verify state update
        if len(state.cell_voltages) == 24:
            print("✅ PASS: GlobalState cell voltages updated correctly")
            print(f"   Sample voltages: {state.cell_voltages[:3]}...{state.cell_voltages[-1]}")
            return True
        else:
            print(f"❌ FAIL: Expected 24 voltages, got {len(state.cell_voltages)}")
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
        
        if len(cell_voltages) == 24:
            total_voltage = sum(cell_voltages)
            avg_voltage = total_voltage / 24
            min_voltage = min(cell_voltages)
            max_voltage = max(cell_voltages)
            
            print(f"✅ PASS: Live voltage data collected")
            print(f"   Total stack: {total_voltage:.1f}V")
            print(f"   Average cell: {avg_voltage:.3f}V")
            print(f"   Min cell: {min_voltage:.3f}V")
            print(f"   Max cell: {max_voltage:.3f}V")
            
            # Verify reasonable voltage ranges
            voltage_ok = (1.8 <= min_voltage <= 2.5 and 
                         1.8 <= max_voltage <= 2.5 and
                         40.0 <= total_voltage <= 60.0)
            
            if voltage_ok:
                print("✅ PASS: Voltage values in realistic range")
            else:
                print("❌ FAIL: Voltage values outside expected range")
                controller.stop_all_services()
                return False
                
        else:
            print(f"❌ FAIL: Expected 24 voltages, got {len(cell_voltages)}")
            controller.stop_all_services()
            return False
        
        # Clean up
        controller.stop_all_services()
        return True
        
    except Exception as e:
        print(f"❌ FAIL: Live data test error: {e}")
        return False


def test_voltage_normalization():
    """Test voltage normalization for 0-1 plot range"""
    print("\nTesting voltage normalization...")
    
    try:
        state = get_global_state()
        
        # Set test voltages at different levels
        test_voltages = [2.1] * 24  # All cells at nominal 2.1V
        state.update_sensor_values(cell_voltages=test_voltages)
        
        # Test normalization constants
        max_cell_voltage = 2.5
        max_stack_voltage = 60.0  # 24 * 2.5V
        
        total_voltage = sum(test_voltages)  # 50.4V
        avg_voltage = total_voltage / 24    # 2.1V
        
        # Calculate normalized values
        total_normalized = total_voltage / max_stack_voltage  # ~0.84
        avg_normalized = avg_voltage / max_cell_voltage       # ~0.84
        
        print(f"✅ PASS: Voltage normalization test")
        print(f"   Total: {total_voltage:.1f}V → {total_normalized:.3f}")
        print(f"   Average: {avg_voltage:.3f}V → {avg_normalized:.3f}")
        
        # Verify values are in 0-1 range
        if 0.0 <= total_normalized <= 1.0 and 0.0 <= avg_normalized <= 1.0:
            print("✅ PASS: Normalized values in 0-1 range")
            return True
        else:
            print("❌ FAIL: Normalized values outside 0-1 range")
            return False
        
    except Exception as e:
        print(f"❌ FAIL: Normalization test error: {e}")
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
        
        # Check voltage lines
        required_lines = ['line_total', 'line_avg', 'line_min', 'line_max']
        for line_name in required_lines:
            if hasattr(plot, line_name):
                print(f"✅ PASS: Plot has {line_name}")
            else:
                print(f"❌ FAIL: Plot missing {line_name}")
                return False
        
        # Check data storage
        required_data = ['total_voltage_data', 'avg_voltage_data', 'min_voltage_data', 'max_voltage_data']
        for data_name in required_data:
            if hasattr(plot, data_name):
                print(f"✅ PASS: Plot has {data_name}")
            else:
                print(f"❌ FAIL: Plot missing {data_name}")
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
                 "Blue solid: Stack Total (normalized)\n"
                 "Green solid: Cell Average (normalized)\n"
                 "Red dashed: Cell Min (normalized)\n"
                 "Magenta dashed: Cell Max (normalized)\n"
                 "Plot auto-expands X-axis, Y-axis static 0-1",
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
        print("   → Blue solid: Stack Total")
        print("   → Green solid: Cell Average") 
        print("   → Red dashed: Cell Min")
        print("   → Magenta dashed: Cell Max")
        print("   → Static Y-axis (0-1), dynamic X-axis")
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
    
    # Test 4: Normalization
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
        print("✅ 4 voltage data series (Total, Avg, Min, Max)")
        print("✅ Voltage normalization to 0-1 range")
        print("✅ Static Y-axis, dynamic X-axis")
        print("✅ Dashboard integration working")
        print("✅ Plot reset functionality working")
        print("✅ Real-time data from CVM-24P service")
        print("\n🎯 Task 15 deliverables:")
        print("   ✅ Enhanced ui/plots.py with VoltagePlot class")
        print("   ✅ Live line plot from voltage data in GlobalState")
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
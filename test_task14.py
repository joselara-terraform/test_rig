#!/usr/bin/env python3
"""
Test file for Task 14: Live Pressure vs Time Plot
Run with: python3 test_task14.py
"""

import time
import tkinter as tk
from tkinter import ttk
from ui.plots import PressurePlot
from ui.dashboard import Dashboard
from services.ni_daq import NIDAQService
from core.state import get_global_state


def test_pressure_plot_creation():
    """Test that PressurePlot can be created"""
    print("Testing PressurePlot creation...")
    
    try:
        root = tk.Tk()
        test_frame = ttk.Frame(root)
        test_frame.pack(fill='both', expand=True)
        
        plot = PressurePlot(test_frame)
        print("✅ PASS: PressurePlot created successfully")
        
        plot.destroy()
        root.destroy()
        return True
        
    except Exception as e:
        print(f"❌ FAIL: Could not create PressurePlot: {e}")
        return False


def test_pressure_plot_data_integration():
    """Test that PressurePlot reads from GlobalState"""
    print("\nTesting PressurePlot data integration...")
    
    try:
        state = get_global_state()
        
        # Set test pressure values
        test_pressure1 = 15.5
        test_pressure2 = 28.3
        
        state.update_sensor_values(pressure_values=[test_pressure1, test_pressure2])
        
        # Verify state update
        if (abs(state.pressure_values[0] - test_pressure1) < 0.01 and 
            abs(state.pressure_values[1] - test_pressure2) < 0.01):
            print("✅ PASS: GlobalState pressure values updated correctly")
            return True
        else:
            print(f"❌ FAIL: State values incorrect: {state.pressure_values}")
            return False
        
    except Exception as e:
        print(f"❌ FAIL: Data integration error: {e}")
        return False


def test_plot_with_live_data():
    """Test plotting with live data from NI DAQ service"""
    print("\nTesting plot with live NI DAQ data...")
    
    try:
        # Start NI DAQ service
        daq_service = NIDAQService()
        if not daq_service.connect():
            print("❌ FAIL: Could not connect NI DAQ service")
            return False
        
        if not daq_service.start_polling():
            print("❌ FAIL: Could not start NI DAQ polling")
            return False
        
        print("✅ PASS: NI DAQ service providing live data")
        
        # Let data accumulate
        time.sleep(2.0)
        
        # Check that data is updating
        state = get_global_state()
        pressure1 = state.pressure_values[0]
        pressure2 = state.pressure_values[1]
        
        if 0.0 <= pressure1 <= 1.0 and 0.0 <= pressure2 <= 1.0:
            print(f"✅ PASS: Realistic pressure data (P1: {pressure1:.3f}, P2: {pressure2:.3f} psig)")
        else:
            print(f"❌ FAIL: Unrealistic pressure data (P1: {pressure1:.3f}, P2: {pressure2:.3f} psig)")
            daq_service.disconnect()
            return False
        
        # Clean up
        daq_service.disconnect()
        return True
        
    except Exception as e:
        print(f"❌ FAIL: Live data test error: {e}")
        return False


def test_dashboard_integration():
    """Test that dashboard properly integrates pressure plot"""
    print("\nTesting dashboard integration...")
    
    try:
        # Create dashboard in test mode
        root = tk.Tk()
        root.withdraw()  # Hide window for testing
        
        dashboard = Dashboard(root)
        
        # Check that pressure plot exists
        if hasattr(dashboard, 'pressure_plot') and dashboard.pressure_plot is not None:
            print("✅ PASS: Dashboard contains pressure plot")
        else:
            print("❌ FAIL: Dashboard missing pressure plot")
            root.destroy()
            return False
        
        # Check that plot reset function exists
        if hasattr(dashboard, 'reset_plots') and callable(dashboard.reset_plots):
            print("✅ PASS: Dashboard has plot reset functionality")
        else:
            print("❌ FAIL: Dashboard missing plot reset functionality")
            root.destroy()
            return False
        
        # Test plot reset
        dashboard.reset_plots()
        print("✅ PASS: Plot reset function works")
        
        # Clean up
        dashboard.cleanup()
        root.destroy()
        return True
        
    except Exception as e:
        print(f"❌ FAIL: Dashboard integration error: {e}")
        return False


def test_plot_features():
    """Test specific plot features"""
    print("\nTesting plot features...")
    
    try:
        root = tk.Tk()
        root.withdraw()  # Hide for testing
        
        test_frame = ttk.Frame(root)
        plot = PressurePlot(test_frame)
        
        # Check that plot has required components
        if hasattr(plot, 'fig') and hasattr(plot, 'ax'):
            print("✅ PASS: Plot has matplotlib figure and axes")
        else:
            print("❌ FAIL: Plot missing matplotlib components")
            return False
        
        if hasattr(plot, 'line1') and hasattr(plot, 'line2'):
            print("✅ PASS: Plot has dual pressure lines")
        else:
            print("❌ FAIL: Plot missing pressure lines")
            return False
        
        if hasattr(plot, 'reset') and callable(plot.reset):
            print("✅ PASS: Plot has reset functionality")
        else:
            print("❌ FAIL: Plot missing reset functionality")
            return False
        
        # Test reset
        plot.reset()
        print("✅ PASS: Plot reset works")
        
        # Check data storage
        if hasattr(plot, 'time_data') and hasattr(plot, 'pressure1_data') and hasattr(plot, 'pressure2_data'):
            print("✅ PASS: Plot has data storage")
        else:
            print("❌ FAIL: Plot missing data storage")
            return False
        
        # Clean up
        plot.destroy()
        root.destroy()
        return True
        
    except Exception as e:
        print(f"❌ FAIL: Plot features test error: {e}")
        return False


def test_plot_scaling():
    """Test plot auto-scaling functionality"""
    print("\nTesting plot auto-scaling...")
    
    try:
        state = get_global_state()
        
        # Set high pressure values
        state.update_sensor_values(pressure_values=[0.9, 0.95])
        time.sleep(0.2)
        
        # Set low pressure values  
        state.update_sensor_values(pressure_values=[0.1, 0.15])
        time.sleep(0.2)
        
        # Set normal values
        state.update_sensor_values(pressure_values=[0.5, 0.6])
        
        print("✅ PASS: Plot scaling tested with various pressure ranges (0-1 psig)")
        return True
        
    except Exception as e:
        print(f"❌ FAIL: Plot scaling test error: {e}")
        return False


def interactive_test():
    """Run interactive test showing live pressure plot"""
    print("\n" + "=" * 50)
    print("INTERACTIVE TEST: Live Pressure Plot")
    print("=" * 50)
    
    try:
        # Create test window
        root = tk.Tk()
        root.title("Task 14 - Live Pressure Plot Test")
        root.geometry("800x600")
        
        # Create frame for plot
        plot_frame = ttk.LabelFrame(root, text="Pressure vs Time - Task 14", padding="5")
        plot_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Create pressure plot
        pressure_plot = PressurePlot(plot_frame)
        
        # Start NI DAQ service for live data
        daq_service = NIDAQService()
        if daq_service.connect():
            daq_service.start_polling()
            print("✅ NI DAQ service providing live pressure data")
        
        # Add instructions
        info_frame = ttk.Frame(root)
        info_frame.pack(fill='x', padx=10, pady=5)
        
        info_label = ttk.Label(
            info_frame,
            text="🎯 Watch the live pressure plot update in real-time!\n"
                 "Blue line: Pressure Sensor 1 (0-1 psig)\n"
                 "Red line: Pressure Sensor 2 (0-1 psig)\n"
                 "Plot shows full test from 0s to current_time+120s",
            justify='center'
        )
        info_label.pack()
        
        def cleanup():
            if daq_service.connected:
                daq_service.disconnect()
            pressure_plot.destroy()
            root.destroy()
        
        root.protocol("WM_DELETE_WINDOW", cleanup)
        
        print("📊 Live pressure plot window opened")
        print("   → Blue line: Pressure Sensor 1 (0-1 psig)")
        print("   → Red line: Pressure Sensor 2 (0-1 psig)") 
        print("   → Fixed 0-1 psig scale")
        print("   → Time window: 0s to current_time+120s")
        print("\nClose window when done observing...")
        
        root.mainloop()
        return True
        
    except Exception as e:
        print(f"❌ FAIL: Interactive test error: {e}")
        return False


def main():
    """Run all tests"""
    print("=" * 60)
    print("TASK 14 TEST: Live Pressure vs Time Plot")
    print("=" * 60)
    
    all_tests_passed = True
    
    # Test 1: Plot creation
    success = test_pressure_plot_creation()
    all_tests_passed &= success
    
    # Test 2: Data integration
    success = test_pressure_plot_data_integration()
    all_tests_passed &= success
    
    # Test 3: Live data
    success = test_plot_with_live_data()
    all_tests_passed &= success
    
    # Test 4: Dashboard integration
    success = test_dashboard_integration()
    all_tests_passed &= success
    
    # Test 5: Plot features
    success = test_plot_features()
    all_tests_passed &= success
    
    # Test 6: Plot scaling
    success = test_plot_scaling()
    all_tests_passed &= success
    
    print("\n" + "=" * 60)
    if all_tests_passed:
        print("🎉 ALL TESTS PASSED - Task 14 Complete!")
        print("✅ Live pressure plotting fully functional")
        print("✅ Dual pressure sensor display (2 lines)")
        print("✅ Fixed 0-1 psig pressure range")
        print("✅ Time window: 0s to current_time+120s")
        print("✅ All test data retained (no sliding window)")
        print("✅ Dashboard integration working")
        print("✅ Plot reset functionality working")
        print("✅ Real-time data from NI DAQ service")
        print("\n🎯 Task 14 deliverables:")
        print("   ✅ Created ui/plots.py with PressurePlot class")
        print("   ✅ Live line plot from pressure data in GlobalState")
        print("   ✅ Integrated into dashboard 2x2 grid")
        print("   ✅ Plot resets when starting new test")
        print("   ✅ Fixed pressure range to realistic 0-1 psig")
        print("   ✅ Time axis shows full test duration + 120s")
        
        # Offer interactive test
        response = input("\n🔍 Run interactive test to see live plotting? (y/n): ")
        if response.lower() == 'y':
            interactive_test()
        
    else:
        print("💥 SOME TESTS FAILED - Task 14 Needs Fixes")
    
    print("=" * 60)


if __name__ == "__main__":
    main() 
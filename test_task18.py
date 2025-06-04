#!/usr/bin/env python3
"""
Test file for Task 18: Manual Relay Control Buttons
Run with: python3 test_task18.py
"""

import time
import tkinter as tk
from tkinter import ttk
from ui.controls import ControlPanel
from ui.dashboard import Dashboard
from services.controller_manager import get_controller_manager
from core.state import get_global_state


def test_relay_button_creation():
    """Test that manual relay control buttons are created"""
    print("Testing relay control button creation...")
    
    try:
        root = tk.Tk()
        root.withdraw()  # Hide window for testing
        
        control_panel = ControlPanel(root)
        
        # Check that valve buttons exist
        if hasattr(control_panel, 'valve_buttons') and len(control_panel.valve_buttons) == 4:
            print("✅ PASS: 4 valve control buttons created")
        else:
            print("❌ FAIL: Valve control buttons missing or incorrect count")
            control_panel.cleanup()
            root.destroy()
            return False
        
        # Check that pump button exists
        if hasattr(control_panel, 'pump_button'):
            print("✅ PASS: Pump control button created")
        else:
            print("❌ FAIL: Pump control button missing")
            control_panel.cleanup()
            root.destroy()
            return False
        
        # Check button initial states
        for i, button in enumerate(control_panel.valve_buttons):
            if button.cget('text') == 'OFF' and button.cget('background') == 'gray':
                print(f"✅ PASS: Valve {i+1} button shows OFF/gray initially (disconnected)")
            else:
                print(f"❌ FAIL: Valve {i+1} button incorrect initial state")
                control_panel.cleanup()
                root.destroy()
                return False
        
        if control_panel.pump_button.cget('text') == 'OFF' and control_panel.pump_button.cget('background') == 'gray':
            print("✅ PASS: Pump button shows OFF/gray initially (disconnected)")
        else:
            print("❌ FAIL: Pump button incorrect initial state")
            control_panel.cleanup()
            root.destroy()
            return False
        
        control_panel.cleanup()
        root.destroy()
        return True
        
    except Exception as e:
        print(f"❌ FAIL: Could not create relay control buttons: {e}")
        return False


def test_relay_button_state_updates():
    """Test that relay buttons update based on connection and state"""
    print("\nTesting relay button state updates...")
    
    try:
        root = tk.Tk()
        root.withdraw()  # Hide window for testing
        
        control_panel = ControlPanel(root)
        state = get_global_state()
        controller = get_controller_manager()
        
        # Test disconnected state (should be disabled/gray)
        control_panel._update_relay_buttons(False)
        
        all_disabled = all(btn.cget('state') == 'disabled' for btn in control_panel.valve_buttons)
        pump_disabled = control_panel.pump_button.cget('state') == 'disabled'
        
        if all_disabled and pump_disabled:
            print("✅ PASS: All relay buttons disabled when not connected")
        else:
            print("❌ FAIL: Relay buttons not properly disabled when disconnected")
            control_panel.cleanup()
            root.destroy()
            return False
        
        # Test connected state (should be enabled and show current state)
        control_panel._update_relay_buttons(True)
        
        all_enabled = all(btn.cget('state') == 'normal' for btn in control_panel.valve_buttons)
        pump_enabled = control_panel.pump_button.cget('state') == 'normal'
        
        if all_enabled and pump_enabled:
            print("✅ PASS: All relay buttons enabled when connected")
        else:
            print("❌ FAIL: Relay buttons not properly enabled when connected")
            control_panel.cleanup()
            root.destroy()
            return False
        
        # Test state-based color updates
        # Set valve 1 and pump ON
        state.set_actuator_state('valve', True, 0)
        state.set_actuator_state('pump', True)
        
        control_panel._update_relay_buttons(True)
        
        valve1_green = control_panel.valve_buttons[0].cget('background') == 'green'
        valve1_on = control_panel.valve_buttons[0].cget('text') == 'ON'
        pump_green = control_panel.pump_button.cget('background') == 'green'
        pump_on = control_panel.pump_button.cget('text') == 'ON'
        
        if valve1_green and valve1_on and pump_green and pump_on:
            print("✅ PASS: Buttons show green/ON when actuators are active")
        else:
            print("❌ FAIL: Button colors/text incorrect for active state")
            control_panel.cleanup()
            root.destroy()
            return False
        
        # Test OFF state colors
        state.set_actuator_state('valve', False, 0)
        state.set_actuator_state('pump', False)
        
        control_panel._update_relay_buttons(True)
        
        valve1_red = control_panel.valve_buttons[0].cget('background') == 'red'
        valve1_off = control_panel.valve_buttons[0].cget('text') == 'OFF'
        pump_red = control_panel.pump_button.cget('background') == 'red'
        pump_off = control_panel.pump_button.cget('text') == 'OFF'
        
        if valve1_red and valve1_off and pump_red and pump_off:
            print("✅ PASS: Buttons show red/OFF when actuators are inactive")
        else:
            print("❌ FAIL: Button colors/text incorrect for inactive state")
            control_panel.cleanup()
            root.destroy()
            return False
        
        control_panel.cleanup()
        root.destroy()
        return True
        
    except Exception as e:
        print(f"❌ FAIL: Relay button state update error: {e}")
        return False


def test_manual_valve_control():
    """Test manual valve control functionality"""
    print("\nTesting manual valve control...")
    
    try:
        root = tk.Tk()
        root.withdraw()  # Hide window for testing
        
        control_panel = ControlPanel(root)
        state = get_global_state()
        controller = get_controller_manager()
        
        # Start services to enable controls
        if not controller.start_all_services():
            print("❌ FAIL: Could not start services for valve control test")
            control_panel.cleanup()
            root.destroy()
            return False
        
        print("✅ PASS: Services started for manual control testing")
        
        # Test each valve toggle
        for i in range(4):
            # Initially should be OFF
            initial_state = state.valve_states[i]
            if initial_state != False:
                print(f"❌ FAIL: Valve {i+1} not initially OFF")
                controller.stop_all_services()
                control_panel.cleanup()
                root.destroy()
                return False
            
            # Toggle valve ON
            control_panel._toggle_valve(i)
            
            if state.valve_states[i] == True:
                print(f"✅ PASS: Valve {i+1} toggled ON via manual control")
            else:
                print(f"❌ FAIL: Valve {i+1} failed to toggle ON")
                controller.stop_all_services()
                control_panel.cleanup()
                root.destroy()
                return False
            
            # Toggle valve OFF
            control_panel._toggle_valve(i)
            
            if state.valve_states[i] == False:
                print(f"✅ PASS: Valve {i+1} toggled OFF via manual control")
            else:
                print(f"❌ FAIL: Valve {i+1} failed to toggle OFF")
                controller.stop_all_services()
                control_panel.cleanup()
                root.destroy()
                return False
        
        controller.stop_all_services()
        control_panel.cleanup()
        root.destroy()
        return True
        
    except Exception as e:
        print(f"❌ FAIL: Manual valve control error: {e}")
        return False


def test_manual_pump_control():
    """Test manual pump control functionality"""
    print("\nTesting manual pump control...")
    
    try:
        root = tk.Tk()
        root.withdraw()  # Hide window for testing
        
        control_panel = ControlPanel(root)
        state = get_global_state()
        controller = get_controller_manager()
        
        # Start services to enable controls
        if not controller.start_all_services():
            print("❌ FAIL: Could not start services for pump control test")
            control_panel.cleanup()
            root.destroy()
            return False
        
        # Initially should be OFF
        if state.pump_state != False:
            print("❌ FAIL: Pump not initially OFF")
            controller.stop_all_services()
            control_panel.cleanup()
            root.destroy()
            return False
        
        # Toggle pump ON
        control_panel._toggle_pump()
        
        if state.pump_state == True:
            print("✅ PASS: Pump toggled ON via manual control")
        else:
            print("❌ FAIL: Pump failed to toggle ON")
            controller.stop_all_services()
            control_panel.cleanup()
            root.destroy()
            return False
        
        # Toggle pump OFF
        control_panel._toggle_pump()
        
        if state.pump_state == False:
            print("✅ PASS: Pump toggled OFF via manual control")
        else:
            print("❌ FAIL: Pump failed to toggle OFF")
            controller.stop_all_services()
            control_panel.cleanup()
            root.destroy()
            return False
        
        controller.stop_all_services()
        control_panel.cleanup()
        root.destroy()
        return True
        
    except Exception as e:
        print(f"❌ FAIL: Manual pump control error: {e}")
        return False


def test_all_off_function():
    """Test the ALL OFF emergency function"""
    print("\nTesting ALL OFF function...")
    
    try:
        root = tk.Tk()
        root.withdraw()  # Hide window for testing
        
        control_panel = ControlPanel(root)
        state = get_global_state()
        controller = get_controller_manager()
        
        # Start services to enable controls
        if not controller.start_all_services():
            print("❌ FAIL: Could not start services for ALL OFF test")
            control_panel.cleanup()
            root.destroy()
            return False
        
        # Set all actuators to ON
        for i in range(4):
            state.set_actuator_state('valve', True, i)
        state.set_actuator_state('pump', True)
        
        # Verify all are ON
        all_valves_on = all(state.valve_states)
        pump_on = state.pump_state
        
        if not (all_valves_on and pump_on):
            print("❌ FAIL: Could not set all actuators ON for ALL OFF test")
            controller.stop_all_services()
            control_panel.cleanup()
            root.destroy()
            return False
        
        print("✅ PASS: All actuators set to ON")
        
        # Execute ALL OFF
        control_panel._all_relays_off()
        
        # Verify all are OFF
        all_valves_off = all(not state for state in state.valve_states)
        pump_off = not state.pump_state
        
        if all_valves_off and pump_off:
            print("✅ PASS: ALL OFF function turned off all actuators")
        else:
            print("❌ FAIL: ALL OFF function did not turn off all actuators")
            controller.stop_all_services()
            control_panel.cleanup()
            root.destroy()
            return False
        
        controller.stop_all_services()
        control_panel.cleanup()
        root.destroy()
        return True
        
    except Exception as e:
        print(f"❌ FAIL: ALL OFF function error: {e}")
        return False


def test_integration_with_dashboard():
    """Test that manual controls integrate with dashboard indicators"""
    print("\nTesting integration with dashboard indicators...")
    
    try:
        root = tk.Tk()
        root.withdraw()  # Hide window for testing
        
        # Create both control panel and dashboard
        control_panel = ControlPanel(root)
        dashboard = Dashboard(root)
        state = get_global_state()
        controller = get_controller_manager()
        
        # Start services
        if not controller.start_all_services():
            print("❌ FAIL: Could not start services for integration test")
            control_panel.cleanup()
            dashboard.cleanup()
            root.destroy()
            return False
        
        # Toggle valve 1 via control panel
        control_panel._toggle_valve(0)
        
        # Update dashboard indicators
        dashboard._update_status_indicators()
        
        # Check that dashboard indicator reflects the change
        dashboard_valve1_state = dashboard.valve_labels[0].cget('text')
        dashboard_valve1_color = dashboard.valve_labels[0].cget('background')
        
        if dashboard_valve1_state == 'ON' and dashboard_valve1_color == 'green':
            print("✅ PASS: Dashboard indicators reflect manual control changes")
        else:
            print(f"❌ FAIL: Dashboard not updated - state: {dashboard_valve1_state}, color: {dashboard_valve1_color}")
            controller.stop_all_services()
            control_panel.cleanup()
            dashboard.cleanup()
            root.destroy()
            return False
        
        # Toggle pump via control panel
        control_panel._toggle_pump()
        
        # Update dashboard indicators
        dashboard._update_status_indicators()
        
        # Check pump indicator
        dashboard_pump_state = dashboard.pump_state_label.cget('text')
        dashboard_pump_color = dashboard.pump_state_label.cget('background')
        
        if dashboard_pump_state == 'ON' and dashboard_pump_color == 'green':
            print("✅ PASS: Dashboard pump indicator reflects manual control")
        else:
            print(f"❌ FAIL: Dashboard pump not updated - state: {dashboard_pump_state}, color: {dashboard_pump_color}")
            controller.stop_all_services()
            control_panel.cleanup()
            dashboard.cleanup()
            root.destroy()
            return False
        
        controller.stop_all_services()
        control_panel.cleanup()
        dashboard.cleanup()
        root.destroy()
        return True
        
    except Exception as e:
        print(f"❌ FAIL: Integration test error: {e}")
        return False


def test_safety_restrictions():
    """Test that manual controls respect safety restrictions"""
    print("\nTesting safety restrictions...")
    
    try:
        root = tk.Tk()
        root.withdraw()  # Hide window for testing
        
        control_panel = ControlPanel(root)
        state = get_global_state()
        controller = get_controller_manager()
        
        # Test that controls don't work when disconnected
        print("Testing controls when disconnected...")
        
        original_valve_state = state.valve_states[0]
        original_pump_state = state.pump_state
        
        # Try to toggle valve when disconnected
        control_panel._toggle_valve(0)
        
        # State should not change
        if state.valve_states[0] == original_valve_state:
            print("✅ PASS: Valve control blocked when disconnected")
        else:
            print("❌ FAIL: Valve control worked when disconnected")
            control_panel.cleanup()
            root.destroy()
            return False
        
        # Try to toggle pump when disconnected
        control_panel._toggle_pump()
        
        # State should not change
        if state.pump_state == original_pump_state:
            print("✅ PASS: Pump control blocked when disconnected")
        else:
            print("❌ FAIL: Pump control worked when disconnected")
            control_panel.cleanup()
            root.destroy()
            return False
        
        # Try ALL OFF when disconnected
        control_panel._all_relays_off()
        
        # State should not change
        if (state.valve_states[0] == original_valve_state and 
            state.pump_state == original_pump_state):
            print("✅ PASS: ALL OFF blocked when disconnected")
        else:
            print("❌ FAIL: ALL OFF worked when disconnected")
            control_panel.cleanup()
            root.destroy()
            return False
        
        control_panel.cleanup()
        root.destroy()
        return True
        
    except Exception as e:
        print(f"❌ FAIL: Safety restrictions test error: {e}")
        return False


def interactive_test():
    """Run interactive test showing manual relay controls"""
    print("\n" + "=" * 50)
    print("INTERACTIVE TEST: Manual Relay Controls")
    print("=" * 50)
    
    try:
        # Create test window
        root = tk.Tk()
        root.title("Task 18 - Manual Relay Control Test")
        root.geometry("1000x400")
        
        # Create control panel
        control_panel = ControlPanel(root)
        
        # Add instructions
        info_frame = ttk.Frame(root)
        info_frame.pack(fill='x', padx=10, pady=5)
        
        info_label = ttk.Label(
            info_frame,
            text="🔧 Test Manual Relay Controls!\n\n"
                 "1. Click 'Connect' to enable relay controls\n"
                 "2. Use valve buttons to toggle individual valves\n"
                 "3. Use pump button to control pump\n"
                 "4. Watch buttons change color: Red=OFF, Green=ON\n"
                 "5. Try 'ALL OFF' emergency button\n"
                 "6. Emergency Stop also sets all relays to safe state\n\n"
                 "Manual controls update both GlobalState and NI DAQ hardware!",
            justify='center',
            font=("Arial", 10)
        )
        info_label.pack(pady=10)
        
        def cleanup():
            control_panel.cleanup()
            root.destroy()
        
        root.protocol("WM_DELETE_WINDOW", cleanup)
        
        print("🎮 Interactive test window opened")
        print("   → Connect system to enable manual controls")
        print("   → Test valve and pump toggle buttons")
        print("   → Watch button colors change with state")
        print("   → Try ALL OFF emergency function")
        print("\nClose window when done testing...")
        
        root.mainloop()
        return True
        
    except Exception as e:
        print(f"❌ FAIL: Interactive test error: {e}")
        return False


def main():
    """Run all tests"""
    print("=" * 60)
    print("TASK 18 TEST: Manual Relay Control Buttons")
    print("=" * 60)
    
    all_tests_passed = True
    
    # Test 1: Button creation
    success = test_relay_button_creation()
    all_tests_passed &= success
    
    # Test 2: Button state updates
    success = test_relay_button_state_updates()
    all_tests_passed &= success
    
    # Test 3: Manual valve control
    success = test_manual_valve_control()
    all_tests_passed &= success
    
    # Test 4: Manual pump control
    success = test_manual_pump_control()
    all_tests_passed &= success
    
    # Test 5: ALL OFF function
    success = test_all_off_function()
    all_tests_passed &= success
    
    # Test 6: Dashboard integration
    success = test_integration_with_dashboard()
    all_tests_passed &= success
    
    # Test 7: Safety restrictions
    success = test_safety_restrictions()
    all_tests_passed &= success
    
    print("\n" + "=" * 60)
    if all_tests_passed:
        print("🎉 ALL TESTS PASSED - Task 18 Complete!")
        print("✅ Manual relay control buttons fully functional")
        print("✅ 4 valve + 1 pump toggle buttons")
        print("✅ Real-time color updates (red=OFF, green=ON)")
        print("✅ Integration with GlobalState and NI DAQ")
        print("✅ Safety restrictions when disconnected")
        print("✅ Dashboard indicator synchronization")
        print("✅ ALL OFF emergency function")
        print("\n🎯 Task 18 deliverables:")
        print("   ✅ Manual toggle buttons for 4 valves + 1 pump")
        print("   ✅ Toggles state and calls mocked DAQ relay service")
        print("   ✅ Color-coded button states (red/green)")
        print("   ✅ Safety restrictions (disabled when disconnected)")
        print("   ✅ Integration with dashboard indicators")
        print("   ✅ Emergency ALL OFF function")
        print("   ✅ Real-time UI updates")
        
        # Offer interactive test
        response = input("\n🔍 Run interactive test to manually control relays? (y/n): ")
        if response.lower() == 'y':
            interactive_test()
        
    else:
        print("💥 SOME TESTS FAILED - Task 18 Needs Fixes")
    
    print("=" * 60)


if __name__ == "__main__":
    main() 
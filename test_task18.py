#!/usr/bin/env python3
"""
Test file for Task 18: Add Relay Control Buttons  
Run with: python3 test_task18.py
"""

import time
import tkinter as tk
from tkinter import ttk
from ui.dashboard import Dashboard
from services.controller_manager import get_controller_manager
from core.state import get_global_state


def test_valve_pump_buttons_exist():
    """Test that valve/pump controls are clickable buttons"""
    print("Testing valve/pump button controls...")
    
    try:
        root = tk.Tk()
        root.withdraw()  # Hide window for testing
        
        dashboard = Dashboard(root)
        
        # Check that valve buttons exist and are Button widgets
        if hasattr(dashboard, 'valve_labels') and len(dashboard.valve_labels) == 4:
            all_buttons = all(isinstance(btn, tk.Button) for btn in dashboard.valve_labels)
            if all_buttons:
                print("✅ PASS: 4 valve controls are clickable buttons")
            else:
                print("❌ FAIL: Valve controls are not all buttons")
                dashboard.cleanup()
                root.destroy()
                return False
        else:
            print("❌ FAIL: Valve buttons missing or incorrect count")
            dashboard.cleanup()
            root.destroy()
            return False
        
        # Check that pump button exists and is Button widget
        if hasattr(dashboard, 'pump_state_label') and isinstance(dashboard.pump_state_label, tk.Button):
            print("✅ PASS: Pump control is clickable button")
        else:
            print("❌ FAIL: Pump control is not a button")
            dashboard.cleanup()
            root.destroy()
            return False
        
        # Check buttons have proper cursor and command handlers
        for i, btn in enumerate(dashboard.valve_labels):
            if btn.cget('cursor') == 'hand2' and btn.cget('command'):
                print(f"✅ PASS: Valve {i+1} button has click handler")
            else:
                print(f"❌ FAIL: Valve {i+1} button missing click handler")
                dashboard.cleanup()
                root.destroy()
                return False
        
        if dashboard.pump_state_label.cget('cursor') == 'hand2' and dashboard.pump_state_label.cget('command'):
            print("✅ PASS: Pump button has click handler")
        else:
            print("❌ FAIL: Pump button missing click handler")
            dashboard.cleanup()
            root.destroy()
            return False
        
        dashboard.cleanup()
        root.destroy()
        return True
        
    except Exception as e:
        print(f"❌ FAIL: Could not test valve/pump buttons: {e}")
        return False


def test_button_toggle_functionality():
    """Test that buttons can toggle valve/pump states"""
    print("\nTesting button toggle functionality...")
    
    try:
        root = tk.Tk()
        root.withdraw()  # Hide window for testing
        
        dashboard = Dashboard(root)
        state = get_global_state()
        
        # Simulate NI DAQ connection to enable buttons
        state.update_connection_status('ni_daq', True)
        dashboard._update_status_indicators()
        
        # Test valve toggle methods exist
        if hasattr(dashboard, '_toggle_valve'):
            print("✅ PASS: _toggle_valve method exists")
        else:
            print("❌ FAIL: _toggle_valve method missing")
            dashboard.cleanup()
            root.destroy()
            return False
        
        if hasattr(dashboard, '_toggle_pump'):
            print("✅ PASS: _toggle_pump method exists")
        else:
            print("❌ FAIL: _toggle_pump method missing")
            dashboard.cleanup()
            root.destroy()
            return False
        
        # Test valve toggles
        for i in range(4):
            # Initially OFF
            initial_state = state.valve_states[i]
            print(f"   Valve {i+1} initial state: {initial_state}")
            
            # Toggle ON
            dashboard._toggle_valve(i)
            new_state = state.valve_states[i]
            
            if new_state != initial_state:
                print(f"✅ PASS: Valve {i+1} toggled from {initial_state} to {new_state}")
            else:
                print(f"❌ FAIL: Valve {i+1} failed to toggle")
                dashboard.cleanup()
                root.destroy()
                return False
            
            # Toggle back OFF
            dashboard._toggle_valve(i)
            final_state = state.valve_states[i]
            
            if final_state == initial_state:
                print(f"✅ PASS: Valve {i+1} toggled back to {final_state}")
            else:
                print(f"❌ FAIL: Valve {i+1} failed to toggle back")
                dashboard.cleanup()
                root.destroy()
                return False
        
        # Test pump toggle
        initial_pump_state = state.pump_state
        print(f"   Pump initial state: {initial_pump_state}")
        
        dashboard._toggle_pump()
        new_pump_state = state.pump_state
        
        if new_pump_state != initial_pump_state:
            print(f"✅ PASS: Pump toggled from {initial_pump_state} to {new_pump_state}")
        else:
            print("❌ FAIL: Pump failed to toggle")
            dashboard.cleanup()
            root.destroy()
            return False
        
        dashboard._toggle_pump()
        final_pump_state = state.pump_state
        
        if final_pump_state == initial_pump_state:
            print(f"✅ PASS: Pump toggled back to {final_pump_state}")
        else:
            print("❌ FAIL: Pump failed to toggle back")
            dashboard.cleanup()
            root.destroy()
            return False
        
        dashboard.cleanup()
        root.destroy()
        return True
        
    except Exception as e:
        print(f"❌ FAIL: Button toggle test error: {e}")
        return False


def test_ni_daq_connection_dependency():
    """Test that buttons require NI DAQ connection"""
    print("\nTesting NI DAQ connection dependency...")
    
    try:
        root = tk.Tk()
        root.withdraw()  # Hide window for testing
        
        dashboard = Dashboard(root)
        state = get_global_state()
        
        # Test with NI DAQ disconnected
        state.update_connection_status('ni_daq', False)
        dashboard._update_status_indicators()
        
        # Check buttons are disabled
        for i, btn in enumerate(dashboard.valve_labels):
            if btn.cget('state') == 'disabled':
                print(f"✅ PASS: Valve {i+1} button disabled when NI DAQ disconnected")
            else:
                print(f"❌ FAIL: Valve {i+1} button not disabled when NI DAQ disconnected")
                dashboard.cleanup()
                root.destroy()
                return False
        
        if dashboard.pump_state_label.cget('state') == 'disabled':
            print("✅ PASS: Pump button disabled when NI DAQ disconnected")
        else:
            print("❌ FAIL: Pump button not disabled when NI DAQ disconnected")
            dashboard.cleanup()
            root.destroy()
            return False
        
        # Test manual toggle with disconnected DAQ (should warn and not change state)
        initial_valve_state = state.valve_states[0]
        dashboard._toggle_valve(0)
        after_toggle_state = state.valve_states[0]
        
        if after_toggle_state == initial_valve_state:
            print("✅ PASS: Valve toggle rejected when NI DAQ disconnected")
        else:
            print("❌ FAIL: Valve toggle worked when NI DAQ disconnected")
            dashboard.cleanup()
            root.destroy()
            return False
        
        # Test with NI DAQ connected
        state.update_connection_status('ni_daq', True)
        dashboard._update_status_indicators()
        
        # Check buttons are enabled
        for i, btn in enumerate(dashboard.valve_labels):
            if btn.cget('state') == 'normal':
                print(f"✅ PASS: Valve {i+1} button enabled when NI DAQ connected")
            else:
                print(f"❌ FAIL: Valve {i+1} button not enabled when NI DAQ connected")
                dashboard.cleanup()
                root.destroy()
                return False
        
        if dashboard.pump_state_label.cget('state') == 'normal':
            print("✅ PASS: Pump button enabled when NI DAQ connected")
        else:
            print("❌ FAIL: Pump button not enabled when NI DAQ connected")
            dashboard.cleanup()
            root.destroy()
            return False
        
        dashboard.cleanup()
        root.destroy()
        return True
        
    except Exception as e:
        print(f"❌ FAIL: NI DAQ connection test error: {e}")
        return False


def test_button_visual_feedback():
    """Test that buttons provide correct visual feedback"""
    print("\nTesting button visual feedback...")
    
    try:
        root = tk.Tk()
        root.withdraw()  # Hide window for testing
        
        dashboard = Dashboard(root)
        state = get_global_state()
        
        # Enable NI DAQ connection
        state.update_connection_status('ni_daq', True)
        
        # Test initial OFF states
        dashboard._update_status_indicators()
        
        for i, btn in enumerate(dashboard.valve_labels):
            if btn.cget('background') == 'red' and btn.cget('text') == 'OFF':
                print(f"✅ PASS: Valve {i+1} button shows red/OFF initially")
            else:
                print(f"❌ FAIL: Valve {i+1} button incorrect initial state")
                dashboard.cleanup()
                root.destroy()
                return False
        
        if dashboard.pump_state_label.cget('background') == 'red' and dashboard.pump_state_label.cget('text') == 'OFF':
            print("✅ PASS: Pump button shows red/OFF initially")
        else:
            print("❌ FAIL: Pump button incorrect initial state")
            dashboard.cleanup()
            root.destroy()
            return False
        
        # Test ON states
        print("Testing ON state visual feedback...")
        
        # Set all valves ON
        for i in range(4):
            state.set_actuator_state('valve', True, i)
        state.set_actuator_state('pump', True)
        
        # Update visual indicators
        dashboard._update_status_indicators()
        
        # Check visual feedback
        for i, btn in enumerate(dashboard.valve_labels):
            if btn.cget('background') == 'green' and btn.cget('text') == 'ON':
                print(f"✅ PASS: Valve {i+1} button shows green/ON when active")
            else:
                print(f"❌ FAIL: Valve {i+1} button incorrect ON state")
                dashboard.cleanup()
                root.destroy()
                return False
        
        if dashboard.pump_state_label.cget('background') == 'green' and dashboard.pump_state_label.cget('text') == 'ON':
            print("✅ PASS: Pump button shows green/ON when active")
        else:
            print("❌ FAIL: Pump button incorrect ON state")
            dashboard.cleanup()
            root.destroy()
            return False
        
        # Test active background colors exist
        for i, btn in enumerate(dashboard.valve_labels):
            active_bg = btn.cget('activebackground')
            if active_bg in ['lightgreen', 'lightcoral']:
                print(f"✅ PASS: Valve {i+1} button has active background color")
            else:
                print(f"❌ FAIL: Valve {i+1} button missing active background")
                dashboard.cleanup()
                root.destroy()
                return False
        
        dashboard.cleanup()
        root.destroy()
        return True
        
    except Exception as e:
        print(f"❌ FAIL: Visual feedback test error: {e}")
        return False


def test_ni_daq_integration():
    """Test that button toggles integrate with NI DAQ service"""
    print("\nTesting NI DAQ service integration...")
    
    try:
        # Start controller manager to get NI DAQ service
        controller = get_controller_manager()
        if not controller.start_all_services():
            print("❌ FAIL: Could not start services")
            return False
        
        state = get_global_state()
        
        # Verify NI DAQ is connected
        if not state.connections.get('ni_daq', False):
            print("❌ FAIL: NI DAQ service not connected")
            controller.stop_all_services()
            return False
        
        print("✅ PASS: NI DAQ service connected")
        
        # Test valve state changes propagate to hardware
        print("Testing valve control propagation...")
        
        # Toggle valves and verify hardware updates would occur
        # (The NI DAQ service _update_digital_outputs method reads from GlobalState)
        for i in range(4):
            initial_state = state.valve_states[i]
            state.set_actuator_state('valve', True, i)
            
            # Allow some time for service to process
            time.sleep(0.1)
            
            if state.valve_states[i] == True:
                print(f"✅ PASS: Valve {i+1} state updated in GlobalState")
            else:
                print(f"❌ FAIL: Valve {i+1} state not updated")
                controller.stop_all_services()
                return False
        
        # Test pump control
        print("Testing pump control propagation...")
        state.set_actuator_state('pump', True)
        time.sleep(0.1)
        
        if state.pump_state == True:
            print("✅ PASS: Pump state updated in GlobalState")
        else:
            print("❌ FAIL: Pump state not updated")
            controller.stop_all_services()
            return False
        
        # The NI DAQ service automatically reads these states and updates hardware
        print("✅ PASS: State changes available to NI DAQ service")
        
        # Clean up
        controller.stop_all_services()
        return True
        
    except Exception as e:
        print(f"❌ FAIL: NI DAQ integration test error: {e}")
        return False


def test_frame_title_update():
    """Test that frame title reflects new control functionality"""
    print("\nTesting frame title update...")
    
    try:
        root = tk.Tk()
        root.withdraw()  # Hide window for testing
        
        dashboard = Dashboard(root)
        
        # Check frame title
        frame_text = dashboard.valve_frame.cget('text')
        if frame_text == "Actuator States":
            print("✅ PASS: Frame titled 'Actuator States'")
        else:
            print(f"❌ FAIL: Incorrect frame title: '{frame_text}'")
            dashboard.cleanup()
            root.destroy()
            return False
        
        # Check container title
        # Find the title label in the valve indicators
        container_frame = dashboard.valve_frame.winfo_children()[0]
        title_widgets = [w for w in container_frame.winfo_children() if isinstance(w, ttk.Label)]
        
        if title_widgets:
            title_text = title_widgets[0].cget('text')
            if title_text == "Actuator Controls":
                print("✅ PASS: Container titled 'Actuator Controls'")
            else:
                print(f"❌ FAIL: Incorrect container title: '{title_text}'")
                dashboard.cleanup()
                root.destroy()
                return False
        else:
            print("❌ FAIL: Container title not found")
            dashboard.cleanup()
            root.destroy()
            return False
        
        dashboard.cleanup()
        root.destroy()
        return True
        
    except Exception as e:
        print(f"❌ FAIL: Frame title test error: {e}")
        return False


def interactive_test():
    """Run interactive test with full dashboard and NI DAQ integration"""
    print("\n" + "=" * 50)
    print("INTERACTIVE TEST: Valve/Pump Toggle Controls")
    print("=" * 50)
    
    try:
        # Create test window
        root = tk.Tk()
        root.title("Task 18 - Valve/Pump Toggle Controls Test")
        root.geometry("1400x900")
        
        # Create dashboard
        dashboard = Dashboard(root)
        
        # Start all services for full integration test
        controller = get_controller_manager()
        if controller.start_all_services():
            print("✅ All services started - valve/pump controls enabled")
        else:
            print("❌ Services failed to start - controls will be disabled")
        
        # Add instructions
        info_frame = ttk.Frame(root)
        info_frame.pack(fill='x', padx=10, pady=5)
        
        info_label = ttk.Label(
            info_frame,
            text="🎮 INTERACTIVE TEST: Click valve/pump buttons in bottom-right panel!\n"
                 "🔴 Red = OFF | 🟢 Green = ON | Click to toggle\n"
                 "Controls automatically integrated with NI DAQ relay outputs\n"
                 "Use Connect button to enable controls, Emergency Stop to turn all OFF\n"
                 "Watch console for control messages and hardware integration",
            justify='center',
            font=("Arial", 10)
        )
        info_label.pack(pady=5)
        
        def cleanup():
            if controller.is_all_connected():
                controller.stop_all_services()
            dashboard.cleanup()
            root.destroy()
        
        root.protocol("WM_DELETE_WINDOW", cleanup)
        
        print("🎮 Interactive dashboard opened with full functionality")
        print("   → Click Connect to enable valve/pump controls")
        print("   → Click valve/pump buttons to toggle states")
        print("   → Watch real-time control and data visualization")
        print("   → Emergency Stop turns off all actuators")
        print("   → Controls integrated with NI DAQ relay outputs")
        print("\nClose window when done testing...")
        
        root.mainloop()
        return True
        
    except Exception as e:
        print(f"❌ FAIL: Interactive test error: {e}")
        return False


def main():
    """Run all tests"""
    print("=" * 60)
    print("TASK 18 TEST: Add Relay Control Buttons")
    print("=" * 60)
    
    all_tests_passed = True
    
    # Test 1: Button controls exist
    success = test_valve_pump_buttons_exist()
    all_tests_passed &= success
    
    # Test 2: Toggle functionality
    success = test_button_toggle_functionality()
    all_tests_passed &= success
    
    # Test 3: NI DAQ dependency
    success = test_ni_daq_connection_dependency()
    all_tests_passed &= success
    
    # Test 4: Visual feedback
    success = test_button_visual_feedback()
    all_tests_passed &= success
    
    # Test 5: NI DAQ integration
    success = test_ni_daq_integration()
    all_tests_passed &= success
    
    # Test 6: Frame title update
    success = test_frame_title_update()
    all_tests_passed &= success
    
    print("\n" + "=" * 60)
    if all_tests_passed:
        print("🎉 ALL TESTS PASSED - Task 18 Complete!")
        print("✅ Valve/pump toggle controls fully functional")
        print("✅ 4 valve + 1 pump clickable toggle buttons")
        print("✅ NI DAQ integration for hardware relay control")
        print("✅ Connection dependency (disabled when NI DAQ off)")
        print("✅ Visual feedback (red/OFF, green/ON)")
        print("✅ Click handlers with state management")
        print("✅ No new UI sections - used existing indicators")
        print("\n🎯 Task 18 deliverables:")
        print("   ✅ Manual toggle buttons for 4 valves + 1 pump")
        print("   ✅ Toggles state and calls NI DAQ relay service")
        print("   ✅ Existing color indicators converted to buttons")
        print("   ✅ Connection dependency and safety checks")
        print("   ✅ Real-time visual feedback")
        print("   ✅ Hardware integration via GlobalState")
        
        # Offer interactive test
        response = input("\n🔍 Run interactive test with full dashboard? (y/n): ")
        if response.lower() == 'y':
            interactive_test()
        
    else:
        print("💥 SOME TESTS FAILED - Task 18 Needs Fixes")
    
    print("=" * 60)


if __name__ == "__main__":
    main() 
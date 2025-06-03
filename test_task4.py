#!/usr/bin/env python3
"""
Test file for Task 4: Timer logic
Run with: python3 test_task4.py
"""

import time
from core.timer import get_timer
from core.state import get_global_state


def test_timer_singleton():
    """Test that get_timer returns the same instance"""
    print("Testing timer singleton pattern...")
    t1 = get_timer()
    t2 = get_timer()
    
    if t1 is t2:
        print("✅ PASS: Timer singleton returns same instance")
    else:
        print("❌ FAIL: Timer singleton returns different instances")
        return False
    return True


def test_timer_start_stop():
    """Test timer start and stop functionality"""
    print("\nTesting timer start/stop...")
    timer = get_timer()
    state = get_global_state()
    
    # Reset first
    timer.reset()
    
    # Test start
    timer.start()
    if not timer.is_running:
        print("❌ FAIL: Timer not running after start")
        return False
    print("✅ PASS: Timer starts correctly")
    
    # Wait a bit and check time progression
    time.sleep(0.2)
    elapsed = timer.get_elapsed_time()
    if elapsed < 0.15 or elapsed > 0.3:
        print(f"❌ FAIL: Timer elapsed time incorrect: {elapsed}")
        timer.stop()
        return False
    print(f"✅ PASS: Timer progressing correctly ({elapsed:.2f}s)")
    
    # Test stop
    timer.stop()
    if timer.is_running:
        print("❌ FAIL: Timer still running after stop")
        return False
    print("✅ PASS: Timer stops correctly")
    
    return True


def test_timer_pause_resume():
    """Test timer pause and resume functionality"""
    print("\nTesting timer pause/resume...")
    timer = get_timer()
    
    # Reset and start
    timer.reset()
    timer.start()
    
    # Run for a bit
    time.sleep(0.1)
    
    # Pause
    timer.pause()
    if not timer.is_paused:
        print("❌ FAIL: Timer not paused after pause")
        timer.stop()
        return False
    
    paused_time = timer.get_elapsed_time()
    print(f"✅ PASS: Timer paused at {paused_time:.2f}s")
    
    # Wait while paused - time shouldn't increase
    time.sleep(0.1)
    still_paused_time = timer.get_elapsed_time()
    if abs(still_paused_time - paused_time) > 0.05:
        print(f"❌ FAIL: Timer progressed while paused: {still_paused_time}")
        timer.stop()
        return False
    print("✅ PASS: Timer doesn't progress while paused")
    
    # Resume
    timer.resume()
    if timer.is_paused:
        print("❌ FAIL: Timer still paused after resume")
        timer.stop()
        return False
    print("✅ PASS: Timer resumes correctly")
    
    # Wait a bit more
    time.sleep(0.1)
    final_time = timer.get_elapsed_time()
    if final_time <= paused_time:
        print(f"❌ FAIL: Timer didn't progress after resume: {final_time}")
        timer.stop()
        return False
    print(f"✅ PASS: Timer progresses after resume ({final_time:.2f}s)")
    
    timer.stop()
    return True


def test_timer_reset():
    """Test timer reset functionality"""
    print("\nTesting timer reset...")
    timer = get_timer()
    state = get_global_state()
    
    # Start timer and run for a bit
    timer.start()
    time.sleep(0.1)
    
    # Reset
    timer.reset()
    
    if timer.is_running:
        print("❌ FAIL: Timer still running after reset")
        return False
    
    elapsed = timer.get_elapsed_time()
    if elapsed != 0.0:
        print(f"❌ FAIL: Timer not zero after reset: {elapsed}")
        return False
    
    if state.timer_value != 0.0:
        print(f"❌ FAIL: State timer value not zero after reset: {state.timer_value}")
        return False
    
    print("✅ PASS: Timer resets to zero")
    print("✅ PASS: State timer value resets to zero")
    
    return True


def test_state_updates():
    """Test that timer updates global state"""
    print("\nTesting state updates...")
    timer = get_timer()
    state = get_global_state()
    
    # Reset and start
    timer.reset()
    timer.start()
    
    # Wait for state to update
    time.sleep(0.3)
    
    # Check that state was updated
    if state.timer_value <= 0:
        print(f"❌ FAIL: State timer value not updated: {state.timer_value}")
        timer.stop()
        return False
    
    print(f"✅ PASS: State timer value updated ({state.timer_value:.2f}s)")
    
    timer.stop()
    return True


def main():
    """Run all tests"""
    print("=" * 50)
    print("TASK 4 TEST: Timer Logic")
    print("=" * 50)
    
    all_tests_passed = True
    
    all_tests_passed &= test_timer_singleton()
    all_tests_passed &= test_timer_start_stop()
    all_tests_passed &= test_timer_pause_resume()
    all_tests_passed &= test_timer_reset()
    all_tests_passed &= test_state_updates()
    
    print("\n" + "=" * 50)
    if all_tests_passed:
        print("🎉 ALL TESTS PASSED - Task 4 Complete!")
    else:
        print("💥 SOME TESTS FAILED - Task 4 Needs Fixes")
    print("=" * 50)


if __name__ == "__main__":
    main() 
"""
Timer/stopwatch logic for AWE test rig
"""

import time
import threading
from .state import get_global_state


class Timer:
    """Stopwatch timer that updates global state"""
    
    def __init__(self):
        self.state = get_global_state()
        self._start_time = None
        self._elapsed_time = 0.0
        self._running = False
        self._paused = False
        self._update_thread = None
        self._stop_event = threading.Event()
    
    def start(self):
        """Start the timer"""
        if not self._running:
            self._start_time = time.time()
            self._running = True
            self._paused = False
            self._stop_event.clear()
            
            # Start update thread
            self._update_thread = threading.Thread(target=self._update_loop)
            self._update_thread.daemon = True
            self._update_thread.start()
    
    def pause(self):
        """Pause the timer"""
        if self._running and not self._paused:
            self._paused = True
            self._elapsed_time += time.time() - self._start_time
    
    def resume(self):
        """Resume the timer from pause"""
        if self._running and self._paused:
            self._paused = False
            self._start_time = time.time()
    
    def stop(self):
        """Stop the timer"""
        if self._running:
            if not self._paused:
                self._elapsed_time += time.time() - self._start_time
            self._running = False
            self._paused = False
            self._stop_event.set()
            
            if self._update_thread and self._update_thread.is_alive():
                self._update_thread.join(timeout=1.0)
    
    def reset(self):
        """Reset the timer to zero"""
        self.stop()
        self._elapsed_time = 0.0
        self.state.update_sensor_values(timer_value=0.0)
    
    def get_elapsed_time(self):
        """Get current elapsed time in seconds"""
        if not self._running:
            return self._elapsed_time
        elif self._paused:
            return self._elapsed_time
        else:
            return self._elapsed_time + (time.time() - self._start_time)
    
    def _update_loop(self):
        """Background thread to update state with current time"""
        while self._running and not self._stop_event.is_set():
            current_time = self.get_elapsed_time()
            self.state.update_sensor_values(timer_value=current_time)
            
            # Update every 100ms
            if self._stop_event.wait(0.1):
                break
    
    @property
    def is_running(self):
        """Check if timer is running"""
        return self._running
    
    @property
    def is_paused(self):
        """Check if timer is paused"""
        return self._paused


# Global timer instance
_timer_instance = None
_timer_lock = threading.Lock()


def get_timer() -> Timer:
    """Get the singleton Timer instance"""
    global _timer_instance
    if _timer_instance is None:
        with _timer_lock:
            if _timer_instance is None:
                _timer_instance = Timer()
    return _timer_instance 
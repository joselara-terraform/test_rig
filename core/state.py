"""
Global application state singleton for AWE test rig
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
import threading


@dataclass
class GlobalState:
    """Centralized state container for the AWE test rig application"""
    
    # Test control
    test_running: bool = False
    test_paused: bool = False
    emergency_stop: bool = False
    timer_value: float = 0.0  # seconds
    
    # Session information
    current_session_id: Optional[str] = None
    session_start_time: Optional[str] = None
    
    # Connection status for each device
    connections: Dict[str, bool] = field(default_factory=lambda: {
        'ni_daq': False,
        'pico_tc08': False,
        'bga244': False,
        'cvm24p': False
    })
    
    # Individual BGA connection status (for 3 separate units)
    bga_connections: Dict[str, bool] = field(default_factory=lambda: {
        'bga244_1': False,
        'bga244_2': False,
        'bga244_3': False
    })
    
    # Sensor values (mocked initially)
    pressure_values: List[float] = field(default_factory=lambda: [0.0, 0.0])  # 2 pressure sensors
    current_value: float = 0.0  # 1 current sensor
    temperature_values: List[float] = field(default_factory=lambda: [0.0] * 8)  # 8 thermocouples
    cell_voltages: List[float] = field(default_factory=lambda: [0.0] * 120)  # 120 cell voltages
    
    # Gas analysis data from BGA244 units
    gas_concentrations: List[Dict[str, float]] = field(default_factory=lambda: [
        {'H2': 0.0, 'O2': 0.0, 'N2': 0.0, 'other': 0.0},  # BGA Unit 1
        {'H2': 0.0, 'O2': 0.0, 'N2': 0.0, 'other': 0.0},  # BGA Unit 2  
        {'H2': 0.0, 'O2': 0.0, 'N2': 0.0, 'other': 0.0}   # BGA Unit 3
    ])
    
    # Enhanced gas analysis data with primary/secondary gas info
    enhanced_gas_data: List[Dict[str, Any]] = field(default_factory=lambda: [
        {'primary_gas': 'H2', 'secondary_gas': 'O2', 'remaining_gas': 'N2',
         'primary_gas_concentration': 0.0, 'secondary_gas_concentration': 0.0, 'remaining_gas_concentration': 0.0},
        {'primary_gas': 'H2', 'secondary_gas': 'O2', 'remaining_gas': 'N2',
         'primary_gas_concentration': 0.0, 'secondary_gas_concentration': 0.0, 'remaining_gas_concentration': 0.0},
        {'primary_gas': 'H2', 'secondary_gas': 'O2', 'remaining_gas': 'N2',
         'primary_gas_concentration': 0.0, 'secondary_gas_concentration': 0.0, 'remaining_gas_concentration': 0.0}
    ])
    
    # Actuator states
    valve_states: List[bool] = field(default_factory=lambda: [False] * 5)  # 5 solenoid valves
    pump_state: bool = False
    koh_pump_state: bool = False
    
    # BGA244 purge mode (changes all secondary gases to N2)
    purge_mode: bool = False
    
    # Thread lock for state updates
    _lock: threading.Lock = field(default_factory=threading.Lock)
    
    def update_sensor_values(self, **kwargs):
        """Thread-safe update of sensor values"""
        with self._lock:
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
    
    def update_connection_status(self, device: str, connected: bool):
        """Thread-safe update of connection status"""
        with self._lock:
            if device in self.connections:
                self.connections[device] = connected
            elif device in self.bga_connections:
                self.bga_connections[device] = connected
    
    def update_test_status(self, running: bool = None, paused: bool = None, 
                          session_id: str = None, session_start_time: str = None):
        """Thread-safe update of test status and session info"""
        with self._lock:
            if running is not None:
                self.test_running = running
            if paused is not None:
                self.test_paused = paused
            if session_id is not None:
                self.current_session_id = session_id
            if session_start_time is not None:
                self.session_start_time = session_start_time
    
    def set_actuator_state(self, actuator: str, state: bool, index: int = None):
        """Thread-safe update of actuator states"""
        with self._lock:
            if actuator == 'pump':
                self.pump_state = state
            elif actuator == 'koh_pump':
                self.koh_pump_state = state
            elif actuator == 'valve' and index is not None:
                if 0 <= index < len(self.valve_states):
                    self.valve_states[index] = state
    
    def set_emergency_stop(self, stop: bool = True):
        """Thread-safe emergency stop activation"""
        with self._lock:
            self.emergency_stop = stop
            if stop:
                self.test_running = False
                self.test_paused = False
    
    def get_test_status(self) -> Dict[str, Any]:
        """Get current test status information"""
        with self._lock:
            return {
                "running": self.test_running,
                "paused": self.test_paused,
                "emergency_stop": self.emergency_stop,
                "timer_value": self.timer_value,
                "session_id": self.current_session_id,
                "session_start_time": self.session_start_time
            }
    
    def get_connection_summary(self) -> Dict[str, Any]:
        """Get summary of all connection statuses"""
        with self._lock:
            return {
                "main_services": self.connections.copy(),
                "bga_units": self.bga_connections.copy(),
                "all_connected": all(self.connections.values()),
                "any_bga_connected": any(self.bga_connections.values())
            }


# Singleton instance
_state_instance = None
_state_lock = threading.Lock()


def get_global_state() -> GlobalState:
    """Get the singleton GlobalState instance"""
    global _state_instance
    if _state_instance is None:
        with _state_lock:
            if _state_instance is None:
                _state_instance = GlobalState()
    return _state_instance 
"""
Global application state singleton for AWE test rig
"""

from dataclasses import dataclass, field
from typing import Dict, List
import threading


@dataclass
class GlobalState:
    """Centralized state container for the AWE test rig application"""
    
    # Test control
    test_running: bool = False
    test_paused: bool = False
    emergency_stop: bool = False
    timer_value: float = 0.0  # seconds
    
    # Connection status for each device
    connections: Dict[str, bool] = field(default_factory=lambda: {
        'ni_daq': False,
        'pico_tc08': False,
        'bga244': False,
        'cvm24p': False
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
    
    # Actuator states
    valve_states: List[bool] = field(default_factory=lambda: [False] * 4)  # 4 solenoid valves
    pump_state: bool = False
    
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
    
    def set_actuator_state(self, actuator: str, state: bool, index: int = None):
        """Thread-safe update of actuator states"""
        with self._lock:
            if actuator == 'pump':
                self.pump_state = state
            elif actuator == 'valve' and index is not None:
                if 0 <= index < len(self.valve_states):
                    self.valve_states[index] = state


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
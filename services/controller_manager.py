#!/usr/bin/env python3
"""
Controller manager for coordinating all hardware services
"""

import time
import threading
from core.state import get_global_state


class ControllerManager:
    """Manages lifecycle of all hardware services"""
    
    def __init__(self):
        self.state = get_global_state()
        self.services_running = False
        self.services = {
            'ni_daq': {'connected': False, 'thread': None},
            'pico_tc08': {'connected': False, 'thread': None},
            'bga244': {'connected': False, 'thread': None},
            'cvm24p': {'connected': False, 'thread': None}
        }
        self._stop_event = threading.Event()
    
    def start_all_services(self):
        """Start all hardware services"""
        if self.services_running:
            print("⚠️  Services already running")
            return False
        
        print("🔌 Starting all hardware services...")
        
        # Reset stop event
        self._stop_event.clear()
        
        # Start each service (mocked)
        success_count = 0
        
        # NI DAQ Service
        if self._start_ni_daq():
            success_count += 1
        
        # Pico TC-08 Service  
        if self._start_pico_tc08():
            success_count += 1
        
        # BGA244 Service
        if self._start_bga244():
            success_count += 1
        
        # CVM-24P Service
        if self._start_cvm24p():
            success_count += 1
        
        # Check if all services started successfully
        if success_count == 4:
            self.services_running = True
            print(f"✅ All {success_count}/4 services started successfully")
            return True
        else:
            print(f"❌ Only {success_count}/4 services started - stopping all")
            self.stop_all_services()
            return False
    
    def stop_all_services(self):
        """Stop all hardware services"""
        if not self.services_running:
            print("⚠️  Services already stopped")
            return
        
        print("🔌 Stopping all hardware services...")
        
        # Set stop event
        self._stop_event.set()
        
        # Stop each service
        self._stop_ni_daq()
        self._stop_pico_tc08()
        self._stop_bga244()
        self._stop_cvm24p()
        
        # Wait for threads to finish
        for service_name, service_info in self.services.items():
            if service_info['thread'] and service_info['thread'].is_alive():
                service_info['thread'].join(timeout=2.0)
        
        self.services_running = False
        print("✅ All services stopped")
    
    def _start_ni_daq(self):
        """Start NI DAQ service (mocked)"""
        try:
            print("   → Starting NI cDAQ service...")
            # Simulate connection delay
            time.sleep(0.1)
            
            # Update state
            self.state.update_connection_status('ni_daq', True)
            self.services['ni_daq']['connected'] = True
            
            # Start mock data thread
            thread = threading.Thread(target=self._ni_daq_loop, daemon=True)
            thread.start()
            self.services['ni_daq']['thread'] = thread
            
            print("   ✅ NI cDAQ connected - Pressure/Current sensors + Valve/Pump control")
            return True
        except Exception as e:
            print(f"   ❌ NI cDAQ failed: {e}")
            return False
    
    def _start_pico_tc08(self):
        """Start Pico TC-08 service (mocked)"""
        try:
            print("   → Starting Pico TC-08 service...")
            time.sleep(0.1)
            
            self.state.update_connection_status('pico_tc08', True)
            self.services['pico_tc08']['connected'] = True
            
            thread = threading.Thread(target=self._pico_tc08_loop, daemon=True)
            thread.start()
            self.services['pico_tc08']['thread'] = thread
            
            print("   ✅ Pico TC-08 connected - 8-channel thermocouple logger")
            return True
        except Exception as e:
            print(f"   ❌ Pico TC-08 failed: {e}")
            return False
    
    def _start_bga244(self):
        """Start BGA244 service (mocked)"""
        try:
            print("   → Starting BGA244 analyzers...")
            time.sleep(0.1)
            
            self.state.update_connection_status('bga244', True)
            self.services['bga244']['connected'] = True
            
            thread = threading.Thread(target=self._bga244_loop, daemon=True)
            thread.start()
            self.services['bga244']['thread'] = thread
            
            print("   ✅ BGA244 connected - 3x gas analyzers (H2, O2, N2)")
            return True
        except Exception as e:
            print(f"   ❌ BGA244 failed: {e}")
            return False
    
    def _start_cvm24p(self):
        """Start CVM-24P service (mocked)"""
        try:
            print("   → Starting CVM-24P service...")
            time.sleep(0.1)
            
            self.state.update_connection_status('cvm24p', True)
            self.services['cvm24p']['connected'] = True
            
            thread = threading.Thread(target=self._cvm24p_loop, daemon=True)
            thread.start()
            self.services['cvm24p']['thread'] = thread
            
            print("   ✅ CVM-24P connected - 24-channel cell voltage monitor")
            return True
        except Exception as e:
            print(f"   ❌ CVM-24P failed: {e}")
            return False
    
    def _stop_ni_daq(self):
        """Stop NI DAQ service"""
        if self.services['ni_daq']['connected']:
            print("   → Stopping NI cDAQ service...")
            self.state.update_connection_status('ni_daq', False)
            self.services['ni_daq']['connected'] = False
            print("   ✅ NI cDAQ disconnected")
    
    def _stop_pico_tc08(self):
        """Stop Pico TC-08 service"""
        if self.services['pico_tc08']['connected']:
            print("   → Stopping Pico TC-08 service...")
            self.state.update_connection_status('pico_tc08', False)
            self.services['pico_tc08']['connected'] = False
            print("   ✅ Pico TC-08 disconnected")
    
    def _stop_bga244(self):
        """Stop BGA244 service"""
        if self.services['bga244']['connected']:
            print("   → Stopping BGA244 analyzers...")
            self.state.update_connection_status('bga244', False)
            self.services['bga244']['connected'] = False
            print("   ✅ BGA244 disconnected")
    
    def _stop_cvm24p(self):
        """Stop CVM-24P service"""
        if self.services['cvm24p']['connected']:
            print("   → Stopping CVM-24P service...")
            self.state.update_connection_status('cvm24p', False)
            self.services['cvm24p']['connected'] = False
            print("   ✅ CVM-24P disconnected")
    
    def _ni_daq_loop(self):
        """Mock NI DAQ data polling loop"""
        while not self._stop_event.is_set() and self.services['ni_daq']['connected']:
            # Mock sensor readings
            import random
            self.state.update_sensor_values(
                pressure_values=[random.uniform(14.5, 15.5), random.uniform(29.0, 31.0)],
                current_value=random.uniform(4.8, 5.2)
            )
            time.sleep(1/250)  # 250 Hz simulation
    
    def _pico_tc08_loop(self):
        """Mock Pico TC-08 data polling loop"""
        while not self._stop_event.is_set() and self.services['pico_tc08']['connected']:
            import random
            temps = [random.uniform(18.0, 25.0) for _ in range(8)]
            self.state.update_sensor_values(temperature_values=temps)
            time.sleep(1.0)  # 1 Hz simulation
    
    def _bga244_loop(self):
        """Mock BGA244 data polling loop"""
        while not self._stop_event.is_set() and self.services['bga244']['connected']:
            # Mock gas analyzer data (would be stored in state when implemented)
            time.sleep(2.0)  # 0.5 Hz simulation
    
    def _cvm24p_loop(self):
        """Mock CVM-24P data polling loop"""
        while not self._stop_event.is_set() and self.services['cvm24p']['connected']:
            import random
            voltages = [random.uniform(3.0, 4.2) for _ in range(24)]
            self.state.update_sensor_values(cell_voltages=voltages)
            time.sleep(0.1)  # 10 Hz simulation
    
    def get_connection_status(self):
        """Get current connection status of all services"""
        return {service: info['connected'] for service, info in self.services.items()}
    
    def is_all_connected(self):
        """Check if all services are connected"""
        return all(info['connected'] for info in self.services.values())


# Singleton instance
_controller_instance = None
_controller_lock = threading.Lock()


def get_controller_manager() -> ControllerManager:
    """Get the singleton ControllerManager instance"""
    global _controller_instance
    if _controller_instance is None:
        with _controller_lock:
            if _controller_instance is None:
                _controller_instance = ControllerManager()
    return _controller_instance


def main():
    """Test the controller manager by running it directly"""
    print("=" * 60)
    print("TASK 9 TEST: Controller Manager")
    print("=" * 60)
    print("✅ Controller manager created")
    print("✅ Service management: NI DAQ, Pico, BGA, CVM")
    print("✅ Mocked connections with realistic polling")
    print("\n🎯 TEST: Verify service coordination:")
    
    manager = get_controller_manager()
    
    print("\n1. Starting all services...")
    success = manager.start_all_services()
    print(f"   Result: {'✅ Success' if success else '❌ Failed'}")
    
    print("\n2. Checking connection status...")
    status = manager.get_connection_status()
    for service, connected in status.items():
        print(f"   {service}: {'✅ Connected' if connected else '❌ Disconnected'}")
    
    print(f"\n3. All connected: {'✅ Yes' if manager.is_all_connected() else '❌ No'}")
    
    print("\n4. Waiting 3 seconds for data polling...")
    time.sleep(3)
    
    print("\n5. Stopping all services...")
    manager.stop_all_services()
    
    print("\n6. Final connection status...")
    status = manager.get_connection_status()
    for service, connected in status.items():
        print(f"   {service}: {'✅ Connected' if connected else '❌ Disconnected'}")
    
    print("\n✅ Controller manager test complete!")
    print("=" * 60)


if __name__ == "__main__":
    main() 
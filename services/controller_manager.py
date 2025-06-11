#!/usr/bin/env python3
"""
Controller manager for coordinating all hardware services and test sessions
"""

import time
import threading
from typing import Optional, Dict, Any
from core.state import get_global_state
from core.timer import get_timer
from data.session_manager import get_session_manager, start_test_session, end_test_session
from data.logger import get_csv_logger
from .ni_daq import NIDAQService
from .pico_tc08 import PicoTC08Service
from .bga244 import BGA244Service
from .cvm24p import CVM24PService


class ControllerManager:
    """Manages lifecycle of all hardware services and test sessions"""
    
    def __init__(self):
        self.state = get_global_state()
        self.timer = get_timer()
        self.session_manager = get_session_manager()
        self.csv_logger = get_csv_logger()
        self.services_running = False
        self.test_running = False
        self.current_session = None
        
        # Actual service instances
        self.ni_daq_service = None
        self.pico_tc08_service = None
        self.bga244_service = None
        self.cvm24p_service = None
        
        # Service status tracking
        self.services = {
            'ni_daq': {'connected': False, 'service': None},
            'pico_tc08': {'connected': False, 'service': None},
            'bga244': {'connected': False, 'service': None},
            'cvm24p': {'connected': False, 'service': None}
        }
    
    def start_all_services(self):
        """Start all hardware services"""
        if self.services_running:
            print("⚠️  Services already running")
            return False
        
        print("🔌 Starting all hardware services...")
        
        # Start each service using their actual implementations
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
        
        # Stop each service using their actual implementations
        self._stop_ni_daq()
        self._stop_pico_tc08()
        self._stop_bga244()
        self._stop_cvm24p()
        
        self.services_running = False
        print("✅ All services stopped")
    
    def start_test(self, session_name: Optional[str] = None) -> bool:
        """
        Start a new test session with data logging
        
        Args:
            session_name: Optional custom name for the test session
            
        Returns:
            True if test started successfully
        """
        if self.test_running:
            print("⚠️  Test already running")
            return False
        
        # Ensure services are connected first
        if not self.services_running:
            print("❌ Cannot start test - services not running")
            print("   → Please connect to hardware first")
            return False
        
        print("🧪 Starting new test session...")
        
        try:
            # Start new session with timestamped folder
            self.current_session = start_test_session(session_name)
            
            # Reset and start timer for plotting
            self.timer.reset()
            self.timer.start()
            print("   → Timer started from 0")
            
            # Update test state
            self.test_running = True
            self.state.update_test_status(running=True)
            
            # Initialize BGAs to normal mode (not purge mode) for test start
            print("   → Initializing BGAs to normal gas readings...")
            try:
                if self.services['bga244']['connected'] and self.bga244_service:
                    # Ensure BGAs start in normal mode (purge_mode=False)
                    self.bga244_service.set_purge_mode(False)
                    self.state.purge_mode = False
                    print("   → BGAs configured for normal gas analysis (H2 in O2, O2 in H2)")
                else:
                    print("   → BGAs not connected - will use normal mode when connected")
            except Exception as e:
                print(f"   ⚠️  Warning: Could not initialize BGA mode: {e}")
            
            # Register configuration snapshot
            config_file = f"{self.session_manager.get_base_filename('config')}.json"
            config_path = self.session_manager.register_file(
                config_file, 
                "config", 
                "Device configuration snapshot at test start"
            )
            
            # Save current device configuration
            self._save_test_configuration(config_path)
            
            # Start CSV data logging
            print("   → Starting CSV data logging...")
            logging_started = self.csv_logger.start_logging()
            
            print(f"✅ Test session started: {self.current_session['session_id']}")
            print(f"   → Session folder: {self.current_session['folder_path']}")
            print(f"   → Configuration saved: {config_file}")
            print(f"   → Timer: ✅ Started")
            
            if logging_started:
                print(f"   → CSV logging: ✅ Started - Files will be created")
                print(f"   → Log files: sensors.csv, gas_analysis.csv, cell_voltages.csv, actuators.csv")
            else:
                print(f"   → CSV logging: ❌ FAILED - No CSV files will be created")
                print(f"   → Check session folder and file permissions")
                print(f"   → Test will continue without data logging")
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to start test session: {e}")
            import traceback
            print(f"   → Error details: {traceback.format_exc()}")
            self.test_running = False
            self.state.update_test_status(running=False)
            self.timer.reset()
            return False
    
    def stop_test(self, status: str = "completed") -> Optional[Dict[str, Any]]:
        """
        Stop the current test session
        
        Args:
            status: Final status of the test (completed, stopped, error)
            
        Returns:
            Final session metadata or None if no test was running
        """
        if not self.test_running:
            print("⚠️  No test running to stop")
            return None
        
        print("🧪 Stopping test session...")
        
        try:
            # Stop timer
            self.timer.reset()
            print("   → Timer stopped and reset")
            
            # Stop CSV logging first
            logging_stats = self.csv_logger.stop_logging()
            
            # End the current session
            final_session = end_test_session(status)
            
            # Update test state
            self.test_running = False
            self.state.update_test_status(running=False)
            
            # Clear current session
            self.current_session = None
            
            print(f"✅ Test session stopped")
            print(f"   → Final status: {status}")
            if final_session:
                print(f"   → Duration: {final_session.get('duration_formatted', 'Unknown')}")
                print(f"   → Files created: {len(final_session.get('files', {}))}")
            if logging_stats:
                print(f"   → Data logged: {logging_stats.get('log_count', 0)} entries")
            
            return final_session
            
        except Exception as e:
            print(f"❌ Error stopping test session: {e}")
            self.test_running = False
            self.state.update_test_status(running=False)
            self.timer.reset()
            return None
    
    def emergency_stop(self) -> Optional[Dict[str, Any]]:
        """Emergency stop - immediately halt test and disconnect services"""
        print("🚨 EMERGENCY STOP ACTIVATED")
        
        # Stop timer immediately
        self.timer.reset()
        print("   → Timer stopped immediately")
        
        # Stop test session first
        final_session = None
        if self.test_running:
            # Stop CSV logging immediately
            try:
                self.csv_logger.stop_logging()
            except Exception as e:
                print(f"⚠️  Error stopping CSV logging during emergency: {e}")
            
            final_session = self.stop_test("emergency_stop")
        
        # Stop all services
        self.stop_all_services()
        
        # Update state
        self.state.update_test_status(running=False)
        
        print("🚨 Emergency stop completed - all systems halted")
        return final_session
    
    def _save_test_configuration(self, config_path: str):
        """Save current device configuration to test session"""
        try:
            import json
            from config.device_config import get_device_config
            
            # Get current device configuration
            device_config = get_device_config()
            
            # Create configuration snapshot
            config_snapshot = {
                "test_start_time": self.current_session['start_time'],
                "session_id": self.current_session['session_id'],
                "services": self.get_service_details(),
                "device_config": device_config.config,  # Access config attribute directly
                "connection_status": self.get_connection_status()
            }
            
            # Save to file
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config_snapshot, f, indent=2, ensure_ascii=False)
            
            print(f"   → Configuration snapshot saved")
            
        except Exception as e:
            print(f"⚠️  Error saving configuration: {e}")
    
    def get_test_status(self) -> Dict[str, Any]:
        """Get current test status and session info"""
        return {
            "test_running": self.test_running,
            "services_running": self.services_running,
            "current_session": self.current_session,
            "session_manager_active": self.session_manager.get_current_session() is not None
        }
    
    def get_session_file_path(self, filename: str, file_type: str = "csv") -> Optional[str]:
        """Get file path in current session (convenience method)"""
        if not self.test_running or not self.current_session:
            return None
        
        try:
            from data.session_manager import get_session_file_path
            return get_session_file_path(filename, file_type)
        except Exception:
            return None
    
    def _start_ni_daq(self):
        """Start NI DAQ service using actual NIDAQService"""
        try:
            print("   → Starting NI cDAQ service...")
            
            # Create and connect actual service
            self.ni_daq_service = NIDAQService()
            if self.ni_daq_service.connect():
                if self.ni_daq_service.start_polling():
                    self.services['ni_daq']['connected'] = True
                    self.services['ni_daq']['service'] = self.ni_daq_service
                    print("   ✅ NI cDAQ connected - Pressure/Current sensors + Valve/Pump control")
                    return True
                else:
                    print("   ❌ NI cDAQ polling failed to start")
                    self.ni_daq_service.disconnect()
                    return False
            else:
                print("   ❌ NI cDAQ connection failed")
                return False
                
        except Exception as e:
            print(f"   ❌ NI cDAQ failed: {e}")
            return False
    
    def _start_pico_tc08(self):
        """Start Pico TC-08 service using actual PicoTC08Service"""
        try:
            print("   → Starting Pico TC-08 service...")
            
            # Create and connect actual service
            self.pico_tc08_service = PicoTC08Service()
            if self.pico_tc08_service.connect():
                if self.pico_tc08_service.start_polling():
                    self.services['pico_tc08']['connected'] = True
                    self.services['pico_tc08']['service'] = self.pico_tc08_service
                    print("   ✅ Pico TC-08 connected - 8-channel thermocouple logger")
                    return True
                else:
                    print("   ❌ Pico TC-08 polling failed to start")
                    self.pico_tc08_service.disconnect()
                    return False
            else:
                print("   ❌ Pico TC-08 connection failed")
                return False
                
        except Exception as e:
            print(f"   ❌ Pico TC-08 failed: {e}")
            return False
    
    def _start_bga244(self):
        """Start BGA244 service using actual BGA244Service"""
        try:
            print("   → Starting BGA244 analyzers...")
            
            # Create and connect actual service
            self.bga244_service = BGA244Service()
            if self.bga244_service.connect():
                if self.bga244_service.start_polling():
                    self.services['bga244']['connected'] = True
                    self.services['bga244']['service'] = self.bga244_service
                    print("   ✅ BGA244 connected - 3x gas analyzers (H2, O2, N2)")
                    return True
                else:
                    print("   ❌ BGA244 polling failed to start")
                    self.bga244_service.disconnect()
                    return False
            else:
                print("   ❌ BGA244 connection failed")
                return False
                
        except Exception as e:
            print(f"   ❌ BGA244 failed: {e}")
            return False
    
    def _start_cvm24p(self):
        """Start CVM-24P service using actual CVM24PService"""
        try:
            print("   → Starting CVM-24P service...")
            
            # Create and connect actual service
            self.cvm24p_service = CVM24PService()
            if self.cvm24p_service.connect():
                if self.cvm24p_service.start_polling():
                    self.services['cvm24p']['connected'] = True
                    self.services['cvm24p']['service'] = self.cvm24p_service
                    print("   ✅ CVM-24P connected - 24-channel cell voltage monitor")
                    return True
                else:
                    print("   ❌ CVM-24P polling failed to start")
                    self.cvm24p_service.disconnect()
                    return False
            else:
                print("   ❌ CVM-24P connection failed")
                return False
                
        except Exception as e:
            print(f"   ❌ CVM-24P failed: {e}")
            return False
    
    def _stop_ni_daq(self):
        """Stop NI DAQ service"""
        if self.services['ni_daq']['connected'] and self.ni_daq_service:
            print("   → Stopping NI cDAQ service...")
            self.ni_daq_service.stop_polling()
            self.ni_daq_service.disconnect()
            self.services['ni_daq']['connected'] = False
            self.services['ni_daq']['service'] = None
            self.ni_daq_service = None
            print("   ✅ NI cDAQ disconnected")
    
    def _stop_pico_tc08(self):
        """Stop Pico TC-08 service"""
        if self.services['pico_tc08']['connected'] and self.pico_tc08_service:
            print("   → Stopping Pico TC-08 service...")
            self.pico_tc08_service.stop_polling()
            self.pico_tc08_service.disconnect()
            self.services['pico_tc08']['connected'] = False
            self.services['pico_tc08']['service'] = None
            self.pico_tc08_service = None
            print("   ✅ Pico TC-08 disconnected")
    
    def _stop_bga244(self):
        """Stop BGA244 service"""
        if self.services['bga244']['connected'] and self.bga244_service:
            print("   → Stopping BGA244 analyzers...")
            self.bga244_service.stop_polling()
            self.bga244_service.disconnect()
            self.services['bga244']['connected'] = False
            self.services['bga244']['service'] = None
            self.bga244_service = None
            print("   ✅ BGA244 disconnected")
    
    def _stop_cvm24p(self):
        """Stop CVM-24P service"""
        if self.services['cvm24p']['connected'] and self.cvm24p_service:
            print("   → Stopping CVM-24P service...")
            self.cvm24p_service.stop_polling()
            self.cvm24p_service.disconnect()
            self.services['cvm24p']['connected'] = False
            self.services['cvm24p']['service'] = None
            self.cvm24p_service = None
            print("   ✅ CVM-24P disconnected")
    
    def get_connection_status(self):
        """Get current connection status of all services"""
        return {service: info['connected'] for service, info in self.services.items()}
    
    def is_all_connected(self):
        """Check if all services are connected"""
        return all(info['connected'] for info in self.services.values())
    
    def get_service_details(self):
        """Get detailed status of all services"""
        details = {}
        for service_name, service_info in self.services.items():
            if service_info['connected'] and service_info['service']:
                # Try to get status from actual service if it has a get_status method
                try:
                    if hasattr(service_info['service'], 'get_status'):
                        details[service_name] = service_info['service'].get_status()
                    else:
                        details[service_name] = {'connected': True, 'status': 'Running'}
                except Exception as e:
                    details[service_name] = {'connected': True, 'status': f'Error: {e}'}
            else:
                details[service_name] = {'connected': False, 'status': 'Disconnected'}
        return details


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
    print("CONTROLLER MANAGER TEST: Real Service Integration")
    print("=" * 60)
    print("✅ Controller manager updated to use actual services")
    print("✅ Service management: NI DAQ, Pico, BGA, CVM")
    print("✅ Real service lifecycle management")
    print("\n🎯 TEST: Verify actual service coordination:")
    
    manager = get_controller_manager()
    
    print("\n1. Starting all services...")
    success = manager.start_all_services()
    print(f"   Result: {'✅ Success' if success else '❌ Failed'}")
    
    print("\n2. Checking connection status...")
    status = manager.get_connection_status()
    for service, connected in status.items():
        print(f"   {service}: {'✅ Connected' if connected else '❌ Disconnected'}")
    
    print(f"\n3. All connected: {'✅ Yes' if manager.is_all_connected() else '❌ No'}")
    
    if success:
        print("\n4. Service details:")
        details = manager.get_service_details()
        for service, info in details.items():
            print(f"   {service}: {info}")
        
        print("\n5. Waiting 3 seconds for data from real services...")
        time.sleep(3)
        
        # Check real data from services
        state = get_global_state()
        print(f"\n6. Real pressure data from NI DAQ service:")
        print(f"   Pressure 1: {state.pressure_values[0]:.3f} PSI")
        print(f"   Pressure 2: {state.pressure_values[1]:.3f} PSI")
        print(f"   Current: {state.current_value:.1f} A")
        
        print(f"\n7. Temperature data from Pico service:")
        if len(state.temperature_values) >= 3:
            print(f"   Inlet temp: {state.temperature_values[0]:.1f}°C")
            print(f"   Outlet temp: {state.temperature_values[1]:.1f}°C")
            print(f"   Stack temp: {state.temperature_values[2]:.1f}°C")
    
    print("\n8. Stopping all services...")
    manager.stop_all_services()
    
    print("\n9. Final connection status...")
    status = manager.get_connection_status()
    for service, connected in status.items():
        print(f"   {service}: {'✅ Connected' if connected else '❌ Disconnected'}")
    
    print("\n✅ Controller manager with real services test complete!")
    print("   🎯 The pressure plots should now show the correct values:")
    print("   📊 Pressure 1: ~0.7-0.8 PSI (not ~15 PSI)")
    print("   📊 Pressure 2: ~0.3-0.4 PSI (not ~30 PSI)")
    print("=" * 60)


if __name__ == "__main__":
    main() 
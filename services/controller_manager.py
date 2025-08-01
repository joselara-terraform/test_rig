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
from utils.logger import log


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
            log.warning("System", "Services already running")
            return False
        
        log.info("System", "Starting all hardware services")
        
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
            log.success("System", f"All {success_count} services started successfully")
            return True
        else:
            log.error("System", f"Only {success_count}/4 services started - stopping all")
            self.stop_all_services()
            return False
    
    def stop_all_services(self):
        """Stop all hardware services"""
        if not self.services_running:
            log.warning("System", "Services already stopped")
            return
        
        # Stop each service using their actual implementations
        self._stop_ni_daq()
        self._stop_pico_tc08()
        self._stop_bga244()
        self._stop_cvm24p()
        
        self.services_running = False
        log.success("System", "All services stopped")
    
    def start_test(self, session_name: Optional[str] = None) -> bool:
        """
        Start a new test session with data logging
        
        Args:
            session_name: Optional custom name for the test session
            
        Returns:
            True if test started successfully
        """
        if self.test_running:
            log.warning("TestRunner", "Test already running")
            return False
        
        # Ensure services are connected first
        if not self.services_running:
            log.error("TestRunner", "Cannot start test - services not running", [
                "→ Please connect to hardware first"
            ])
            return False
        
        try:
            # Start new session with timestamped folder
            self.current_session = start_test_session(session_name)
            
            # Reset and start timer for plotting
            self.timer.reset()
            self.timer.start()
            
            # Update test state
            self.test_running = True
            self.state.update_test_status(running=True)
            
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
            logging_started = self.csv_logger.start_logging()
            
            session_details = [
                f"→ Session name: {self.current_session['session_id']}",
                f"→ Configuration saved: {config_file}",
                f"→ Timer: Started"
            ]
            
            if logging_started:
                session_details.append("→ CSV logging: 4 files created (1.0s interval)")
            else:
                session_details.extend([
                    "→ CSV logging: FAILED - No CSV files will be created",
                    "→ Check session folder and file permissions",
                    "→ Test will continue without data logging"
                ])
            
            log.success("TestRunner", "Starting test session", session_details)
            return True
            
        except Exception as e:
            log.error("TestRunner", f"Failed to start test session: {e}")
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
            log.warning("TestRunner", "No test running to stop")
            return None
        
        try:
            # Stop timer
            self.timer.reset()
            
            # Stop CSV logging first
            logging_stats = self.csv_logger.stop_logging()
            
            # End the current session (this saves active channels automatically)
            final_session = end_test_session(status)
            
            # Run post-processing on the completed session (skip for emergency stops)
            if final_session and logging_stats.get('log_count', 0) > 0 and status != "emergency_stop":
                try:
                    from data.post_processor import process_session_data
                    
                    # Get active channels from the final session metadata
                    active_channels = final_session.get('active_channels')
                    
                    # Process the session data
                    post_success = process_session_data(
                        final_session['folder_path'], 
                        active_channels
                    )
                    
                    # Post-processing messages are handled in post_processor.py
                        
                except Exception as e:
                    log.error("PostProcessor", f"Post-processing error: {e}", [
                        "→ Test session saved successfully, but plots not generated"
                    ])
            
            # Update test state
            self.test_running = False
            self.state.update_test_status(running=False)
            
            # Clear current session
            self.current_session = None
            
            # Build final summary
            stop_details = [f"→ Duration: {final_session.get('duration_formatted', 'Unknown') if final_session else 'Unknown'}"]
            if final_session:
                stop_details.append(f"→ Files created: {len(final_session.get('files', {}))}")
            if logging_stats:
                stop_details.append(f"→ Entries logged: {logging_stats.get('log_count', 0)}")
            
            log.info("TestRunner", f"Stopping test session", stop_details)
            
            return final_session
            
        except Exception as e:
            log.error("TestRunner", f"Error stopping test session: {e}")
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
        
        # Stop test session first (this will skip post-processing due to emergency status)
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
        print("   → Post-processing skipped due to emergency stop")
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
            # Create and connect actual service
            self.ni_daq_service = NIDAQService()
            if self.ni_daq_service.connect():
                if self.ni_daq_service.start_polling():
                    self.services['ni_daq']['connected'] = True
                    self.services['ni_daq']['service'] = self.ni_daq_service
                    # Service connection message is handled by NIDAQService itself
                    return True
                else:
                    log.error("System", "NI cDAQ polling failed to start")
                    self.ni_daq_service.disconnect()
                    return False
            else:
                log.error("System", "NI cDAQ connection failed")
                return False
                
        except Exception as e:
            log.error("System", f"NI cDAQ failed: {e}")
            return False
    
    def _start_pico_tc08(self):
        """Start Pico TC-08 service using actual PicoTC08Service"""
        try:
            # Create and connect actual service
            self.pico_tc08_service = PicoTC08Service()
            if self.pico_tc08_service.connect():
                if self.pico_tc08_service.start_polling():
                    self.services['pico_tc08']['connected'] = True
                    self.services['pico_tc08']['service'] = self.pico_tc08_service
                    # Service connection message is handled by PicoTC08Service itself
                    return True
                else:
                    log.error("System", "Pico TC-08 polling failed to start")
                    self.pico_tc08_service.disconnect()
                    return False
            else:
                log.error("System", "Pico TC-08 connection failed")
                return False
                
        except Exception as e:
            log.error("System", f"Pico TC-08 failed: {e}")
            return False
    
    def _start_bga244(self):
        """Start BGA244 service using actual BGA244Service"""
        try:
            # Create and connect actual service
            self.bga244_service = BGA244Service()
            if self.bga244_service.connect():
                if self.bga244_service.start_polling():
                    self.services['bga244']['connected'] = True
                    self.services['bga244']['service'] = self.bga244_service
                    # Service connection message is handled by BGA244Service itself
                    return True
                else:
                    log.error("System", "BGA244 polling failed to start")
                    self.bga244_service.disconnect()
                    return False
            else:
                log.error("System", "BGA244 connection failed")
                return False
                
        except Exception as e:
            log.error("System", f"BGA244 failed: {e}")
            return False
    
    def _start_cvm24p(self):
        """Start CVM-24P service using actual CVM24PService"""
        try:
            # Create and connect actual service
            self.cvm24p_service = CVM24PService()
            if self.cvm24p_service.connect():
                if self.cvm24p_service.start_polling():
                    self.services['cvm24p']['connected'] = True
                    self.services['cvm24p']['service'] = self.cvm24p_service
                    # Service connection message is handled by CVM24PService itself
                    return True
                else:
                    log.error("System", "CVM-24P polling failed to start")
                    self.cvm24p_service.disconnect()
                    return False
            else:
                log.error("System", "CVM-24P connection failed")
                return False
                
        except Exception as e:
            log.error("System", f"CVM-24P failed: {e}")
            return False
    
    def _stop_ni_daq(self):
        """Stop NI DAQ service"""
        if self.services['ni_daq']['connected'] and self.ni_daq_service:
            self.ni_daq_service.stop_polling()
            self.ni_daq_service.disconnect()
            self.services['ni_daq']['connected'] = False
            self.services['ni_daq']['service'] = None
            self.ni_daq_service = None
            # Service disconnection message is handled by NIDAQService itself
    
    def _stop_pico_tc08(self):
        """Stop Pico TC-08 service"""
        if self.services['pico_tc08']['connected'] and self.pico_tc08_service:
            self.pico_tc08_service.stop_polling()
            self.pico_tc08_service.disconnect()
            self.services['pico_tc08']['connected'] = False
            self.services['pico_tc08']['service'] = None
            self.pico_tc08_service = None
            # Service disconnection message is handled by PicoTC08Service itself
    
    def _stop_bga244(self):
        """Stop BGA244 service"""
        if self.services['bga244']['connected'] and self.bga244_service:
            self.bga244_service.stop_polling()
            self.bga244_service.disconnect()
            self.services['bga244']['connected'] = False
            self.services['bga244']['service'] = None
            self.bga244_service = None
            # Service disconnection message is handled by BGA244Service itself
    
    def _stop_cvm24p(self):
        """Stop CVM-24P service"""
        if self.services['cvm24p']['connected'] and self.cvm24p_service:
            self.cvm24p_service.stop_polling()
            self.cvm24p_service.disconnect()
            self.services['cvm24p']['connected'] = False
            self.services['cvm24p']['service'] = None
            self.cvm24p_service = None
            # Service disconnection message is handled by CVM24PService itself
    
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
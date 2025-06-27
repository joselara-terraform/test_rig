"""
Session folder management for AWE test rig
Handles creation of timestamped test session folders and file organization
"""

import os
import json
import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from core.state import get_global_state


class SessionManager:
    """Manages test session folders and file organization"""
    
    def __init__(self, base_data_dir: str = "data"):
        self.base_data_dir = Path(base_data_dir)
        self.sessions_dir = self.base_data_dir / "sessions"
        self.current_session = None
        self.current_session_path = None
        self.session_start_time = None
        
        # Ensure directories exist
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Create necessary directory structure"""
        self.base_data_dir.mkdir(exist_ok=True)
        self.sessions_dir.mkdir(exist_ok=True)
        
        # Create archive folder for old sessions
        archive_dir = self.sessions_dir / "archive"
        archive_dir.mkdir(exist_ok=True)
    
    def start_new_session(self, session_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Start a new test session with timestamped folder
        
        Args:
            session_name: Optional custom name for the session
            
        Returns:
            Dict with session info including paths and metadata
        """
        # Generate timestamp
        self.session_start_time = datetime.datetime.now()
        timestamp = self.session_start_time.strftime("%Y-%m-%d_%H-%M-%S")
        
        # Create session folder name
        if session_name:
            # Sanitize custom session name
            clean_name = "".join(c for c in session_name if c.isalnum() or c in ('-', '_', ' ')).strip()
            clean_name = clean_name.replace(' ', '_')
            folder_name = f"{timestamp}_{clean_name}"
        else:
            folder_name = f"{timestamp}_test_session"
        
        # Create session directory
        self.current_session_path = self.sessions_dir / folder_name
        self.current_session_path.mkdir(exist_ok=True)
        
        # Create subdirectories for different data types
        subdirs = [
            "csv_data",      # Raw sensor data CSV files
            "plots",         # Generated plots and charts
            "config",        # Configuration snapshots
            "logs",          # Log files and debug info
            "analysis"       # Post-test analysis results
        ]
        
        for subdir in subdirs:
            (self.current_session_path / subdir).mkdir(exist_ok=True)
        
        # Create session metadata
        self.current_session = {
            "session_id": folder_name,
            "start_time": self.session_start_time.isoformat(),
            "session_name": session_name or "Default Test Session",
            "folder_path": str(self.current_session_path),
            "status": "running",
            "files": {},
            "metadata": {
                "test_rig_version": "1.0",
                "operator": os.getenv("USERNAME", "unknown"),
                "platform": "Windows"
            }
        }
        
        # Save session metadata
        self._save_session_metadata()
        
        # Log session start
        print(f"📁 New test session started: {folder_name}")
        print(f"   → Session path: {self.current_session_path}")
        print(f"   → Start time: {self.session_start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        return self.current_session.copy()
    
    def get_file_path(self, filename: str, subdir: str = "csv_data") -> Path:
        """
        Get full path for a file in the current session
        
        Args:
            filename: Name of the file
            subdir: Subdirectory within session folder
            
        Returns:
            Full path to the file
        """
        if not self.current_session_path:
            raise RuntimeError("No active session. Call start_new_session() first.")
        
        return self.current_session_path / subdir / filename
    
    def get_base_filename(self, file_type: str = "data") -> str:
        """
        Generate base filename with timestamp for current session
        
        Args:
            file_type: Type of file (data, config, log, etc.) - not used in filename
            
        Returns:
            Base filename with timestamp only: YYYY-MM-DD_hh-mm-ss
        """
        if not self.session_start_time:
            raise RuntimeError("No active session. Call start_new_session() first.")
        
        timestamp = self.session_start_time.strftime("%Y-%m-%d_%H-%M-%S")
        return timestamp
    
    def register_file(self, filename: str, file_type: str, description: str = "") -> str:
        """
        Register a file as part of the current session
        
        Args:
            filename: Name of the file
            file_type: Type of file (csv, config, log, etc.)
            description: Optional description of the file
            
        Returns:
            Full path to the registered file
        """
        if not self.current_session:
            raise RuntimeError("No active session. Call start_new_session() first.")
        
        # Determine subdirectory based on file type
        subdir_map = {
            "csv": "csv_data",
            "data": "csv_data", 
            "config": "config",
            "log": "logs",
            "plot": "plots",
            "analysis": "analysis"
        }
        
        subdir = subdir_map.get(file_type, "csv_data")
        full_path = self.get_file_path(filename, subdir)
        
        # Register in session metadata
        self.current_session["files"][filename] = {
            "path": str(full_path),
            "type": file_type,
            "description": description,
            "created": datetime.datetime.now().isoformat()
        }
        
        # Update metadata file
        self._save_session_metadata()
        
        return str(full_path)
    
    def end_session(self, status: str = "completed") -> Dict[str, Any]:
        """
        End the current session and finalize metadata
        
        Args:
            status: Final status of the session (completed, stopped, error)
            
        Returns:
            Final session metadata
        """
        if not self.current_session:
            print("⚠️  No active session to end")
            return {}
        
        # Update session metadata
        end_time = datetime.datetime.now()
        duration = end_time - self.session_start_time
        
        self.current_session.update({
            "end_time": end_time.isoformat(),
            "duration_seconds": duration.total_seconds(),
            "duration_formatted": str(duration).split('.')[0],  # Remove microseconds
            "status": status
        })
        
        # Save final metadata
        self._save_session_metadata()
        
        print(f"📁 Session ended: {self.current_session['session_id']}")
        print(f"   → Duration: {self.current_session['duration_formatted']}")
        print(f"   → Status: {status}")
        print(f"   → Files created: {len(self.current_session['files'])}")
        
        # Return copy before clearing
        final_session = self.current_session.copy()
        
        # Clear current session
        self.current_session = None
        self.current_session_path = None
        self.session_start_time = None
        
        return final_session
    
    def _save_session_metadata(self):
        """Save session metadata to JSON file"""
        if not self.current_session or not self.current_session_path:
            return
        
        metadata_path = self.current_session_path / "session_metadata.json"
        
        try:
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(self.current_session, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️  Error saving session metadata: {e}")
    
    def get_current_session(self) -> Optional[Dict[str, Any]]:
        """Get current session information"""
        return self.current_session.copy() if self.current_session else None
    
    def list_recent_sessions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        List recent test sessions
        
        Args:
            limit: Maximum number of sessions to return
            
        Returns:
            List of session metadata dictionaries
        """
        sessions = []
        
        try:
            # Get all session directories
            session_dirs = [d for d in self.sessions_dir.iterdir() 
                          if d.is_dir() and d.name != "archive"]
            
            # Sort by creation time (newest first)
            session_dirs.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            # Load metadata for each session
            for session_dir in session_dirs[:limit]:
                metadata_path = session_dir / "session_metadata.json"
                
                if metadata_path.exists():
                    try:
                        with open(metadata_path, 'r', encoding='utf-8') as f:
                            metadata = json.load(f)
                            sessions.append(metadata)
                    except Exception as e:
                        print(f"⚠️  Error reading session metadata for {session_dir.name}: {e}")
                else:
                    # Create basic metadata for sessions without metadata file
                    sessions.append({
                        "session_id": session_dir.name,
                        "folder_path": str(session_dir),
                        "status": "unknown",
                        "start_time": datetime.datetime.fromtimestamp(
                            session_dir.stat().st_mtime
                        ).isoformat()
                    })
        
        except Exception as e:
            print(f"⚠️  Error listing sessions: {e}")
        
        return sessions
    
    def archive_old_sessions(self, days_old: int = 30) -> int:
        """
        Archive sessions older than specified days
        
        Args:
            days_old: Move sessions older than this many days to archive
            
        Returns:
            Number of sessions archived
        """
        archived_count = 0
        cutoff_time = datetime.datetime.now() - datetime.timedelta(days=days_old)
        
        try:
            archive_dir = self.sessions_dir / "archive"
            
            for session_dir in self.sessions_dir.iterdir():
                if session_dir.is_dir() and session_dir.name != "archive":
                    # Check if session is old enough
                    if datetime.datetime.fromtimestamp(session_dir.stat().st_mtime) < cutoff_time:
                        # Move to archive
                        archive_path = archive_dir / session_dir.name
                        session_dir.rename(archive_path)
                        archived_count += 1
                        print(f"📦 Archived session: {session_dir.name}")
        
        except Exception as e:
            print(f"⚠️  Error archiving sessions: {e}")
        
        return archived_count


# Global session manager instance
_session_manager = None


def get_session_manager() -> SessionManager:
    """Get the global session manager instance"""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager


def start_test_session(session_name: Optional[str] = None) -> Dict[str, Any]:
    """Convenience function to start a new test session"""
    return get_session_manager().start_new_session(session_name)


def end_test_session(status: str = "completed") -> Dict[str, Any]:
    """Convenience function to end the current test session"""
    return get_session_manager().end_session(status)


def get_session_file_path(filename: str, file_type: str = "csv") -> str:
    """Convenience function to get a file path in the current session"""
    manager = get_session_manager()
    
    # Determine subdirectory
    subdir_map = {
        "csv": "csv_data",
        "data": "csv_data",
        "config": "config", 
        "log": "logs",
        "plot": "plots",
        "analysis": "analysis"
    }
    
    subdir = subdir_map.get(file_type, "csv_data")
    return str(manager.get_file_path(filename, subdir)) 
"""
Standardized logging utility for AWE Test Rig
Provides consistent message formatting across all components
"""

import time
from datetime import datetime
from typing import Optional, List


class TestRigLogger:
    """Standardized logger for test rig operations"""
    
    # ANSI color codes for terminal output
    COLORS = {
        'INFO': '\033[94m',      # Blue
        'SUCCESS': '\033[92m',   # Green  
        'WARNING': '\033[93m',   # Yellow
        'ERROR': '\033[91m',     # Red
        'RESET': '\033[0m'       # Reset
    }
    
    @staticmethod
    def _get_timestamp() -> str:
        """Get formatted timestamp"""
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    @staticmethod
    def _format_message(level: str, component: str, message: str, color: bool = True) -> str:
        """Format message according to standard format"""
        timestamp = TestRigLogger._get_timestamp()
        
        # Pad level to 8 characters for alignment
        level_padded = f"{level:<8}"
        
        # Pad component to 12 characters for alignment  
        component_padded = f"[{component}]"
        component_formatted = f"{component_padded:<14}"
        
        if color and level in TestRigLogger.COLORS:
            color_code = TestRigLogger.COLORS[level]
            reset_code = TestRigLogger.COLORS['RESET']
            formatted_msg = f"[{timestamp}] {color_code}{level_padded}{reset_code} {component_formatted} - {message}"
        else:
            formatted_msg = f"[{timestamp}] {level_padded} {component_formatted} - {message}"
        
        return formatted_msg
    
    @staticmethod
    def info(component: str, message: str, sublines: Optional[List[str]] = None):
        """Log INFO level message"""
        print(TestRigLogger._format_message("INFO", component, message))
        if sublines:
            for subline in sublines:
                print(f"    {subline}")
    
    @staticmethod
    def success(component: str, message: str, sublines: Optional[List[str]] = None):
        """Log SUCCESS level message"""
        print(TestRigLogger._format_message("SUCCESS", component, message))
        if sublines:
            for subline in sublines:
                print(f"    {subline}")
    
    @staticmethod
    def warning(component: str, message: str, sublines: Optional[List[str]] = None):
        """Log WARNING level message"""
        print(TestRigLogger._format_message("WARNING", component, message))
        if sublines:
            for subline in sublines:
                print(f"    {subline}")
    
    @staticmethod
    def error(component: str, message: str, sublines: Optional[List[str]] = None):
        """Log ERROR level message"""
        print(TestRigLogger._format_message("ERROR", component, message))
        if sublines:
            for subline in sublines:
                print(f"    {subline}")


# Convenience instance for easy importing
log = TestRigLogger() 
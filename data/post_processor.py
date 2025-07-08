"""
Data Post-Processing Script for AWE Test Rig
Generates analysis plots from CSV data files
Can run independently or as part of the test application
"""

import os
import sys
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import json
import argparse
from datetime import datetime
import numpy as np

# Add parent directory to path for imports when running standalone
if __name__ == "__main__":
    sys.path.append(str(Path(__file__).parent.parent))

from core.state import get_global_state
from data.session_manager import get_session_manager


class DataPostProcessor:
    """Post-processing engine for AWE test rig data analysis"""
    
    def __init__(self, session_folder: str, active_channels: Optional[Dict[str, Any]] = None):
        """
        Initialize post-processor
        
        Args:
            session_folder: Path to session folder containing CSV data
            active_channels: Dictionary of active channels during test (optional)
        """
        self.session_folder = Path(session_folder)
        self.csv_folder = self.session_folder / "csv_data"
        self.plots_folder = self.session_folder / "plots"
        
        # Ensure plots folder exists
        self.plots_folder.mkdir(exist_ok=True)
        
        # Active channels configuration
        self.active_channels = active_channels or self._load_channel_config()
        
        # Plot configuration matching UI settings
        self.plot_config = {
            'pressure': {
                'y_limits': (0, 1),  # 0-1 normalized
                'title': 'Pressure vs Time',
                'ylabel': 'Normalized Pressure',
                'channels': ['h2_header', 'o2_header', 'post_ms', 'pre_ms', 'h2_bop']
            },
            'gas_purity': {
                'y_limits': (0, 100),  # 0-100%
                'title': 'Gas Purity vs Time', 
                'ylabel': 'Gas Concentration (%)',
                'channels': ['bga1_pct', 'bga2_pct', 'bga3_pct']
            },
            'temperature': {
                'y_limits': (0, 100),  # 0-100°C
                'title': 'Temperatures vs Time',
                'ylabel': 'Temperature (°C)',
                'channels': ['tc01', 'tc02', 'tc03', 'tc04', 'tc05', 'tc06', 'tc07', 'tc08']
            },
            'cell_voltage': {
                'y_limits': (0, 5),  # 0-5V
                'title': 'Cell Voltages vs Time',
                'ylabel': 'Voltage (V)',
                'channels': [f'cell_{i+1:03d}_v' for i in range(120)]  # All 120 cells
            },
            'current': {
                'y_limits': (0, 150),  # 0-150A
                'title': 'Current vs Time',
                'ylabel': 'Current (A)',
                'channels': ['current']
            },
            'flowrate': {
                'y_limits': (0, 50),  # 0-50 SLM
                'title': 'Mass Flowrate vs Time',
                'ylabel': 'Flowrate (SLM)',
                'channels': ['flowrate']
            }
        }
        
        # Load CSV data
        self.data = {}
        self.max_time = 0
        
    def _load_channel_config(self) -> Dict[str, Any]:
        """Load active channel configuration from session metadata"""
        try:
            metadata_file = self.session_folder / "session_metadata.json"
            if metadata_file.exists():
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
                    return metadata.get('active_channels', {})
        except Exception as e:
            print(f"⚠️  Could not load channel config: {e}")
        
        # Default active channels if not found
        return {
            'pressure': [0, 1, 2, 3, 4],  # All pressure channels
            'gas': [0, 1, 2],  # All BGA channels
            'temperature': [0, 1, 2, 3, 4, 5, 6, 7],  # All TC channels
            'voltage': list(range(120)),  # All voltage channels
            'current': [0],  # Current channel
            'flowrate': [0]  # Flowrate channel
        }
    
    def load_csv_data(self) -> bool:
        """Load all CSV data files"""
        print(f"📊 Loading CSV data from {self.csv_folder}")
        
        # Expected CSV files
        csv_files = {
            'sensors': 'sensors.csv',
            'gas_analysis': 'gas_analysis.csv', 
            'cell_voltages': 'cell_voltages.csv',
            'actuators': 'actuators.csv'
        }
        
        # Find actual CSV files (they have timestamps in names)
        actual_files = {}
        for file_type, expected_suffix in csv_files.items():
            for csv_file in self.csv_folder.glob(f"*_{expected_suffix}"):
                actual_files[file_type] = csv_file
                break
        
        if not actual_files:
            print(f"❌ No CSV files found in {self.csv_folder}")
            return False
        
        # Load each CSV file
        for file_type, csv_path in actual_files.items():
            try:
                print(f"   → Loading {file_type}: {csv_path.name}")
                df = pd.read_csv(csv_path)
                
                if df.empty:
                    print(f"   ⚠️  {file_type} is empty")
                    continue
                
                self.data[file_type] = df
                
                # Track maximum time for consistent x-axis
                if 'elapsed_seconds' in df.columns:
                    max_time_in_file = df['elapsed_seconds'].max()
                    self.max_time = max(self.max_time, max_time_in_file)
                
                print(f"   ✅ Loaded {len(df)} rows from {file_type}")
                
            except Exception as e:
                print(f"   ❌ Error loading {file_type}: {e}")
                continue
        
        print(f"✅ Data loaded successfully, max time: {self.max_time:.1f}s")
        return len(self.data) > 0
    
    def generate_pressure_plot(self) -> bool:
        """Generate pressure vs time plot"""
        if 'sensors' not in self.data:
            print("❌ No sensor data available for pressure plot")
            return False
        
        try:
            print("📊 Generating pressure plot...")
            
            df = self.data['sensors']
            config = self.plot_config['pressure']
            
            fig, ax = plt.subplots(figsize=(10, 6))
            
            # Plot pressure channels that are active
            pressure_columns = ['h2_header', 'o2_header', 'post_ms', 'pre_ms', 'h2_bop']
            colors = ['blue', 'red', 'green', 'orange', 'purple']
            active_pressure = self.active_channels.get('pressure', [0, 1, 2, 3, 4])
            
            for i, col in enumerate(pressure_columns):
                if i in active_pressure and col in df.columns:
                    ax.plot(df['elapsed_seconds'], df[col], 
                           color=colors[i], linewidth=2, label=col.replace('_', ' ').title())
            
            ax.set_xlim(0, max(self.max_time * 1.1, 120))
            ax.set_ylim(config['y_limits'])
            ax.set_xlabel('Time (s)')
            ax.set_ylabel(config['ylabel'])
            ax.set_title(config['title'])
            ax.grid(True, alpha=0.3)
            ax.legend()
            
            # Save as JPEG
            output_path = self.plots_folder / "pressure.jpg"
            plt.savefig(output_path, format='jpeg', dpi=300, bbox_inches='tight')
            plt.close()
            
            print(f"✅ Pressure plot saved: {output_path}")
            return True
            
        except Exception as e:
            print(f"❌ Error generating pressure plot: {e}")
            return False
    
    def generate_gas_purity_plot(self) -> bool:
        """Generate gas purity vs time plot"""
        if 'gas_analysis' not in self.data:
            print("❌ No gas analysis data available for purity plot")
            return False
        
        try:
            print("📊 Generating gas purity plot...")
            
            df = self.data['gas_analysis']
            config = self.plot_config['gas_purity']
            
            fig, ax = plt.subplots(figsize=(10, 6))
            
            # Plot BGA channels that are active
            gas_columns = ['bga1_pct', 'bga2_pct', 'bga3_pct']
            colors = ['blue', 'red', 'green']
            active_gas = self.active_channels.get('gas', [0, 1, 2])
            
            for i, col in enumerate(gas_columns):
                if i in active_gas and col in df.columns:
                    ax.plot(df['elapsed_seconds'], df[col], 
                           color=colors[i], linewidth=2, label=f'BGA{i+1}')
            
            ax.set_xlim(0, max(self.max_time * 1.1, 120))
            ax.set_ylim(config['y_limits'])
            ax.set_xlabel('Time (s)')
            ax.set_ylabel(config['ylabel'])
            ax.set_title(config['title'])
            ax.grid(True, alpha=0.3)
            ax.legend()
            
            # Save as JPEG
            output_path = self.plots_folder / "gas_purity.jpg"
            plt.savefig(output_path, format='jpeg', dpi=300, bbox_inches='tight')
            plt.close()
            
            print(f"✅ Gas purity plot saved: {output_path}")
            return True
            
        except Exception as e:
            print(f"❌ Error generating gas purity plot: {e}")
            return False
    
    def generate_temperature_plot(self) -> bool:
        """Generate temperature vs time plot"""
        if 'sensors' not in self.data:
            print("❌ No sensor data available for temperature plot")
            return False
        
        try:
            print("📊 Generating temperature plot...")
            
            df = self.data['sensors']
            config = self.plot_config['temperature']
            
            fig, ax = plt.subplots(figsize=(10, 6))
            
            # Plot temperature channels that are active
            temp_columns = ['tc01', 'tc02', 'tc03', 'tc04', 'tc05', 'tc06', 'tc07', 'tc08']
            colors = plt.cm.tab10(np.linspace(0, 1, 8))
            active_temp = self.active_channels.get('temperature', list(range(8)))
            
            for i, col in enumerate(temp_columns):
                if i in active_temp and col in df.columns:
                    # Different line styles for different channel groups
                    linestyle = '-' if i < 4 else '--'
                    linewidth = 2 if i < 4 else 1.5
                    
                    ax.plot(df['elapsed_seconds'], df[col], 
                           color=colors[i], linewidth=linewidth, linestyle=linestyle,
                           label=col.upper())
            
            ax.set_xlim(0, max(self.max_time * 1.1, 120))
            ax.set_ylim(config['y_limits'])
            ax.set_xlabel('Time (s)')
            ax.set_ylabel(config['ylabel'])
            ax.set_title(config['title'])
            ax.grid(True, alpha=0.3)
            ax.legend()
            
            # Save as JPEG
            output_path = self.plots_folder / "temperature.jpg"
            plt.savefig(output_path, format='jpeg', dpi=300, bbox_inches='tight')
            plt.close()
            
            print(f"✅ Temperature plot saved: {output_path}")
            return True
            
        except Exception as e:
            print(f"❌ Error generating temperature plot: {e}")
            return False
    
    def generate_cell_voltage_plot(self) -> bool:
        """Generate cell voltage vs time plot"""
        if 'cell_voltages' not in self.data:
            print("❌ No cell voltage data available for voltage plot")
            return False
        
        try:
            print("📊 Generating cell voltage plot...")
            
            df = self.data['cell_voltages']
            config = self.plot_config['cell_voltage']
            
            fig, ax = plt.subplots(figsize=(10, 6))
            
            # Get active voltage channels
            active_voltage = self.active_channels.get('voltage', list(range(120)))
            
            # Limit to reasonable number of channels for visibility
            if len(active_voltage) > 20:
                print(f"   → Limiting to first 20 voltage channels for plot clarity")
                active_voltage = active_voltage[:20]
            
            colors = plt.cm.tab20(np.linspace(0, 1, len(active_voltage)))
            
            for i, channel_idx in enumerate(active_voltage):
                col_name = f'cell_{channel_idx+1:03d}_v'
                if col_name in df.columns:
                    ax.plot(df['elapsed_seconds'], df[col_name], 
                           color=colors[i], linewidth=1.5, 
                           label=f'Cell {channel_idx+1}')
            
            ax.set_xlim(0, max(self.max_time * 1.1, 120))
            ax.set_ylim(config['y_limits'])
            ax.set_xlabel('Time (s)')
            ax.set_ylabel(config['ylabel'])
            ax.set_title(config['title'])
            ax.grid(True, alpha=0.3)
            
            # Only show legend if reasonable number of channels
            if len(active_voltage) <= 10:
                ax.legend()
            
            # Save as JPEG
            output_path = self.plots_folder / "cell_voltage.jpg"
            plt.savefig(output_path, format='jpeg', dpi=300, bbox_inches='tight')
            plt.close()
            
            print(f"✅ Cell voltage plot saved: {output_path}")
            return True
            
        except Exception as e:
            print(f"❌ Error generating cell voltage plot: {e}")
            return False
    
    def generate_current_plot(self) -> bool:
        """Generate current vs time plot"""
        if 'sensors' not in self.data:
            print("❌ No sensor data available for current plot")
            return False
        
        try:
            print("📊 Generating current plot...")
            
            df = self.data['sensors']
            config = self.plot_config['current']
            
            fig, ax = plt.subplots(figsize=(10, 6))
            
            # Plot current if active
            active_current = self.active_channels.get('current', [0])
            
            if 0 in active_current and 'current' in df.columns:
                ax.plot(df['elapsed_seconds'], df['current'], 
                       color='blue', linewidth=2, label='Stack Current')
            
            ax.set_xlim(0, max(self.max_time * 1.1, 120))
            ax.set_ylim(config['y_limits'])
            ax.set_xlabel('Time (s)')
            ax.set_ylabel(config['ylabel'])
            ax.set_title(config['title'])
            ax.grid(True, alpha=0.3)
            ax.legend()
            
            # Save as JPEG
            output_path = self.plots_folder / "current.jpg"
            plt.savefig(output_path, format='jpeg', dpi=300, bbox_inches='tight')
            plt.close()
            
            print(f"✅ Current plot saved: {output_path}")
            return True
            
        except Exception as e:
            print(f"❌ Error generating current plot: {e}")
            return False
    
    def generate_flowrate_plot(self) -> bool:
        """Generate flowrate vs time plot"""
        if 'sensors' not in self.data:
            print("❌ No sensor data available for flowrate plot")
            return False
        
        try:
            print("📊 Generating flowrate plot...")
            
            df = self.data['sensors']
            config = self.plot_config['flowrate']
            
            fig, ax = plt.subplots(figsize=(10, 6))
            
            # Plot flowrate if active
            active_flowrate = self.active_channels.get('flowrate', [0])
            
            if 0 in active_flowrate and 'flowrate' in df.columns:
                ax.plot(df['elapsed_seconds'], df['flowrate'], 
                       color='red', linewidth=2, label='Mass Flowrate')
            
            ax.set_xlim(0, max(self.max_time * 1.1, 120))
            ax.set_ylim(config['y_limits'])
            ax.set_xlabel('Time (s)')
            ax.set_ylabel(config['ylabel'])
            ax.set_title(config['title'])
            ax.grid(True, alpha=0.3)
            ax.legend()
            
            # Save as JPEG
            output_path = self.plots_folder / "flowrate.jpg"
            plt.savefig(output_path, format='jpeg', dpi=300, bbox_inches='tight')
            plt.close()
            
            print(f"✅ Flowrate plot saved: {output_path}")
            return True
            
        except Exception as e:
            print(f"❌ Error generating flowrate plot: {e}")
            return False
    
    def process_session(self) -> bool:
        """Process complete session data and generate all plots"""
        print(f"🔄 Starting post-processing for session: {self.session_folder.name}")
        
        # Load CSV data
        if not self.load_csv_data():
            print("❌ Failed to load CSV data")
            return False
        
        # Generate all plots
        plots_generated = 0
        
        if self.generate_pressure_plot():
            plots_generated += 1
            
        if self.generate_gas_purity_plot():
            plots_generated += 1
            
        if self.generate_temperature_plot():
            plots_generated += 1
            
        if self.generate_cell_voltage_plot():
            plots_generated += 1
            
        if self.generate_current_plot():
            plots_generated += 1
            
        if self.generate_flowrate_plot():
            plots_generated += 1
        
        print(f"✅ Post-processing complete: {plots_generated}/6 plots generated")
        print(f"   → Plots saved to: {self.plots_folder}")
        
        return plots_generated > 0


def process_session_data(session_folder: str, active_channels: Optional[Dict[str, Any]] = None) -> bool:
    """
    Convenience function to process session data
    
    Args:
        session_folder: Path to session folder
        active_channels: Dictionary of active channels (optional)
    
    Returns:
        True if processing succeeded
    """
    processor = DataPostProcessor(session_folder, active_channels)
    return processor.process_session()


def main():
    """Main function for standalone execution"""
    parser = argparse.ArgumentParser(description='AWE Test Rig Data Post-Processor')
    parser.add_argument('session_folder', help='Path to session folder containing CSV data')
    parser.add_argument('--channels', help='JSON file with active channel configuration (optional)')
    
    args = parser.parse_args()
    
    # Validate session folder
    session_path = Path(args.session_folder)
    if not session_path.exists():
        print(f"❌ Session folder not found: {session_path}")
        return 1
    
    csv_folder = session_path / "csv_data"
    if not csv_folder.exists():
        print(f"❌ CSV data folder not found: {csv_folder}")
        return 1
    
    # Load active channels if provided
    active_channels = None
    if args.channels:
        try:
            with open(args.channels, 'r') as f:
                active_channels = json.load(f)
        except Exception as e:
            print(f"⚠️  Could not load channels file: {e}")
    
    print("=" * 60)
    print("AWE Test Rig Data Post-Processor")
    print("=" * 60)
    print(f"Session folder: {session_path}")
    print(f"CSV data folder: {csv_folder}")
    
    # Process the session
    success = process_session_data(str(session_path), active_channels)
    
    if success:
        print("=" * 60)
        print("✅ Post-processing completed successfully!")
        return 0
    else:
        print("=" * 60)
        print("❌ Post-processing failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main()) 
#!/usr/bin/env python3
"""
Test script for standalone post-processor usage
Demonstrates how to run the post-processor independently on existing session data
"""

import sys
from pathlib import Path
from data.post_processor import process_session_data

def main():
    """Test standalone post-processor functionality"""
    
    print("=" * 60)
    print("AWE Test Rig Post-Processor - Standalone Test")
    print("=" * 60)
    
    if len(sys.argv) < 2:
        print("Usage: python test_post_processor.py <session_folder_path>")
        print("\nExample:")
        print("  python test_post_processor.py data/sessions/2025-07-01_12-25-53_UI_Test_Session")
        print("\nThis script will:")
        print("  1. Load CSV data from the session folder")
        print("  2. Generate 5 plots: pressure, gas purity, temperature, cell voltage, current")
        print("  3. Save plots as JPEG files in the session's plots folder")
        return 1
    
    session_folder = Path(sys.argv[1])
    
    # Validate session folder
    if not session_folder.exists():
        print(f"❌ Session folder not found: {session_folder}")
        return 1
    
    csv_folder = session_folder / "csv_data"
    if not csv_folder.exists():
        print(f"❌ CSV data folder not found: {csv_folder}")
        return 1
    
    print(f"📁 Processing session: {session_folder.name}")
    print(f"📊 CSV data location: {csv_folder}")
    
    # Check for existing plots folder
    plots_folder = session_folder / "plots"
    if plots_folder.exists():
        existing_plots = list(plots_folder.glob("*.jpg"))
        if existing_plots:
            print(f"⚠️  Found {len(existing_plots)} existing plot files:")
            for plot in existing_plots:
                print(f"   → {plot.name}")
            print("   → These will be overwritten")
    
    # Run post-processing
    print("\n🔄 Starting post-processing...")
    success = process_session_data(str(session_folder))
    
    if success:
        print("\n✅ Post-processing completed successfully!")
        
        # List generated plots
        plots_folder = session_folder / "plots"
        if plots_folder.exists():
            plot_files = list(plots_folder.glob("*.jpg"))
            if plot_files:
                print(f"\n📊 Generated {len(plot_files)} plot files:")
                for plot in sorted(plot_files):
                    print(f"   → {plot.name}")
                print(f"\nPlots saved to: {plots_folder}")
            else:
                print("\n⚠️  No plot files found after processing")
        
        return 0
    else:
        print("\n❌ Post-processing failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 
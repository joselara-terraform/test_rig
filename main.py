#!/usr/bin/env python3
"""
AWE Electrolyzer Test Rig - Main Entry Point
"""

import tkinter as tk
from ui.dashboard import Dashboard


def main():
    """Launch the AWE test rig dashboard"""
    root = tk.Tk()
    dashboard = Dashboard(root)
    root.mainloop()


if __name__ == "__main__":
    main() 
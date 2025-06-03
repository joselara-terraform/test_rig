#!/usr/bin/env python3
"""
AWE Electrolyzer Test Rig - Main Entry Point
"""

import tkinter as tk
from tkinter import ttk


def main():
    """Launch the AWE test rig dashboard"""
    root = tk.Tk()
    root.title("AWE Electrolyzer Test Rig")
    root.geometry("800x600")
    
    # Placeholder dashboard content
    label = ttk.Label(root, text="Hello, AWE", font=("Arial", 24))
    label.pack(expand=True)
    
    root.mainloop()


if __name__ == "__main__":
    main() 
import customtkinter as ctk
from utils.config_manager import ConfigManager
from tkinter import ttk, messagebox
import os
import tkinter as tk
from PIL import Image

class EditDayWindow(ctk.CTkToplevel):
    def __init__(self, parent, config, symbol, day, on_close=None):
        super().__init__(parent)
        
        self.config = config
        self.symbol = symbol
        self.day = day
        self.on_close = on_close
        self.parent = parent
        
        # Configure theme colors
        self._button_color = "#4d4d4d"  # Darker gray for button
        self._button_hover_color = "#666666"  # Medium gray for hover
        self._checkbox_color = "#666666"
        self._entry_color = "#343638"  # Default entry background color
        
        # Configure component styles
        self._checkbox_border_width = 2
        self._checkbox_corner_radius = 4
        self._button_border_width = 0
        self._button_corner_radius = 4
        
        # Window setup
        self.title(f"Edit {day} Schedule - {symbol}")
        
        # Try to inherit icon from parent first
        try:
            parent_icon = self.parent.wm_iconbitmap()
            if parent_icon:
                self.wm_iconbitmap(parent_icon)
        except Exception as e:
            print(f"Could not inherit parent icon: {str(e)}")
        
        # Bind to Map event for icon setting
        self.bind("<Map>", self._on_map)
        self._icon_set = False
        
        # Make window modal
        self.transient(parent)
        self.grab_set()
        self.resizable(False, False)  # Make window unresizable
        
        # Set window size and position
        window_width = 400
        window_height = 230
        
        # Position window in center of parent
        self.withdraw()  # Hide window during positioning
        self.update_idletasks()  # Update window size
        
        parent_x = self.parent.winfo_x()
        parent_y = self.parent.winfo_y()
        parent_width = self.parent.winfo_width()
        parent_height = self.parent.winfo_height()
        
        x = parent_x + (parent_width - window_width) // 2
        y = parent_y + (parent_height - window_height) // 2
        
        self.geometry(f"{window_width}x{window_height}+{x}+{y}")
        self.deiconify()  # Show window at calculated position
        
        # Time settings frame
        self.time_frame = ctk.CTkFrame(self)
        self.time_frame.pack(fill="x", padx=10, pady=10)
        
        # Pause Start Time
        self.pause_start_label = ctk.CTkLabel(self.time_frame, text="Pause at:", anchor="w", font=("", 12))
        self.pause_start_label.grid(row=0, column=0, padx=10, pady=(5,0), sticky="w")
        
        self.pause_start_entry = ctk.CTkEntry(
            self.time_frame,
            placeholder_text="21:30",
            fg_color=self._entry_color
        )
        self.pause_start_entry.grid(row=1, column=0, padx=10, pady=(0,5), sticky="ew")
        
        # Pause Duration
        self.pause_duration_label = ctk.CTkLabel(self.time_frame, text="Pause duration:", anchor="w", font=("", 12))
        self.pause_duration_label.grid(row=2, column=0, padx=10, pady=(5,0), sticky="w")
        
        self.pause_duration_entry = ctk.CTkEntry(
            self.time_frame,
            placeholder_text="03:00",
            fg_color=self._entry_color
        )
        self.pause_duration_entry.grid(row=3, column=0, padx=10, pady=(0,10), sticky="ew")
        
        # Close Positions Checkbox
        self.close_positions_var = ctk.BooleanVar()
        self.close_positions_checkbox = ctk.CTkCheckBox(
            self.time_frame,
            text="Close Positions on Pause",
            variable=self.close_positions_var,
            fg_color=self._checkbox_color,
            hover_color=self._button_hover_color,
            border_width=self._checkbox_border_width,
            corner_radius=self._checkbox_corner_radius
        )
        self.close_positions_checkbox.grid(row=4, column=0, padx=10, pady=(5,10), sticky="w")
        
        # Configure grid for time frame
        self.time_frame.grid_columnconfigure(0, weight=1)
        
        # Buttons frame (transparent)
        self.button_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.button_frame.pack(fill="x", padx=10, pady=(0,10))
        
        # Load button images
        self.save_icon = ctk.CTkImage(
            light_image=Image.open(os.path.join("assets", "save_666666.png")),
            dark_image=Image.open(os.path.join("assets", "save_666666.png")),
            size=(20, 20)
        )
        self.save_hover_icon = ctk.CTkImage(
            light_image=Image.open(os.path.join("assets", "save.png")),
            dark_image=Image.open(os.path.join("assets", "save.png")),
            size=(20, 20)
        )
        self.close_icon = ctk.CTkImage(
            light_image=Image.open(os.path.join("assets", "close_666666.png")),
            dark_image=Image.open(os.path.join("assets", "close_666666.png")),
            size=(20, 20)
        )
        self.close_hover_icon = ctk.CTkImage(
            light_image=Image.open(os.path.join("assets", "close.png")),
            dark_image=Image.open(os.path.join("assets", "close.png")),
            size=(20, 20)
        )
        
        # Save button
        self.save_button = ctk.CTkButton(
            self.button_frame,
            text="",
            image=self.save_icon,
            command=self._save_changes,
            width=32,
            height=32,
            fg_color="transparent",
            hover_color=self._button_hover_color,
            corner_radius=8
        )
        self.save_button.pack(side="right", padx=5)
        
        # Cancel button
        self.cancel_button = ctk.CTkButton(
            self.button_frame,
            text="",
            image=self.close_icon,
            command=self.destroy,
            width=32,
            height=32,
            fg_color="transparent",
            hover_color=self._button_hover_color,
            corner_radius=8
        )
        self.cancel_button.pack(side="right", padx=5)
        
        # Bind hover events
        self.save_button.bind("<Enter>", lambda e: self.save_button.configure(image=self.save_hover_icon))
        self.save_button.bind("<Leave>", lambda e: self.save_button.configure(image=self.save_icon))
        self.cancel_button.bind("<Enter>", lambda e: self.cancel_button.configure(image=self.close_hover_icon))
        self.cancel_button.bind("<Leave>", lambda e: self.cancel_button.configure(image=self.close_icon))
        
        # Load current settings
        self._load_current_settings()
        
    def _load_current_settings(self):
        """Load the current settings for this day from the config"""
        for rule in self.config.get("alert_rules", []):
            if rule.get("symbol") == self.symbol:
                schedule = rule.get("schedule", [])
                for schedule_item in schedule:
                    if schedule_item.get("day") == self.day:
                        self.pause_start_entry.insert(0, schedule_item.get("pause_start", "21:30"))
                        self.pause_duration_entry.insert(0, schedule_item.get("pause_duration", "03:00"))
                        self.close_positions_var.set(schedule_item.get("close_positions_on_pause", False))
                        break
                break
    
    def _validate_time_format(self, time_str):
        """Validate if time string is in format hh:mm or hh:mm:ss and doesn't exceed 23:59:59"""
        parts = time_str.split(':')
        if len(parts) not in [2, 3]:  # Must have 2 or 3 parts
            return False
            
        try:
            # Check hours (00-23)
            hours = int(parts[0])
            if not (0 <= hours <= 23):
                return False
                
            # Check minutes (00-59)
            minutes = int(parts[1])
            if not (0 <= minutes <= 59):
                return False
                
            # For HH:MM format, ensure it's not more than 23:59
            if len(parts) == 2 and (hours == 23 and minutes > 59):
                return False
                
            # Check seconds if provided (00-59)
            if len(parts) == 3:
                seconds = int(parts[2])
                if not (0 <= seconds <= 59):
                    return False
                # For HH:MM:SS format, ensure it's not more than 23:59:59
                if hours == 23 and minutes == 59 and seconds > 59:
                    return False
                    
            return True
        except ValueError:
            return False

    def _save_changes(self):
        """Save the changes made to this day's schedule"""
        # Get values
        pause_start = self.pause_start_entry.get().strip()
        pause_duration = self.pause_duration_entry.get().strip()
        
        # Validate time formats
        if not self._validate_time_format(pause_start):
            messagebox.showerror("Invalid Time Format", 
                "Pause start time must be in format hh:mm or hh:mm:ss\n"
                "Example: 21:30 or 21:30:00\n"
                "Maximum value is 23:59 or 23:59:59")
            return
            
        if not self._validate_time_format(pause_duration):
            messagebox.showerror("Invalid Time Format", 
                "Pause duration must be in format hh:mm or hh:mm:ss\n"
                "Example: 03:00 or 03:00:00\n"
                "Maximum value is 23:59 or 23:59:59")
            return
        
        # If validation passes, save the changes
        for rule in self.config.get("alert_rules", []):
            if rule.get("symbol") == self.symbol:
                schedule = rule.get("schedule", [])
                for schedule_item in schedule:
                    if schedule_item.get("day") == self.day:
                        schedule_item["pause_start"] = pause_start
                        schedule_item["pause_duration"] = pause_duration
                        schedule_item["close_positions_on_pause"] = self.close_positions_var.get()
                        break
                break
        
        # Save config
        ConfigManager.save_config(self.config)
        
        # Call on_close callback if provided
        if self.on_close:
            self.on_close()
            
        self.destroy()
        
    def _on_map(self, event):
        """Called when window is mapped to screen"""
        if not self._icon_set:
            self.after(200, self._set_icon)  # Set icon with delay
            self._icon_set = True
            
    def _set_icon(self):
        """Set window icon after window is fully initialized"""
        icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "logo.ico")
        try:
            self.iconbitmap(icon_path)
        except Exception as e:
            print(f"Could not set icon: {str(e)}")

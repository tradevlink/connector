import customtkinter as ctk
from utils.config_manager import ConfigManager
from tkinter import messagebox, ttk
import os
from gui.edit_day import EditDayWindow

class EditRuleWindow(ctk.CTkToplevel):
    def __init__(self, parent, config, symbol=None, on_close=None):
        """Initialize EditRuleWindow."""
        super().__init__(parent)
        
        # Store references
        self.parent = parent
        self.symbol = symbol
        self.config = config
        self.original_symbol = symbol  # Store original symbol for comparison
        self.on_close = on_close
        
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
        
        # Configure window
        self.title("Edit Rule")
        self.resizable(False, False)
        
        # Set initial window size based on schedule state
        initial_height = 350
        if symbol:
            alert_rules = self.config.get("alert_rules", [])
            for rule in alert_rules:
                if rule["symbol"] == symbol and rule.get("active_schedule", 0):
                    initial_height = 550
                    break
        
        self.geometry(f"500x{initial_height}")
        
        # Configure theme colors
        self._button_color = "#4d4d4d"
        self._button_hover_color = "#666666"
        self._checkbox_color = "#666666"
        self._entry_color = "#343638"
        
        # Configure component styles
        self._checkbox_border_width = 2
        self._checkbox_corner_radius = 4
        self._button_border_width = 0
        self._button_corner_radius = 4
        
        # Configure grid layout
        self.grid_columnconfigure(0, weight=1)  # Make column expandable
        
        # Symbol Frame
        symbol_frame = ctk.CTkFrame(self)
        symbol_frame.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="ew")
        symbol_frame.grid_columnconfigure(0, weight=1)
        
        symbol_label = ctk.CTkLabel(symbol_frame, text="Symbol", anchor="w", font=("", 12))
        symbol_label.grid(row=0, column=0, padx=10, pady=(5,0), sticky="w")
        
        self.symbol_entry = ctk.CTkEntry(
            symbol_frame,
            placeholder_text="Enter symbol",
            fg_color=self._entry_color
        )
        self.symbol_entry.grid(row=1, column=0, padx=10, pady=(0,5), sticky="ew")
        if symbol:
            self.symbol_entry.insert(0, symbol)
        self.symbol_entry.bind("<KeyRelease>", self._on_symbol_changed)
        
        # Volume Frame
        volume_frame = ctk.CTkFrame(self)
        volume_frame.grid(row=1, column=0, padx=10, pady=5, sticky="ew")
        volume_frame.grid_columnconfigure(0, weight=1)
        
        volume_label = ctk.CTkLabel(volume_frame, text="Volume", anchor="w", font=("", 12))
        volume_label.grid(row=0, column=0, padx=10, pady=(5,0), sticky="w")
        
        volume_controls = ctk.CTkFrame(volume_frame, fg_color="transparent")
        volume_controls.grid(row=1, column=0, sticky="ew")
        volume_controls.grid_columnconfigure(0, weight=1)
        
        self.volume_entry = ctk.CTkEntry(
            volume_controls,
            placeholder_text="0.01",
            fg_color=self._entry_color
        )
        self.volume_entry.grid(row=0, column=0, padx=10, pady=(0,5), sticky="ew")
        
        self.volume_from_alert = ctk.CTkCheckBox(
            volume_controls,
            text="Volume from Alert",
            fg_color=self._checkbox_color,
            hover_color=self._button_hover_color,
            border_width=self._checkbox_border_width,
            corner_radius=self._checkbox_corner_radius
        )
        self.volume_from_alert.grid(row=0, column=1, padx=10, pady=(0,5))
        
        # Values Frame
        values_frame = ctk.CTkFrame(self)
        values_frame.grid(row=2, column=0, padx=10, pady=5, sticky="ew")
        values_frame.grid_columnconfigure(0, weight=1)
        values_frame.grid_columnconfigure(1, weight=1)
        values_frame.grid_columnconfigure(2, weight=1)
        
        # Take Profit
        tp_label = ctk.CTkLabel(values_frame, text="Take Profit", anchor="w", font=("", 12))
        tp_label.grid(row=0, column=0, padx=10, pady=(5,0), sticky="w")
        
        self.tp_entry = ctk.CTkEntry(
            values_frame,
            placeholder_text="0.0",
            fg_color=self._entry_color
        )
        self.tp_entry.grid(row=1, column=0, padx=10, pady=(0,5), sticky="ew")
        
        # Stop Loss
        sl_label = ctk.CTkLabel(values_frame, text="Stop Loss", anchor="w", font=("", 12))
        sl_label.grid(row=0, column=1, padx=10, pady=(5,0), sticky="w")
        
        self.sl_entry = ctk.CTkEntry(
            values_frame,
            placeholder_text="0.0",
            fg_color=self._entry_color
        )
        self.sl_entry.grid(row=1, column=1, padx=10, pady=(0,5), sticky="ew")
        
        # Profit Trailing Stop
        pts_label = ctk.CTkLabel(values_frame, text="Profit Trailing Stop", anchor="w", font=("", 12))
        pts_label.grid(row=0, column=2, padx=10, pady=(5,0), sticky="w")
        
        self.pts_entry = ctk.CTkEntry(
            values_frame,
            placeholder_text="0.0",
            fg_color=self._entry_color
        )
        self.pts_entry.grid(row=1, column=2, padx=10, pady=(0,5), sticky="ew")
        
        # Close Positions Frame
        close_frame = ctk.CTkFrame(self)
        close_frame.grid(row=3, column=0, padx=10, pady=5, sticky="ew")
        close_frame.grid_columnconfigure(0, weight=1)
        
        self.close_positions = ctk.CTkCheckBox(
            close_frame,
            text="Close Positions on Entry",
            fg_color=self._checkbox_color,
            hover_color=self._button_hover_color,
            border_width=self._checkbox_border_width,
            corner_radius=self._checkbox_corner_radius
        )
        self.close_positions.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        
        # Schedule frame
        self.schedule_frame = ctk.CTkFrame(self)
        self.schedule_frame.grid(row=4, column=0, columnspan=2, padx=10, pady=(5, 10), sticky="nsew")
        self.schedule_frame.grid_columnconfigure(0, weight=1)  # Make frame expand horizontally
        
        # Schedule checkbox
        self.active_schedule_var = ctk.IntVar()
        self.active_schedule = ctk.CTkCheckBox(
            self.schedule_frame,
            text="Active Schedule",
            command=self._on_schedule_changed,
            variable=self.active_schedule_var,
            fg_color=self._checkbox_color,
            hover_color=self._button_hover_color,
            border_width=self._checkbox_border_width,
            corner_radius=self._checkbox_corner_radius
        )
        self.active_schedule.grid(row=0, column=0, padx=10, pady=5, sticky="w")

        # Schedule treeview
        self.schedule_table = ttk.Treeview(
            self.schedule_frame,
            columns=("day", "pause_start", "pause_duration", "close_positions"),
            show="headings",
            height=7
        )
        
        # Configure treeview columns
        self.schedule_table.heading("day", text="Active Day")
        self.schedule_table.heading("pause_start", text="Pause at")
        self.schedule_table.heading("pause_duration", text="Pause duration")
        self.schedule_table.heading("close_positions", text="Close Positions")
        
        total_width = 480  # Total width minus padding
        self.schedule_table.column("day", width=int(total_width * 0.3))
        self.schedule_table.column("pause_start", width=int(total_width * 0.20))
        self.schedule_table.column("pause_duration", width=int(total_width * 0.20))
        self.schedule_table.column("close_positions", width=int(total_width * 0.3))
        
        # Bind double click event
        self.schedule_table.bind("<Double-1>", self._on_schedule_double_click)
        
        self.schedule_table.grid(row=1, column=0, padx=10, pady=(5,10), sticky="nsew")
        if not self.active_schedule_var.get():
            self.schedule_table.grid_remove()
        
        # Load values if editing existing rule
        if symbol:
            alert_rules = self.config.get("alert_rules", [])
            for rule in alert_rules:
                if rule["symbol"] == symbol:
                    self.volume_entry.insert(0, str(rule["volume"]))
                    self.tp_entry.insert(0, str(rule["take_profit"]))
                    self.sl_entry.insert(0, str(rule["stop_loss"]))
                    self.pts_entry.insert(0, str(rule["profit_trailing_stop"]))
                    if rule.get("volume_from_alert", False):
                        self.volume_from_alert.select()
                    if rule.get("close_positions_on_entry", False):
                        self.close_positions.select()
                    if rule.get("active_schedule", False):
                        self.active_schedule_var.set(1)
                        self.schedule_table.grid()
                        self.geometry("500x550")  # Increased height to fully fit treeview
                        
                        # Load schedule data
                        schedule = rule.get("schedule", [])
                        for schedule_item in schedule:
                            self.schedule_table.insert("", "end", values=(
                                schedule_item.get("day", "").capitalize(),
                                schedule_item.get("pause_start", ""),
                                schedule_item.get("pause_duration", ""),
                                "Yes" if schedule_item.get("close_positions_on_pause", False) else "No"
                            ))
                    break
        
        # Bind entry events
        self.volume_entry.bind("<KeyRelease>", self._on_volume_changed)
        self.tp_entry.bind("<KeyRelease>", self._on_tp_changed)
        self.sl_entry.bind("<KeyRelease>", self._on_sl_changed)
        self.pts_entry.bind("<KeyRelease>", self._on_pts_changed)
        
        # Bind checkbox events
        self.volume_from_alert.configure(command=self._on_checkbox_changed)
        self.close_positions.configure(command=self._on_checkbox_changed)
        
        # Override window close button
        self.protocol("WM_DELETE_WINDOW", self._on_closing)
        
        # Bind escape key to close window
        self.bind("<Escape>", lambda e: self._on_closing())
    
    def _get_current_rule(self):
        """Get the current rule being edited."""
        alert_rules = self.config.get("alert_rules", [])
        for rule in alert_rules:
            if rule.get("symbol") == self.original_symbol:
                return rule
        return {
            "symbol": "",
            "volume": 0.01,
            "volume_from_alert": False,
            "take_profit": 0.0,
            "stop_loss": 0.0,
            "profit_trailing_stop": 0.0,
            "close_positions_on_entry": False,
            "active_schedule": False,
            "schedule": []
        }
    
    def _save_rule(self):
        """Save all current values to the rule."""
        alert_rules = self.config.get("alert_rules", [])
        
        # Get current rule
        current_rule = None
        for rule in alert_rules:
            if rule.get("symbol") == self.original_symbol:
                current_rule = rule
                break
        
        # Create new rule if not found
        if not current_rule:
            current_rule = {
                "symbol": self.symbol_entry.get(),
                "volume": float(self.volume_entry.get() or 0.01),
                "volume_from_alert": self.volume_from_alert.get(),
                "take_profit": float(self.tp_entry.get() or 0.0),
                "stop_loss": float(self.sl_entry.get() or 0.0),
                "profit_trailing_stop": float(self.pts_entry.get() or 0.0),
                "close_positions_on_entry": self.close_positions.get(),
                "active_schedule": self.active_schedule_var.get(),
                "schedule": []
            }
            alert_rules.append(current_rule)
        else:
            # Update existing rule
            current_rule["symbol"] = self.symbol_entry.get()
            current_rule["volume"] = float(self.volume_entry.get() or 0.01)
            current_rule["volume_from_alert"] = self.volume_from_alert.get()
            current_rule["take_profit"] = float(self.tp_entry.get() or 0.0)
            current_rule["stop_loss"] = float(self.sl_entry.get() or 0.0)
            current_rule["profit_trailing_stop"] = float(self.pts_entry.get() or 0.0)
            current_rule["close_positions_on_entry"] = self.close_positions.get()
            current_rule["active_schedule"] = self.active_schedule_var.get()
        
        # Update schedule if active
        if self.active_schedule_var.get():
            schedule = []
            for item in self.schedule_table.get_children():
                values = self.schedule_table.item(item)["values"]
                schedule.append({
                    "day": values[0],
                    "pause_start": values[1],
                    "pause_duration": values[2],
                    "close_positions_on_pause": bool(values[3] == "Yes")
                })
            current_rule["schedule"] = schedule
        
        # Save back to config
        self.config.set("alert_rules", alert_rules)
        
        # Update original_symbol if symbol changed
        if current_rule["symbol"] != self.original_symbol:
            self.original_symbol = current_rule["symbol"]
    
    def _validate_symbol_char(self, symbol):
        """Validate each character in the symbol string."""
        # Only allow ASCII letters (a-z, A-Z), numbers (0-9), dots and minus
        return ''.join(c for c in symbol if (c.isascii() and c.isalnum()) or c in '.-')

    def _on_symbol_changed(self, event=None):
        """Handle symbol entry changes."""
        # Get current text and cursor position
        current_text = self.symbol_entry.get()
        cursor_pos = self.symbol_entry.index("insert")
        
        # Validate and filter the text
        filtered_text = self._validate_symbol_char(current_text)
        
        # If text changed after filtering, update the entry
        if filtered_text != current_text:
            self.symbol_entry.delete(0, "end")
            self.symbol_entry.insert(0, filtered_text)
            # Try to maintain cursor position, but don't go beyond the filtered text length
            self.symbol_entry.icursor(min(cursor_pos - 1, len(filtered_text)))
        
        # Update the current symbol
        self.symbol = filtered_text
        
        # Save changes
        self._save_rule()
    
    def _on_volume_changed(self, event=None):
        """Handle volume entry changes."""
        self._save_rule()
    
    def _on_tp_changed(self, event=None):
        """Handle take profit entry changes."""
        self._save_rule()
    
    def _on_sl_changed(self, event=None):
        """Handle stop loss entry changes."""
        self._save_rule()
    
    def _on_pts_changed(self, event=None):
        """Handle profit trailing stop entry changes."""
        self._save_rule()
    
    def _on_checkbox_changed(self):
        """Handle checkbox changes."""
        self._save_rule()
    
    def _validate_symbol(self, symbol):
        """Validate the symbol name."""
        if not symbol:
            return False, "Symbol name cannot be empty"
            
        if symbol == "NEW":
            return False, "Cannot save with symbol name 'NEW'"
            
        # Get existing rules
        alert_rules = self.config.get("alert_rules", [])
        
        # Check if symbol exists in other rules
        for rule in alert_rules:
            if (rule["symbol"] == symbol and 
                (not self.original_symbol or  # New rule
                 symbol != self.original_symbol)):  # Changed symbol
                return False, f"Symbol '{symbol}' already exists"
        
        return True, None
    
    def _on_closing(self):
        """Handle window closing."""
        symbol = self.symbol_entry.get()
        
        # Validate symbol before closing
        is_valid, error_msg = self._validate_symbol(symbol)
        if not is_valid:
            messagebox.showerror("Invalid Symbol", error_msg)
            return
            
        # Call on_close callback if provided
        if self.on_close:
            self.on_close()
            
        self.destroy()
    
    def _on_map(self, event):
        """Called when window is mapped to screen"""
        if not self._icon_set:
            icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "logo.ico")
            if os.path.exists(icon_path):
                # Bug in customtkinter: https://stackoverflow.com/a/75825532
                try:
                    self.after(250, lambda: self._set_icon(icon_path))
                    self._icon_set = True
                except Exception as e:
                    print(f"Error scheduling icon set: {str(e)}")
    
    def _set_icon(self, icon_path):
        """Set window icon after window is fully initialized"""
        try:
            # Try direct iconbitmap first
            self.iconbitmap(icon_path)
        except Exception as e:
            print(f"Error setting icon after map: {str(e)}")
            try:
                # Fallback to low-level tk call
                self.tk.call('wm', 'iconbitmap', self._w, icon_path)
            except Exception as e:
                print(f"Error setting icon using tk.call: {str(e)}")
    
    def _on_schedule_changed(self):
        """Handle schedule checkbox changes."""
        if self.active_schedule_var.get():
            self.schedule_table.grid()
            self.geometry("500x550")  # Keep height at 550 when schedule is shown
            # If no schedule data exists, add default schedule
            if len(self.schedule_table.get_children()) == 0:
                days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
                for day in days:
                    self.schedule_table.insert("", "end", values=(
                        day.capitalize(),
                        "21:30",
                        "03:00",
                        "Yes"
                    ))
        else:
            self.schedule_table.grid_remove()
            self.geometry("500x350")  # Keep height at 350 when schedule is hidden
            
        # Save changes to config
        self._save_rule()

    def _on_schedule_double_click(self, event):
        """Handle double click on schedule table"""
        item = self.schedule_table.identify_row(event.y)
        if not item:
            return
            
        # Get the day from the selected row
        values = self.schedule_table.item(item)["values"]
        if not values:
            return
            
        day = values[0]
        
        # Open edit day window
        edit_day_window = EditDayWindow(
            self,
            self.config,
            self.symbol,
            day,
            on_close=self._refresh_schedule
        )
        
    def _refresh_schedule(self):
        """Refresh the schedule table after editing a day"""
        # Clear current items
        for item in self.schedule_table.get_children():
            self.schedule_table.delete(item)
            
        # Get current rule
        current_rule = self._get_current_rule()
        schedule = current_rule.get("schedule", [])
        
        # Reload items
        for schedule_item in schedule:
            self.schedule_table.insert("", "end", values=(
                schedule_item.get("day", "").capitalize(),
                schedule_item.get("pause_start", ""),
                schedule_item.get("pause_duration", ""),
                "Yes" if schedule_item.get("close_positions_on_pause", False) else "No"
            ))

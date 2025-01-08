import customtkinter as ctk
from utils.config_manager import ConfigManager
from utils.api_client import APIClient
from gui.edit_rule_window import EditRuleWindow
from utils.flask_server import FlaskServer
import os
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from PIL import Image

class SettingsWindow(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        
        # Store references
        self.parent = parent
        self.config = ConfigManager()
        self.api_client = APIClient()
        self.flask_server = None
        
        # Check if server is already running in parent
        self.server_running = False
        if hasattr(self.parent, 'flask_server') and self.parent.flask_server and self.parent.flask_server.server:
            self.flask_server = self.parent.flask_server
            self.server_running = True
        
        # Configure window
        self.title("Settings")
        self.geometry("380")
        self.resizable(False, False)
        
        # Configure gray theme colors
        self._button_color = "#4d4d4d"  # Darker gray for button
        self._button_hover_color = "#666666"  # Medium gray for hover
        self._checkbox_color = "#666666"
        self._tabview_color = "#4d4d4d"
        self._disabled_color = "#212121"  # Darker gray for disabled state
        self._entry_color = "#343638"  # Default entry background color
        
        # Configure component styles
        self._checkbox_border_width = 2
        self._checkbox_corner_radius = 4
        self._button_border_width = 0
        self._button_corner_radius = 4
        self._tab_corner_radius = 16
        
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
        
        # Position window in center of parent
        self.update_idletasks()
        parent_x = self.parent.winfo_x()
        parent_y = self.parent.winfo_y()
        parent_width = self.parent.winfo_width()
        parent_height = self.parent.winfo_height()
        
        window_width = 600
        window_height = 380
        
        x = parent_x + (parent_width - window_width) // 2
        y = parent_y + (parent_height - window_height) // 2
        
        self.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
        # Configure grid layout
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        # Create TabView
        self.tabview = ctk.CTkTabview(
            self,
            fg_color="transparent",
            segmented_button_fg_color="#212121",  # Darker gray for unselected tabs
            segmented_button_selected_color="#666666",  # Medium gray for selected tab
            segmented_button_selected_hover_color="#808080",
            segmented_button_unselected_color="#212121",  # Darker gray for unselected tabs
            segmented_button_unselected_hover_color="#666666",
            corner_radius=self._tab_corner_radius
        )
        self.tabview.grid(row=0, column=0, padx=15, pady=15, sticky="nsew")
        
        # Add tabs
        self.tab_general = self.tabview.add("General")
        self.tab_local_server = self.tabview.add("Local Server")
        self.tab_rules = self.tabview.add("Rules")

        # Configure grid for each tab
        for tab in [self.tab_general, self.tab_local_server, self.tab_rules]:
            tab.grid_columnconfigure(0, weight=1)

        # License Frame
        license_frame = ctk.CTkFrame(self.tab_general)
        license_frame.grid(row=0, column=0, columnspan=2, padx=15, pady=(10,10), sticky="ew")
        license_frame.grid_columnconfigure(1, weight=1)

        license_label = ctk.CTkLabel(license_frame, text="Licensed:", anchor="w")
        license_label.grid(row=0, column=0, padx=(10,5), pady=3)

        # Get and mask license key
        license_key = self.config.get("license_key", "")
        user_type = self.config.get("user", {}).get("type", 0)
        user_type_str = "Premium" if user_type == 1 else "Basic"
        
        if license_key:
            masked_key = self._mask_license_key(license_key)
            display_text = f"{masked_key}, {user_type_str}"
        else:
            display_text = "Not Licensed"

        self.license_value = ctk.CTkLabel(license_frame, text=display_text, anchor="w")
        self.license_value.grid(row=0, column=1, padx=5, pady=3, sticky="w")

        if license_key:
            # Create both normal and hover icons
            self.delete_icon = ctk.CTkImage(
                light_image=Image.open("assets/delete_666666.png"),
                dark_image=Image.open("assets/delete_666666.png"),
                size=(16, 16)
            )
            self.delete_hover_icon = ctk.CTkImage(
                light_image=Image.open("assets/delete.png"),
                dark_image=Image.open("assets/delete.png"),
                size=(16, 16)
            )
            self.test_icon = ctk.CTkImage(
                light_image=Image.open("assets/test_666666.png"),
                dark_image=Image.open("assets/test_666666.png"),
                size=(16, 16)
            )
            self.test_hover_icon = ctk.CTkImage(
                light_image=Image.open("assets/test.png"),
                dark_image=Image.open("assets/test.png"),
                size=(16, 16)
            )
            self.play_icon = ctk.CTkImage(
                light_image=Image.open("assets/play_666666.png"),
                dark_image=Image.open("assets/play_666666.png"),
                size=(16, 16)
            )
            self.play_hover_icon = ctk.CTkImage(
                light_image=Image.open("assets/play.png"),
                dark_image=Image.open("assets/play.png"),
                size=(16, 16)
            )
            self.stop_icon = ctk.CTkImage(
                light_image=Image.open("assets/stop_666666.png"),
                dark_image=Image.open("assets/stop_666666.png"),
                size=(16, 16)
            )
            self.stop_hover_icon = ctk.CTkImage(
                light_image=Image.open("assets/stop.png"),
                dark_image=Image.open("assets/stop.png"),
                size=(16, 16)
            )
            
            self.remove_button = ctk.CTkButton(
                license_frame,
                text="",
                command=self._remove_license,
                fg_color="transparent",
                hover_color=self._button_hover_color,
                border_width=0,
                corner_radius=self._button_corner_radius,
                width=24,
                image=self.delete_icon
            )
            self.remove_button.grid(row=0, column=2, padx=(5,10), pady=3)
            
            # Bind hover events
            self.remove_button.bind("<Enter>", lambda e: self.remove_button.configure(image=self.delete_hover_icon))
            self.remove_button.bind("<Leave>", lambda e: self.remove_button.configure(image=self.delete_icon))
        
        # Log Settings
        log_frame = ctk.CTkFrame(self.tab_general)
        log_frame.grid(row=1, column=0, columnspan=2, padx=15, pady=10, sticky="ew")
        log_frame.grid_columnconfigure(1, weight=1)

        self.show_seconds = ctk.CTkCheckBox(
            log_frame,
            text="Show seconds in log",
            command=self._on_show_seconds_changed,
            fg_color=self._checkbox_color,
            hover_color=self._button_hover_color,
            border_width=self._checkbox_border_width,
            corner_radius=self._checkbox_corner_radius
        )
        self.show_seconds.grid(row=0, column=0, padx=(10,10), pady=5, sticky="w")
        self.show_seconds.select() if self.config.get("show_seconds_in_log", False) else self.show_seconds.deselect()

        self.save_log = ctk.CTkCheckBox(
            log_frame,
            text="Save log to file",
            command=self._on_save_log_changed,
            fg_color=self._checkbox_color,
            hover_color=self._button_hover_color,
            border_width=self._checkbox_border_width,
            corner_radius=self._checkbox_corner_radius
        )
        self.save_log.grid(row=0, column=1, padx=0, pady=5, sticky="w")
        self.save_log.select() if self.config.get("save_log", True) else self.save_log.deselect()

        # Alert Settings
        alert_frame = ctk.CTkFrame(self.tab_general)
        alert_frame.grid(row=2, column=0, columnspan=2, padx=15, pady=10, sticky="ew")
        alert_frame.grid_columnconfigure(0, weight=1)

        self.listen_to_alerts = ctk.CTkCheckBox(
            alert_frame,
            text="Listen to alerts",
            command=self._on_listen_to_alerts_changed,
            fg_color=self._checkbox_color,
            hover_color=self._button_hover_color,
            border_width=self._checkbox_border_width,
            corner_radius=self._checkbox_corner_radius
        )
        self.listen_to_alerts.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        self.listen_to_alerts.select() if self.config.get("listen_to_alerts", True) else self.listen_to_alerts.deselect()

        # Discord Settings
        discord_frame = ctk.CTkFrame(self.tab_general)
        discord_frame.grid(row=3, column=0, columnspan=2, padx=15, pady=10, sticky="ew")
        discord_frame.grid_columnconfigure(0, weight=1)

        # Discord webhook URL
        discord_label = ctk.CTkLabel(discord_frame, text="Discord Webhook", anchor="w", font=("", 12))
        discord_label.grid(row=0, column=0, padx=10, pady=(5,0), sticky="w")

        self.webhook_entry = ctk.CTkEntry(
            discord_frame,
            placeholder_text="https://discord.com/api/webhooks/XXXXXX"
        )
        self.webhook_entry.grid(row=1, column=0, padx=10, pady=(0,5), sticky="ew")
        webhook_url = self.config.get("discord_webhook_url", "")
        if webhook_url:  # Only insert if URL exists
            self.webhook_entry.insert(0, webhook_url)
        self.webhook_entry.bind("<KeyRelease>", self._on_webhook_changed)

        # Message Settings
        message_frame = ctk.CTkFrame(discord_frame, fg_color="transparent")
        message_frame.grid(row=2, column=0, columnspan=2, padx=10, pady=(0,5), sticky="ew")
        message_frame.grid_columnconfigure(1, weight=1)

        self.message_alerts = ctk.CTkCheckBox(
            message_frame,
            text="Message incoming alerts",
            command=self._on_message_alerts_changed,
            fg_color=self._checkbox_color,
            hover_color=self._button_hover_color,
            border_width=self._checkbox_border_width,
            corner_radius=self._checkbox_corner_radius
        )
        self.message_alerts.grid(row=0, column=0, padx=(0,10), pady=0, sticky="w")
        self.message_alerts.select() if self.config.get("discord_message_alerts", False) else self.message_alerts.deselect()

        self.message_errors = ctk.CTkCheckBox(
            message_frame,
            text="Message errors",
            command=self._on_message_errors_changed,
            fg_color=self._checkbox_color,
            hover_color=self._button_hover_color,
            border_width=self._checkbox_border_width,
            corner_radius=self._checkbox_corner_radius
        )
        self.message_errors.grid(row=0, column=1, padx=0, pady=0, sticky="w")
        self.message_errors.select() if self.config.get("discord_message_errors", False) else self.message_errors.deselect()

        # Local Server Settings
        server_frame = ctk.CTkFrame(self.tab_local_server)
        server_frame.grid(row=0, column=0, columnspan=2, padx=15, pady=(10,10), sticky="ew")
        server_frame.grid_columnconfigure(0, weight=3)  # Host column gets more weight
        server_frame.grid_columnconfigure(1, weight=1)  # Port column gets less weight

        # Host settings
        host_label = ctk.CTkLabel(server_frame, text="Host", anchor="w", font=("", 12))
        host_label.grid(row=0, column=0, padx=10, pady=(5,0), sticky="w")

        self.host_entry = ctk.CTkEntry(
            server_frame,
            placeholder_text="0.0.0.0",
            fg_color=self._entry_color  # Changed to default entry color
        )
        self.host_entry.grid(row=1, column=0, padx=10, pady=(0,5), sticky="ew")
        flask_config = self.config.get("flask", {})
        host = flask_config.get("host", "")
        if host:  # Only insert if host exists
            self.host_entry.insert(0, host)
        self.host_entry.bind("<KeyRelease>", self._on_host_changed)

        # Port settings
        port_label = ctk.CTkLabel(server_frame, text="Port", anchor="w", font=("", 12))
        port_label.grid(row=0, column=1, padx=10, pady=(5,0), sticky="w")

        self.port_entry = ctk.CTkEntry(
            server_frame,
            placeholder_text="80",
            fg_color=self._entry_color  # Changed to default entry color
        )
        self.port_entry.grid(row=1, column=1, padx=10, pady=(0,5), sticky="ew")
        port = flask_config.get("port", "")
        if port:  # Only insert if port exists
            self.port_entry.insert(0, str(port))
        self.port_entry.bind("<KeyRelease>", self._on_port_changed)

        # SSL Settings
        ssl_frame = ctk.CTkFrame(self.tab_local_server)
        ssl_frame.grid(row=1, column=0, columnspan=2, padx=15, pady=10, sticky="ew")
        ssl_frame.grid_columnconfigure(0, weight=1)
        ssl_frame.grid_columnconfigure(1, weight=1)

        # SSL Checkbox
        self.use_ssl = ctk.CTkCheckBox(
            ssl_frame,
            text="Use SSL",
            command=self._on_use_ssl_changed,
            fg_color=self._checkbox_color,
            hover_color=self._button_hover_color,
            border_width=self._checkbox_border_width,
            corner_radius=self._checkbox_corner_radius
        )
        self.use_ssl.grid(row=0, column=0, columnspan=2, padx=10, pady=5, sticky="w")
        use_ssl = flask_config.get("use_ssl", False)
        self.use_ssl.select() if use_ssl else self.use_ssl.deselect()

        # SSL Certificate Files
        cert_label = ctk.CTkLabel(ssl_frame, text="Certificate File", anchor="w", font=("", 12))
        cert_label.grid(row=1, column=0, padx=10, pady=(5,0), sticky="w")

        key_label = ctk.CTkLabel(ssl_frame, text="Key File", anchor="w", font=("", 12))
        key_label.grid(row=1, column=1, padx=10, pady=(5,0), sticky="w")

        self.cert_entry = ctk.CTkEntry(
            ssl_frame,
            placeholder_text="C:\server.crt",
            fg_color=self._entry_color
        )
        self.cert_entry.grid(row=2, column=0, padx=10, pady=(0,5), sticky="ew")
        certfile = flask_config.get("certfile", "")
        if certfile != "":  # Only insert if not empty string
            self.cert_entry.insert(0, certfile)
        self.cert_entry.bind("<KeyRelease>", self._on_cert_changed)

        self.key_entry = ctk.CTkEntry(
            ssl_frame,
            placeholder_text="C:\server.key",
            fg_color=self._entry_color
        )
        self.key_entry.grid(row=2, column=1, padx=10, pady=(0,5), sticky="ew")
        keyfile = flask_config.get("keyfile", "")
        if keyfile != "":  # Only insert if not empty string
            self.key_entry.insert(0, keyfile)
        self.key_entry.bind("<KeyRelease>", self._on_key_changed)

        # Controls Frame
        controls_frame = ctk.CTkFrame(self.tab_local_server)
        controls_frame.grid(row=2, column=0, columnspan=2, padx=15, pady=10, sticky="ew")
        controls_frame.grid_columnconfigure(0, weight=1)  # Space before buttons
        controls_frame.grid_columnconfigure(1, weight=0)  # Start/Stop button
        controls_frame.grid_columnconfigure(2, weight=0)  # Test button
        controls_frame.grid_columnconfigure(3, weight=1)  # Space after buttons

        # Server control button
        self.start_stop_button = ctk.CTkButton(
            controls_frame,
            text="",
            image=self.stop_icon if self.server_running else self.play_icon,
            fg_color="transparent",
            hover_color=self._button_hover_color,
            border_width=0,
            corner_radius=self._button_corner_radius,
            width=48,
            command=self._toggle_server
        )
        self.start_stop_button.grid(row=0, column=1, padx=5, pady=10)

        # Bind hover events for start/stop button
        self.start_stop_button.bind("<Enter>", lambda e: self.start_stop_button.configure(image=self.stop_hover_icon if self.server_running else self.play_hover_icon))
        self.start_stop_button.bind("<Leave>", lambda e: self.start_stop_button.configure(image=self.stop_icon if self.server_running else self.play_icon))

        # Test Button
        self.test_button = ctk.CTkButton(
            controls_frame,
            text="",
            image=self.test_icon,
            command=self._test_local_server,
            width=32,
            fg_color="transparent",
            hover_color=self._button_hover_color
        )
        self.test_button.grid(row=0, column=2, padx=5, pady=10)
        
        # Bind hover events for test button
        self.test_button.bind("<Enter>", lambda e: self.test_button.configure(image=self.test_hover_icon))
        self.test_button.bind("<Leave>", lambda e: self.test_button.configure(image=self.test_icon))

        # Rules Tab
        # Import tkinter for the table
        style = ttk.Style()
        style.theme_use('clam')
        
        # Create a frame for the button
        button_frame = ctk.CTkFrame(self.tab_rules, fg_color="transparent")
        button_frame.grid(row=0, column=0, columnspan=3, sticky="e", padx=15, pady=(5,0))

        # Load remove button images
        self.remove_image = ctk.CTkImage(
            light_image=Image.open("assets/remove_666666.png"),
            dark_image=Image.open("assets/remove_666666.png"),
            size=(20, 20)
        )

        # Remove button
        self.remove_button = ctk.CTkButton(
            button_frame,
            text="",
            image=self.remove_image,
            width=32,
            height=32,
            fg_color="transparent",
            hover_color="#1f1f1f",
            corner_radius=8,
            command=self._remove_selected_rule
        )
        self.remove_button.grid(row=0, column=0, padx=(0, 5), pady=0)
        self.remove_button.grid_remove()  # Initially hide since no rule is selected

        def on_remove_enter(e):
            self.remove_button.configure(image=ctk.CTkImage(
                light_image=Image.open("assets/remove.png"),
                dark_image=Image.open("assets/remove.png"),
                size=(20, 20)
            ))

        def on_remove_leave(e):
            self.remove_button.configure(image=self.remove_image)

        self.remove_button.bind("<Enter>", on_remove_enter)
        self.remove_button.bind("<Leave>", on_remove_leave)

        # Load add button images
        add_image = ctk.CTkImage(
            light_image=Image.open("assets/add_666666.png"),
            dark_image=Image.open("assets/add_666666.png"),
            size=(20, 20)
        )

        # Add button
        add_button = ctk.CTkButton(
            button_frame,
            text="",
            image=add_image,
            width=32,
            height=32,
            fg_color="transparent",
            hover_color="#1f1f1f",
            corner_radius=8,
            command=self._add_new_rule
        )
        add_button.grid(row=0, column=1, padx=0, pady=0)

        def on_add_enter(e):
            add_button.configure(image=ctk.CTkImage(
                light_image=Image.open("assets/add.png"),
                dark_image=Image.open("assets/add.png"),
                size=(20, 20)
            ))

        def on_add_leave(e):
            add_button.configure(image=add_image)

        add_button.bind("<Enter>", on_add_enter)
        add_button.bind("<Leave>", on_add_leave)

        # Configure Treeview
        style.configure("Treeview", 
            background="#2b2b2b",
            foreground="white",
            fieldbackground="#2b2b2b",
            borderwidth=0,
            rowheight=25,
            relief="flat"
        )
        style.configure("Treeview.Heading",
            background="#1f1f1f",
            foreground="white",
            borderwidth=1,
            relief="flat"
        )
        style.map("Treeview.Heading",
            background=[("active", "#666666")]  # This adds hover effect
        )
        style.map("Treeview",
            background=[("selected", "#666666")],
            foreground=[("selected", "white")]
        )
        style.layout("Treeview", [('Treeview.treearea', {'sticky': 'nswe'})])

        # Configure modern scrollbar style
        def create_element_if_not_exists(element_name):
            try:
                style.element_create(element_name, "from", "clam")
            except tk.TclError as e:
                if "Duplicate element" not in str(e):
                    raise e

        create_element_if_not_exists("Vertical.TScrollbar.trough")
        create_element_if_not_exists("Vertical.TScrollbar.thumb")
        create_element_if_not_exists("Vertical.TScrollbar.grip")
        
        style.layout("Vertical.TScrollbar", [
            ('Vertical.TScrollbar.trough', {
                'sticky': 'ns',
                'children': [('Vertical.TScrollbar.thumb', {
                    'sticky': 'nswe',
                    'children': [('Vertical.TScrollbar.grip', {'sticky': ''})],
                })],
            })])

        style.configure("Vertical.TScrollbar",
            background="#2b2b2b",
            darkcolor="#1f1f1f",
            lightcolor="#2b2b2b",
            troughcolor="#1f1f1f",
            bordercolor="#1f1f1f",
            arrowcolor="#666666",
            relief="flat",
            borderwidth=0
        )
        
        style.map("Vertical.TScrollbar",
            background=[("pressed", "#666666"),
                       ("active", "#4d4d4d")],
            darkcolor=[("pressed", "#1f1f1f"),
                      ("active", "#1f1f1f")],
            lightcolor=[("pressed", "#666666"),
                       ("active", "#4d4d4d")],
            troughcolor=[("pressed", "#1f1f1f"),
                        ("active", "#1f1f1f")],
            bordercolor=[("pressed", "#1f1f1f"),
                        ("active", "#1f1f1f")],
            arrowcolor=[("pressed", "#ffffff"),
                       ("active", "#ffffff")]
        )

        # Create a frame with dark background for the Treeview
        tree_frame = ttk.Frame(self.tab_rules, style="Dark.TFrame")
        tree_frame.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=15, pady=10)
        tree_frame.grid_columnconfigure(0, weight=1)
        tree_frame.grid_rowconfigure(0, weight=1)

        # Configure dark frame style
        style.configure("Dark.TFrame", background="#1f1f1f")

        # Create Treeview
        self.rules_table = ttk.Treeview(
            tree_frame,
            columns=("symbol", "volume", "tp", "sl", "pts"),
            show="headings",
            style="Treeview",
            height=10  # Set fixed height
        )
        
        # Configure column headings
        self.rules_table.heading("symbol", text="Symbol")
        self.rules_table.heading("volume", text="Volume")
        self.rules_table.heading("tp", text="TP")
        self.rules_table.heading("sl", text="SL")
        self.rules_table.heading("pts", text="PTS")
        
        # Set minimum column widths
        for col in ("symbol", "volume", "tp", "sl", "pts"):
            self.rules_table.column(col, minwidth=50)

        def _resize_columns(event):
            """Resize columns to be equal width when treeview is resized"""
            width = event.width
            # Calculate equal width for each column, accounting for potential scrollbar
            scrollbar_width = 20  # Approximate width of scrollbar
            if len(self.rules_table.get_children()) > self.rules_table["height"]:
                width -= scrollbar_width
            col_width = width // 5  # 5 columns
            for col in ("symbol", "volume", "tp", "sl", "pts"):
                self.rules_table.column(col, width=col_width)

        # Bind Configure event to resize columns
        self.rules_table.bind("<Configure>", _resize_columns)

        # Load alert rules from config
        alert_rules = self.config.get("alert_rules", [])
        for rule in alert_rules:
            self.rules_table.insert("", "end", values=(
                rule.get("symbol", ""),
                rule.get("volume", ""),
                rule.get("take_profit", ""),
                rule.get("stop_loss", ""),
                rule.get("profit_trailing_stop", "")
            ))

        # Add scrollbar with modern style
        scrollbar = ttk.Scrollbar(
            tree_frame,
            orient="vertical", 
            command=self.rules_table.yview,
            style="Vertical.TScrollbar"
        )
        scrollbar.grid(row=0, column=1, sticky="ns")
                
        # Configure the Treeview with scrollbar
        self.rules_table.configure(yscrollcommand=scrollbar.set)

        # Grid the table with proper expansion
        self.rules_table.grid(row=0, column=0, sticky="nsew")

        # Configure tab_rules column weights
        self.tab_rules.grid_columnconfigure(0, weight=1)
        self.tab_rules.grid_rowconfigure(1, weight=1)

        # Bind double click event to treeview
        self.rules_table.bind("<Double-1>", self._on_rule_double_click)

        # Bind selection event to treeview
        self.rules_table.bind("<<TreeviewSelect>>", self._on_rule_select)

        # Set default tab
        self.tabview.set("General")

        # Bind escape key to close window
        self.bind("<Escape>", lambda e: self.destroy())
        
        self.selected_symbol = None  # Add variable to track selected symbol

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
                print(f"Error setting icon using tk.call after map: {str(e)}")
                try:
                    # Final attempt with wm_iconbitmap
                    self.wm_iconbitmap(icon_path)
                except Exception as e:
                    print(f"All icon setting methods failed: {str(e)}")
                    
    def _save_settings(self):
        """Save settings and close window"""
        # Add your save logic here
        # Example:
        # self.config.set("some_setting", self.some_setting.get())
        # self.config.save_config()
        self.destroy()

    def _mask_license_key(self, key: str) -> str:
        """Mask the license key, showing only the first and last 4 characters."""
        if not key:
            return "Not Licensed"
        
        # Show first 4 and last 4 characters, mask everything else with X's
        if len(key) <= 8:  # If key is 8 or fewer chars, just return it as is
            return key
        else:
            return f"{key[:4]}{'X' * (len(key)-8)}{key[-4:]}"

    def _remove_license(self):
        if messagebox.askyesno("Remove License", "Are you sure you want to remove the license key?", icon='warning'):
            self.config.set("license_key", "")
            self.config.set("user", {
                "type": 0,
                "ws_url": None,
                "expiration_timestamp": None
            })
            self.config.save_config()
            
            # Close settings window and show login frame
            self.destroy()
            self.parent.show_login_frame()
        
            # Reset login frame to normal state
            if hasattr(self.parent, 'login_frame'):
                self.parent.login_frame.reset_to_normal_state()
            
            # Show success message after switching to login frame
            messagebox.showinfo("Success", "License removed successfully")
        
    def _on_show_seconds_changed(self):
        self.config.set("show_seconds_in_log", self.show_seconds.get())
        self.config.save_config()

    def _on_save_log_changed(self):
        self.config.set("save_log", self.save_log.get())
        self.config.save_config()

    def _on_listen_to_alerts_changed(self):
        self.config.set("listen_to_alerts", self.listen_to_alerts.get())
        self.config.save_config()

    def _on_webhook_changed(self, event=None):
        self.config.set("discord_webhook_url", self.webhook_entry.get().strip())
        self.config.save_config()

    def _on_message_alerts_changed(self):
        self.config.set("discord_message_alerts", self.message_alerts.get())
        self.config.save_config()

    def _on_message_errors_changed(self):
        self.config.set("discord_message_errors", self.message_errors.get())
        self.config.save_config()

    def _on_host_changed(self, event=None):
        host = self.host_entry.get().strip()
        flask_config = self.config.get("flask", {})
        flask_config["host"] = host
        self.config.set("flask", flask_config)
        self.config.save_config()

    def _on_port_changed(self, event=None):
        port = self.port_entry.get().strip()
        if port:
            try:
                port = int(port)
                if not (0 <= port <= 65535):
                    raise ValueError("Port number must be between 0 and 65535")
                flask_config = self.config.get("flask", {})
                flask_config["port"] = port
                self.config.set("flask", flask_config)
                self.config.save_config()
            except ValueError as e:
                error_message = str(e) if "Port number must be between" in str(e) else "Port must be a valid number"
                messagebox.showerror("Invalid Port", error_message)
                # Restore previous value
                flask_config = self.config.get("flask", {})
                port = flask_config.get("port", "")
                self.port_entry.delete(0, "end")
                if port:
                    self.port_entry.insert(0, str(port))

    def _on_use_ssl_changed(self):
        flask_config = self.config.get("flask", {})
        use_ssl = self.use_ssl.get()
        flask_config["use_ssl"] = use_ssl
        self.config.set("flask", flask_config)
        self.config.save_config()

    def _on_cert_changed(self, event=None):
        certfile = self.cert_entry.get().strip()
        flask_config = self.config.get("flask", {})
        flask_config["certfile"] = certfile
        self.config.set("flask", flask_config)
        self.config.save_config()

    def _on_key_changed(self, event=None):
        keyfile = self.key_entry.get().strip()
        flask_config = self.config.get("flask", {})
        flask_config["keyfile"] = keyfile
        self.config.set("flask", flask_config)
        self.config.save_config()

    def _test_local_server(self):
        """Test if the local server is accessible externally"""
        if not self.server_running or not self.flask_server:
            messagebox.showinfo("Info", "Please start the local server first.")
            return
            
        try:
            # Get current configuration
            flask_config = self.config.get("flask", {})
            port = int(self.port_entry.get().strip() or flask_config.get("port", 5000))
            use_ssl = bool(int(flask_config.get("use_ssl", 0)))
            license_key = self.config.get("license_key", "")
            
            # Send test request
            response = self.api_client.post(
                '/test-local-server',
                json={
                    'license_key': license_key,
                    'use_ssl': use_ssl,
                    'port': port
                },
                timeout=5
            )
            
            if response.status_code == 200:
                json_response = response.json()
                if json_response.get('success', False):
                    messagebox.showinfo("Success", "The local server can be accessed externally.")
                else:
                    messagebox.showwarning("Warning", "The local server cannot be accessed externally.")
            else:
                messagebox.showerror("Error", "Failed to test server connection.")
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to test server: {str(e)}")

    def test_connection(self):
        """Test the connection to the local server"""
        host = self.host_entry.get()
        port = self.port_entry.get()
        
        try:
            # Create a socket connection to test
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)  # 2 second timeout
            
            # Try to connect
            result = sock.connect_ex((host, int(port)))
            sock.close()
            
            if result == 0:
                messagebox.showinfo("Success", f"Successfully connected to {host}:{port}")
            else:
                messagebox.showerror("Error", f"Could not connect to {host}:{port}")
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid port number")
        except Exception as e:
            messagebox.showerror("Error", f"Connection test failed: {str(e)}")

    def _open_edit_rule_window(self, symbol=None):
        """Open the edit rule window with an optional symbol."""
        edit_window = EditRuleWindow(
            self, 
            self.config, 
            symbol,
            on_close=self._refresh_rules_treeview
        )
        edit_window.geometry(f"+{self.winfo_x() + 50}+{self.winfo_y() + 50}")
        edit_window.grab_set()  # Make window modal
        edit_window.focus()  # Focus the window
    
    def _on_rule_double_click(self, event):
        """Handle double click on a rule in the treeview."""
        item = self.rules_table.selection()
        if item:
            values = self.rules_table.item(item[0])["values"]
            if values:
                symbol = values[0]  # Get symbol from first column
                self._open_edit_rule_window(symbol)

    def _add_new_rule(self):
        """Add a new rule with default values and open edit window."""
        # Default values for new rule
        default_rule = {
            "symbol": "NEW",
            "volume": 0.01,
            "volume_from_alert": False,
            "take_profit": 0.0,
            "stop_loss": 0.0,
            "profit_trailing_stop": 0.0,
            "close_positions_on_entry": True,
            "active_schedule": False
        }
        
        # Add to treeview
        item = self.rules_table.insert("", "end", values=(
            default_rule["symbol"],
            default_rule["volume"],
            default_rule["take_profit"],
            default_rule["stop_loss"],
            default_rule["profit_trailing_stop"]
        ))
        
        # Add to config
        alert_rules = self.config.get("alert_rules", [])
        alert_rules.append(default_rule)
        self.config.set("alert_rules", alert_rules)
        
        # Select the new item
        self.rules_table.selection_set(item)
        self.rules_table.see(item)  # Ensure the new item is visible
        
        # Open edit window
        self._open_edit_rule_window("NEW")

    def _refresh_rules_treeview(self):
        """Refresh the rules treeview."""
        # Clear the treeview
        for item in self.rules_table.get_children():
            self.rules_table.delete(item)
        
        # Load alert rules from config
        alert_rules = self.config.get("alert_rules", [])
        for rule in alert_rules:
            self.rules_table.insert("", "end", values=(
                rule.get("symbol", ""),
                rule.get("volume", ""),
                rule.get("take_profit", ""),
                rule.get("stop_loss", ""),
                rule.get("profit_trailing_stop", "")
            ))
            
        # Hide remove button since selection is lost
        self.selected_symbol = None
        self.remove_button.grid_remove()

    def _on_rule_select(self, event):
        """Handle rule selection in treeview"""
        selection = self.rules_table.selection()
        if selection:
            item = self.rules_table.item(selection[0])
            self.selected_symbol = item['values'][0]  # First column contains symbol
            self.remove_button.grid()  # Show remove button
        else:
            self.selected_symbol = None
            self.remove_button.grid_remove()  # Hide remove button

    def _remove_selected_rule(self):
        """Remove the selected rule after confirmation"""
        if not self.selected_symbol:
            return

        # Show confirmation dialog
        if messagebox.askyesno("Confirm Removal", f"Do you really want to remove the rules for Symbol {self.selected_symbol}?"):
            # Get current rules
            alert_rules = self.config.get("alert_rules", [])
            
            # Remove rule for selected symbol
            alert_rules = [rule for rule in alert_rules if rule.get("symbol") != self.selected_symbol]
            
            # Update config
            self.config.set("alert_rules", alert_rules)
            self.config.save_config()

            # Clear treeview
            for item in self.rules_table.get_children():
                self.rules_table.delete(item)

            # Reload rules
            for rule in alert_rules:
                self.rules_table.insert("", "end", values=(
                    rule.get("symbol", ""),
                    rule.get("volume", ""),
                    rule.get("take_profit", ""),
                    rule.get("stop_loss", ""),
                    rule.get("profit_trailing_stop", "")
                ))

            # Reset selected symbol
            self.selected_symbol = None
            self.remove_button.grid_remove()  # Hide remove button

    def show_scrollbar(self, *args):
        """Show scrollbar if necessary"""
        if self.rules_table.yview() != (0.0, 1.0):
            scrollbar = self.rules_table.winfo_children()[1]
            scrollbar.grid()
        else:
            scrollbar = self.rules_table.winfo_children()[1]
            scrollbar.grid_remove()

    def _toggle_server(self):
        """Toggle the Flask server on/off"""
        if not self.server_running:
            # Start server
            try:
                # Get config values
                flask_config = self.config.get("flask", {})
                host = self.host_entry.get().strip() or flask_config.get("host", "127.0.0.1")
                port = int(self.port_entry.get().strip() or flask_config.get("port", 5000))
                use_ssl = bool(int(flask_config.get("use_ssl", 0)))
                certfile = flask_config.get("certfile", "")
                keyfile = flask_config.get("keyfile", "")
                
                # Validate SSL configuration
                if use_ssl and (not certfile or not keyfile):
                    messagebox.showerror("Error", "SSL is enabled but certificate or key file paths are not configured.")
                    return
                
                # Create server instance
                self.flask_server = FlaskServer(
                    host=host,
                    port=port,
                    use_ssl=use_ssl,
                    certfile=certfile if use_ssl else None,
                    keyfile=keyfile if use_ssl else None
                )
                
                # Set main_frame and config references
                self.flask_server.main_frame = self.parent.main_frame
                self.flask_server.config = self.config
                
                # Start the server
                self.flask_server.start()
                
                # Store in app
                self.parent.flask_server = self.flask_server
                
                # Update UI
                self.server_running = True
                self.start_stop_button.configure(image=self.stop_icon)
                self.start_stop_button.bind("<Enter>", lambda e: self.start_stop_button.configure(image=self.stop_hover_icon))
                self.start_stop_button.bind("<Leave>", lambda e: self.start_stop_button.configure(image=self.stop_icon))
                
                # Log server start
                self.parent.main_frame.add_log(f"Local server started on {host}:{port}")
                
                messagebox.showinfo("Success", f"Server started successfully on {host}:{port}")
                
            except FileNotFoundError:
                messagebox.showerror("Error", "SSL certificate or key file not found. Please check your SSL configuration.")
                self.flask_server = None
                self.parent.flask_server = None
            except ValueError as e:
                messagebox.showerror("Error", f"Invalid port number. Please enter a valid number.")
                self.flask_server = None
                self.parent.flask_server = None
            except Exception as e:
                messagebox.showerror("Error", f"Failed to start server: {str(e)}")
                self.flask_server = None
                self.parent.flask_server = None
        else:
            # Stop server
            try:
                if self.flask_server:
                    self.flask_server.stop()
                    self.flask_server = None
                    self.parent.flask_server = None
                
                # Update UI
                self.server_running = False
                self.start_stop_button.configure(image=self.play_icon)
                self.start_stop_button.bind("<Enter>", lambda e: self.start_stop_button.configure(image=self.play_hover_icon))
                self.start_stop_button.bind("<Leave>", lambda e: self.start_stop_button.configure(image=self.play_icon))
                
                # Log server stop
                self.parent.main_frame.add_log("Local server stopped")
                
                messagebox.showinfo("Success", "Server stopped successfully")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to stop server: {str(e)}")

    def destroy(self):
        """Override destroy to validate Discord webhook URL"""
        webhook_url = self.webhook_entry.get().strip()
        if webhook_url and not webhook_url.startswith("https://discord.com/api/webhooks/"):
            messagebox.showerror("Invalid Discord Webhook", "The Discord webhook URL must start with 'https://discord.com/api/webhooks/'")
            return
        super().destroy()

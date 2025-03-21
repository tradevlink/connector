import customtkinter as ctk
from utils.image_loader import ImageLoader
from tkinter import messagebox
from utils.trade_status_task import TradeStatusTask
from utils.trade_filter import TradeFilter
from gui.settings_window import SettingsWindow
from datetime import datetime
import os
import requests
import threading

class MainFrame(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        
        # Initialize trade status task and trade filter
        self.trade_status_task = TradeStatusTask(self)
        self.trade_filter = TradeFilter(self)
        
        # Configure grid layout
        self.grid_rowconfigure(1, weight=1)  # Text area row expands
        self.grid_rowconfigure((0, 2), weight=0)  # Fixed height for top and bottom rows
        self.grid_columnconfigure(0, weight=1)
        
        # Top row with buttons
        self.top_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.top_frame.grid(row=0, column=0, sticky="e", padx=(0, 5), pady=5)
        
        # Load button icons
        image_loader = ImageLoader()
        settings_icon = image_loader.get_image("settings.png", size=(20, 20))
        delete_icon = image_loader.get_image("delete.png", size=(20, 20))
        
        # Create icon buttons
        self.settings_button = ctk.CTkButton(
            self.top_frame,
            text="",
            image=settings_icon,
            width=30,
            fg_color="transparent",
            hover_color=("gray75", "gray25"),
            command=self._show_settings
        )
        self.settings_button.grid(row=0, column=0, padx=5)
        
        # Middle text area
        self.text_area = ctk.CTkTextbox(
            self,
            wrap="word",
            state="disabled"
        )
        self.text_area.grid(row=1, column=0, padx=10, pady=5, sticky="nsew")
        
        # Bottom row with connection status
        self.bottom_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.bottom_frame.grid(row=2, column=0, sticky="w", padx=10, pady=5)

        # Create a frame for status elements
        self.status_group = ctk.CTkFrame(self.bottom_frame, fg_color="transparent")
        self.status_group.grid(row=0, column=0, sticky="nsew")
        self.status_group.grid_columnconfigure(1, weight=1)  # Give weight to text column

        # Status dot (colored circle)
        self.status_dot = ctk.CTkLabel(
            self.status_group,
            text="⬤",  # Different dot character
            font=("", 12),  # Slightly smaller font
            width=20,
            text_color=None,  # Will be set by the periodic task
            justify="center"
        )
        self.status_dot.grid(row=0, column=0, padx=(0, 2))

        # Connection status text
        self.connection_status = ctk.CTkLabel(
            self.status_group,
            text="",
            font=("", 12)
        )
        self.connection_status.grid(row=0, column=1, sticky="w")

        # Clear button frame (right side)
        self.clear_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.clear_frame.grid(row=2, column=0, sticky="e", padx=10, pady=5)
        
        self.clear_button = ctk.CTkButton(
            self.clear_frame,
            text="",
            image=delete_icon,
            width=30,
            fg_color="transparent",
            hover_color=("gray75", "gray25"),
            command=self.clear_text
        )
        self.clear_button.grid(row=0, column=0)
        
        # Start trade status task
        self.trade_status_task.start()
        
    def add_text(self, text: str):
        """Add new text to the text area"""
        self.text_area.configure(state="normal")
        self.text_area.insert("end", text + "\n")
        self.text_area.configure(state="disabled")
        self.text_area.see("end")
        
    def add_log(self, message: str, file_only_message: str = None):
        """Add a log message with timestamp
        Args:
            message: Message to show in UI and log file
            file_only_message: Optional message to write only to log file
        """
        now = datetime.now()
        
        # Get current time for display
        show_seconds = self.parent.config.get("show_seconds_in_log", False)
        display_time = now.strftime("%H:%M" if not show_seconds else "%H:%M:%S")
        
        # Display in text area
        self.add_text(f"{display_time}\t{message}")
        
        # Save to log file if enabled
        if self.parent.config.get("save_log", False):
            try:
                # Use full timestamp for log file entry
                full_timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
                
                # Create logs directory if it doesn't exist
                log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
                os.makedirs(log_dir, exist_ok=True)
                
                # Use current date as filename
                log_file = os.path.join(log_dir, f"{now.strftime('%Y-%m-%d')}.txt")
                
                # Append the log entry efficiently
                with open(log_file, 'a', encoding='utf-8') as f:
                    f.write(f"{full_timestamp}\t{message}\n")
                    if file_only_message:
                        f.write(f"{full_timestamp}\t{file_only_message}\n")
            except Exception as e:
                print(f"Error writing to log file: {e}")

    def clear_text(self):
        """Clear all text from the text area after confirmation"""
        if messagebox.askyesno("Confirm Clear", "Are you sure you want to clear the log?"):
            self.text_area.configure(state="normal")
            self.text_area.delete("1.0", "end")
            self.text_area.configure(state="disabled")

    def _show_settings(self):
        """Show settings window"""
        settings_window = SettingsWindow(self.winfo_toplevel())
        self.wait_window(settings_window)  # Wait for settings window to close

    def send_webhook(self, message: str, type: str):
        """Send a message to Discord webhook asynchronously.
        
        Args:
            message: Message to send
            type: Type of message ('alert' or 'error')
        """
        # Check if we should send this type of message
        if type == 'alert' and not self.parent.config.get("discord_message_alerts", False):
            return
        if type == 'error' and not self.parent.config.get("discord_message_errors", False):
            return
            
        # Get webhook URL
        webhook_url = self.parent.config.get("discord_webhook_url", "").strip()
        if not webhook_url:
            return
            
        # Prepare webhook data
        data = {
            "content": message,
            "username": "TradevLink"
        }
        
        def send_request():
            try:
                response = requests.post(webhook_url, json=data, timeout=5)
                if response.status_code not in [200, 204]:
                    self.add_log(f"Discord webhook failed with status code: {response.status_code}")
            except requests.exceptions.Timeout:
                self.add_log("Discord webhook timed out after 5 seconds")
            except requests.exceptions.ConnectionError:
                self.add_log("Discord webhook failed: Could not reach server")
            except requests.exceptions.RequestException as e:
                self.add_log(f"Discord webhook failed: {str(e)}")
        
        # Start webhook request in a new thread
        threading.Thread(target=send_request, daemon=True).start()

    def destroy(self):
        """Override destroy to cleanup resources"""
        # Stop trade status task before destroying frame
        if hasattr(self, 'trade_status_task'):
            try:
                self.trade_status_task.stop()
            except Exception:
                pass
            self.trade_status_task = None
            
        # Destroy the frame
        super().destroy()

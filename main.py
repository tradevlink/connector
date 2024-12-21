import customtkinter as ctk
import os
import tkinter as tk
import argparse
from gui.login_frame import LoginFrame
from gui.main_frame import MainFrame
from utils.config_manager import ConfigManager
from utils.dev_mode import set_dev_mode, is_dev_mode
from utils.app_periodic_task import AppPeriodicTask

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Initialize config manager
        self.config = ConfigManager()
        
        # Initialize and start periodic task
        self.periodic_task = AppPeriodicTask(self)
        self.periodic_task.start()
        
        # Set theme
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")
        
        # Configure window
        self.title("TradevLink - Connector")
        self.geometry("600x400")
        self.resizable(False, False)  # Disable both horizontal and vertical resizing
        
        # Center window on screen
        self.update_idletasks()  # Update window size
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width - 600) // 2
        y = (screen_height - 400) // 2
        self.geometry(f"600x400+{x}+{y}")
        
        # Set window icon
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "logo.ico")
        if os.path.exists(icon_path):
            self.iconbitmap(icon_path)
        
        # Configure grid layout
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        # Initialize frames
        self.login_frame = LoginFrame(self)
        self.main_frame = None  # Initialize later when needed
        
        # Show login frame initially
        self.show_login_frame()
        
        # Bind window close event
        self.protocol("WM_DELETE_WINDOW", self._on_closing)
    
    def _on_closing(self):
        """Handle window closing event"""
        if hasattr(self, 'periodic_task'):
            self.periodic_task.stop()
        self.quit()
    
    def show_login_frame(self):
        """Switch to login frame"""
        if self.main_frame:
            self.main_frame.grid_forget()
            self.main_frame.destroy()  # Destroy to stop the trade status task
            self.main_frame = None  # Allow garbage collection
            
        self.login_frame.grid(row=0, column=0, sticky="nsew")
    
    def show_main_frame(self):
        """Switch to main frame"""
        if self.login_frame:
            self.login_frame.grid_forget()
        
        # Create main frame if it doesn't exist
        if not self.main_frame:
            self.main_frame = MainFrame(self)
            
        # Reset periodic task connection state to allow new connection
        self.periodic_task.reset_connection_state()
            
        self.main_frame.grid(row=0, column=0, sticky="nsew")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='TradevLink Connector')
    parser.add_argument('--dev', action='store_true', help='Run in development mode')
    args = parser.parse_args()
    
    # Set development mode
    set_dev_mode(args.dev)
    
    app = App()
    app.mainloop()

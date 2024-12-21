import customtkinter as ctk
from utils.image_loader import ImageLoader
from datetime import datetime
import requests
from utils.api_client import APIClient
from tkinter import messagebox
from utils.version import TRADEVLINK_VERSION
from utils.config_manager import ConfigManager
from PIL import Image

class LoginFrame(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self._request_in_progress = False
        self.config = ConfigManager()
        self._original_license_key = None  # Store the original key
        
        # Configure grid layout (4 rows, 2 columns)
        self.grid_rowconfigure((0, 1, 2), weight=1)
        self.grid_rowconfigure(3, weight=0)  # No weight for copyright row
        self.grid_columnconfigure((0, 1), weight=1)
        
        # Load logo
        image_loader = ImageLoader()
        logo_image = image_loader.get_image("logo.png", size=(200, 200), preserve_ratio=True)
        
        # Load icons for connect button
        self.connect_icon = ctk.CTkImage(
            light_image=Image.open("assets/arrow_right_666666.png"),
            dark_image=Image.open("assets/arrow_right_666666.png"),
            size=(16, 16)
        )
        self.connect_hover_icon = ctk.CTkImage(
            light_image=Image.open("assets/arrow_right.png"),
            dark_image=Image.open("assets/arrow_right.png"),
            size=(16, 16)
        )
        self.pending_icon = ctk.CTkImage(
            light_image=Image.open("assets/pending_666666.png"),
            dark_image=Image.open("assets/pending_666666.png"),
            size=(16, 16)
        )
        
        # Create widgets
        # 1. Logo at the top
        self.logo_label = ctk.CTkLabel(
            self,
            image=logo_image,
            text=""  # No text, only image
        )
        self.logo_label.grid(row=0, column=0, columnspan=2, padx=20, pady=(40, 20))
        
        # Create a frame for license input and button
        self.input_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.input_frame.grid(row=1, column=0, columnspan=2, pady=(0, 20))
        self.input_frame.grid_columnconfigure(0, weight=1)  # For license entry
        self.input_frame.grid_columnconfigure(1, weight=0)  # For button
        
        # 2. License text label
        self.license_text = ctk.CTkLabel(
            self.input_frame,
            text="Connect with TradevLink's services",
            font=ctk.CTkFont(size=16)
        )
        self.license_text.grid(row=0, column=0, columnspan=2, padx=20, pady=(0, 5))
        
        # 3. License key input field
        self.license_entry = ctk.CTkEntry(
            self.input_frame,
            placeholder_text="",
            width=300
        )
        self.license_entry.grid(row=1, column=0, padx=(20, 5))
        # Bind Enter key to login
        self.license_entry.bind("<Return>", lambda event: self.login())
        # Bind key events for handling asterisk display
        self.license_entry.bind("<Key>", self._on_key_press)
        self.license_entry.bind("<BackSpace>", self._on_key_press)
        self.license_entry.bind("<Delete>", self._on_key_press)
        
        # 4. Connect button
        self.connect_button = ctk.CTkButton(
            self.input_frame,
            text="",  # Empty text since we're using icons
            command=self.login,
            width=32,  # Adjust width for icon
            image=self.connect_icon,
            fg_color="transparent",
            hover_color=self._button_hover_color if hasattr(self, '_button_hover_color') else "#666666"
        )
        self.connect_button.grid(row=1, column=1, padx=(5, 20))
        
        # Bind hover events for connect button
        self.connect_button.bind("<Enter>", lambda e: self.connect_button.configure(image=self.connect_hover_icon))
        self.connect_button.bind("<Leave>", lambda e: self.connect_button.configure(image=self.connect_icon))
        
        # Add copyright text at the bottom
        copyright_text = f"TradevLink {TRADEVLINK_VERSION}. All rights reserved."
        self.copyright_label = ctk.CTkLabel(
            self,
            text=copyright_text,
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        self.copyright_label.grid(row=3, column=0, columnspan=2, pady=(0, 10))
        
        # Check for saved license key
        saved_key = self.config.get('license_key')
        if saved_key:
            self._original_license_key = saved_key
            self.license_entry.insert(0, saved_key)
            self.license_entry.configure(show="*")  # Show asterisks
            # Hide normal content and show validation message
            self.license_text.configure(text="Validating License...")
            self.license_entry.grid_remove()
            self.connect_button.grid_remove()
            # Schedule validation after the window is fully loaded
            self.after(100, self.login)
            
    def _on_key_press(self, event):
        """Handle key press in license entry field"""
        if self._original_license_key and self.license_entry.get() == self._original_license_key:
            # If this is the first edit of a saved key, clear the field and show normal text
            self.license_entry.configure(show="")
            self.license_entry.delete(0, 'end')
            self._original_license_key = None  # Clear the original key
            
    def validate_license(self, license_key):
        """Validate license key with the server"""
        api_client = APIClient()
        
        try:
            response = api_client.post('/validate-license', json={'license_key': license_key}, timeout=5)
            
            if response.status_code == 200:
                json_response = response.json()
                if json_response.get('success', False):
                    # Save license key and user data to config
                    self.config.set('license_key', license_key)
                    self.config.set('user', {
                        'type': json_response['type'],
                        'ws_url': json_response['ws_url'],
                        'expiration_timestamp': json_response['expiration_timestamp']
                    })
                    self.parent.show_main_frame()
                    return True
                else:
                    # Show normal content on error
                    self.license_text.configure(text="Connect with TradevLink's services")
                    self.license_entry.grid()
                    self.license_entry.configure(state="normal")
                    self.connect_button.grid()
                    self.connect_button.configure(state="normal", image=self.connect_icon)
                    messagebox.showwarning(
                        title="Invalid License",
                        message="The provided license key is not valid."
                    )
            else:
                # Show normal content on error
                self.license_text.configure(text="Connect with TradevLink's services")
                self.license_entry.grid()
                self.license_entry.configure(state="normal")
                self.connect_button.grid()
                self.connect_button.configure(state="normal", image=self.connect_icon)
                messagebox.showwarning(
                    title="Server Error",
                    message="Something went wrong while connecting with the server."
                )
        except Exception:
            # Show normal content on error
            self.license_text.configure(text="Connect with TradevLink's services")
            self.license_entry.grid()
            self.license_entry.configure(state="normal")
            self.connect_button.grid()
            self.connect_button.configure(state="normal", image=self.connect_icon)
            messagebox.showwarning(
                title="Connection Error",
                message="Could not connect to the server. Please check your internet connection."
            )
        return False
            
    def login(self):
        if self._request_in_progress:
            return
            
        try:
            self._request_in_progress = True
            license_key = self.license_entry.get().strip()
            
            if not license_key:
                messagebox.showwarning(
                    title="Empty License Key",
                    message="The license key cannot be empty. If you need help regarding your license key, contact us at support@tradevlink.com"
                )
                return
            
            # Set request in progress and disable button
            self.connect_button.configure(state="disabled", image=self.pending_icon)
            self.license_entry.configure(state="disabled")
            # Force UI update
            self.update()
            
            if not self.validate_license(license_key):
                # Reset text and state if validation fails
                self.license_text.configure(text="Connect with TradevLink's services")
                self.license_entry.grid()
                self.license_entry.configure(state="normal")
                self.connect_button.grid()
                self.connect_button.configure(state="normal", image=self.connect_icon)
                
        except requests.exceptions.Timeout:
            # Reset text and state on timeout
            self.license_text.configure(text="Connect with TradevLink's services")
            self.license_entry.grid()
            self.license_entry.configure(state="normal")
            self.connect_button.grid()
            self.connect_button.configure(state="normal", image=self.connect_icon)
            messagebox.showwarning(
                title="Connection Timeout",
                message="The server took too long to respond. Please try again."
            )
        except requests.exceptions.RequestException:
            messagebox.showwarning(
                title="Connection Error",
                message="Something went wrong while connecting with the server."
            )
        finally:
            # Reset request state
            self._request_in_progress = False

    def reset_to_normal_state(self):
        """Reset the login frame to its normal state"""
        self.license_text.configure(text="Connect with TradevLink's services")
        self.license_entry.grid()
        self.license_entry.configure(state="normal", show="")  # Reset show property
        self.connect_button.grid()
        self.connect_button.configure(state="normal", image=self.connect_icon)
        self.license_entry.delete(0, 'end')  # Clear any existing text
        self._original_license_key = None  # Clear the original key

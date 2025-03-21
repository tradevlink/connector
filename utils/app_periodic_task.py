from utils.periodic_task import PeriodicTask
from datetime import datetime
import asyncio
import threading
from utils.websocket_client import WebSocketClient
import tkinter.messagebox as messagebox
from utils.api_client import APIClient
from utils.version import TRADEVLINK_VERSION
from packaging.version import Version
import os

class AppPeriodicTask(PeriodicTask):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.websocket = None
        self.last_connection_attempt = None
        self.connection_cooldown = 5  # seconds
        self.websocket_thread = None
        self.loop = None
        self.was_connected = False  # Track if we were previously connected
        self.last_ping_time = None  # Track when we last sent a ping
        self.ping_interval = 30  # seconds
        self.license_validation_failures = 0
        self.last_license_validation = datetime.now().timestamp()
        self.license_validation_cooldown = 60  # seconds
        self.latest_desktop_version = None  # Store latest version from server
        
    async def handle_verify_request(self, data):
        """Handle verify_request message by sending license key"""
        if self.websocket and self.websocket.running:
            license_key = self.app.config.get("license_key")
            if license_key:
                await self.websocket.send_message("verify", {"license_key": license_key})

    async def handle_verify_response(self, data):
        """Handle verify_response message from server"""
        status = data.get("status")
        if status == "success":
            self.app.main_frame.add_log("Connected with TradevLink's server")
        else:
            self.app.main_frame.add_log("Connection with TradevLink's server rejected.")

    async def handle_alert(self, data):
        """Handle alert message from server"""
        # Extract required fields
        symbol = data.get("symbol")
        volume = data.get("volume")  # Can be None
        action = data.get("action")  # buy or sell

        if symbol and action:
            # Log the incoming alert
            if hasattr(self.app, 'main_frame') and self.app.main_frame:
                # Create log message - only include volume if it exists
                log_message = f"Incoming alert: {symbol}, {action.lower()}"
                if volume is not None:
                    log_message += f", {volume}"
                self.app.main_frame.add_log(log_message)
                self.app.main_frame.send_webhook(log_message, 'alert')
                
                # Process the trade through trade filter
                trade_filter = self.app.main_frame.trade_filter
                if trade_filter:
                    # Convert volume to float only if it's not None
                    volume_float = float(volume) if volume is not None else None
                    await self.loop.run_in_executor(None, trade_filter.process_trade, symbol, volume_float, action.lower())

    async def send_ping(self):
        """Send a ping message to the server"""
        if self.websocket and self.websocket.running:
            await self.websocket.send_message("ping", {})
            self.last_ping_time = datetime.now()
        
    def _start_websocket_thread(self, ws_url):
        """Start a new thread for WebSocket operations"""
        if self.websocket_thread and self.websocket_thread.is_alive():
            return
            
        def run_websocket():
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            
            self.websocket = WebSocketClient(ws_url)
            
            def handle_websocket_error(error):
                def safe_log(ui_message, error_details=None):
                    # Only try to log if app and main_frame exist
                    if hasattr(self, 'app') and self.app and hasattr(self.app, 'main_frame') and self.app.main_frame:
                        file_msg = f"WebSocket error details: {error_details}" if error_details else None
                        self.app.main_frame.add_log(ui_message, file_msg)
                
                if isinstance(error, dict):
                    code = error.get("code")
                    reason = error.get("reason", "")
                    
                    if (code == 4003 and reason == "License logged in from another location") or \
                       (code == 4002 and reason == "License is invalid"):
                        # Handle both duplicate login and invalid license cases
                        self.was_connected = False  # Prevent reconnection attempts
                        # Pass the error code to show appropriate message
                        self.app.after(0, lambda: self._handle_duplicate_login(code, reason))
                        safe_log("License logged in from another location" if code == 4003 else "License is invalid", error)
                    elif code == 4002 and reason == "Premium license required":
                        # Handle premium license required error
                        self.was_connected = False  # Prevent reconnection attempts
                        # Update user type in config to prevent future connection attempts
                        current_user = self.app.config.get("user", {})
                        current_user["type"] = 0
                        self.app.config.set("user", current_user)
                        safe_log("Premium license required. Connection with TradevLink's server disabled", error)
                    elif code == "CONNECTION_FAILED":
                        # Initial connection failure
                        self.app.after(0, lambda: safe_log("Cannot establish connection with TradevLink's server", error))
                    else:
                        # For connection errors after we were connected, show disconnection message
                        if self.was_connected:
                            self.app.after(0, lambda: safe_log("Connection with TradevLink's server closed", error))
                        else:
                            self.app.after(0, lambda: safe_log("Cannot establish connection with TradevLink's server", error))
                else:
                    # Fallback for any non-dict errors
                    self.app.after(0, lambda: safe_log("Cannot establish connection with TradevLink's server", str(error)))
            
            self.websocket.set_error_handler(handle_websocket_error)
            
            # Register message handlers
            self.websocket.on("verify_request", self.handle_verify_request)
            self.websocket.on("verify_response", self.handle_verify_response)
            self.websocket.on("alert", self.handle_alert)  # Register alert handler
            
            try:
                self.loop.run_until_complete(self.websocket.connect())
                if self.websocket.running:
                    self.was_connected = True
                    self.last_ping_time = datetime.now()  # Initialize ping timer
                    self.loop.run_until_complete(self.websocket.receive_messages())
            except asyncio.CancelledError:
                # Handle task cancellation gracefully
                if self.websocket:
                    self.loop.run_until_complete(self.websocket.close())
                return
            except Exception as e:
                def safe_log(message, error_details=None):
                    if hasattr(self, 'app') and self.app and hasattr(self.app, 'main_frame') and self.app.main_frame:
                        file_msg = f"WebSocket error details: {error_details}" if error_details else None
                        self.app.main_frame.add_log(message, file_msg)
                
                error_str = str(e)  # Capture the error string here
                # If we never managed to connect, show a connection failure message
                if not self.was_connected:
                    self.app.after(0, lambda: safe_log("Cannot establish connection with TradevLink's server", error_str))
                else:
                    self.app.after(0, lambda: safe_log("Connection with TradevLink's server closed", error_str))
            finally:
                # Properly clean up the event loop
                try:
                    # Cancel all running tasks
                    pending = asyncio.all_tasks(self.loop)
                    for task in pending:
                        task.cancel()
                    # Run the event loop one last time to let tasks clean up
                    if pending:
                        self.loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                    # Now we can safely close
                    if not self.loop.is_closed():
                        self.loop.run_until_complete(self.loop.shutdown_asyncgens())
                        self.loop.close()
                except Exception:
                    pass  # Ignore any errors during cleanup
                self.loop = None
                self.websocket = None  # Clear websocket when connection ends
        
        self.websocket_thread = threading.Thread(target=run_websocket, daemon=True)
        self.websocket_thread.start()
        
    def _stop_websocket(self):
        """Stop the WebSocket connection and thread"""
        if not self.websocket or not self.loop:
            # Clear references and return if there's nothing to clean
            self.websocket = None
            self.loop = None
            self.websocket_thread = None
            return

        # Store loop reference to prevent it from being cleared during cleanup
        loop = self.loop
        
        try:
            if not loop.is_closed():
                # Create cleanup coroutine
                async def cleanup():
                    # Close websocket first
                    if self.websocket:
                        try:
                            await self.websocket.close()
                        except Exception as e:
                            print(f"Error closing websocket: {str(e)}")
                    
                    # Cancel all pending tasks except the cleanup task itself
                    try:
                        current_task = asyncio.current_task(loop)
                        pending = [task for task in asyncio.all_tasks(loop) 
                                 if task is not current_task and not task.done()]
                        
                        if pending:
                            # Cancel all pending tasks
                            for task in pending:
                                task.cancel()
                            
                            # Wait for cancellation to complete
                            try:
                                await asyncio.wait(pending, timeout=2.0)
                            except Exception:
                                pass  # Ignore timeout errors during shutdown
                    except Exception as e:
                        print(f"Error cancelling tasks: {str(e)}")
                    
                    # Shutdown async generators
                    try:
                        await loop.shutdown_asyncgens()
                    except Exception as e:
                        print(f"Error shutting down async generators: {str(e)}")
                
                # Schedule cleanup in the event loop
                if loop.is_running():
                    # If loop is running, schedule the cleanup
                    try:
                        future = asyncio.run_coroutine_threadsafe(cleanup(), loop)
                        future.result(timeout=2.0)  # Reduced timeout
                    except Exception as e:
                        print(f"Error during async cleanup: {str(e)}")
                        # Try to cancel the cleanup task if it's still running
                        try:
                            future.cancel()
                        except Exception:
                            pass
                else:
                    # If loop is not running, we can use run_until_complete
                    try:
                        loop.run_until_complete(cleanup())
                    except Exception as e:
                        print(f"Error during sync cleanup: {str(e)}")

                # Stop the loop if it's still running
                try:
                    if loop.is_running():
                        loop.stop()
                except Exception as e:
                    print(f"Error stopping event loop: {str(e)}")
                
                # Only try to close if not running
                if not loop.is_running():
                    try:
                        loop.close()
                    except Exception as e:
                        print(f"Error closing event loop: {str(e)}")
        except Exception as e:
            print(f"Error during websocket cleanup: {str(e)}")
        finally:
            # Clear all references
            self.websocket = None
            self.loop = None
            self.websocket_thread = None
            # Don't reset was_connected here - we want to remember if we were connected before

    def _handle_duplicate_login(self, code=None, reason=None):
        self.app.show_login_frame()  # Switch to login frame first
        try:
            self.app.login_frame.reset_to_normal_state()
        except Exception:
            pass  # Ignore any GUI-related errors during reset
        
        if code == 4002 and reason == "License is invalid":
            messagebox.showwarning("Invalid License", "Your license is invalid. Please check your license key and try again.")
        else:
            messagebox.showwarning("Session Ended", "Your license is being used in another location. Please connect again.")

    def reset_connection_state(self):
        """Reset the connection state to allow new connections"""
        self.was_connected = False
        self.last_connection_attempt = None
        self.last_ping_time = None
        self.websocket = None
        self.websocket_thread = None
        self.loop = None

    def _get_connection_status(self):
        """Get the connection status text and color for display"""
        # Check MT5 connection
        mt5_connected = False
        if hasattr(self.app, 'main_frame') and self.app.main_frame:
            mt5_client = self.app.main_frame.trade_status_task.mt5_client
            if mt5_client:
                mt5_connected = mt5_client.is_connected()

        # Check WebSocket connection
        ws_connected = self.websocket and self.websocket.running
        
        # Check if premium user
        is_premium = self.app.config.get("user", {}).get("type") == 1
        
        # Check local server
        local_server_running = False
        if hasattr(self.app, 'flask_server') and self.app.flask_server and self.app.flask_server.server:
            local_server_running = True

        # Determine dot color
        if mt5_connected:
            dot_color = "#28a745"  # Green
        else:
            dot_color = "#6c757d"  # Gray

        # Build status text
        status_parts = []
        if mt5_connected:
            status_parts.append("MT5 Connected")
        else:
            status_parts.append("MT5 Not Connected")

        '''if is_premium:
            if ws_connected:
                status_parts.append("TradevLink Connected")
            else:
                status_parts.append("Not Connected to TradevLink")'''

        if local_server_running:
            status_parts.append("Local Server")

        if self.latest_desktop_version and Version(self.latest_desktop_version) > Version(TRADEVLINK_VERSION):
            status_parts = [f"Update Available ({self.latest_desktop_version})"]
            dot_color = "#d97a21"

        status_text = " & ".join(status_parts)

        return dot_color, status_text

    def task(self):
        # Update the connection status in the main frame
        if hasattr(self.app, 'main_frame') and self.app.main_frame:
            main_frame = self.app.main_frame
            if main_frame.winfo_exists():  # Check if window exists instead of mapped
                # Get connection status
                dot_color, status_text = self._get_connection_status()
                
                # Update dot color and status text separately
                main_frame.status_dot.configure(text_color=dot_color)
                main_frame.connection_status.configure(text=status_text)
                
                # Check if we need to validate license
                current_time = datetime.now().timestamp()
                if (current_time - self.last_license_validation) >= self.license_validation_cooldown:
                    self.last_license_validation = current_time
                    self._validate_license()
                
                # Check if we need to send a ping
                if (self.websocket and self.websocket.running and self.loop and 
                    self.last_ping_time and 
                    (datetime.now() - self.last_ping_time).total_seconds() >= self.ping_interval):
                    try:
                        self.loop.call_soon_threadsafe(
                            lambda: asyncio.create_task(self.send_ping())
                        )
                    except Exception as e:
                        self.app.main_frame.add_log(f"Error sending ping: {str(e)}")
                
                # Check if we should manage WebSocket connection
                config = self.app.config
                license_key = config.get("license_key")
                user_type = config.get("user", {}).get("type")
                ws_url = config.get("user", {}).get("ws_url")
                
                # WebSocket from 2025 not available
                if False and license_key and user_type == 1 and ws_url:
                    # Should have active WebSocket
                    current_time = datetime.now().timestamp()
                    
                    # Check if we need to reconnect
                    if not self.websocket and (
                        self.was_connected or not self.last_connection_attempt
                    ) and (
                        not self.last_connection_attempt or 
                        current_time - self.last_connection_attempt >= self.connection_cooldown
                    ):
                        self.last_connection_attempt = current_time

                        self._start_websocket_thread(ws_url)
                else:
                    # Should not have active WebSocket
                    if self.websocket:
                        main_frame.add_log("Closing TradevLink connection...")
                        self._stop_websocket()
                    self.was_connected = False  # Reset connection memory if conditions are not met
            else:
                # Main frame not visible, close WebSocket if open
                if self.websocket:
                    self._stop_websocket()
        else:
            # No main frame, close WebSocket if open
            if self.websocket:
                self._stop_websocket()

    def stop(self):
        """Stop the periodic task and cleanup resources"""
        # First stop the periodic task
        super().stop()
        
        # Then cleanup the websocket connection
        if self.websocket or self.loop:
            try:
                self._stop_websocket()
            except Exception as e:
                print(f"Error during final cleanup: {str(e)}")

    def _validate_license(self):
        """Validate license key with the server"""
        api_client = APIClient()
        license_key = self.app.config.get('license_key')
        
        if not license_key:
            return
            
        try:
            response = api_client.post('/validate-license', json={'license_key': license_key}, timeout=5)
            
            if response.status_code == 200:
                json_response = response.json()
                if json_response.get('success', False):
                    # Reset failure counter on success
                    self.license_validation_failures = 0

                    self.app.config.set('user', {
                        'type': json_response['type'],
                        'ws_url': json_response['ws_url'],
                        'expiration_timestamp': json_response['expiration_timestamp']
                    })

                    self.latest_desktop_version = json_response.get('desktop_version')
                else:
                    self._handle_license_validation_failure()
            else:
                self._handle_license_validation_failure()
                
        except Exception:
            self._handle_license_validation_failure()
            
    def _handle_license_validation_failure(self):
        """Handle license validation failure"""
        self.license_validation_failures += 1
        # Only redirect to login if we have too many failures AND no active websocket
        if self.license_validation_failures > 3 and (not self.websocket or not self.websocket.running):
            messagebox.showwarning(
                title="License Validation Failed",
                message="Failed to validate your license. Please login again."
            )
            if hasattr(self.app, 'login_frame'):
                # Clear the license key from config first
                self.app.config.set('license_key', None)
                self.app.show_login_frame()
                try:
                    self.app.login_frame.reset_to_normal_state()
                except Exception:
                    pass  # Ignore any GUI-related errors during reset

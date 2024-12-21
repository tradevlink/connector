import asyncio
import websockets
import json
from typing import Dict, Any, Optional, Callable

class WebSocketClient:
    def __init__(self, uri: str):
        self.uri = uri
        self.websocket = None
        self.running = False
        self.message_handlers: Dict[str, Callable] = {}
        self.on_message: Optional[Callable] = None
        self.on_error: Optional[Callable] = None
        
    def on(self, message_type: str, handler: Callable):
        """Register a handler for a specific message type"""
        self.message_handlers[message_type] = handler
        
    def set_message_handler(self, handler: Callable):
        """Set a general message handler for all messages"""
        self.on_message = handler
        
    def set_error_handler(self, handler: Callable):
        """Set an error handler"""
        self.on_error = handler
    
    async def connect(self):
        """Connect to the WebSocket server"""
        try:
            # Add timeout for connection
            self.websocket = await asyncio.wait_for(
                websockets.connect(self.uri),
                timeout=30  # 30 seconds timeout
            )
            self.running = True
            return True
        except asyncio.TimeoutError:
            if self.on_error:
                self.on_error({"code": "CONNECTION_TIMEOUT", "reason": "Connection attempt timed out"})
            return False
        except Exception as e:
            if self.on_error:
                self.on_error({"code": "CONNECTION_FAILED", "reason": str(e)})
            return False
    
    async def receive_messages(self):
        """Receive and handle messages"""
        while self.running:
            try:
                message = await self.websocket.recv()
                
                # Try to parse JSON message
                try:
                    data = json.loads(message)
                    
                    # Handle message based on type if it exists
                    if isinstance(data, dict) and "type" in data:
                        message_type = data["type"]
                        if message_type in self.message_handlers:
                            await self._handle_async(self.message_handlers[message_type], data)
                    
                    # Call general message handler if exists
                    if self.on_message:
                        await self._handle_async(self.on_message, data)
                        
                except json.JSONDecodeError:
                    if self.on_error:
                        self.on_error({"code": "INVALID_JSON", "reason": f"Invalid JSON message received: {message}"})
                    
            except websockets.exceptions.ConnectionClosed as e:
                self.running = False
                if self.on_error:
                    self.on_error({"code": e.code, "reason": e.reason})
                break
            except Exception as e:
                if self.on_error:
                    self.on_error({"code": "RECEIVE_ERROR", "reason": str(e)})
    
    async def send_message(self, message_type: str, data: Dict[str, Any] = None):
        """Send a JSON message with type and data"""
        if not self.websocket:
            if self.on_error:
                self.on_error({"code": "NOT_CONNECTED", "reason": "Not connected to WebSocket server"})
            return False
            
        try:
            message = {
                "type": message_type,
                **(data or {})
            }
            await self.websocket.send(json.dumps(message))
            return True
        except Exception as e:
            if self.on_error:
                self.on_error({"code": "SEND_ERROR", "reason": str(e)})
            return False
    
    async def close(self):
        """Close the WebSocket connection"""
        self.running = False
        if self.websocket:
            try:
                await self.websocket.close()
            except Exception as e:
                if self.on_error:
                    self.on_error({"code": "CLOSE_ERROR", "reason": str(e)})
            finally:
                self.websocket = None  # Ensure websocket is cleared
            
    @staticmethod
    async def _handle_async(handler: Callable, *args, **kwargs):
        """Helper method to handle both async and sync handlers"""
        if asyncio.iscoroutinefunction(handler):
            await handler(*args, **kwargs)
        else:
            handler(*args, **kwargs)

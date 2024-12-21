import MetaTrader5 as mt5
from typing import Dict, List, Optional, Union, Tuple
import pandas as pd
from datetime import datetime
import time

class MT5Client:
    _instance = None
    watched_trades = {}
    
    def __new__(cls, main_frame=None):
        if cls._instance is None:
            cls._instance = super(MT5Client, cls).__new__(cls)
            cls._instance._initialized = False
        if main_frame is not None:
            cls._instance.main_frame = main_frame  # Always update main_frame reference
        return cls._instance
    
    def __init__(self, main_frame=None):
        if self._initialized:
            if main_frame is not None:
                self.main_frame = main_frame  # Update main_frame even if already initialized
            return
            
        self.main_frame = main_frame
        self._initialized = True
        self._connected = False
        self._connecting = False
        self._last_connect_attempt = 0

    def _log_message(self, message: str, webhook_type: str = None):
        """Safely log a message to UI and optionally send webhook"""
        try:
            if self.main_frame and hasattr(self.main_frame, 'winfo_exists') and self.main_frame.winfo_exists():
                self.main_frame.add_log(message)
                if webhook_type:
                    self.main_frame.send_webhook(message, webhook_type)
        except Exception:
            pass

    def connect(self) -> bool:
        """
        Initialize connection to MetaTrader 5 terminal
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        # Don't attempt to connect if we're already connected
        if self._connected:
            return True
            
        # Don't attempt to connect if another connection attempt is in progress
        if self._connecting:
            return False
            
        try:
            # Check if we've attempted to connect recently (within 5 seconds)
            current_time = time.time()
            if current_time - self._last_connect_attempt < 5:
                return False
                
            self._last_connect_attempt = current_time
            self._connecting = True
            
            # Initialize MT5 connection
            if not mt5.initialize():
                self._log_message(f"Failed to initialize MT5: {mt5.last_error()}", 'error')
                return False
            
            self._connected = True
            return True
            
        except Exception as e:
            self._log_message(f"Error connecting to MT5: {str(e)}", 'error')
            self._connected = False
            return False
        finally:
            self._connecting = False
    
    def disconnect(self) -> None:
        """Shutdown connection to MetaTrader 5 terminal"""
        if self._connected:
            mt5.shutdown()
            self._connected = False
    
    def is_connected(self) -> bool:
        """Check if connected to MetaTrader 5"""
        try:
            # If we think we're connected but MT5 isn't responding, reset state
            if self._connected and mt5.terminal_info() is None:
                self._connected = False
                self._connecting = False
                self._last_connect_attempt = 0
                mt5.shutdown()  # Clean shutdown when connection is lost
                return False
            return self._connected and mt5.terminal_info() is not None
        except:
            # If any error occurs, reset connection state
            self._connected = False
            self._connecting = False
            self._last_connect_attempt = 0
            try:
                mt5.shutdown()
            except:
                pass
            return False
    
    def get_account_info(self) -> Optional[Dict]:
        """
        Get account information
        
        Returns:
            dict: Account information or None if failed
        """
        if not self.is_connected():
            return None
            
        try:
            account_info = mt5.account_info()
            if account_info is None:
                return None
                
            return {
                'login': account_info.login,
                'server': account_info.server,
                'balance': account_info.balance,
                'equity': account_info.equity,
                'margin': account_info.margin,
                'free_margin': account_info.margin_free,
                'leverage': account_info.leverage,
                'currency': account_info.currency
            }
        except Exception as e:
            self._log_message(f"Error getting account info: {str(e)}", 'error')
            return None
    
    def place_market_order(self, symbol: str, order_type: str, volume: float, sl: float = None, tp: float = None, comment: str = "", pts: float = None) -> bool:
        """Place a market order"""
        try:
            # Check if symbol exists and select it in Market Watch
            if not mt5.symbol_select(symbol, True):
                self._log_message(f"Failed to select symbol {symbol} in Market Watch", 'error')
                return False

            # Get symbol info
            symbol_info = mt5.symbol_info_tick(symbol)
            if symbol_info is None:
                self._log_message(f"Failed to get symbol info for {symbol}", 'error')
                return False

            # Prepare the request
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": volume,
                "type": mt5.ORDER_TYPE_BUY if order_type.upper() == "BUY" else mt5.ORDER_TYPE_SELL,
                "price": symbol_info.ask if order_type.upper() == "BUY" else symbol_info.bid,
                "deviation": 20,
                "magic": 8723385465,
                "comment": comment,
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            
            # Send the order
            result = mt5.order_send(request)
            
            if result is None:
                self._log_message("Trade failed to be placed", 'error')
                return False
                
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                if result.retcode == 10027:
                    self._log_message("Algo Trading is not enabled at MetaTrader 5", 'error')
                else:
                    self._log_message(f"Trade failed to be executed. Error Code: {result.retcode}", 'error')
                return False
                
            # Log successful trade
            self._log_message(f"Trade #{result.order} executed. {symbol}, {order_type.lower()}@{result.price}, {result.volume}")
            
            # Add to watched_trades if pts is set
            if pts is not None:
                self.watched_trades[result.order] = {"runup": 0, "drawdown": 0, "pts": pts}
            
            # If sl or tp is set, modify the position
            if (sl is not None or tp is not None) and result.order > 0:
                self.modify_position(result.order, sl, tp)
            
            return True
            
        except Exception as e:
            self._log_message(f"Error placing market order: {str(e)}", 'error')
            return False

    def close_position(self, ticket: int) -> bool:
        """
        Close a specific position by its ticket number
        
        Args:
            ticket (int): Position ticket number
            
        Returns:
            bool: True if position closed successfully, False otherwise
        """
        if not self.is_connected():
            return False
            
        try:
            # Get position info
            position = mt5.positions_get(ticket=ticket)
            if position is None or len(position) == 0:
                self._log_message(f"Position {ticket} not found", 'error')
                return False
                
            position = position[0]
            
            # Prepare close request
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "position": ticket,
                "symbol": position.symbol,
                "volume": position.volume,
                "type": mt5.ORDER_TYPE_SELL if position.type == mt5.POSITION_TYPE_BUY else mt5.ORDER_TYPE_BUY,
                "price": mt5.symbol_info_tick(position.symbol).bid if position.type == mt5.POSITION_TYPE_BUY else mt5.symbol_info_tick(position.symbol).ask,
                "deviation": 20,
                "magic": 8723385465,
                "comment": "Closed by TradevLink",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            
            # Send close request
            result = mt5.order_send(request)
            
            if result is None:
                self._log_message(f"Trade #{ticket} could not be closed.", 'error')
                return False
                
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                self._log_message(f"Trade #{ticket} could not be closed. Error Code: {result.retcode}", 'error')
                return False
                
            self._log_message(f"Trade #{ticket} closed.")
            return True
            
        except Exception as e:
            self._log_message(f"Error closing position: {str(e)}", 'error')
            return False
    
    def get_positions(self) -> Optional[List[Dict]]:
        """
        Get all open positions
        
        Returns:
            list: List of open positions or None if failed
        """
        if not self.is_connected():
            return None
            
        try:
            positions = mt5.positions_get()
            if positions is None:
                return None
                
            return [{
                'ticket': pos.ticket,
                'symbol': pos.symbol,
                'type': 'BUY' if pos.type == mt5.ORDER_TYPE_BUY else 'SELL',
                'volume': pos.volume,
                'open_price': pos.price_open,
                'current_price': pos.price_current,
                'sl': pos.sl,
                'tp': pos.tp,
                'profit': pos.profit,
                'comment': pos.comment,
                'time': datetime.fromtimestamp(pos.time).strftime('%Y-%m-%d %H:%M:%S')
            } for pos in positions]
            
        except Exception as e:
            self._log_message(f"Error getting positions: {str(e)}", 'error')
            return None
    
    def modify_position(self, ticket: int, sl: float = None, tp: float = None) -> bool:
        """Modify an existing position"""
        try:
            # Get position details
            position = mt5.positions_get(ticket=ticket)
            if not position:
                return False
            position = position[0]

            # Calculate sl and tp based on position type
            is_buy = position.type == mt5.POSITION_TYPE_BUY
            if is_buy:
                sl_price = round(position.price_open - sl, 2) if sl is not None else None
                tp_price = round(position.price_open + tp, 2) if tp is not None else None
            else:  # SELL
                sl_price = round(position.price_open + sl, 2) if sl is not None else None
                tp_price = round(position.price_open - tp, 2) if tp is not None else None

            # Prepare the request
            request = {
                "action": mt5.TRADE_ACTION_SLTP,
                "position": ticket,
                "symbol": position.symbol,
            }

            # Only add sl and tp to request if they are set
            if sl_price is not None:
                request["sl"] = sl_price
            if tp_price is not None:
                request["tp"] = tp_price

            # Send the modification request
            result = mt5.order_send(request)
            if result is not None and result.retcode == mt5.TRADE_RETCODE_DONE:
                # Build modification log message
                mod_msg = f"Trade #{ticket} modified."
                if tp_price is not None:
                    mod_msg += f" TP@{tp_price}"
                if sl_price is not None:
                    if tp_price is not None:
                        mod_msg += ","
                    mod_msg += f" SL@{sl_price}"
                self._log_message(mod_msg)
                return True
            return False

        except Exception as e:
            self._log_message(f"Error modifying position: {str(e)}", 'error')
            return False

    def close_positions_by_symbol(self, symbol: str) -> bool:
        """Close all positions for a given symbol"""
        try:
            # Get all positions for the symbol
            positions = mt5.positions_get(symbol=symbol)
            if positions is None:
                return True  # No positions to close
            
            success = True
            for position in positions:
                if not self.close_position(position.ticket):
                    success = False
                    
            return success
            
        except Exception as e:
            self._log_message(f"Error closing positions for {symbol}: {str(e)}", 'error')
            return False

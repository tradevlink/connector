from datetime import datetime
from utils.periodic_task import PeriodicTask
from utils.mt5_client import MT5Client
from utils.trade_filter import TradeFilter
import time

class TradeStatusTask(PeriodicTask):
    def __init__(self, main_frame):
        super().__init__(interval_seconds=1)
        self.main_frame = main_frame
        self.mt5_client = None
        self.trade_filter = None
        self._first_mt5_attempt = True
        self._account_found = False
        self._connection_start_time = None
        
    def stop(self):
        """Stop the task and cleanup resources"""
        super().stop()
        if self.mt5_client:
            try:
                self.mt5_client.shutdown()
            except Exception:
                pass
        self.mt5_client = None
        self.trade_filter = None
        self.main_frame = None  # Clear reference to prevent memory leaks
        
    def task(self):
        """Check and maintain MT5 connection and account status"""
        try:
            # Check if main_frame is still valid
            if not self.main_frame or not hasattr(self.main_frame, 'winfo_exists') or not self.main_frame.winfo_exists():
                return
                
            # Initialize MT5 client on first task run
            if self.mt5_client is None:
                self.mt5_client = MT5Client()
                self.trade_filter = TradeFilter(self.main_frame)
                return
                
            # Try to connect if not connected
            if not self.mt5_client.is_connected():
                # Reset account found flag when connection is lost
                if self._account_found:
                    self._account_found = False
                    self._first_mt5_attempt = True  # Reset first attempt flag to show message again
                    self._connection_start_time = None  # Reset connection timing
                
                # Start timing connection attempts
                if self._connection_start_time is None:
                    self._connection_start_time = time.time()
                
                # Only show initial message after 5 seconds of failed attempts
                if self._first_mt5_attempt and time.time() - self._connection_start_time >= 5:
                    try:
                        if self.main_frame and self.main_frame.winfo_exists():
                            self.main_frame.add_log("No connection with MetaTrader5 could be established")
                            self._first_mt5_attempt = False
                    except Exception:
                        pass
                
                # Try to connect
                self.mt5_client.connect()
                return
            
            # Reset connection timing when connected
            self._connection_start_time = None
            
            # Check account info if connected
            account_info = self.mt5_client.get_account_info()
            
            # If we're connected but no account info
            if account_info is None:
                if not self._account_found:  # Only show once when transitioning to this state
                    try:
                        if self.main_frame and self.main_frame.winfo_exists():
                            self.main_frame.add_log("Connected with MetaTrader5. No account found.")
                            self._account_found = False
                    except Exception:
                        pass
                return
            
            # If we have account info and haven't logged it yet
            if not self._account_found:
                try:
                    if self.main_frame and self.main_frame.winfo_exists():
                        self.main_frame.add_log(f"Connected with MetaTrader5. Current Account: #{account_info['login']}")
                        self._account_found = True
                except Exception:
                    pass

            # Only monitor trades when we have a confirmed connection and account
            if self._account_found and self.mt5_client.is_connected():
                # Monitor watched trades
                if hasattr(self.mt5_client, 'watched_trades') and self.mt5_client.watched_trades:
                    # Get all current positions
                    positions = self.mt5_client.get_positions()
                    if positions is None:
                        return

                    # Convert positions to a dict for faster lookup
                    active_positions = {pos['ticket']: pos for pos in positions}
                    
                    # Create a list of orders to remove to avoid dictionary size change during iteration
                    orders_to_remove = []
                    
                    # Check each watched trade
                    for order_id, trade_data in self.mt5_client.watched_trades.items():
                        if order_id not in active_positions:
                            # Position is closed, mark for removal
                            orders_to_remove.append(order_id)
                            continue

                        position = active_positions[order_id]
                        
                        # Find rule for this symbol
                        symbol = position['symbol']
                        rule = None
                        for r in self.trade_filter.config.get("alert_rules", []):
                            if r.get("symbol") == symbol:
                                rule = r
                                break
                        
                        # If we found a rule and trading is paused, close the position
                        if rule and rule.get("active_schedule", True):
                            if self.trade_filter.is_trading_paused(symbol, rule, check_close_on_pause=True):
                                try:
                                    if self.main_frame and self.main_frame.winfo_exists():
                                        self.main_frame.add_log(f"Closing trade #{order_id} due to trading pause for {symbol}")
                                        self.mt5_client.close_position(order_id)
                                        orders_to_remove.append(order_id)
                                except Exception:
                                    continue
                                continue

                        current_price = position['current_price']
                        open_price = position['open_price']
                        pts = trade_data['pts']
                        
                        # Update runup and drawdown based on position type
                        if position['type'] == 'BUY':
                            # For buy positions, track highest price for runup and lowest for drawdown
                            trade_data['runup'] = max(trade_data['runup'], current_price)
                            trade_data['drawdown'] = min(trade_data['drawdown'], current_price) if trade_data['drawdown'] > 0 else current_price
                            
                            # Check if runup shows profit and current price has dropped more than pts
                            # Also ensure we still have profit
                            if (trade_data['runup'] > open_price and 
                                (trade_data['runup'] - current_price) >= pts and 
                                position['profit'] > 0):
                                try:
                                    if self.main_frame and self.main_frame.winfo_exists():
                                        self.main_frame.add_log(f"Trade #{order_id} reached PTS@{current_price}, RUN-UP@{trade_data['runup']}")
                                        self.mt5_client.close_position(order_id)
                                        orders_to_remove.append(order_id)
                                except Exception:
                                    continue
                                
                        else:  # SELL position
                            # For sell positions, track lowest price for runup and highest for drawdown
                            trade_data['runup'] = min(trade_data['runup'], current_price) if trade_data['runup'] > 0 else current_price
                            trade_data['drawdown'] = max(trade_data['drawdown'], current_price)
                            
                            # Check if runup shows profit and current price has risen more than pts
                            # Also ensure we still have profit
                            if (trade_data['runup'] < open_price and 
                                (current_price - trade_data['runup']) >= pts and 
                                position['profit'] > 0):
                                try:
                                    if self.main_frame and self.main_frame.winfo_exists():
                                        self.main_frame.add_log(f"Trade #{order_id} reached PTS@{current_price}, RUN-UP@{trade_data['runup']}")
                                        self.mt5_client.close_position(order_id)
                                        orders_to_remove.append(order_id)
                                except Exception:
                                    continue
                    
                    # Safely remove closed positions from watched_trades
                    for order_id in orders_to_remove:
                        self.mt5_client.watched_trades.pop(order_id, None)
                
        except Exception as e:
            # Only try to log errors if main_frame is still valid
            if self.main_frame and hasattr(self.main_frame, 'winfo_exists') and self.main_frame.winfo_exists():
                try:
                    print(f"Error in trade status task: {str(e)}")
                except Exception:
                    pass

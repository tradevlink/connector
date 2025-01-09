from datetime import datetime, timedelta
from typing import Optional, Dict
from utils.config_manager import ConfigManager
from utils.mt5_client import MT5Client
import time

class TradeFilter:
    def __init__(self, main_frame):
        self.config = ConfigManager()
        self.mt5_client = MT5Client(main_frame)  # Pass main_frame to ensure MT5Client has the right reference
        self.main_frame = main_frame
        self.EXECUTION_THRESHOLD_MS = 5000  # 5 seconds in milliseconds

    def _convert_time_to_seconds(self, time_str: str) -> int:
        """Convert time string (HH:MM or HH:MM:SS) to seconds"""
        try:
            # Try HH:MM:SS format first
            time_parts = time_str.split(":")
            if len(time_parts) == 3:
                hours, minutes, seconds = map(int, time_parts)
            else:
                # HH:MM format
                hours, minutes = map(int, time_parts)
                seconds = 0
            return hours * 3600 + minutes * 60 + seconds
        except:
            return 0

    def _log_message(self, message: str, webhook_type: str = None):
        """Safely log a message to UI and optionally send webhook"""
        try:
            if self.main_frame and hasattr(self.main_frame, 'winfo_exists') and self.main_frame.winfo_exists():
                self.main_frame.add_log(message)
                if webhook_type:
                    self.main_frame.send_webhook(message, webhook_type)
        except Exception:
            pass

    def _measure_execution_time(self, operation_name: str, start_time: float) -> None:
        """Measure execution time and log if it exceeds threshold"""
        execution_time_ms = (time.time() - start_time) * 1000
        if execution_time_ms > self.EXECUTION_THRESHOLD_MS:
            self._log_message(
                f"Warning: {operation_name} took too long to execute ({int(execution_time_ms)}ms)", 
                'error'
            )

    def is_trading_paused(self, symbol: str, rule: dict, check_close_on_pause: bool = False) -> bool:
        """
        Check if trading is currently paused based on the schedule in the rule.
        
        Args:
            symbol (str): The trading symbol for logging purposes
            rule (dict): The rule containing the schedule configuration
            check_close_on_pause (bool): If True, only return True if close_positions_on_pause is also True
            
        Returns:
            bool: True if trading is paused (and close_positions_on_pause is True if check_close_on_pause is True), False otherwise
        """
        if not rule.get("active_schedule", True):
            return False
            
        # Get current time
        now = datetime.now()
        current_day = now.strftime("%A")  # Get day name (Monday, Tuesday, etc.)
        
        # Find schedule for current day and previous day
        current_day_schedule = None
        previous_day_schedule = None
        previous_day = (now - timedelta(days=1)).strftime("%A")
        
        for schedule in rule.get("schedule", []):
            if schedule.get("day") == current_day:
                current_day_schedule = schedule
            elif schedule.get("day") == previous_day:
                previous_day_schedule = schedule
                
        # Get current timestamp
        now_timestamp = int(time.time())
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
        yesterday_start = today_start - 86400  # 24 hours in seconds
        
        # Check if we're in a pause period
        in_pause = False
        close_on_pause = False
        
        # Check current day's schedule
        if current_day_schedule:
            pause_start = current_day_schedule.get("pause_start", "")
            pause_duration = current_day_schedule.get("pause_duration", "")
            
            pause_start_seconds = self._convert_time_to_seconds(pause_start)
            pause_duration_seconds = self._convert_time_to_seconds(pause_duration)
            
            pause_start_timestamp = int(today_start) + pause_start_seconds
            pause_end_timestamp = pause_start_timestamp + pause_duration_seconds
            
            if pause_start_timestamp <= now_timestamp <= pause_end_timestamp:
                in_pause = True
                if check_close_on_pause:
                    close_on_pause = current_day_schedule.get("close_positions_on_pause", False)
        
        # Check previous day's schedule for overlapping pauses
        if previous_day_schedule and not in_pause:
            pause_start = previous_day_schedule.get("pause_start", "")
            pause_duration = previous_day_schedule.get("pause_duration", "")
            
            pause_start_seconds = self._convert_time_to_seconds(pause_start)
            pause_duration_seconds = self._convert_time_to_seconds(pause_duration)
            
            pause_start_timestamp = int(yesterday_start) + pause_start_seconds
            pause_end_timestamp = pause_start_timestamp + pause_duration_seconds
            
            # Check if the pause from previous day extends to current day
            if pause_end_timestamp > today_start and now_timestamp <= pause_end_timestamp:
                in_pause = True
                if check_close_on_pause:
                    close_on_pause = previous_day_schedule.get("close_positions_on_pause", False)
        
        # If we're checking for close_on_pause, both conditions must be true
        if check_close_on_pause:
            return in_pause and close_on_pause
        
        return in_pause

    def process_trade(self, symbol: str, volume: float, action: str = "buy") -> bool:
        """
        Process a trade request for a given symbol and volume.
        
        Args:
            symbol (str): The trading symbol (e.g. 'EURUSD')
            volume (float): The trading volume from alert. Can be None.
            action (str): Trade action, either 'buy' or 'sell'. Defaults to 'buy'
            
        Returns:
            bool: True if trade was processed successfully, False otherwise
        """
        # Check if alerts are enabled in config
        if not self.config.get("listen_to_alerts", False):
            self._log_message("Cannot process trade: Alerts are disabled in settings")
            return False

        # Check MT5 connection first
        if not self.mt5_client.is_connected():
            self._log_message("Cannot process trade: Not connected to MT5", 'error')
            return False

        # Find rule for this symbol
        rule = None
        for r in self.config.get("alert_rules", []):
            if r.get("symbol") == symbol:
                rule = r
                break
                
        if not rule:
            self._log_message(f"No rule found for symbol {symbol}. Trade could not be executed.", 'error')
            return False

        # Determine which volume to use
        trade_volume = rule.get("volume", 0.0)  # Default from rule
        if volume is not None and rule.get("volume_from_alert", False):
            trade_volume = volume  # Use volume from alert if specified and enabled

        # Check if trading schedule is active
        if rule.get("active_schedule", True):
            if self.is_trading_paused(symbol, rule, check_close_on_pause=False):
                self._log_message(f"Trading for {symbol} is paused due to schedule. Trade could not be executed.")
                return False
        
        # If we get here, all checks passed
        # Place the order using MT5Client
        try:
            if self.mt5_client.is_connected():
                # Close existing positions if configured
                if rule.get("close_positions_on_entry", False):
                    start_time = time.time()
                    close_result = self.mt5_client.close_positions_by_symbol(symbol)
                    self._measure_execution_time("Closing positions", start_time)
                
                # Get the values from the rule
                take_profit = rule.get("take_profit", 0.0)
                stop_loss = rule.get("stop_loss", 0.0)
                pts = rule.get("profit_trailing_stop", 0.0)
                
                # Pass None if tp/sl is 0
                tp = take_profit if take_profit > 0 else None
                sl = stop_loss if stop_loss > 0 else None
                pts_value = pts if pts != 0.0 else None
                
                # Place the market order
                start_time = time.time()
                result = self.mt5_client.place_market_order(
                    symbol=symbol,
                    order_type=action.lower(),
                    volume=trade_volume,
                    sl=sl,
                    tp=tp,
                    comment="TradevLink Alert",
                    pts=pts_value
                )
                self._measure_execution_time("Trade execution", start_time)
                return result
                
            return False
            
        except Exception as e:
            self._log_message(f"Error placing trade: {str(e)}", 'error')
            return False

from flask import Flask, request, jsonify
import threading
import os
import re
from werkzeug.serving import make_server
import queue

class FlaskServer:
    def __init__(self, host='127.0.0.1', port=5000, use_ssl=False, certfile=None, keyfile=None):
        self.app = Flask(__name__)
        self.host = host
        self.port = port
        self.use_ssl = use_ssl
        self.certfile = certfile
        self.keyfile = keyfile
        self.server = None
        self.server_thread = None
        self.error_queue = queue.Queue()
        self.main_frame = None  # Will be set by the app
        self.config = None  # Will be set by the app
        
        # Define routes
        @self.app.route('/', methods=['GET'])
        def home():
            return jsonify({"status": "running TradevLink server"})
            
        @self.app.route('/alert/<license_key>', methods=['POST'])
        def alert(license_key):
            # Validate license key
            if not self.config or license_key != self.config.get("license_key", ""):
                return jsonify({"error": "Invalid license key"}), 401
            
            # Get and validate request body
            try:
                body = request.get_data(as_text=True).strip()
                if not body:
                    return jsonify({"error": "Empty request body"}), 400
                
                # Split body into parts
                parts = body.split(',')
                if len(parts) not in [2, 3]:
                    return jsonify({"error": "Invalid request format. Expected: symbol,action[,volume]"}), 400
                
                # Validate symbol (allow alphanumeric, $, ., -, _)
                symbol = parts[0].strip()
                if not re.match(r'^[\w\$\.\-]+$', symbol):
                    return jsonify({"error": "Invalid symbol format"}), 400
                
                # Validate action
                action = parts[1].strip().lower()
                if action not in ['buy', 'sell']:
                    return jsonify({"error": "Invalid action. Must be 'buy' or 'sell'"}), 400
                
                # Validate volume if provided
                volume = None
                if len(parts) == 3:
                    try:
                        volume = float(parts[2].strip())
                        if volume <= 0:
                            return jsonify({"error": "Volume must be greater than 0"}), 400
                    except ValueError:
                        return jsonify({"error": "Invalid volume format"}), 400
                
                # Process the alert through trade filter
                if self.main_frame and self.main_frame.trade_filter:
                    # Log the incoming alert
                    log_message = f"Incoming local alert: {symbol}, {action.lower()}"
                    if volume is not None:
                        log_message += f", {volume}"
                    self.main_frame.add_log(log_message)
                    self.main_frame.send_webhook(log_message, 'alert')
                    
                    success = self.main_frame.trade_filter.process_trade(symbol, volume, action)
                    if success:
                        return jsonify({"status": "success"}), 200
                    else:
                        return jsonify({"error": "Trade processing failed"}), 400
                else:
                    return jsonify({"error": "Trade filter not initialized"}), 500
                    
            except Exception as e:
                return jsonify({"error": str(e)}), 500
    
    def start(self):
        def run_server():
            try:
                ssl_context = None
                if self.use_ssl and self.certfile and self.keyfile:
                    if not os.path.exists(self.certfile) or not os.path.exists(self.keyfile):
                        raise FileNotFoundError("SSL certificate or key file not found")
                    ssl_context = (self.certfile, self.keyfile)
                
                self.server = make_server(self.host, self.port, self.app, ssl_context=ssl_context)
                self.server.serve_forever()
            except Exception as e:
                self.error_queue.put(e)
                return
        
        self.server_thread = threading.Thread(target=run_server)
        self.server_thread.daemon = True
        self.server_thread.start()
        
        # Wait a short time to check for any startup errors
        try:
            error = self.error_queue.get(timeout=1.0)
            raise error
        except queue.Empty:
            # No error occurred during startup
            pass
    
    def stop(self):
        if self.server:
            self.server.shutdown()
            self.server = None
            self.server_thread = None

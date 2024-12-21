import threading
import time
import traceback

class PeriodicTask:
    def __init__(self, interval_seconds=1):
        self.interval = interval_seconds
        self._running = False
        self._thread = None
        
    def start(self):
        """Start the periodic task in a background thread"""
        if not self._running:
            self._running = True
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()
    
    def stop(self):
        """Stop the periodic task"""
        self._running = False
        if self._thread:
            self._thread = None
            
    def _run(self):
        """Main loop that runs the task periodically"""
        while self._running:
            try:
                self.task()
            except Exception as e:
                print(f"Error in periodic task: {str(e)}")
                print(traceback.format_exc())
            time.sleep(self.interval)
    
    def task(self):
        """Override this method in subclass to define the task"""
        pass

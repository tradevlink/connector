import requests
from utils.dev_mode import is_dev_mode

# API URLs
DEV_BASE_URL = "http://localhost:3001"
PROD_BASE_URL = "https://api.tradevlink.com"

class APIClient:
    def __init__(self):
        self.base_url = DEV_BASE_URL if is_dev_mode() else PROD_BASE_URL
        self.session = requests.Session()
    
    def post(self, endpoint, data=None, json=None, timeout=None):
        url = f"{self.base_url}{endpoint}"
        response = self.session.post(url, data=data, json=json, timeout=timeout)
        return response
    
    def close(self):
        self.session.close()

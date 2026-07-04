"""Configuration settings for Dojobay application."""
from pathlib import Path

# Application paths
BASE_DIR = Path(__file__).parent
CACHE_FILE = BASE_DIR / "status_cache.json"
DOJOS_DATA_FILE = BASE_DIR / "dojos_data.json"

# Tor proxy configuration
DEFAULT_PROXIES = {
    "http": "socks5h://127.0.0.1:9050",
    "https": "socks5h://127.0.0.1:9050"
}

# Cache settings
CACHE_DURATION = 600  # 10 minutes in seconds

# Request settings
REQUEST_TIMEOUT = 45  # seconds (increased for slow/unreliable Tor connections)

# Server settings
HOST = '0.0.0.0'
PORT = 5002
DEBUG = False

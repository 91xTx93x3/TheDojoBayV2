"""Configuration settings for Dojobay application."""
from pathlib import Path
import secrets as _secrets

# Application paths
BASE_DIR = Path(__file__).parent
CACHE_FILE = BASE_DIR / "status_cache.json"
UPTIME_HISTORY_FILE = BASE_DIR / "uptime_history.json"
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

# Submissions file for user-submitted dojos
SUBMISSIONS_FILE = BASE_DIR / 'dojo_submissions.json'

# ── Auth47 / PayNym ────────────────────────────────────────────────────────────
import os as _os
SITE_URL = _os.environ.get('SITE_URL', 'https://dojobay.pw')
AUTH47_CALLBACK_URL = f"{SITE_URL}/api/auth47/verify"

# Secret key for Flask sessions (generated once, stored in .secret_key)
_secret_key_file = BASE_DIR / '.secret_key'
try:
    if _secret_key_file.exists():
        SECRET_KEY = _secret_key_file.read_text().strip()
    else:
        SECRET_KEY = _secrets.token_hex(32)
        _secret_key_file.write_text(SECRET_KEY)
except Exception:
    SECRET_KEY = _secrets.token_hex(32)

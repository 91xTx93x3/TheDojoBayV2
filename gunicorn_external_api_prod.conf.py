# Gunicorn configuration for Dojobay External API - Production
# Usage: gunicorn -c gunicorn_external_api_prod.conf.py external_api:app

import os
from pathlib import Path

# Get workspace directory
WORKSPACE_DIR = Path(__file__).resolve().parent

# Server Socket
bind = os.getenv("DOJOBAY_BIND", "127.0.0.1:8080")
backlog = 2048

# Worker Processes - tuned for API workload
# For external API, we can use more workers since it's stateless
workers = int(os.getenv("DOJOBAY_WORKERS", 4))
worker_class = "sync"  # Use sync for better stability with Flask-CORS
threads = 1
worker_connections = 1000
timeout = 30
keepalive = 5

# Logging
accesslog = os.getenv("DOJOBAY_ACCESS_LOG", "-")  # stdout
errorlog = os.getenv("DOJOBAY_ERROR_LOG", "-")    # stderr
loglevel = os.getenv("DOJOBAY_LOG_LEVEL", "info").lower()

# Process Naming
proc_name = "dojobay-api"

# Server Mechanics
daemon = False
pidfile = os.getenv("DOJOBAY_PID_FILE", None)
umask = 0o002
user = os.getenv("DOJOBAY_USER", None)
group = os.getenv("DOJOBAY_GROUP", None)
tmp_upload_dir = None

# Security
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190

# SSL/TLS (uncomment and set paths if using HTTPS)
# keyfile = os.getenv("DOJOBAY_KEY_FILE", None)
# certfile = os.getenv("DOJOBAY_CERT_FILE", None)

# Performance
max_requests = int(os.getenv("DOJOBAY_MAX_REQUESTS", 10000))
max_requests_jitter = int(os.getenv("DOJOBAY_MAX_REQUESTS_JITTER", 1000))

# HTTP Settings
keep_alive = 5

def on_starting(server):
    """Called just before the master process is initialized."""
    print("[GUNICORN] Starting Dojobay External API")
    print(f"[GUNICORN] Workers: {workers}")
    print(f"[GUNICORN] Bind: {bind}")
    print(f"[GUNICORN] Log level: {loglevel}")

def when_ready(server):
    """Called just after the server is started."""
    print("[GUNICORN] Server is ready. Spawning workers")

def on_exit(server):
    """Called just before exiting Gunicorn."""
    print("[GUNICORN] Shutting down Dojobay External API")

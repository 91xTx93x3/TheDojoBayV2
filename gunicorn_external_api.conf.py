# Gunicorn configuration for external_api.py

# Server Socket
bind = "0.0.0.0:8080"
backlog = 2048

# Worker Processes
workers = 2
worker_class = "gthread"
threads = 4
worker_connections = 1000
timeout = 30
keepalive = 2

# Logging
accesslog = "/root/dojobay/external_api_access.log"
errorlog = "/root/dojobay/external_api_error.log"
loglevel = "info"

# Process Naming
proc_name = "dojobay_external_api"

# Server Mechanics
daemon = True
pidfile = "/root/dojobay/external_api.pid"
umask = 0
user = None
group = None
tmp_upload_dir = None

# Security
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190

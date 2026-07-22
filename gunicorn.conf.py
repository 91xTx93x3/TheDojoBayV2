# Gunicorn configuration file

# Server Socket
bind = "0.0.0.0:5002"
backlog = 2048

# Worker Processes
workers = 1
worker_class = "gthread"
threads = 2
worker_connections = 1000
timeout = 30
keepalive = 2

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"

# Process Naming
proc_name = "dojobay"

# Server Mechanics
daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None

# Security
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190


# Startup hooks
def post_worker_init(worker):
    """Initialize background checker after worker initialization."""
    from app import background_checker
    background_checker.start()
    print(f"[WORKER {worker.pid}] Attempted to start background checker")

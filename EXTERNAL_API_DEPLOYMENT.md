# Dojobay External API - Production Deployment Guide

## Overview

The Dojobay External API is a standalone REST API that provides external applications with easy access to Dojo node information. This guide covers production deployment, security, and best practices.

## Key Features

- ✅ **Stateless Design**: No internal state, easy to scale horizontally
- ✅ **Authentication**: Bearer token-based security
- ✅ **CORS Support**: Browser-based requests from external origins
- ✅ **Health Checks**: Built-in health endpoint for monitoring
- ✅ **Comprehensive Documentation**: Auto-generated API docs at `/api/docs`
- ✅ **Production Ready**: Security headers, proper logging, error handling
- ✅ **Easy Deployment**: Gunicorn configuration included

## Architecture

```
External App 1 ──┐
External App 2 ──┼──> Gunicorn Workers (external_api.py)
External App 3 ──┤        │
                 │        └──> dojos_data.json
Browser   ───────┘
```

## Prerequisites

- Python 3.8+
- pip/venv
- Linux/Unix environment (for production)
- Git (optional, for deployment)

## Installation

### 1. Install Dependencies

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install requirements
pip install -r requirements.txt

# Install Gunicorn for production
pip install gunicorn
```

### 2. Set Environment Variables

**CRITICAL**: You MUST set a secure API token before starting.

```bash
# Development (example)
export DOJOBAY_API_TOKEN="your-development-token-here"

# Production (use a strong, random token)
export DOJOBAY_API_TOKEN="$(openssl rand -hex 32)"
```

For production, store the token securely:

- Use environment variable management (systemd, Docker secrets, etc.)
- Never commit tokens to git
- Rotate tokens regularly
- Use strong, random tokens (min 32 characters)

### 3. Verify the Data File

Ensure `dojos_data.json` exists and contains valid data:

```bash
# Check the file exists
ls -la dojos_data.json

# Verify JSON is valid
python3 -c "import json; json.load(open('dojos_data.json'))"
```

## Running in Development

For testing and development:

```bash
# Set token
export DOJOBAY_API_TOKEN="test-token"

# Run with Flask development server
python3 external_api.py

# API will be available at http://localhost:8080
```

Test with curl:

```bash
curl -H "Authorization: Bearer test-token" http://localhost:8080/api/dojos
```

## Production Deployment

### Using the Deploy Script (Recommended)

```bash
# Make script executable
chmod +x deploy_api.sh

# Set token
export DOJOBAY_API_TOKEN="your-production-token"

# Start API
./deploy_api.sh start

# Check status
./deploy_api.sh status

# Stop API
./deploy_api.sh stop

# Restart API
./deploy_api.sh restart
```

### Manual Gunicorn Start

```bash
# Set required environment variables
export DOJOBAY_API_TOKEN="your-production-token"
export DOJOBAY_BIND="0.0.0.0:8080"  # If behind reverse proxy
export DOJOBAY_WORKERS=4
export DOJOBAY_LOG_LEVEL="info"

# Start with Gunicorn
gunicorn -c gunicorn_external_api_prod.conf.py external_api:app
```

### Configuration Options

Set via environment variables:

| Variable               | Default          | Description                                 |
| ---------------------- | ---------------- | ------------------------------------------- |
| `DOJOBAY_API_TOKEN`    | **REQUIRED**     | API authentication token                    |
| `DOJOBAY_BIND`         | `127.0.0.1:8080` | Address and port to bind to                 |
| `DOJOBAY_WORKERS`      | `4`              | Number of Gunicorn workers                  |
| `DOJOBAY_LOG_LEVEL`    | `info`           | Logging level (debug, info, warning, error) |
| `DOJOBAY_ACCESS_LOG`   | stdout           | Path to access log file                     |
| `DOJOBAY_ERROR_LOG`    | stderr           | Path to error log file                      |
| `DOJOBAY_MAX_REQUESTS` | `10000`          | Max requests per worker before restart      |
| `DOJOBAY_USER`         | current user     | User to run Gunicorn as                     |
| `DOJOBAY_GROUP`        | current group    | Group to run Gunicorn as                    |

## Running Behind a Reverse Proxy

For production, always use a reverse proxy (Nginx, Apache, Caddy, etc.)

### Nginx Example

```nginx
upstream dojobay_api {
    server 127.0.0.1:8080;
}

server {
    listen 443 ssl http2;
    server_name api.example.com;

    # SSL certificates (use Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/api.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.example.com/privkey.pem;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req zone=api burst=20 nodelay;

    location / {
        proxy_pass http://dojobay_api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeouts
        proxy_connect_timeout 10s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
    }
}
```

## Systemd Service (Linux)

Create `/etc/systemd/system/dojobay-api.service`:

```ini
[Unit]
Description=Dojobay External API
After=network.target

[Service]
Type=notify
User=dojobay
WorkingDirectory=/opt/dojobay
Environment="DOJOBAY_API_TOKEN=your-token-here"
Environment="DOJOBAY_WORKERS=4"
Environment="DOJOBAY_BIND=127.0.0.1:8080"
ExecStart=/opt/dojobay/venv/bin/gunicorn -c gunicorn_external_api_prod.conf.py external_api:app
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable dojobay-api
sudo systemctl start dojobay-api
sudo systemctl status dojobay-api
```

## Docker Deployment

Create `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# Copy application
COPY external_api.py .
COPY dojos_data.json .

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Run with Gunicorn
EXPOSE 8080
CMD ["gunicorn", "-c", "gunicorn_external_api_prod.conf.py", "external_api:app"]
```

Build and run:

```bash
docker build -t dojobay-api .
docker run -e DOJOBAY_API_TOKEN="your-token" -p 8080:8080 dojobay-api
```

## Security Checklist

- [ ] Set strong `DOJOBAY_API_TOKEN` (min 32 characters)
- [ ] Never use Flask dev server in production
- [ ] Run behind HTTPS reverse proxy
- [ ] Set `DOJOBAY_API_DEBUG=false` (should be default)
- [ ] Use appropriate file permissions (600 for config files)
- [ ] Run as unprivileged user (never as root)
- [ ] Keep dependencies updated
- [ ] Monitor logs for suspicious activity
- [ ] Implement rate limiting at reverse proxy level
- [ ] Use firewall to restrict access if needed
- [ ] Enable security headers (included in API)
- [ ] Rotate API token regularly

## Monitoring

### Health Check

```bash
curl http://localhost:8080/health
```

Response:

```json
{
  "status": "ok",
  "timestamp": "2026-07-04T12:00:00Z",
  "version": "1.0"
}
```

### Logs

Monitor logs for errors:

```bash
# If using deploy script
tail -f logs/error.log
tail -f logs/access.log

# If using systemd
journalctl -u dojobay-api -f

# If using Docker
docker logs -f container_id
```

### Prometheus Metrics

Consider adding Prometheus monitoring with `prometheus-flask-exporter`:

```python
from prometheus_flask_exporter import PrometheusMetrics
metrics = PrometheusMetrics(app)
```

## API Usage Examples

### Get All Dojos

```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  https://api.example.com/api/dojos
```

### Get Mainnet Dojos Only

```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "https://api.example.com/api/dojos?network=mainnet"
```

### Check API Info

```bash
curl https://api.example.com/api/info
```

### View Documentation

Visit: `https://api.example.com/api/docs`

## Troubleshooting

### API won't start

1. Check token is set:

   ```bash
   echo $DOJOBAY_API_TOKEN
   ```

2. Check data file exists:

   ```bash
   ls -la dojos_data.json
   ```

3. Check JSON validity:

   ```bash
   python3 -c "import json; json.load(open('dojos_data.json'))"
   ```

4. Check port availability:
   ```bash
   lsof -i :8080
   ```

### Slow responses

1. Increase workers in `gunicorn_external_api_prod.conf.py`
2. Check system resources (CPU, memory)
3. Enable caching at reverse proxy level
4. Monitor with `top` or `htop`

### Connection refused

1. Check if API is running: `./deploy_api.sh status`
2. Verify bind address and port are correct
3. Check firewall rules
4. Verify reverse proxy is configured correctly

### Authentication failing

1. Verify token is set correctly: `echo $DOJOBAY_API_TOKEN`
2. Check Authorization header format: `Authorization: Bearer <token>`
3. Verify token matches between client and server
4. Check logs for authentication attempts

## Performance Tuning

### Recommended Settings by Load

**Low (~10 requests/sec):**

```bash
DOJOBAY_WORKERS=2
DOJOBAY_BIND=127.0.0.1:8080
```

**Medium (~50 requests/sec):**

```bash
DOJOBAY_WORKERS=4
DOJOBAY_BIND=0.0.0.0:8080
```

**High (~200+ requests/sec):**

```bash
DOJOBAY_WORKERS=8
DOJOBAY_BIND=0.0.0.0:8080
# Also use load balancer, caching, CDN
```

### Connection Pooling

For high-traffic scenarios, configure reverse proxy connection pooling:

```nginx
upstream dojobay_api {
    keepalive 32;
    server 127.0.0.1:8080;
    server 127.0.0.1:8081;
    server 127.0.0.1:8082;
}
```

## Maintenance

### Updating Data

Replace `dojos_data.json` without restarting:

```bash
# Update file
cp new_dojos_data.json dojos_data.json

# API will pick up changes on next request
curl http://localhost:8080/api/dojos
```

### Rotating API Token

1. Generate new token: `openssl rand -hex 32`
2. Update environment variable
3. Restart API: `./deploy_api.sh restart`
4. Update client applications with new token

### Upgrading Dependencies

```bash
source venv/bin/activate
pip install --upgrade -r requirements.txt
./deploy_api.sh restart
```

## Support

- Check logs: `tail -f logs/error.log`
- Test endpoint: `curl http://localhost:8080/health`
- View docs: Visit `/api/docs` endpoint
- Check configuration: `cat gunicorn_external_api_prod.conf.py`

## License

Same as main Dojobay project.

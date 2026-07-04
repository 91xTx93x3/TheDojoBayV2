# API Subdomain Setup - api.dojobay.pw

## Overview

This guide will expose your Dojobay API to the internet at `https://api.dojobay.pw` using Nginx as a reverse proxy and Let's Encrypt for SSL.

## Prerequisites

- ✅ Dojobay API running on `127.0.0.1:8090`
- ✅ Nginx installed and running
- ✅ Domain `dojobay.pw` already configured
- ✅ Access to DNS settings

## Server Information

**Your Server IP**: `5.181.181.21`

## Setup Instructions

### Step 1: Configure DNS (5-15 minutes)

Go to your DNS provider (Godaddy, Namecheap, Cloudflare, etc) and add:

**Option A: A Record (Recommended)**
```
Name:    api
Type:    A
Value:   5.181.181.21
TTL:     3600
```

**Option B: CNAME**
```
Name:    api
Type:    CNAME
Value:   dojobay.pw
TTL:     3600
```

**Verify DNS Resolution**:
```bash
nslookup api.dojobay.pw
# or
dig api.dojobay.pw +short
```

Wait until you see the IP address returned (5.181.181.21).

### Step 2: Run Setup Script

Once DNS is propagated (usually 5-15 minutes), run:

```bash
sudo bash /root/dojobay/setup_api_subdomain.sh
```

This script will:
1. ✓ Verify DNS resolution
2. ✓ Obtain SSL certificate from Let's Encrypt
3. ✓ Configure Nginx as reverse proxy
4. ✓ Reload Nginx
5. ✓ Verify everything works

### Step 3: Verify Installation

Test your API:

```bash
# Health check
curl https://api.dojobay.pw/health

# Get dojos
curl https://api.dojobay.pw/api/dojos

# With authentication
curl -H "Authorization: Bearer YOUR_TOKEN" \
     https://api.dojobay.pw/api/dojos
```

## API Endpoints

Once configured, your API is available at:

```
https://api.dojobay.pw/api/dojos
https://api.dojobay.pw/api/dojos?network=mainnet
https://api.dojobay.pw/api/dojos?network=testnet
https://api.dojobay.pw/health
https://api.dojobay.pw/api/info
```

## Configuration Files

- **Setup Script**: `/root/dojobay/setup_api_subdomain.sh`
- **Nginx Config**: `/root/dojobay/nginx_api.conf`
- **Systemd Service**: `/root/dojobay/dojobay-api.service`
- **Environment**: `/root/dojobay/.env.production`

## Troubleshooting

### DNS not resolving

```bash
# Check DNS
nslookup api.dojobay.pw

# Clear DNS cache (Linux)
sudo systemd-resolve --flush-caches

# Wait longer (up to 48 hours for propagation)
```

### Certificate not obtained

```bash
# Check Nginx logs
sudo tail -f /var/log/nginx/error.log

# Manually request certificate
sudo certbot certonly --nginx -d api.dojobay.pw
```

### Nginx error after setup

```bash
# Test Nginx config
sudo nginx -t

# View logs
sudo journalctl -u nginx -f

# Reload Nginx
sudo systemctl reload nginx
```

### API not responding

```bash
# Check Gunicorn
ps aux | grep gunicorn | grep external_api

# Check service status
sudo systemctl status dojobay-api

# View API logs
journalctl -u dojobay-api -f

# Test locally
curl http://127.0.0.1:8090/health
```

## Security Features

✅ **HTTPS/SSL** - Free certificates from Let's Encrypt, auto-renewal
✅ **Security Headers** - HSTS, X-Frame-Options, X-Content-Type-Options
✅ **Rate Limiting** - 100 requests/minute per IP
✅ **Bearer Token Auth** - Required for API access
✅ **CORS** - Configured for GET/OPTIONS only
✅ **Reverse Proxy** - Nginx hides internal architecture

## Sharing with Partners

Now you can share with your partners:

1. **API Documentation**: `/root/dojobay/DEVELOPER_INTEGRATION_GUIDE.md`
2. **API Base URL**: `https://api.dojobay.pw`
3. **Their Bearer Token**: (distribute separately, securely)

Example for partners:
```bash
curl -H "Authorization: Bearer their-token-here" \
     https://api.dojobay.pw/api/dojos | jq '.'
```

## Monitoring

Monitor your API:

```bash
# View real-time monitoring
bash /root/dojobay/monitor_api.sh --continuous

# View Nginx access logs
tail -f /var/log/nginx/api.dojobay.pw_access.log

# View Nginx error logs
tail -f /var/log/nginx/api.dojobay.pw_error.log

# View API service logs
journalctl -u dojobay-api -f
```

## Certificate Renewal

Let's Encrypt certificates are valid for 90 days. They auto-renew:

```bash
# Check renewal
sudo certbot renew --dry-run

# Manual renewal
sudo certbot renew
```

## Support

For issues or questions, check:
- API logs: `journalctl -u dojobay-api -f`
- Nginx logs: `/var/log/nginx/api.dojobay.pw_*`
- Systemd status: `sudo systemctl status dojobay-api`


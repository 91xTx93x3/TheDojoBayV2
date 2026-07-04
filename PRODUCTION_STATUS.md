# 🚀 Dojobay External API - Production Deployment Summary

## Status: ✅ ACTIVE IN PRODUCTION

### API Service Information

**Service Status:** Running ✅  
**Process ID:** Multiple worker processes (4x sync workers)  
**Bind Address:** 127.0.0.1:8090  
**Server:** Gunicorn 23.0.0  
**Framework:** Flask 3.1.2

### API Endpoints

| Endpoint                     | Method | Authentication | Purpose                                   |
| ---------------------------- | ------ | -------------- | ----------------------------------------- |
| `/api/info`                  | GET    | Required       | API information and available endpoints   |
| `/api/dojos`                 | GET    | Required       | Get list of all dojos (mainnet + testnet) |
| `/api/dojos?network=mainnet` | GET    | Required       | Filter dojos by network                   |
| `/health`                    | GET    | Not required   | Health check endpoint                     |

### Authentication

**Method:** Bearer Token (Authorization header)  
**Token:** `e3a15e137191a5016644dfb6f6fe4f7c7dac2156157a0b4bfcd73bc5614727d7`

**Example Request:**

```bash
curl -H "Authorization: Bearer e3a15e137191a5016644dfb6f6fe4f7c7dac2156157a0b4bfcd73bc5614727d7" \
     http://127.0.0.1:8090/api/dojos
```

### Response Example

```json
{
  "count": 19,
  "dojos": [
    {
      "user": "+bumpyblank89",
      "name": "Compiler",
      "network": "mainnet",
      "electrum_server": "http://eaa3qxan44q2rksr23nferh5ntxsqcdcdkjmotly..."
    }
    // ... more dojos
  ]
}
```

### Deployment Configuration

**Configuration Files:**

- `external_api.py` - Main API application
- `gunicorn_external_api_prod.conf.py` - Gunicorn production configuration
- `.env.production` - Environment variables for production

**Environment Variables Set:**

```bash
DOJOBAY_API_TOKEN=e3a15e137191a5016644dfb6f6fe4f7c7dac2156157a0b4bfcd73bc5614727d7
DOJOBAY_BIND=127.0.0.1:8090
DOJOBAY_WORKERS=4
DOJOBAY_API_LOG_LEVEL=info
```

### Logs

**Access Log:** `/root/dojobay/external_api_access.log`  
**Error Log:** `/root/dojobay/external_api_error.log`  
**Startup Log:** `/root/dojobay/external_api.log`

View logs:

```bash
# Real-time access log
tail -f external_api_access.log

# Real-time error log
tail -f external_api_error.log

# Full startup log
cat external_api.log
```

### Security Features

✅ **Security Headers:**

- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`
- `Strict-Transport-Security: max-age=31536000`

✅ **CORS Support:**

- Allows cross-origin requests
- Restricted to GET and OPTIONS methods
- CORS headers properly configured

✅ **Authentication:**

- Bearer token validation on all protected endpoints
- Invalid tokens are rejected with 401 Unauthorized
- Token is checked on every request

✅ **Error Handling:**

- Comprehensive error responses
- Graceful handling of malformed requests
- Detailed logging for debugging

### Performance

**Workers:** 4 (sync model)  
**Timeout:** 30 seconds per request  
**Max Requests per Worker:** 10,000 (with 1,000 jitter)  
**Connection Backlog:** 2,048  
**Max Worker Connections:** 1,000

### Management Commands

**Check Status:**

```bash
ps aux | grep gunicorn | grep external_api
netstat -tlnp | grep 8090
```

**View Logs:**

```bash
tail -f /root/dojobay/external_api.log
tail -f /root/dojobay/external_api_access.log
tail -f /root/dojobay/external_api_error.log
```

**Restart Service:**

```bash
# Kill existing process
pkill -f "gunicorn.*external_api"

# Start new instance
cd /root/dojobay
source venv/bin/activate
export DOJOBAY_API_TOKEN="your-token-here"
export DOJOBAY_BIND="127.0.0.1:8090"
nohup gunicorn -c gunicorn_external_api_prod.conf.py external_api:app > external_api.log 2>&1 &
```

**Stop Service:**

```bash
pkill -f "gunicorn.*external_api"
```

### Integration for External Applications

External applications can now easily access Dojo information:

**Python Example:**

```python
import requests

token = "e3a15e137191a5016644dfb6f6fe4f7c7dac2156157a0b4bfcd73bc5614727d7"
headers = {"Authorization": f"Bearer {token}"}

# Get all dojos
response = requests.get(
    "http://127.0.0.1:8090/api/dojos",
    headers=headers
)
dojos = response.json()

# Get mainnet dojos only
response = requests.get(
    "http://127.0.0.1:8090/api/dojos?network=mainnet",
    headers=headers
)
mainnet_dojos = response.json()
```

**JavaScript Example:**

```javascript
const token =
  "e3a15e137191a5016644dfb6f6fe4f7c7dac2156157a0b4bfcd73bc5614727d7";
const headers = { Authorization: `Bearer ${token}` };

// Get all dojos
fetch("http://127.0.0.1:8090/api/dojos", { headers })
  .then((r) => r.json())
  .then((data) => console.log(data.dojos));
```

**cURL Example:**

```bash
TOKEN="e3a15e137191a5016644dfb6f6fe4f7c7dac2156157a0b4bfcd73bc5614727d7"
curl -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8090/api/dojos
```

### Production Checklist

- ✅ API is running in production on port 8090
- ✅ All dependencies are installed
- ✅ Gunicorn is configured for production
- ✅ Security headers are enabled
- ✅ Authentication is enforced
- ✅ Logging is configured
- ✅ Data file is accessible and valid
- ✅ CORS is properly configured
- ✅ Error handling is in place

### Next Steps

1. **Configure Reverse Proxy:** Set up Nginx/Apache to proxy requests to 127.0.0.1:8090
2. **Enable HTTPS/SSL:** Configure SSL certificates for secure communication
3. **Set Up Monitoring:** Monitor logs and performance metrics
4. **Create Systemd Service:** For automatic startup on server reboot
5. **Backup Configuration:** Ensure token is securely stored
6. **Documentation:** Share API docs with external teams

---

**Deployment Date:** July 4, 2026  
**API Version:** 1.0  
**Framework:** Flask + Gunicorn  
**Status:** Production Ready ✅

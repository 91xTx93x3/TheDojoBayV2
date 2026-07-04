#!/bin/bash
# Quick Reference Guide for Dojobay External API Production

# ═══════════════════════════════════════════════════════════════════
# PRODUCTION API REFERENCE - QUICK GUIDE
# ═══════════════════════════════════════════════════════════════════

# API LOCATION: 127.0.0.1:8090
# TOKEN: e3a15e137191a5016644dfb6f6fe4f7c7dac2156157a0b4bfcd73bc5614727d7

# ═══════════════════════════════════════════════════════════════════
# COMMON COMMANDS
# ═══════════════════════════════════════════════════════════════════

# Check if API is running
ps aux | grep "gunicorn.*external_api" | grep -v grep

# View access logs
tail -f /root/dojobay/external_api_access.log

# View error logs
tail -f /root/dojobay/external_api_error.log

# View startup logs
tail -f /root/dojobay/external_api.log

# ═══════════════════════════════════════════════════════════════════
# API TESTS
# ═══════════════════════════════════════════════════════════════════

# Test API Info
curl -H "Authorization: Bearer e3a15e137191a5016644dfb6f6fe4f7c7dac2156157a0b4bfcd73bc5614727d7" \
     http://127.0.0.1:8090/api/info | python3 -m json.tool

# Get all dojos
curl -H "Authorization: Bearer e3a15e137191a5016644dfb6f6fe4f7c7dac2156157a0b4bfcd73bc5614727d7" \
     http://127.0.0.1:8090/api/dojos | python3 -m json.tool

# Get only mainnet dojos
curl -H "Authorization: Bearer e3a15e137191a5016644dfb6f6fe4f7c7dac2156157a0b4bfcd73bc5614727d7" \
     "http://127.0.0.1:8090/api/dojos?network=mainnet" | python3 -m json.tool

# Get only testnet dojos
curl -H "Authorization: Bearer e3a15e137191a5016644dfb6f6fe4f7c7dac2156157a0b4bfcd73bc5614727d7" \
     "http://127.0.0.1:8090/api/dojos?network=testnet" | python3 -m json.tool

# ═══════════════════════════════════════════════════════════════════
# MANAGEMENT
# ═══════════════════════════════════════════════════════════════════

# Restart API Service
restart_api() {
    echo "Stopping API..."
    pkill -f "gunicorn.*external_api"
    sleep 2
    
    echo "Starting API..."
    cd /root/dojobay
    source venv/bin/activate
    export DOJOBAY_API_TOKEN="e3a15e137191a5016644dfb6f6fe4f7c7dac2156157a0b4bfcd73bc5614727d7"
    export DOJOBAY_BIND="127.0.0.1:8090"
    nohup gunicorn -c gunicorn_external_api_prod.conf.py external_api:app > external_api.log 2>&1 &
    
    echo "API restarted. Checking status in 2 seconds..."
    sleep 2
    ps aux | grep "gunicorn.*external_api" | grep -v grep
}

# Stop API Service
stop_api() {
    echo "Stopping Dojobay External API..."
    pkill -f "gunicorn.*external_api"
    echo "API stopped"
}

# ═══════════════════════════════════════════════════════════════════
# DOCUMENTATION REFERENCES
# ═══════════════════════════════════════════════════════════════════

# Full deployment guide: /root/dojobay/EXTERNAL_API_DEPLOYMENT.md
# Production status: /root/dojobay/PRODUCTION_STATUS.md
# API source code: /root/dojobay/external_api.py
# Gunicorn config: /root/dojobay/gunicorn_external_api_prod.conf.py
# Environment file: /root/dojobay/.env.production

# ═══════════════════════════════════════════════════════════════════
# EXTERNAL APPLICATION EXAMPLES
# ═══════════════════════════════════════════════════════════════════

# Python example (save as test_api.py):
cat > test_api.py << 'EOF'
#!/usr/bin/env python3
import requests
import json

TOKEN = "e3a15e137191a5016644dfb6f6fe4f7c7dac2156157a0b4bfcd73bc5614727d7"
BASE_URL = "http://127.0.0.1:8090"

def get_dojos(network=None):
    """Get dojos from the API"""
    headers = {"Authorization": f"Bearer {TOKEN}"}
    params = {}
    if network:
        params["network"] = network
    
    response = requests.get(f"{BASE_URL}/api/dojos", headers=headers, params=params)
    response.raise_for_status()
    return response.json()

if __name__ == "__main__":
    # Get all dojos
    print("All dojos:")
    data = get_dojos()
    print(f"Total: {data['count']} dojos")
    for dojo in data['dojos']:
        print(f"  - {dojo['name']} ({dojo['network']}): {dojo['user']}")
    
    # Get mainnet dojos
    print("\nMainnet dojos:")
    data = get_dojos("mainnet")
    print(f"Total: {data['count']} dojos")
EOF

chmod +x test_api.py
python3 test_api.py

# JavaScript/Node.js example (save as test_api.js):
cat > test_api.js << 'EOF'
const fetch = require('node-fetch');

const TOKEN = "e3a15e137191a5016644dfb6f6fe4f7c7dac2156157a0b4bfcd73bc5614727d7";
const BASE_URL = "http://127.0.0.1:8090";

async function getDojos(network = null) {
    const headers = { "Authorization": `Bearer ${TOKEN}` };
    let url = `${BASE_URL}/api/dojos`;
    
    if (network) {
        url += `?network=${network}`;
    }
    
    const response = await fetch(url, { headers });
    return response.json();
}

(async () => {
    const data = await getDojos();
    console.log(`Total dojos: ${data.count}`);
    data.dojos.forEach(dojo => {
        console.log(`  - ${dojo.name} (${dojo.network}): ${dojo.user}`);
    });
})();
EOF

# ═══════════════════════════════════════════════════════════════════
# PERFORMANCE MONITORING
# ═══════════════════════════════════════════════════════════════════

# Check memory usage
ps aux | grep "gunicorn.*external_api" | grep -v grep | awk '{print $2, $3, $4, $6}'

# Count active connections
netstat -an | grep 8090 | wc -l

# Watch logs in real-time
watch_logs() {
    echo "Access log:"
    tail -20 /root/dojobay/external_api_access.log
    echo ""
    echo "Error log:"
    tail -20 /root/dojobay/external_api_error.log
}

echo "API Production Reference Guide Loaded"
echo "Use commands above to manage the API"
echo "Run 'restart_api' to restart the service"
echo "Run 'stop_api' to stop the service"

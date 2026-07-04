# Dojobay External API - Integration Guide for Developers

Welcome! This guide will help you integrate your application with the Dojobay External API. You'll find everything you need to get started within the next few minutes.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Authentication](#authentication)
3. [API Endpoints](#api-endpoints)
4. [Code Examples](#code-examples)
5. [Error Handling](#error-handling)
6. [Rate Limiting](#rate-limiting)
7. [Best Practices](#best-practices)
8. [Troubleshooting](#troubleshooting)

---

## Quick Start

### Prerequisites

- Your API token (provided separately)
- cURL, Python 3.6+, Node.js 12+, or any HTTP client
- Basic knowledge of REST APIs

### First Request

Replace `YOUR_TOKEN` with your actual token:

```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
     https://api.yourdomain.com/api/dojos | python3 -m json.tool
```

Expected response:

```json
{
  "count": 19,
  "dojos": [
    {
      "user": "+bumpyblank89",
      "name": "Compiler",
      "network": "mainnet",
      "electrum_server": "http://eaa3qxan44q2rksr..."
    }
  ]
}
```

---

## Authentication

### How It Works

The API uses **Bearer Token Authentication**. Every request to a protected endpoint must include:

```
Authorization: Bearer YOUR_API_TOKEN
```

### Token Information

- **Token Type**: Bearer Token (64 hex characters)
- **Provided By**: Your Dojobay API administrator
- **Expiration**: No automatic expiration (rotate on request)
- **Scope**: Full read access to Dojo data
- **Security**: Keep your token private and secure

### Token Storage Best Practices

**DO:**

```python
# Good: Store in environment variables
import os
api_token = os.getenv('DOJOBAY_API_TOKEN')

# Good: Store in secure config file (not in git)
# config.yml (in .gitignore)
api_token: "e3a15e137191a5016644dfb6f6fe4f7c7dac2156157a0b4bfcd73bc5614727d7"
```

**DON'T:**

```python
# Bad: Hardcode in source code
api_token = "e3a15e137191a5016644dfb6f6fe4f7c7dac2156157a0b4bfcd73bc5614727d7"

# Bad: Commit to git repository
# Never commit tokens to version control!
```

### Token Rotation

If your token is compromised:

1. Notify your API administrator immediately
2. Request a new token
3. Update your application
4. The old token will be revoked

---

## API Endpoints

### Base URL

```
https://api.yourdomain.com/api
```

All endpoints require authentication unless noted otherwise.

### Available Endpoints

#### 1. Get All Dojos

**Endpoint:** `GET /api/dojos`

Get a list of all Dojos (both mainnet and testnet).

**Request:**

```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
     https://api.yourdomain.com/api/dojos
```

**Response:**

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

#### 2. Filter by Network

**Endpoint:** `GET /api/dojos?network=NETWORK`

Get Dojos filtered by network.

**Parameters:**

- `network` (optional): `mainnet` or `testnet`

**Examples:**

```bash
# Mainnet only
curl -H "Authorization: Bearer YOUR_TOKEN" \
     https://api.yourdomain.com/api/dojos?network=mainnet

# Testnet only
curl -H "Authorization: Bearer YOUR_TOKEN" \
     https://api.yourdomain.com/api/dojos?network=testnet
```

**Response:**

```json
{
  "count": 15,
  "dojos": [
    {
      "user": "+mundanepunch78",
      "name": "@maxtannahill",
      "network": "mainnet",
      "electrum_server": "http://eefhmn3z6jmh72kph6777fahelbal..."
    }
  ]
}
```

#### 3. API Information

**Endpoint:** `GET /api/info`

Get API information and available endpoints.

**Request:**

```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
     https://api.yourdomain.com/api/info
```

**Response:**

```json
{
  "name": "Dojobay External API",
  "version": "1.0",
  "description": "API for accessing Dojobay node information",
  "authentication": "Bearer token in Authorization header",
  "endpoints": {
    "GET /api/dojos": "Get list of dojos (requires authentication)",
    "GET /api/info": "This endpoint - API information",
    "GET /health": "Health check endpoint"
  }
}
```

#### 4. Health Check

**Endpoint:** `GET /health`

Check if the API is healthy. **No authentication required**.

**Request:**

```bash
curl https://api.yourdomain.com/health
```

**Response:**

```json
{
  "status": "healthy",
  "timestamp": "2026-07-04T13:45:00Z"
}
```

---

## Code Examples

### Python

#### Installation

```bash
pip install requests
```

#### Basic Usage

```python
import requests
import json

# Configuration
API_TOKEN = "YOUR_API_TOKEN"
API_BASE_URL = "https://api.yourdomain.com"

# Set up headers
headers = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json"
}

# Get all dojos
response = requests.get(
    f"{API_BASE_URL}/api/dojos",
    headers=headers
)

if response.status_code == 200:
    data = response.json()
    print(f"Found {data['count']} dojos:")

    for dojo in data['dojos']:
        print(f"  - {dojo['name']} ({dojo['network']})")
        print(f"    User: {dojo['user']}")
        print(f"    Server: {dojo['electrum_server']}")
else:
    print(f"Error: {response.status_code}")
    print(response.text)
```

#### Get Mainnet Dojos Only

```python
# Get only mainnet dojos
response = requests.get(
    f"{API_BASE_URL}/api/dojos?network=mainnet",
    headers=headers
)

mainnet_dojos = response.json()['dojos']
print(f"Mainnet dojos: {len(mainnet_dojos)}")
```

#### Async Example (Python 3.7+)

```python
import aiohttp
import asyncio

async def get_dojos():
    api_token = "YOUR_API_TOKEN"
    api_base_url = "https://api.yourdomain.com"

    headers = {
        "Authorization": f"Bearer {api_token}"
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{api_base_url}/api/dojos",
            headers=headers
        ) as response:
            data = await response.json()
            return data

# Run async function
dojos = asyncio.run(get_dojos())
print(f"Found {dojos['count']} dojos")
```

### JavaScript / Node.js

#### Installation

```bash
npm install node-fetch
# or
npm install axios
```

#### Using Fetch API (Node 18+)

```javascript
const apiToken = "YOUR_API_TOKEN";
const apiBaseUrl = "https://api.yourdomain.com";

// Get all dojos
async function getDojos() {
  const response = await fetch(`${apiBaseUrl}/api/dojos`, {
    headers: {
      Authorization: `Bearer ${apiToken}`,
      "Content-Type": "application/json",
    },
  });

  if (!response.ok) {
    throw new Error(`API Error: ${response.status}`);
  }

  const data = await response.json();
  return data;
}

// Usage
getDojos()
  .then((data) => {
    console.log(`Found ${data.count} dojos:`);
    data.dojos.forEach((dojo) => {
      console.log(`  - ${dojo.name} (${dojo.network})`);
      console.log(`    User: ${dojo.user}`);
    });
  })
  .catch((error) => console.error("Error:", error));
```

#### Using Axios

```javascript
const axios = require("axios");

const apiToken = "YOUR_API_TOKEN";
const apiClient = axios.create({
  baseURL: "https://api.yourdomain.com",
  headers: {
    Authorization: `Bearer ${apiToken}`,
    "Content-Type": "application/json",
  },
});

// Get dojos by network
async function getDojosByNetwork(network = "mainnet") {
  try {
    const response = await apiClient.get("/api/dojos", {
      params: { network },
    });
    return response.data;
  } catch (error) {
    console.error("API Error:", error.response?.data || error.message);
    throw error;
  }
}

// Usage
getDojosByNetwork("mainnet")
  .then((data) => console.log(data))
  .catch((error) => console.error(error));
```

### cURL

#### Get All Dojos

```bash
TOKEN="YOUR_API_TOKEN"
curl -X GET "https://api.yourdomain.com/api/dojos" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json"
```

#### Get Mainnet Dojos with Pretty Output

```bash
TOKEN="YOUR_API_TOKEN"
curl -s "https://api.yourdomain.com/api/dojos?network=mainnet" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

#### Get API Info

```bash
TOKEN="YOUR_API_TOKEN"
curl "https://api.yourdomain.com/api/info" \
  -H "Authorization: Bearer $TOKEN"
```

### PHP

```php
<?php

$apiToken = "YOUR_API_TOKEN";
$apiBaseUrl = "https://api.yourdomain.com";

// Get all dojos
$url = "$apiBaseUrl/api/dojos";
$headers = [
    "Authorization: Bearer $apiToken",
    "Content-Type: application/json"
];

$ch = curl_init();
curl_setopt($ch, CURLOPT_URL, $url);
curl_setopt($ch, CURLOPT_HTTPHEADER, $headers);
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);

$response = curl_exec($ch);
$httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
curl_close($ch);

if ($httpCode === 200) {
    $data = json_decode($response, true);
    echo "Found " . $data['count'] . " dojos:\n";

    foreach ($data['dojos'] as $dojo) {
        echo "  - " . $dojo['name'] . " (" . $dojo['network'] . ")\n";
    }
} else {
    echo "Error: $httpCode\n";
    echo $response;
}
?>
```

### Java

```java
import java.net.URL;
import java.net.HttpURLConnection;
import java.io.BufferedReader;
import java.io.InputStreamReader;
import com.google.gson.JsonParser;

public class DojobayClient {
    private static final String API_TOKEN = "YOUR_API_TOKEN";
    private static final String API_BASE_URL = "https://api.yourdomain.com";

    public static void getDojos() throws Exception {
        URL url = new URL(API_BASE_URL + "/api/dojos");
        HttpURLConnection conn = (HttpURLConnection) url.openConnection();

        // Set headers
        conn.setRequestMethod("GET");
        conn.setRequestProperty("Authorization", "Bearer " + API_TOKEN);
        conn.setRequestProperty("Content-Type", "application/json");

        // Read response
        BufferedReader in = new BufferedReader(
            new InputStreamReader(conn.getInputStream())
        );
        String inputLine;
        StringBuilder response = new StringBuilder();

        while ((inputLine = in.readLine()) != null) {
            response.append(inputLine);
        }
        in.close();

        // Parse and print
        var json = JsonParser.parseString(response.toString());
        System.out.println("Found " + json.getAsJsonObject()
            .get("count") + " dojos");
    }
}
```

---

## Error Handling

### HTTP Status Codes

| Code | Meaning           | Action                                    |
| ---- | ----------------- | ----------------------------------------- |
| 200  | OK                | Request successful                        |
| 400  | Bad Request       | Check your query parameters               |
| 401  | Unauthorized      | Verify your API token                     |
| 404  | Not Found         | Endpoint doesn't exist                    |
| 429  | Too Many Requests | Rate limit exceeded, wait before retrying |
| 500  | Server Error      | Contact support                           |

### Error Response Examples

#### Missing Token

```bash
$ curl https://api.yourdomain.com/api/dojos
```

```json
{
  "error": "Unauthorized",
  "message": "Missing or invalid Authorization header",
  "required_format": "Authorization: Bearer <token>"
}
```

#### Invalid Token

```json
{
  "error": "Unauthorized",
  "message": "Invalid token"
}
```

#### Invalid Network Filter

```json
{
  "error": "Bad Request",
  "message": "Invalid network parameter. Must be 'mainnet' or 'testnet'"
}
```

### Error Handling in Python

```python
import requests

api_token = "YOUR_API_TOKEN"
api_url = "https://api.yourdomain.com/api/dojos"

try:
    response = requests.get(
        api_url,
        headers={"Authorization": f"Bearer {api_token}"}
    )

    # Check status code
    if response.status_code == 401:
        print("Error: Invalid or missing token")
    elif response.status_code == 429:
        print("Error: Rate limit exceeded. Please wait before retrying.")
    elif response.status_code == 200:
        data = response.json()
        print(f"Success: {data['count']} dojos found")
    else:
        print(f"Unexpected error: {response.status_code}")

except requests.exceptions.ConnectionError:
    print("Error: Cannot connect to API server")
except requests.exceptions.Timeout:
    print("Error: Request timeout")
except Exception as e:
    print(f"Error: {str(e)}")
```

---

## Rate Limiting

### Limits

- **Rate Limit**: 100 requests per minute
- **Burst Allowance**: 20 additional requests
- **Reset Time**: 1 minute

### Headers

The API includes rate limit information in response headers:

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1656950460
```

### Handling Rate Limits

```python
import requests
import time

def get_dojos_with_retry(api_token, api_url, max_retries=3):
    headers = {"Authorization": f"Bearer {api_token}"}

    for attempt in range(max_retries):
        response = requests.get(api_url, headers=headers)

        if response.status_code == 429:
            # Rate limited - wait and retry
            reset_time = int(response.headers.get('X-RateLimit-Reset', 0))
            wait_time = reset_time - time.time()

            if wait_time > 0:
                print(f"Rate limited. Waiting {wait_time} seconds...")
                time.sleep(wait_time + 1)
                continue

        return response

    raise Exception("Max retries exceeded")
```

---

## Best Practices

### 1. Cache Results

Don't fetch the same data repeatedly. Cache results locally:

```python
import json
import time

class DojobayCache:
    def __init__(self, cache_file="dojos_cache.json", ttl=3600):
        self.cache_file = cache_file
        self.ttl = ttl  # Time to live in seconds

    def get_dojos(self, api_client):
        # Check cache first
        if self.is_valid():
            with open(self.cache_file, 'r') as f:
                return json.load(f)

        # Fetch from API
        data = api_client.get_dojos()

        # Save to cache
        with open(self.cache_file, 'w') as f:
            json.dump(data, f)

        return data

    def is_valid(self):
        try:
            stat = os.stat(self.cache_file)
            age = time.time() - stat.st_mtime
            return age < self.ttl
        except FileNotFoundError:
            return False
```

### 2. Implement Timeouts

Prevent hanging requests:

```python
# Python
response = requests.get(
    url,
    headers=headers,
    timeout=10  # 10 seconds
)

# JavaScript (Axios)
const config = {
    timeout: 10000  // 10 seconds
};
const response = await axios.get(url, config);
```

### 3. Use Connection Pooling

Reuse connections for better performance:

```python
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

session = requests.Session()

# Retry strategy
retry = Retry(
    total=3,
    backoff_factor=0.5,
    status_forcelist=[500, 502, 503, 504]
)

adapter = HTTPAdapter(max_retries=retry)
session.mount('http://', adapter)
session.mount('https://', adapter)

# Use session for requests
response = session.get(url, headers=headers)
```

### 4. Monitor API Health

Check health before making requests:

```python
def is_api_healthy(api_base_url):
    try:
        response = requests.get(
            f"{api_base_url}/health",
            timeout=5
        )
        return response.status_code == 200
    except:
        return False

# Usage
if is_api_healthy("https://api.yourdomain.com"):
    # Make API calls
    pass
else:
    print("API is down. Try again later.")
```

### 5. Log API Interactions

Track all API calls for debugging:

```python
import logging

# Setup logging
logging.basicConfig(
    filename='api_calls.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def log_api_call(method, endpoint, status_code, response_time):
    logging.info(
        f"{method} {endpoint} - {status_code} - {response_time}ms"
    )
```

### 6. Validate Data Before Using

Don't assume the API response is always valid:

```python
def validate_dojo_data(dojo):
    required_fields = ['user', 'name', 'network', 'electrum_server']

    for field in required_fields:
        if field not in dojo or not dojo[field]:
            return False

    if dojo['network'] not in ['mainnet', 'testnet']:
        return False

    return True

# Usage
data = response.json()
valid_dojos = [d for d in data['dojos'] if validate_dojo_data(d)]
```

---

## Troubleshooting

### "Unauthorized" Error

**Problem**: Getting 401 Unauthorized

**Solutions**:

1. Check if your token is correct
2. Verify token hasn't been revoked
3. Ensure token is in the Authorization header format
4. Check for extra spaces or line breaks in token

```bash
# Correct format
curl -H "Authorization: Bearer YOUR_TOKEN" https://api.yourdomain.com/api/dojos

# Wrong format (missing "Bearer ")
curl -H "Authorization: YOUR_TOKEN" https://api.yourdomain.com/api/dojos
```

### "Connection Refused" Error

**Problem**: Cannot connect to API

**Solutions**:

1. Check if API is running: `sudo systemctl status dojobay-api`
2. Verify API URL is correct
3. Check firewall rules allow access
4. Try pinging the server: `ping api.yourdomain.com`

### "Timeout" Error

**Problem**: Request takes too long

**Solutions**:

1. Increase timeout value in your client
2. Check network connectivity
3. Check API server load
4. Try again later if API is under heavy load

### "Rate Limit Exceeded"

**Problem**: Getting 429 status code

**Solutions**:

1. Wait before making more requests
2. Implement exponential backoff
3. Cache results to reduce API calls
4. Batch requests when possible

```python
# Exponential backoff
import random
import time

def call_api_with_backoff(api_func, max_retries=5):
    for attempt in range(max_retries):
        try:
            return api_func()
        except RateLimitError:
            wait_time = 2 ** attempt + random.random()
            print(f"Rate limited. Waiting {wait_time}s...")
            time.sleep(wait_time)

    raise Exception("Max retries exceeded")
```

### "Empty or Invalid Response"

**Problem**: API returns empty or malformed JSON

**Solutions**:

1. Check response Content-Type header
2. Verify API is returning valid JSON
3. Check for API errors in response

```python
response = requests.get(url, headers=headers)

# Debug response
print(f"Status: {response.status_code}")
print(f"Headers: {response.headers}")
print(f"Content: {response.text}")

try:
    data = response.json()
except json.JSONDecodeError:
    print("Response is not valid JSON")
```

---

## Support & Resources

### When Something Goes Wrong

1. **Check this guide** - Ctrl+F to search for your issue
2. **Review error messages** - They often indicate the problem
3. **Check API health** - `curl https://api.yourdomain.com/health`
4. **Contact API administrator** - Send complete error details:
   - Exact error message
   - Your request (with token hidden)
   - Timestamp when error occurred
   - Your application environment

### Example Error Report

```
Error: 401 Unauthorized
Endpoint: GET /api/dojos?network=mainnet
Request Time: 2026-07-04 14:30:00 UTC
Environment: Python 3.9, requests 2.28.0
Error Message: Invalid token

Steps taken:
1. Verified token is correct
2. Checked network connectivity
3. Tried both endpoints
```

---

## Summary

You now have everything needed to integrate with the Dojobay External API:

✅ **Authentication** - Know how to authenticate requests  
✅ **Endpoints** - Understand available endpoints and parameters  
✅ **Code Examples** - Ready-to-use code in multiple languages  
✅ **Error Handling** - Know how to handle errors gracefully  
✅ **Rate Limiting** - Understand rate limits and quotas  
✅ **Best Practices** - Follow recommended patterns  
✅ **Troubleshooting** - Fix common issues

---

## Next Steps

1. **Get your API token** from the administrator
2. **Test the API** with cURL or your language of choice
3. **Integrate into your application**
4. **Monitor performance** and adjust caching as needed
5. **Keep your token secure** - never commit it to version control

---

**API Version**: 1.0  
**Last Updated**: July 4, 2026  
**Status**: Production Ready

Happy coding! 🚀

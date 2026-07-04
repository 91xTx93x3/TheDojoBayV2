"""Standalone external API for Dojobay.

This file does not modify app.py and can run independently.
Optimized for production deployment with Gunicorn.

API Documentation:
    - Base URL: http://your-domain/api
    - Authentication: Bearer token in Authorization header
    
Environment Variables (Production):
    - DOJOBAY_API_TOKEN: API authentication token (REQUIRED - no default in production)
    - DOJOBAY_API_HOST: Host to bind to (default: 127.0.0.1)
    - DOJOBAY_API_PORT: Port to bind to (default: 8080)
    - DOJOBAY_API_DEBUG: Enable debug mode (default: false - NEVER set to true in production)
    - DOJOBAY_API_LOG_LEVEL: Logging level (default: INFO)
    - DOJOBAY_API_WORKERS: Number of workers (managed by Gunicorn in production)

Production Deployment:
    gunicorn -c gunicorn_external_api.conf.py external_api:app
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import json
import os
import logging
import logging.handlers
from pathlib import Path
from datetime import datetime
import sys

# Setup logging for production
def setup_logging():
    """Configure logging for production deployment."""
    log_level = os.getenv("DOJOBAY_API_LOG_LEVEL", "INFO").upper()
    
    # Create logger
    logger = logging.getLogger(__name__)
    logger.setLevel(getattr(logging, log_level, logging.INFO))
    
    # Create formatters
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler for stdout (Gunicorn will manage this)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logger

logger = setup_logging()

DATA_FILE = Path(__file__).resolve().parent / "dojos_data.json"
VALID_NETWORKS = {"mainnet", "testnet"}

# Production: Token MUST be set via environment variable
API_TOKEN = os.getenv("DOJOBAY_API_TOKEN", "").strip()
if not API_TOKEN:
    logger.error("FATAL: DOJOBAY_API_TOKEN environment variable not set!")
    logger.error("Set it before starting the API: export DOJOBAY_API_TOKEN='your-secure-token'")
    sys.exit(1)

API_HOST = os.getenv("DOJOBAY_API_HOST", "127.0.0.1")
API_PORT = int(os.getenv("DOJOBAY_API_PORT", 8080))
DEBUG_MODE = os.getenv("DOJOBAY_API_DEBUG", "false").lower() == "true"

if DEBUG_MODE:
    logger.warning("WARNING: Debug mode is enabled! Never use in production!")

app = Flask(__name__)

# Security headers middleware
@app.after_request
def add_security_headers(response):
    """Add security headers to all responses."""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    return response

# Enable CORS for external applications (only GET and OPTIONS for security)
CORS(app, 
     resources={r"/api/*": {
         "origins": "*", 
         "methods": ["GET", "OPTIONS"],
         "max_age": 3600
     }},
     expose_headers=['Content-Type']
)

logger.info(f"Dojobay External API configured (host={API_HOST}, port={API_PORT})")
logger.info(f"Debug mode: {DEBUG_MODE}")


def require_api_token():
    """Validate Authorization: Bearer <token> against env var token.
    
    Returns:
        None if token is valid, otherwise returns (error_response, status_code)
    """
    auth_header = request.headers.get("Authorization", "").strip()
    if not auth_header.startswith("Bearer "):
        logger.warning(f"Missing or invalid Authorization header from {request.remote_addr}")
        return (
            jsonify(
                {
                    "error": "Unauthorized",
                    "message": "Missing or invalid Authorization header",
                    "required_format": "Authorization: Bearer <token>",
                }
            ),
            401,
        )

    received_token = auth_header.replace("Bearer ", "", 1).strip()
    if not received_token or received_token != API_TOKEN:
        logger.warning(f"Invalid token attempt from {request.remote_addr}")
        return jsonify({"error": "Unauthorized", "message": "Invalid token"}), 401

    logger.debug(f"Successful authentication from {request.remote_addr}")
    return None


def load_dojos_data():
    """Load Dojo data from disk.
    
    Returns:
        tuple: (mainnet_dojos, testnet_dojos)
        
    Raises:
        FileNotFoundError: If dojos_data.json not found
        json.JSONDecodeError: If dojos_data.json has invalid JSON
    """
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        mainnet = data.get("mainnet", [])
        testnet = data.get("testnet", [])
        
        logger.debug(f"Loaded {len(mainnet)} mainnet dojos and {len(testnet)} testnet dojos")
        return mainnet, testnet
    except FileNotFoundError:
        logger.error(f"Data file not found: {DATA_FILE}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in {DATA_FILE}: {str(e)}")
        raise


def pick_electrum_server(dojo):
    """Extract electrum server-like URL from known fields.
    
    Args:
        dojo: Dictionary containing dojo information
        
    Returns:
        str or None: URL of electrum server
    """
    return (
        dojo.get("electrum_server")
        or (dojo.get("explorer", {}).get("url") if isinstance(dojo.get("explorer"), dict) else None)
        or (dojo.get("pairing", {}).get("url") if isinstance(dojo.get("pairing"), dict) else None)
    )


def normalize_dojo(dojo, network):
    """Return the public API shape requested by user.
    
    Args:
        dojo: Raw dojo data dictionary
        network: Network name (mainnet or testnet)
        
    Returns:
        dict: Normalized dojo information with user, name, network, and electrum_server
    """
    return {
        "user": dojo.get("user") or dojo.get("paynym") or "unknown",
        "name": dojo.get("name", "unknown"),
        "network": network,
        "electrum_server": pick_electrum_server(dojo),
    }


def parse_network_filter():
    """Validate optional ?network=mainnet|testnet filter.
    
    Returns:
        tuple: (network, error_response, status_code)
               network is empty string if no filter or valid network name
               error_response is None if valid, otherwise error dict
    """
    network = request.args.get("network", "").strip().lower()
    if network and network not in VALID_NETWORKS:
        logger.warning(f"Invalid network filter from {request.remote_addr}: {network}")
        return None, jsonify(
            {
                "error": "Invalid network parameter",
                "message": f"Network must be one of: {', '.join(sorted(VALID_NETWORKS))}",
                "example": "/api/dojos?network=mainnet",
            }
        ), 400
    return network, None, None


@app.route("/api/dojos", methods=["GET", "OPTIONS"])
def api_dojos():
    """Get list of Dojo nodes.
    
    Public endpoint returns user, name, network and electrum_server for each dojo.
    
    Query Parameters:
        network (optional): Filter by network (mainnet or testnet)
        
    Authentication:
        Required: Authorization: Bearer <token> header
        
    Returns:
        JSON with:
            - count: Number of dojos returned
            - filter: Applied network filter
            - dojos: List of dojo objects
            - examples: Example dojo objects
            
    Status Codes:
        200: Success
        400: Invalid parameters
        401: Authentication failed
        500: Server error
    """
    # Handle CORS preflight
    if request.method == "OPTIONS":
        return "", 204
    
    try:
        auth_error = require_api_token()
        if auth_error is not None:
            return auth_error

        network_filter, err_body, err_code = parse_network_filter()
        if err_body is not None:
            return err_body, err_code

        mainnet, testnet = load_dojos_data()

        dojos = []
        if not network_filter or network_filter == "mainnet":
            dojos.extend(normalize_dojo(d, "mainnet") for d in mainnet)
        if not network_filter or network_filter == "testnet":
            dojos.extend(normalize_dojo(d, "testnet") for d in testnet)

        examples = [
            {
                "user": "91xTx93x3",
                "name": "TantoE",
                "network": "mainnet",
                "electrum_server": "3xmxfolrxdyaqbfwohdxsntem4agugpbozb2u5re2vrwhpgkl6c5ufqd.onion:50001",
            },
            {
                "user": "91xTx93x3",
                "name": "Red",
                "network": "mainnet",
                "electrum_server": "tmie4ggcjawm53fh2yvvmznqwahgvwuqpip7acp63ruw2ct5wagddzyd.onion:50001",
            },
            {
                "user": "e91xTx93x3",
                "name": "Yellow",
                "network": "mainnet",
                "electrum_server": "x444eboylam4gmun3dcozm25edjrr6kd3a4n6rlvazazb5vxdyx3o7qd.onion",
            },
        ]

        response = {
            "count": len(dojos),
            "filter": network_filter or "all",
            "dojos": dojos,
            "examples": examples,
        }
        
        logger.info(f"API call /api/dojos - returned {len(dojos)} dojos (filter: {network_filter or 'all'})")
        return jsonify(response), 200
        
    except FileNotFoundError:
        logger.error("dojos_data.json not found")
        return jsonify({"error": "Service unavailable", "message": "Data file not found"}), 500
    except json.JSONDecodeError:
        logger.error("dojos_data.json has invalid JSON")
        return jsonify({"error": "Service unavailable", "message": "Invalid data format"}), 500
    except Exception as e:
        logger.error(f"Unexpected error in /api/dojos: {str(e)}", exc_info=True)
        return jsonify({"error": "Internal server error", "message": str(e)}), 500


@app.route("/health", methods=["GET", "OPTIONS"])
def health():
    """Health check endpoint for API availability and status.
    
    Returns:
        JSON with:
            - status: 'ok' or 'degraded'
            - timestamp: Current server timestamp
            - version: API version
    """
    if request.method == "OPTIONS":
        return "", 204
    
    try:
        # Try to load data to verify service is fully functional
        load_dojos_data()
        status = "ok"
    except Exception as e:
        logger.warning(f"Health check degraded: {str(e)}")
        status = "degraded"
    
    return jsonify({
        "status": status,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "version": "1.0"
    }), 200


@app.route("/api/info", methods=["GET", "OPTIONS"])
def api_info():
    """API information and documentation endpoint.
    
    Returns:
        JSON with:
            - name: API name
            - version: API version
            - description: API description
            - endpoints: List of available endpoints
    """
    if request.method == "OPTIONS":
        return "", 204
    
    endpoints = {
        "GET /health": "Health check endpoint",
        "GET /api/info": "This endpoint - API information",
        "GET /api/dojos": "Get list of dojos (requires authentication)",
    }
    
    return jsonify({
        "name": "Dojobay External API",
        "version": "1.0",
        "description": "API for accessing Dojobay node information",
        "authentication": "Bearer token in Authorization header",
        "endpoints": endpoints,
        "documentation": "See /api/docs for detailed documentation",
    }), 200


@app.route("/api/docs", methods=["GET"])
def api_docs():
    """Basic API documentation.
    
    Returns:
        HTML with usage examples and API documentation
    """
    docs = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Dojobay External API Documentation</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }
            .container { max-width: 900px; margin: 0 auto; background-color: white; padding: 20px; border-radius: 5px; }
            h1 { color: #333; }
            h2 { color: #666; border-bottom: 2px solid #007bff; padding-bottom: 10px; }
            code { background-color: #f0f0f0; padding: 2px 6px; border-radius: 3px; font-family: monospace; }
            .endpoint { background-color: #f9f9f9; padding: 15px; margin: 15px 0; border-left: 4px solid #007bff; }
            .example { background-color: #f0f0f0; padding: 10px; margin: 10px 0; overflow-x: auto; }
            .success { color: #28a745; }
            .error { color: #dc3545; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🔗 Dojobay External API Documentation</h1>
            
            <h2>Authentication</h2>
            <p>All API endpoints (except /health and /api/info) require Bearer token authentication.</p>
            <p><strong>Header:</strong> <code>Authorization: Bearer YOUR_TOKEN</code></p>
            <p><strong>Default token:</strong> <code>FREESAMOURAI</code></p>
            <p><strong>To use custom token:</strong> Set environment variable <code>DOJOBAY_API_TOKEN</code></p>
            
            <h2>Endpoints</h2>
            
            <div class="endpoint">
                <h3>GET /health</h3>
                <p>Health check endpoint. No authentication required.</p>
                <div class="example">
curl -X GET http://localhost:8080/health
                </div>
                <p><strong class="success">Response (200):</strong></p>
                <div class="example">
{
    "status": "ok",
    "timestamp": "2026-07-04T12:00:00Z",
    "version": "1.0"
}
                </div>
            </div>
            
            <div class="endpoint">
                <h3>GET /api/info</h3>
                <p>API information endpoint. No authentication required.</p>
                <div class="example">
curl -X GET http://localhost:8080/api/info
                </div>
            </div>
            
            <div class="endpoint">
                <h3>GET /api/dojos</h3>
                <p>Get list of Dojo nodes. <strong>Authentication required.</strong></p>
                <p><strong>Query Parameters:</strong></p>
                <ul>
                    <li><code>network</code> (optional): Filter by 'mainnet' or 'testnet'</li>
                </ul>
                <p><strong>Examples:</strong></p>
                <div class="example">
# Get all dojos
curl -X GET "http://localhost:8080/api/dojos" \\
  -H "Authorization: Bearer FREESAMOURAI"
                </div>
                <div class="example">
# Get only mainnet dojos
curl -X GET "http://localhost:8080/api/dojos?network=mainnet" \\
  -H "Authorization: Bearer FREESAMOURAI"
                </div>
                <div class="example">
# Get only testnet dojos
curl -X GET "http://localhost:8080/api/dojos?network=testnet" \\
  -H "Authorization: Bearer FREESAMOURAI"
                </div>
                <p><strong class="success">Response (200):</strong></p>
                <div class="example">
{
    "count": 3,
    "filter": "all",
    "dojos": [
        {
            "user": "91xTx93x3",
            "name": "TantoE",
            "network": "mainnet",
            "electrum_server": "3xmxfolrxdyaqbfwohdxsntem4agugpbozb2u5re2vrwhpgkl6c5ufqd.onion:50001"
        }
    ],
    "examples": [...]
}
                </div>
                <p><strong class="error">Response (401 - No auth):</strong></p>
                <div class="example">
{
    "error": "Unauthorized",
    "message": "Missing or invalid Authorization header",
    "required_format": "Authorization: Bearer <token>"
}
                </div>
            </div>
            
            <h2>Error Handling</h2>
            <p>All errors return JSON with 'error' and 'message' fields:</p>
            <div class="example">
{
    "error": "Invalid network parameter",
    "message": "Network must be one of: mainnet, testnet"
}
            </div>
            
            <h2>CORS Support</h2>
            <p>API supports CORS for browser-based requests from any origin.</p>
            
            <h2>Support</h2>
            <p>For issues or questions, check the main application documentation.</p>
        </div>
    </body>
    </html>
    """
    return docs, 200, {'Content-Type': 'text/html; charset=utf-8'}


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({
        "error": "Not found",
        "message": "Endpoint not found. See /api/info or /api/docs for available endpoints."
    }), 404


@app.errorhandler(405)
def method_not_allowed(error):
    """Handle 405 errors."""
    return jsonify({
        "error": "Method not allowed",
        "message": f"HTTP method {request.method} is not allowed for this endpoint."
    }), 405


if __name__ == "__main__":
    logger.info("=" * 70)
    logger.info("Starting Dojobay External API")
    logger.info(f"Host: {API_HOST}")
    logger.info(f"Port: {API_PORT}")
    logger.info(f"Debug: {DEBUG_MODE}")
    logger.info(f"Data file: {DATA_FILE}")
    logger.info("Endpoints:")
    logger.info("  - GET /health (no auth)")
    logger.info("  - GET /api/info (no auth)")
    logger.info("  - GET /api/docs (no auth)")
    logger.info("  - GET /api/dojos (requires Bearer token)")
    logger.info("=" * 70)
    logger.info("For production, use: gunicorn -c gunicorn_external_api.conf.py external_api:app")
    logger.info("=" * 70)
    
    try:
        # Development server only - NEVER use in production
        if DEBUG_MODE:
            app.run(host=API_HOST, port=API_PORT, debug=True, use_reloader=False)
        else:
            # For development without debug mode, still use Flask dev server
            # Production MUST use Gunicorn
            app.run(host=API_HOST, port=API_PORT, debug=False, use_reloader=False)
    except Exception as e:
        logger.error(f"Failed to start API: {str(e)}", exc_info=True)
        sys.exit(1)

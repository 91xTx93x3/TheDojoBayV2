"""Flask application for Dojobay - Public Dojo Directory."""
from flask import Flask, render_template, jsonify, send_from_directory
import os

from config import (
    DEFAULT_PROXIES, CACHE_FILE, DOJOS_DATA_FILE, 
    CACHE_DURATION, REQUEST_TIMEOUT, HOST, PORT, DEBUG
)
from cache import StatusCache
from checker import DojoChecker
from data_loader import DojoDataLoader
from background_checker import BackgroundChecker


# Initialize Flask app
app = Flask(__name__)

# Initialize components
data_loader = DojoDataLoader(DOJOS_DATA_FILE)
mainnet_dojos, testnet_dojos = data_loader.load()

cache = StatusCache(CACHE_FILE, CACHE_DURATION)
checker = DojoChecker(DEFAULT_PROXIES, REQUEST_TIMEOUT)

background_checker = BackgroundChecker(
    checker=checker,
    cache=cache,
    mainnet_dojos=mainnet_dojos,
    testnet_dojos=testnet_dojos,
    check_interval=CACHE_DURATION
)


# Routes
@app.route('/')
def index():
    """Main page with live Dojo status."""
    cached = cache.get()
    if cached:
        return render_template('index.html', status=cached)
    
    # No cache available, return empty state - JS will fetch via API
    from datetime import datetime
    empty_status = {
        "mainnet": [],
        "testnet": [],
        "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "stats": {
            "mainnet_active": 0,
            "mainnet_total": len(mainnet_dojos),
            "testnet_active": 0,
            "testnet_total": len(testnet_dojos)
        }
    }
    return render_template('index.html', status=empty_status)


@app.route('/about')
def about():
    """About page."""
    return render_template('about.html')


@app.route('/disclaimer')
def disclaimer():
    """Disclaimer page."""
    return render_template('disclaimer.html')


@app.route('/faq')
def faq():
    """FAQ page."""
    return render_template('faq.html')


@app.route('/api/status')
def api_status():
    """API endpoint to get current Dojo status."""
    try:
        cached = cache.get()
        if cached:
            return jsonify(cached)
        
        # No cache available, return loading message
        return jsonify({"loading": True, "message": "Updating node status..."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/health')
def health():
    """Health check endpoint."""
    from datetime import datetime
    return jsonify({
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "nodes": {
            "mainnet": len(mainnet_dojos),
            "testnet": len(testnet_dojos)
        }
    })


@app.route('/favicon.ico')
def favicon():
    """Serve favicon from static/images."""
    static_dir = os.path.join(app.root_path, 'static', 'images')
    return send_from_directory(
        static_dir,
        'favicon.ico',
        mimetype='image/vnd.microsoft.icon'
    )


if __name__ == '__main__':
    print("Starting Dojobay web application...")
    print(f"Loaded {len(mainnet_dojos)} mainnet and {len(testnet_dojos)} testnet nodes")
    
    # Start background checker
    background_checker.start()
    
    print(f"Server starting on http://{HOST}:{PORT}")
    app.run(debug=DEBUG, host=HOST, port=PORT)

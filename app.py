from flask import Flask, render_template, jsonify
import requests
from datetime import datetime
import json
from pathlib import Path
import threading
import time

app = Flask(__name__)

# Configuration
DEFAULT_PROXIES = {"http": "socks5h://127.0.0.1:9050", "https": "socks5h://127.0.0.1:9050"}
CACHE_FILE = Path(__file__).parent / "status_cache.json"
CACHE_DURATION = 300  # 5 minutos en segundos

# Load Dojo URLs from JSON file
DOJOS_DATA_FILE = Path(__file__).parent / "dojos_data.json"
def load_dojos_data():
    try:
        with open(DOJOS_DATA_FILE, "r") as f:
            data = json.load(f)
            mainnet = data.get("mainnet", [])
            testnet = data.get("testnet", [])
            return mainnet, testnet
    except Exception as e:
        print(f"Error loading dojos_data.json: {e}")
        return [], []

MAINNET_DOJOS, TESTNET_DOJOS = load_dojos_data()

# Global cache

_status_cache = {
    "data": None,
    "timestamp": None
}
_cache_lock = threading.Lock()

def background_checker():
    while True:
        try:
            results = {
                "mainnet": [],
                "testnet": [],
                "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            for dojo in MAINNET_DOJOS:
                result = check_onion_url(dojo, DEFAULT_PROXIES)
                results["mainnet"].append(result)
            for dojo in TESTNET_DOJOS:
                result = check_onion_url(dojo, DEFAULT_PROXIES)
                results["testnet"].append(result)
            results["stats"] = {
                "mainnet_active": sum(1 for d in results["mainnet"] if d["status"] == "Active"),
                "mainnet_total": len(results["mainnet"]),
                "testnet_active": sum(1 for d in results["testnet"] if d["status"] == "Active"),
                "testnet_total": len(results["testnet"])
            }
            save_cache(results)
        except Exception as e:
            print(f"[BG CHECK] Error: {e}")
        time.sleep(CACHE_DURATION)

def start_background_thread():
    t = threading.Thread(target=background_checker, daemon=True)
    t.start()


def get_cached_status():
    """Get cached status if available and recent"""
    with _cache_lock:
        if _status_cache["data"] and _status_cache["timestamp"]:
            age = (datetime.now() - _status_cache["timestamp"]).seconds
            if age < CACHE_DURATION:
                return _status_cache["data"]
    
    # Try file cache as fallback
    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE, 'r') as f:
                cache = json.load(f)
                cache_time = datetime.fromisoformat(cache['timestamp'])
                if (datetime.now() - cache_time).seconds < CACHE_DURATION:
                    return cache['data']
        except Exception:
            pass
    return None


def save_cache(data):
    """Save status data to cache"""
    with _cache_lock:
        _status_cache["data"] = data
        _status_cache["timestamp"] = datetime.now()
    
    # Also save to file
    try:
        cache = {
            'timestamp': datetime.now().isoformat(),
            'data': data
        }
        with open(CACHE_FILE, 'w') as f:
            json.dump(cache, f)
    except Exception as e:
        print(f"Failed to save cache to file: {e}")


def check_onion_url(dojo_info, proxies):
    """Check a single onion URL"""
    entry = dojo_info.copy()
    
    # Preserve signature if present
    if "signature" in dojo_info and isinstance(dojo_info["signature"], str):
        entry["signature"] = str(dojo_info["signature"])
    elif "signature" in entry:
        entry.pop("signature")

    # Initialize status fields
    entry["status"] = "Inactive"
    entry["checked_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Skip check if marked as out of service
    if dojo_info.get("status") == "out_of_service":
        entry["status"] = "Out of Service"
        return entry

    # Extract base URL (up to .onion)
    url = None
    full_url = dojo_info.get("pairing", {}).get("url") or dojo_info.get("url")
    if full_url:
        idx = full_url.find(".onion")
        if idx != -1:
            url = full_url[:idx+6]

    if not url:
        entry["error"] = "Missing or invalid URL"
        print(f"[ERROR] Invalid URL for node: {dojo_info.get('name', 'Unknown')}")
        return entry

    try:
        resp = requests.get(url, proxies=proxies, timeout=15)
        entry["status"] = "Active" if resp.status_code == 200 else "Inactive"
        if resp.status_code != 200:
            entry["error"] = f"HTTP {resp.status_code}"
    except requests.RequestException as e:
        entry["error"] = f"{type(e).__name__}"
        print(f"[ERROR] {url}: {type(e).__name__}")
    
    return entry


def check_all_dojos():
    """Check all Dojo onion services"""
    # Check cache first
    cached = get_cached_status()
    if cached:
        return cached
    
    results = {
        "mainnet": [],
        "testnet": [],
        "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    # Check mainnet
    for dojo in MAINNET_DOJOS:
        result = check_onion_url(dojo, DEFAULT_PROXIES)
        results["mainnet"].append(result)
    
    # Check testnet
    for dojo in TESTNET_DOJOS:
        result = check_onion_url(dojo, DEFAULT_PROXIES)
        results["testnet"].append(result)
    
    # Calculate stats
    results["stats"] = {
        "mainnet_active": sum(1 for d in results["mainnet"] if d["status"] == "Active"),
        "mainnet_total": len(results["mainnet"]),
        "testnet_active": sum(1 for d in results["testnet"] if d["status"] == "Active"),
        "testnet_total": len(results["testnet"])
    }
    
    # Save to cache
    save_cache(results)
    
    return results


@app.route('/')
def index():
    """Main page with live Dojo status"""
    status = check_all_dojos()
    return render_template('index.html', status=status)


@app.route('/about')
def about():
    """About page"""
    return render_template('about.html')


@app.route('/disclaimer')
def disclaimer():
    """Disclaimer page"""
    return render_template('disclaimer.html')


@app.route('/faq')
def faq():
    """FAQ page"""
    return render_template('faq.html')


@app.route('/api/status')
def api_status():
    """API endpoint to get current Dojo status"""
    try:
        cached = get_cached_status()
        if cached:
            return jsonify(cached)
        
        # No cache available, return loading message
        return jsonify({"loading": True, "message": "Updating node status..."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({"status": "ok", "timestamp": datetime.now().isoformat()})



# Ruta explícita para favicon.ico
from flask import send_from_directory
import os

@app.route('/favicon.ico')
def favicon():
    """Serve favicon from static/images"""
    static_dir = os.path.join(app.root_path, 'static', 'images')
    return send_from_directory(static_dir, 'favicon.ico', mimetype='image/vnd.microsoft.icon')


if __name__ == '__main__':
    print("Starting Dojobay web application...")
    start_background_thread()
    print("Server starting on http://0.0.0.0:5002")
    app.run(debug=False, host='0.0.0.0', port=5002)

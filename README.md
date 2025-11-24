# Dojobay - Public Dojo Directory

A Flask-based web application for monitoring public Bitcoin Dojo nodes on the Tor network.

## Features

- Real-time monitoring of mainnet and testnet Dojo nodes
- Signature verification for trusted nodes
- QR code display for easy pairing
- Responsive design with mobile support
- Automatic status updates every 10 minutes
- Tor network integration for onion service checking

## Project Structure

```
dojobay/
├── app.py                      # Main Flask application
├── config.py                   # Configuration settings
├── cache.py                    # Cache management
├── checker.py                  # Dojo status checker
├── data_loader.py              # JSON data loader
├── background_checker.py       # Background status updater
├── dojos_data.json            # Dojo node configurations
├── requirements.txt           # Python dependencies
├── gunicorn.conf.py          # Gunicorn configuration
├── templates/                 # HTML templates
│   ├── base.html
│   ├── index.html
│   ├── about.html
│   ├── faq.html
│   └── disclaimer.html
└── static/                    # Static assets
    └── images/
        ├── favicon/
        └── qr/
```

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Ensure Tor is running on port 9050

3. Run the application:
```bash
python app.py
```

Or with Gunicorn:
```bash
gunicorn -c gunicorn.conf.py app:app
```

## Configuration

Edit `config.py` to customize:
- Cache duration
- Request timeout
- Server host/port
- Tor proxy settings

## API Endpoints

- `GET /` - Main status page
- `GET /api/status` - JSON status data
- `GET /health` - Health check endpoint
- `GET /about` - About page
- `GET /faq` - FAQ page
- `GET /disclaimer` - Disclaimer page

## Development

The application uses:
- Flask for web framework
- Requests with SOCKS proxy for Tor connectivity
- Threading for background status checks
- JSON file-based cache for performance

## License

See LICENSE file for details.

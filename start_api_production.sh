#!/bin/bash
# Dojobay External API - Production Startup Script
# Usage: ./start_api_production.sh [token] [workers] [bind]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check if running in virtual environment
if [[ -z "$VIRTUAL_ENV" ]]; then
    echo -e "${YELLOW}Activating virtual environment...${NC}"
    source venv/bin/activate || {
        echo -e "${RED}Error: Virtual environment not found. Please run: python3 -m venv venv${NC}"
        exit 1
    }
fi

# Validate dependencies
echo -e "${GREEN}Checking dependencies...${NC}"
python3 -c "import flask; import flask_cors; import gunicorn" 2>/dev/null || {
    echo -e "${YELLOW}Installing missing dependencies...${NC}"
    pip install -q flask flask-cors gunicorn
}

# Validate data file
if [[ ! -f "dojos_data.json" ]]; then
    echo -e "${RED}Error: dojos_data.json not found!${NC}"
    exit 1
fi

# Validate JSON
python3 -c "import json; json.load(open('dojos_data.json'))" || {
    echo -e "${RED}Error: dojos_data.json contains invalid JSON!${NC}"
    exit 1
}

# Set API Token (from argument or prompt)
if [[ -z "$1" ]]; then
    echo -e "${YELLOW}No token provided. Using environment variable DOJOBAY_API_TOKEN${NC}"
    if [[ -z "$DOJOBAY_API_TOKEN" ]]; then
        echo -e "${RED}Error: DOJOBAY_API_TOKEN not set and no token provided as argument${NC}"
        echo "Usage: $0 <token> [workers] [bind]"
        echo "Example: $0 'e3a15e137191a5016644dfb6f6fe4f7c7dac2156157a0b4bfcd73bc5614727d7' 4 '0.0.0.0:8080'"
        exit 1
    fi
else
    export DOJOBAY_API_TOKEN="$1"
fi

# Set workers (default: 4)
WORKERS="${2:-4}"
export DOJOBAY_WORKERS="$WORKERS"

# Set bind address (default: 127.0.0.1:8080)
BIND="${3:-127.0.0.1:8080}"
export DOJOBAY_BIND="$BIND"

# Log files
ACCESS_LOG="${SCRIPT_DIR}/external_api_access.log"
ERROR_LOG="${SCRIPT_DIR}/external_api_error.log"

echo -e "${GREEN}Starting Dojobay External API in Production${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "Token: ${YELLOW}$(echo $DOJOBAY_API_TOKEN | cut -c1-8)...${NC}"
echo "Workers: $WORKERS"
echo "Bind address: $BIND"
echo "Access log: $ACCESS_LOG"
echo "Error log: $ERROR_LOG"
echo "Data file: $(pwd)/dojos_data.json"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Start Gunicorn
export DOJOBAY_ACCESS_LOG="$ACCESS_LOG"
export DOJOBAY_ERROR_LOG="$ERROR_LOG"

gunicorn \
    -c gunicorn_external_api_prod.conf.py \
    --access-logfile "$ACCESS_LOG" \
    --error-logfile "$ERROR_LOG" \
    external_api:app

echo -e "${GREEN}Dojobay External API stopped${NC}"

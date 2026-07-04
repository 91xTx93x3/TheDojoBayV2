#!/bin/bash
# Install Dojobay External API - Complete Production Setup
# This script installs the API as a systemd service

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Dojobay External API - Complete Production Installation${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}This script must be run as root${NC}"
   echo "Run with: sudo bash install_production.sh"
   exit 1
fi

API_DIR="/root/dojobay"
VENV_DIR="${API_DIR}/venv"

echo -e "${BLUE}Step 1: Verifying Environment${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Python 3 is not installed${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Python 3 found: $(python3 --version)${NC}"

# Check virtual environment
if [ ! -f "${VENV_DIR}/bin/activate" ]; then
    echo -e "${RED}Virtual environment not found at ${VENV_DIR}${NC}"
    echo "Please run: cd $API_DIR && python3 -m venv venv"
    exit 1
fi
echo -e "${GREEN}✓ Virtual environment found${NC}"

# Check dependencies
echo -e "${BLUE}Step 2: Installing Dependencies${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

source "${VENV_DIR}/bin/activate"
pip install --quiet -r "${API_DIR}/requirements.txt"
echo -e "${GREEN}✓ Dependencies installed${NC}"

# Check data file
echo -e "${BLUE}Step 3: Verifying Data File${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ ! -f "${API_DIR}/dojos_data.json" ]; then
    echo -e "${RED}Data file not found: ${API_DIR}/dojos_data.json${NC}"
    exit 1
fi

python3 -c "import json; json.load(open('${API_DIR}/dojos_data.json'))" || {
    echo -e "${RED}Invalid JSON in dojos_data.json${NC}"
    exit 1
}
echo -e "${GREEN}✓ Data file is valid${NC}"

# Install systemd service
echo -e "${BLUE}Step 4: Installing Systemd Service${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ ! -f "${API_DIR}/dojobay-api.service" ]; then
    echo -e "${RED}Service file not found: ${API_DIR}/dojobay-api.service${NC}"
    exit 1
fi

cp "${API_DIR}/dojobay-api.service" /etc/systemd/system/
systemctl daemon-reload
echo -e "${GREEN}✓ Systemd service installed${NC}"

# Make scripts executable
echo -e "${BLUE}Step 5: Making Scripts Executable${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

chmod +x "${API_DIR}/setup_ssl.sh"
chmod +x "${API_DIR}/monitor_api.sh"
chmod +x "${API_DIR}/manage_tokens.sh"
chmod +x "${API_DIR}/API_QUICK_REFERENCE.sh"
chmod +x "${API_DIR}/start_api_production.sh"

echo -e "${GREEN}✓ Scripts are executable${NC}"

# Create necessary directories
mkdir -p "${API_DIR}/tokens"
mkdir -p "${API_DIR}/backups"
chmod 700 "${API_DIR}/tokens"

echo -e "${BLUE}Step 6: Setting Permissions${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Set restrictive permissions on sensitive files
chmod 600 "${API_DIR}/.env.production"
chmod 600 "${API_DIR}/dojobay-api.service"

echo -e "${GREEN}✓ Permissions set${NC}"

# Installation complete
echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✓ Installation Complete!${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
echo ""

echo -e "${BLUE}Next Steps:${NC}"
echo ""
echo "1. Start the API service:"
echo "   systemctl start dojobay-api"
echo ""
echo "2. Enable auto-start on boot:"
echo "   systemctl enable dojobay-api"
echo ""
echo "3. Check service status:"
echo "   systemctl status dojobay-api"
echo ""
echo "4. View logs:"
echo "   journalctl -u dojobay-api -f"
echo ""
echo "5. Setup SSL/TLS (Required for production):"
echo "   sudo bash ${API_DIR}/setup_ssl.sh"
echo ""
echo "6. Monitor the API:"
echo "   bash ${API_DIR}/monitor_api.sh"
echo ""
echo "7. Manage tokens for external teams:"
echo "   bash ${API_DIR}/manage_tokens.sh create team-name"
echo ""

echo -e "${BLUE}Useful Commands:${NC}"
echo ""
echo "# Stop the service"
echo "systemctl stop dojobay-api"
echo ""
echo "# Restart the service"
echo "systemctl restart dojobay-api"
echo ""
echo "# View logs"
echo "journalctl -u dojobay-api -f"
echo ""
echo "# View service configuration"
echo "systemctl cat dojobay-api"
echo ""
echo "# Edit service configuration"
echo "systemctl edit dojobay-api"
echo ""

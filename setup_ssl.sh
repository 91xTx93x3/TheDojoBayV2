#!/bin/bash
# Setup SSL/TLS Certificates for Dojobay External API
# This script helps you obtain and configure SSL certificates

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Dojobay External API - SSL/TLS Certificate Setup${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}This script must be run as root${NC}"
   echo "Run with: sudo bash setup_ssl.sh"
   exit 1
fi

# Get domain
read -p "Enter your domain name (e.g., api.dojobay.com): " DOMAIN
if [[ -z "$DOMAIN" ]]; then
    echo -e "${RED}Domain is required${NC}"
    exit 1
fi

# Option 1: Let's Encrypt (Recommended for production)
echo ""
echo -e "${YELLOW}SSL Certificate Options:${NC}"
echo "1. Let's Encrypt (FREE - Recommended for production)"
echo "2. Self-signed certificate (Testing/Development only)"
read -p "Choose option (1 or 2): " CERT_OPTION

if [ "$CERT_OPTION" = "1" ]; then
    echo ""
    echo -e "${BLUE}Setting up Let's Encrypt with Certbot...${NC}"
    
    # Install certbot if not present
    if ! command -v certbot &> /dev/null; then
        echo -e "${YELLOW}Installing certbot...${NC}"
        apt-get update
        apt-get install -y certbot python3-certbot-nginx
    fi
    
    # Obtain certificate
    echo -e "${BLUE}Obtaining Let's Encrypt certificate for ${DOMAIN}...${NC}"
    certbot certonly --standalone \
        -d "$DOMAIN" \
        -d "www.$DOMAIN" \
        --email admin@"$DOMAIN" \
        --agree-tos \
        --non-interactive \
        --preferred-challenges http
    
    CERT_PATH="/etc/letsencrypt/live/${DOMAIN}/fullchain.pem"
    KEY_PATH="/etc/letsencrypt/live/${DOMAIN}/privkey.pem"
    
    if [ -f "$CERT_PATH" ]; then
        echo -e "${GREEN}✓ Certificate obtained successfully${NC}"
        echo "Certificate: $CERT_PATH"
        echo "Private Key: $KEY_PATH"
        
        # Setup auto-renewal
        echo ""
        echo -e "${BLUE}Setting up automatic certificate renewal...${NC}"
        certbot renew --dry-run
        systemctl enable certbot.timer
        systemctl start certbot.timer
        echo -e "${GREEN}✓ Auto-renewal enabled${NC}"
    else
        echo -e "${RED}✗ Failed to obtain certificate${NC}"
        exit 1
    fi

elif [ "$CERT_OPTION" = "2" ]; then
    echo ""
    echo -e "${BLUE}Generating self-signed certificate...${NC}"
    
    CERT_DIR="/etc/nginx/ssl"
    mkdir -p "$CERT_DIR"
    
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout "$CERT_DIR/privkey.pem" \
        -out "$CERT_DIR/fullchain.pem" \
        -subj "/CN=$DOMAIN"
    
    CERT_PATH="$CERT_DIR/fullchain.pem"
    KEY_PATH="$CERT_DIR/privkey.pem"
    
    echo -e "${YELLOW}⚠ Self-signed certificate created (Testing only)${NC}"
    echo "Certificate: $CERT_PATH"
    echo "Private Key: $KEY_PATH"
else
    echo -e "${RED}Invalid option${NC}"
    exit 1
fi

# Install Nginx if not present
if ! command -v nginx &> /dev/null; then
    echo ""
    echo -e "${BLUE}Installing Nginx...${NC}"
    apt-get update
    apt-get install -y nginx
fi

# Setup Nginx configuration
echo ""
echo -e "${BLUE}Configuring Nginx...${NC}"

# Copy Nginx config
cp /root/dojobay/nginx_config.conf /etc/nginx/sites-available/dojobay-api

# Update domain and certificate paths in config
sed -i "s/your-domain\.com/$DOMAIN/g" /etc/nginx/sites-available/dojobay-api
sed -i "s|/etc/letsencrypt/live/your-domain.com/fullchain.pem|$CERT_PATH|g" \
    /etc/nginx/sites-available/dojobay-api
sed -i "s|/etc/letsencrypt/live/your-domain.com/privkey.pem|$KEY_PATH|g" \
    /etc/nginx/sites-available/dojobay-api

# Enable site
ln -sf /etc/nginx/sites-available/dojobay-api /etc/nginx/sites-enabled/

# Test and reload Nginx
echo -e "${BLUE}Testing Nginx configuration...${NC}"
nginx -t

echo -e "${BLUE}Reloading Nginx...${NC}"
systemctl reload nginx

echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✓ SSL/TLS Setup Complete!${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${BLUE}Certificate Information:${NC}"
echo "Domain: $DOMAIN"
echo "Certificate: $CERT_PATH"
echo "Private Key: $KEY_PATH"
echo ""
echo -e "${BLUE}Your API is now accessible at:${NC}"
echo "https://$DOMAIN/api/dojos"
echo "https://$DOMAIN/api/info"
echo ""
echo -e "${BLUE}Test with:${NC}"
echo "curl -H \"Authorization: Bearer \$(cat /root/dojobay/.env.production | grep DOJOBAY_API_TOKEN | cut -d'=' -f2)\" \\"
echo "     https://$DOMAIN/api/dojos | python3 -m json.tool"
echo ""

# Certificate renewal instructions
if [ "$CERT_OPTION" = "1" ]; then
    echo -e "${YELLOW}Certificate Renewal:${NC}"
    echo "Certbot will automatically renew your certificate 30 days before expiration"
    echo "To manually renew: certbot renew --force-renewal"
    echo "To check renewal status: systemctl status certbot.timer"
fi

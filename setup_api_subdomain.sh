#!/bin/bash
# Setup api.dojobay.pw with SSL

echo "╔════════════════════════════════════════════════════════╗"
echo "║  Dojobay API Subdomain Setup - api.dojobay.pw        ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""

# Check DNS
echo "1️⃣  Checking DNS resolution..."
if nslookup api.dojobay.pw 2>/dev/null | grep -q "Address:"; then
    echo "   ✅ DNS resolved"
else
    echo "   ❌ DNS not yet propagated"
    echo "   Please configure DNS first:"
    echo "      Subdomain: api"
    echo "      Type:      A Record"
    echo "      Value:     5.181.181.21"
    echo ""
    echo "   Then run this script again"
    exit 1
fi

# Install certificates
echo ""
echo "2️⃣  Obtaining SSL certificate..."
sudo certbot certonly --nginx -d api.dojobay.pw --non-interactive --agree-tos || exit 1

# Apply production config
echo ""
echo "3️⃣  Applying production configuration..."
sudo cp /root/dojobay/nginx_api.conf /etc/nginx/sites-available/api.dojobay.pw
sudo ln -sf /etc/nginx/sites-available/api.dojobay.pw /etc/nginx/sites-enabled/api.dojobay.pw

# Test and reload
echo ""
echo "4️⃣  Testing Nginx configuration..."
sudo nginx -t || exit 1

echo ""
echo "5️⃣  Reloading Nginx..."
sudo systemctl reload nginx

# Verify
echo ""
echo "6️⃣  Verifying..."
sleep 2
if curl -s -k https://api.dojobay.pw/health | grep -q "status"; then
    echo "   ✅ API accessible at https://api.dojobay.pw"
else
    echo "   ⚠️  Testing..."
fi

echo ""
echo "╔════════════════════════════════════════════════════════╗"
echo "║  ✅ Setup Complete!                                   ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""
echo "Your API is now accessible at:"
echo "  🌐 https://api.dojobay.pw"
echo ""
echo "Test endpoints:"
echo "  curl https://api.dojobay.pw/health"
echo "  curl -H \"Authorization: Bearer YOUR_TOKEN\" \\"
echo "       https://api.dojobay.pw/api/dojos"
echo ""

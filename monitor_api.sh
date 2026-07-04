#!/bin/bash
# Monitor Dojobay External API - Real-time monitoring and alerts

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
API_HOST="127.0.0.1"
API_PORT="8090"
LOG_FILE="/root/dojobay/external_api_monitoring.log"
ALERT_THRESHOLD_CPU=80
ALERT_THRESHOLD_MEM=80
ALERT_THRESHOLD_ERROR_RATE=10

# Functions
log_message() {
    echo -e "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

check_process() {
    if pgrep -f "gunicorn.*external_api" > /dev/null; then
        echo -e "${GREEN}✓ API Process${NC}: Running"
        return 0
    else
        echo -e "${RED}✗ API Process${NC}: NOT Running"
        log_message "ALERT: API process not running"
        return 1
    fi
}

check_port() {
    if nc -z "$API_HOST" "$API_PORT" 2>/dev/null; then
        echo -e "${GREEN}✓ Port ${API_PORT}${NC}: Open"
        return 0
    else
        echo -e "${RED}✗ Port ${API_PORT}${NC}: Closed"
        log_message "ALERT: Port $API_PORT is not responding"
        return 1
    fi
}

check_health() {
    local response=$(curl -s -w "\n%{http_code}" "http://$API_HOST:$API_PORT/health" 2>/dev/null || echo -e "\n000")
    local http_code=$(echo "$response" | tail -n1)
    
    if [ "$http_code" = "200" ]; then
        echo -e "${GREEN}✓ Health Check${NC}: OK (HTTP $http_code)"
        return 0
    else
        echo -e "${RED}✗ Health Check${NC}: FAILED (HTTP $http_code)"
        log_message "ALERT: Health check returned HTTP $http_code"
        return 1
    fi
}

check_api_response() {
    local response=$(curl -s -w "\n%{http_code}" \
        -H "Authorization: Bearer e3a15e137191a5016644dfb6f6fe4f7c7dac2156157a0b4bfcd73bc5614727d7" \
        "http://$API_HOST:$API_PORT/api/info" 2>/dev/null || echo -e "\n000")
    local http_code=$(echo "$response" | tail -n1)
    
    if [ "$http_code" = "200" ]; then
        echo -e "${GREEN}✓ API Response${NC}: OK (HTTP $http_code)"
        return 0
    else
        echo -e "${RED}✗ API Response${NC}: FAILED (HTTP $http_code)"
        log_message "ALERT: API response returned HTTP $http_code"
        return 1
    fi
}

check_resources() {
    # Get API process info
    local pid=$(pgrep -f "gunicorn.*external_api" | head -n1)
    
    if [ -z "$pid" ]; then
        echo -e "${YELLOW}⚠ Resources${NC}: Process not found"
        return
    fi
    
    # CPU and Memory
    local cpu=$(ps -p "$pid" -o %cpu= | xargs)
    local mem=$(ps -p "$pid" -o %mem= | xargs)
    
    echo -e "  CPU: $cpu%"
    echo -e "  MEM: $mem%"
    
    # Check thresholds
    if (( $(echo "$cpu > $ALERT_THRESHOLD_CPU" | bc -l) )); then
        echo -e "${RED}⚠ CPU usage high!${NC}"
        log_message "ALERT: CPU usage $cpu%"
    fi
    
    if (( $(echo "$mem > $ALERT_THRESHOLD_MEM" | bc -l) )); then
        echo -e "${RED}⚠ Memory usage high!${NC}"
        log_message "ALERT: Memory usage $mem%"
    fi
}

check_error_logs() {
    # Count errors in last hour
    local error_count=$(tail -1000 /root/dojobay/external_api_error.log 2>/dev/null | grep -i error | wc -l || echo 0)
    
    if [ "$error_count" -gt 0 ]; then
        echo -e "${YELLOW}⚠ Recent Errors${NC}: $error_count"
        
        if [ "$error_count" -gt "$ALERT_THRESHOLD_ERROR_RATE" ]; then
            log_message "ALERT: High error rate detected ($error_count errors)"
        fi
    else
        echo -e "${GREEN}✓ Errors${NC}: None"
    fi
}

check_disk() {
    # Check disk usage in /root/dojobay
    local disk_usage=$(df /root/dojobay | awk 'NR==2 {print $5}' | sed 's/%//')
    
    echo -e "  Disk Usage: $disk_usage%"
    
    if [ "$disk_usage" -gt 80 ]; then
        echo -e "${RED}⚠ Disk usage high!${NC}"
        log_message "ALERT: Disk usage $disk_usage%"
    fi
}

check_log_files() {
    # Check log file sizes
    local access_size=$(stat -f%z /root/dojobay/external_api_access.log 2>/dev/null || stat -c%s /root/dojobay/external_api_access.log 2>/dev/null || echo 0)
    local error_size=$(stat -f%z /root/dojobay/external_api_error.log 2>/dev/null || stat -c%s /root/dojobay/external_api_error.log 2>/dev/null || echo 0)
    
    local access_mb=$((access_size / 1048576))
    local error_mb=$((error_size / 1048576))
    
    echo -e "  Access Log: ${access_mb}MB"
    echo -e "  Error Log: ${error_mb}MB"
    
    if [ "$access_mb" -gt 100 ]; then
        echo -e "${YELLOW}⚠ Access log is large (${access_mb}MB)${NC}"
        echo "    Consider rotating with: logrotate"
    fi
}

show_dashboard() {
    clear
    
    echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║     Dojobay External API - Monitoring Dashboard                ║${NC}"
    echo -e "${BLUE}║     $(date '+%Y-%m-%d %H:%M:%S')                                     ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    
    echo -e "${BLUE}Service Status:${NC}"
    check_process
    check_port
    echo ""
    
    echo -e "${BLUE}API Health:${NC}"
    check_health
    check_api_response
    echo ""
    
    echo -e "${BLUE}Resource Usage:${NC}"
    check_resources
    echo ""
    
    echo -e "${BLUE}Error Monitoring:${NC}"
    check_error_logs
    echo ""
    
    echo -e "${BLUE}Storage:${NC}"
    check_disk
    echo ""
    
    echo -e "${BLUE}Log Files:${NC}"
    check_log_files
    echo ""
    
    echo -e "${BLUE}Recent Log Entries:${NC}"
    echo "Access (last 5):"
    tail -5 /root/dojobay/external_api_access.log | head -5
    echo ""
    echo "Errors (last 5):"
    tail -5 /root/dojobay/external_api_error.log | head -5
    echo ""
    
    echo -e "${YELLOW}Press Ctrl+C to exit, will refresh every 30 seconds...${NC}"
}

# Main loop
if [ "$1" = "--continuous" ]; then
    while true; do
        show_dashboard
        sleep 30
    done
else
    show_dashboard
    echo ""
    echo -e "${BLUE}For continuous monitoring, run:${NC}"
    echo "  $0 --continuous"
fi

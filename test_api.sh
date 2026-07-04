#!/bin/bash
# Comprehensive API Test Suite for Dojobay External API

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

API_HOST="127.0.0.1"
API_PORT="8090"
MASTER_TOKEN="e3a15e137191a5016644dfb6f6fe4f7c7dac2156157a0b4bfcd73bc5614727d7"
TEST_LOG="/tmp/api_test_$(date +%s).log"

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0

# Functions
log_test() {
    echo "[$(date '+%H:%M:%S')] $1" >> "$TEST_LOG"
}

test_endpoint() {
    local name="$1"
    local endpoint="$2"
    local token="$3"
    local expected_status="$4"
    
    echo -ne "${CYAN}Testing: $name${NC}... "
    
    local response=$(curl -s -w "\n%{http_code}" \
        ${token:+-H "Authorization: Bearer $token"} \
        "http://$API_HOST:$API_PORT$endpoint" 2>/dev/null || echo -e "\n000")
    
    local http_code=$(echo "$response" | tail -n1)
    local body=$(echo "$response" | head -n-1)
    
    if [ "$http_code" = "$expected_status" ]; then
        echo -e "${GREEN}✓ PASS${NC} (HTTP $http_code)"
        log_test "✓ $name - PASS (HTTP $http_code)"
        ((TESTS_PASSED++))
        return 0
    else
        echo -e "${RED}✗ FAIL${NC} (Expected HTTP $expected_status, got $http_code)"
        log_test "✗ $name - FAIL (Expected HTTP $expected_status, got $http_code)"
        ((TESTS_FAILED++))
        return 0
    fi
}

test_response_json() {
    local name="$1"
    local endpoint="$2"
    local token="$3"
    local json_path="$4"
    
    echo -ne "${CYAN}Testing: $name${NC}... "
    
    local response=$(curl -s \
        ${token:+-H "Authorization: Bearer $token"} \
        "http://$API_HOST:$API_PORT$endpoint" 2>/dev/null || echo "{}")
    
    # Check if response is valid JSON
    if echo "$response" | python3 -m json.tool > /dev/null 2>&1; then
        if [ -z "$json_path" ]; then
            echo -e "${GREEN}✓ PASS${NC} (Valid JSON)"
            log_test "✓ $name - PASS (Valid JSON)"
            ((TESTS_PASSED++))
            return 0
        else
            # Check if json_path exists
            local value=$(echo "$response" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('$json_path', ''))" 2>/dev/null || echo "")
            if [ ! -z "$value" ]; then
                echo -e "${GREEN}✓ PASS${NC} (JSON path exists)"
                log_test "✓ $name - PASS (JSON path '$json_path' exists)"
                ((TESTS_PASSED++))
                return 0
            fi
        fi
    fi
    
    echo -e "${RED}✗ FAIL${NC} (Invalid JSON response)"
    log_test "✗ $name - FAIL (Invalid JSON response)"
    ((TESTS_FAILED++))
    return 0
}

# Header
echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     Dojobay External API - Comprehensive Test Suite            ║${NC}"
echo -e "${BLUE}║     $(date '+%Y-%m-%d %H:%M:%S')                                     ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Connection tests
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}Connection Tests${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# Check if server is running
echo -ne "${CYAN}Checking API availability${NC}... "
if nc -z "$API_HOST" "$API_PORT" 2>/dev/null; then
    echo -e "${GREEN}✓ API is responding${NC}"
    log_test "✓ API is responding"
else
    echo -e "${RED}✗ Cannot connect to API${NC}"
    log_test "✗ Cannot connect to API"
    echo ""
    echo -e "${RED}Aborting tests - API is not running${NC}"
    echo "Start the API with: sudo systemctl start dojobay-api"
    exit 1
fi

echo ""

# Authentication tests
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}Authentication Tests${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

test_endpoint "No token" "/api/dojos" "" "401"
test_endpoint "Invalid token" "/api/dojos" "invalid-token" "401"
test_endpoint "Valid token" "/api/dojos" "$MASTER_TOKEN" "200"

echo ""

# Endpoint tests
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}API Endpoint Tests${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

test_endpoint "GET /api/info" "/api/info" "$MASTER_TOKEN" "200"
test_endpoint "GET /api/dojos" "/api/dojos" "$MASTER_TOKEN" "200"
test_endpoint "GET /api/dojos?network=mainnet" "/api/dojos?network=mainnet" "$MASTER_TOKEN" "200"
test_endpoint "GET /api/dojos?network=testnet" "/api/dojos?network=testnet" "$MASTER_TOKEN" "200"
test_endpoint "GET /api/dojos?network=invalid" "/api/dojos?network=invalid" "$MASTER_TOKEN" "400"
test_endpoint "GET /health" "/health" "" "200"

echo ""

# Response format tests
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}Response Format Tests${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

test_response_json "API Info JSON" "/api/info" "$MASTER_TOKEN" "name"
test_response_json "Dojos Count" "/api/dojos" "$MASTER_TOKEN" "count"
test_response_json "Dojos Array" "/api/dojos" "$MASTER_TOKEN" "dojos"
test_response_json "Health JSON" "/health" "" "status"

echo ""

# Data content tests
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}Data Content Tests${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

echo -ne "${CYAN}Testing: Dojos contain data${NC}... "
dojos_count=$(curl -s -H "Authorization: Bearer $MASTER_TOKEN" \
    "http://$API_HOST:$API_PORT/api/dojos" | \
    python3 -c "import json,sys; print(json.load(sys.stdin).get('count', 0))" 2>/dev/null || echo 0)

if [ "$dojos_count" -gt 0 ]; then
    echo -e "${GREEN}✓ PASS${NC} ($dojos_count dojos found)"
    log_test "✓ Dojos contain data - PASS ($dojos_count dojos found)"
    ((TESTS_PASSED++))
else
    echo -e "${RED}✗ FAIL${NC} (No dojos found)"
    log_test "✗ Dojos contain data - FAIL (No dojos found)"
    ((TESTS_FAILED++))
fi

echo ""

# Performance tests
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}Performance Tests${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

echo -ne "${CYAN}Testing: Response time${NC}... "
response_time=$(curl -s -w "%{time_total}" -o /dev/null \
    -H "Authorization: Bearer $MASTER_TOKEN" \
    "http://$API_HOST:$API_PORT/api/dojos" 2>/dev/null || echo "999")

# Convert to milliseconds
response_ms=$(echo "$response_time * 1000" | bc 2>/dev/null || echo "999000")

if (( $(echo "$response_time < 1" | bc -l 2>/dev/null || echo 1) )); then
    echo -e "${GREEN}✓ PASS${NC} (${response_ms}ms)"
    log_test "✓ Response time - PASS (${response_ms}ms)"
    ((TESTS_PASSED++))
else
    echo -e "${YELLOW}⚠ SLOW${NC} (${response_ms}ms - may need optimization)"
    log_test "⚠ Response time - SLOW (${response_ms}ms)"
fi

echo ""

# Summary
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}Test Summary${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed!${NC}"
    echo "Passed: $TESTS_PASSED"
    echo ""
    echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}API is production-ready! 🚀${NC}"
    echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
    exit 0
else
    echo -e "${RED}✗ Some tests failed${NC}"
    echo "Passed: $TESTS_PASSED"
    echo "Failed: $TESTS_FAILED"
    echo ""
    echo "Test log: $TEST_LOG"
    exit 1
fi

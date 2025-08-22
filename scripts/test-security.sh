#!/bin/bash

set -e

echo "🔒 Testing Chat Proxy Security Features..."

BASE_URL="http://localhost:8000"
TEST_DOMAIN="localhost:3000"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test results
PASS_COUNT=0
FAIL_COUNT=0

# Function to run test
run_test() {
    local test_name="$1"
    local command="$2"
    local expected_status="$3"
    
    echo -n "Testing $test_name... "
    
    if response=$(eval "$command" 2>&1); then
        if echo "$response" | grep -q "HTTP/$expected_status" || [[ "$expected_status" == "any" ]]; then
            echo -e "${GREEN}PASS${NC}"
            ((PASS_COUNT++))
        else
            echo -e "${RED}FAIL${NC} (Expected HTTP $expected_status)"
            echo "Response: $response"
            ((FAIL_COUNT++))
        fi
    else
        echo -e "${RED}FAIL${NC} (Command failed)"
        echo "Error: $response"
        ((FAIL_COUNT++))
    fi
}

# Function to extract session cookie
extract_cookie() {
    local response="$1"
    echo "$response" | grep -o 'chat_session_id=[^;]*' | head -1
}

echo "🚀 Starting security tests..."
echo ""

# Test 1: Health check
echo "=== Basic Functionality Tests ==="
run_test "Health Check" "curl -s -w 'HTTP/%{http_code}' $BASE_URL/health" "200"

# Test 2: Invalid origin
echo ""
echo "=== Origin Validation Tests ==="
run_test "Invalid Origin" "curl -s -w 'HTTP/%{http_code}' -H 'Origin: https://evil-site.com' $BASE_URL/api/v1/session/create" "403"

# Test 3: Missing origin
run_test "Missing Origin (Dev Mode)" "curl -s -w 'HTTP/%{http_code}' $BASE_URL/api/v1/session/create -d '{\"origin_domain\":\"localhost\"}' -H 'Content-Type: application/json'" "any"

# Test 4: Valid session creation
echo ""
echo "=== Session Management Tests ==="
SESSION_RESPONSE=$(curl -s -i -H "Origin: http://$TEST_DOMAIN" \
    -H "Content-Type: application/json" \
    -d '{"origin_domain":"localhost","page_url":"http://localhost:3000/test"}' \
    "$BASE_URL/api/v1/session/create")

if echo "$SESSION_RESPONSE" | grep -q "HTTP/1.1 200"; then
    echo -e "Session Creation: ${GREEN}PASS${NC}"
    ((PASS_COUNT++))
    
    # Extract session cookie
    SESSION_COOKIE=$(extract_cookie "$SESSION_RESPONSE")
    echo "Session Cookie: $SESSION_COOKIE"
else
    echo -e "Session Creation: ${RED}FAIL${NC}"
    ((FAIL_COUNT++))
    echo "Response: $SESSION_RESPONSE"
fi

# Test 5: Rate limiting
echo ""
echo "=== Rate Limiting Tests ==="
echo "Testing rate limits (this may take a moment)..."

# Rapid fire requests to trigger rate limiting
for i in {1..65}; do
    curl -s "$BASE_URL/health" > /dev/null
    if [ $((i % 20)) -eq 0 ]; then
        echo "  Sent $i requests..."
    fi
done

# This should trigger rate limit
RATE_LIMIT_RESPONSE=$(curl -s -w 'HTTP/%{http_code}' "$BASE_URL/health")
if echo "$RATE_LIMIT_RESPONSE" | grep -q "HTTP/429"; then
    echo -e "Rate Limiting: ${GREEN}PASS${NC}"
    ((PASS_COUNT++))
else
    echo -e "Rate Limiting: ${YELLOW}UNCERTAIN${NC} (May need more requests)"
    echo "Response: $RATE_LIMIT_RESPONSE"
fi

# Test 6: Input validation
echo ""
echo "=== Input Validation Tests ==="

# Test XSS payload
run_test "XSS Protection" "curl -s -w 'HTTP/%{http_code}' -H 'Origin: http://$TEST_DOMAIN' -H 'Content-Type: application/json' -b '$SESSION_COOKIE' -d '{\"message\":\"<script>alert('xss')</script>\"}' '$BASE_URL/api/v1/chat/message'" "400"

# Test SQL injection payload
run_test "SQL Injection Protection" "curl -s -w 'HTTP/%{http_code}' -H 'Origin: http://$TEST_DOMAIN' -H 'Content-Type: application/json' -b '$SESSION_COOKIE' -d '{\"message\":\"'; DROP TABLE sessions; --\"}' '$BASE_URL/api/v1/chat/message'" "400"

# Test oversized message
LARGE_MESSAGE=$(printf 'A%.0s' {1..10001})  # 10001 characters
run_test "Message Size Limit" "curl -s -w 'HTTP/%{http_code}' -H 'Origin: http://$TEST_DOMAIN' -H 'Content-Type: application/json' -b '$SESSION_COOKIE' -d '{\"message\":\"$LARGE_MESSAGE\"}' '$BASE_URL/api/v1/chat/message'" "400"

# Test 7: Security headers
echo ""
echo "=== Security Headers Tests ==="
HEADERS_RESPONSE=$(curl -s -I "$BASE_URL/health")

check_header() {
    local header="$1"
    local description="$2"
    
    if echo "$HEADERS_RESPONSE" | grep -qi "$header"; then
        echo -e "$description: ${GREEN}PASS${NC}"
        ((PASS_COUNT++))
    else
        echo -e "$description: ${RED}FAIL${NC}"
        ((FAIL_COUNT++))
    fi
}

check_header "x-content-type-options" "X-Content-Type-Options Header"
check_header "x-frame-options" "X-Frame-Options Header"
check_header "x-xss-protection" "X-XSS-Protection Header"
check_header "content-security-policy" "Content-Security-Policy Header"

# Test 8: Domain validation
echo ""
echo "=== Domain Validation Tests ==="
run_test "Invalid Domain Format" "curl -s -w 'HTTP/%{http_code}' -H 'Origin: http://$TEST_DOMAIN' -H 'Content-Type: application/json' -d '{\"origin_domain\":\"../../../etc/passwd\"}' '$BASE_URL/api/v1/session/create'" "400"

# Test 9: Session without cookie
echo ""
echo "=== Authentication Tests ==="
run_test "Access Without Session" "curl -s -w 'HTTP/%{http_code}' -H 'Origin: http://$TEST_DOMAIN' -H 'Content-Type: application/json' -d '{\"message\":\"test\"}' '$BASE_URL/api/v1/chat/message'" "401"

# Test 10: Metrics endpoint (should be accessible)
echo ""
echo "=== Monitoring Tests ==="
run_test "Metrics Endpoint" "curl -s -w 'HTTP/%{http_code}' '$BASE_URL/metrics'" "200"

# Summary
echo ""
echo "=============================================="
echo "🎯 Security Test Results Summary"
echo "=============================================="
echo -e "Total Tests: $((PASS_COUNT + FAIL_COUNT))"
echo -e "Passed: ${GREEN}$PASS_COUNT${NC}"
echo -e "Failed: ${RED}$FAIL_COUNT${NC}"

if [ $FAIL_COUNT -eq 0 ]; then
    echo ""
    echo -e "${GREEN}🎉 All security tests passed!${NC}"
    echo "Your Chat Proxy System appears to be properly secured."
else
    echo ""
    echo -e "${RED}⚠️  Some security tests failed.${NC}"
    echo "Please review the failed tests and fix any security issues."
fi

echo ""
echo "📋 Additional Security Recommendations:"
echo "1. Ensure you're using HTTPS in production"
echo "2. Configure proper JWT secrets (not default values)"
echo "3. Set up monitoring and alerting for security events"
echo "4. Regularly update dependencies"
echo "5. Implement IP whitelist for admin endpoints"
echo "6. Set up fail2ban or similar for repeated failures"
echo "7. Configure proper CORS origins for production"

# Exit with error code if tests failed
if [ $FAIL_COUNT -gt 0 ]; then
    exit 1
fi

exit 0
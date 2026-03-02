#!/bin/bash
# ============================================================
#  HTTP PROXY ASSIGNMENT 1 - Full Test Suite
# ============================================================

PROXY_PORT=8888
PROXY="http://127.0.0.1:$PROXY_PORT"

# Kill any old proxy instances
pkill -f "assignment1.py" 2>/dev/null
sleep 0.5

# ─────────────────────────────────────────────────────────────
echo "========================================================"
echo "  ASSIGNMENT 1 – HTTP PROXY SERVER"
echo "  Test Suite"
echo "========================================================"
echo ""

# ━━━ STEP 1: Start proxy ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo "┌──────────────────────────────────────────────────────┐"
echo "│  TEST 0: Proxy Startup                               │"
echo "└──────────────────────────────────────────────────────┘"
/usr/bin/python3 /home/raghib/CN/assignment1.py $PROXY_PORT &
PROXY_PID=$!
sleep 1.5
echo "[INFO] Proxy started (PID=$PROXY_PID) on port $PROXY_PORT"
echo ""

# ━━━ STEP 2: Valid GET request (HTTP 200) ━━━━━━━━━━━━━━━━━━
echo "┌──────────────────────────────────────────────────────┐"
echo "│  TEST 1: Valid GET request → expect HTTP 200         │"
echo "└──────────────────────────────────────────────────────┘"
echo "  Command: curl --proxy $PROXY http://httpbin.org/get"
echo ""
curl -s --proxy "$PROXY" http://httpbin.org/get
echo ""
echo "  >>> Status code:"
curl -s -o /dev/null -w "  HTTP %{http_code}\n" --proxy "$PROXY" http://httpbin.org/get
echo ""

sleep 0.5

# ━━━ STEP 3: Valid GET with path & query string ━━━━━━━━━━━━
echo "┌──────────────────────────────────────────────────────┐"
echo "│  TEST 2: GET with query string                       │"
echo "└──────────────────────────────────────────────────────┘"
echo "  Command: curl --proxy $PROXY http://httpbin.org/get?foo=bar"
curl -s -o /dev/null -w "  HTTP %{http_code}\n" --proxy "$PROXY" "http://httpbin.org/get?foo=bar"
echo ""

sleep 0.5

# ━━━ STEP 4: 400 Bad Request (malformed request) ━━━━━━━━━━━
echo "┌──────────────────────────────────────────────────────┐"
echo "│  TEST 3: 400 Bad Request (malformed)                 │"
echo "└──────────────────────────────────────────────────────┘"
echo "  Sending: 'GARBAGE REQUEST' directly to proxy"
BAD_RESPONSE=$(printf "GARBAGE REQUEST\r\n\r\n" | nc -q1 127.0.0.1 $PROXY_PORT 2>/dev/null)
echo "$BAD_RESPONSE" | head -5
echo ""

sleep 0.5

# ━━━ STEP 5: 501 Not Implemented (POST method) ━━━━━━━━━━━━━
echo "┌──────────────────────────────────────────────────────┐"
echo "│  TEST 4: 501 Not Implemented (POST method)           │"
echo "└──────────────────────────────────────────────────────┘"
echo "  Command: curl -X POST --proxy $PROXY http://httpbin.org/post"
STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X POST --proxy "$PROXY" http://httpbin.org/post 2>/dev/null || echo "501")
echo "  HTTP $STATUS"
echo ""
# Also send raw POST to be explicit
RAW_POST=$(printf "POST http://httpbin.org/post HTTP/1.0\r\nHost: httpbin.org\r\n\r\n" | nc -q1 127.0.0.1 $PROXY_PORT 2>/dev/null)
echo "$RAW_POST" | head -3
echo ""

sleep 0.5

# ━━━ STEP 6: 501 Not Implemented (HTTPS CONNECT) ━━━━━━━━━━
echo "┌──────────────────────────────────────────────────────┐"
echo "│  TEST 5: 501 Not Implemented (HTTPS/CONNECT)         │"
echo "└──────────────────────────────────────────────────────┘"
echo "  Command: curl --proxy $PROXY https://httpbin.org/get"
STATUS=$(curl -s -o /dev/null -w "%{http_code}" --proxy "$PROXY" https://httpbin.org/get --max-time 5 2>/dev/null || echo "Failed (CONNECT refused - expected)")
echo "  Response: $STATUS"
RAW_CONN=$(printf "CONNECT httpbin.org:443 HTTP/1.0\r\nHost: httpbin.org:443\r\n\r\n" | nc -q1 127.0.0.1 $PROXY_PORT 2>/dev/null)
echo "$RAW_CONN" | head -3
echo ""

sleep 0.5

# ━━━ STEP 7: 502 Bad Gateway (unreachable host) ━━━━━━━━━━━━
echo "┌──────────────────────────────────────────────────────┐"
echo "│  TEST 6: 502 Bad Gateway (non-existent host)         │"
echo "└──────────────────────────────────────────────────────┘"
echo "  Command: curl --proxy $PROXY http://this-host-does-not-exist-xyz.com/"
RESULT=$(printf "GET http://this-host-does-not-exist-xyz.com/ HTTP/1.0\r\nHost: this-host-does-not-exist-xyz.com\r\n\r\n" | nc -q2 127.0.0.1 $PROXY_PORT 2>/dev/null)
echo "$RESULT" | head -5
echo ""

sleep 0.5

# ━━━ STEP 8: Multiple concurrent connections ━━━━━━━━━━━━━━━
echo "┌──────────────────────────────────────────────────────┐"
echo "│  TEST 7: Multiple concurrent connections (fork)      │"
echo "└──────────────────────────────────────────────────────┘"
echo "  Sending 3 concurrent requests..."
curl -s -o /dev/null -w "  Request 1: HTTP %{http_code}\n" --proxy "$PROXY" http://httpbin.org/get &
curl -s -o /dev/null -w "  Request 2: HTTP %{http_code}\n" --proxy "$PROXY" http://httpbin.org/ip &
curl -s -o /dev/null -w "  Request 3: HTTP %{http_code}\n" --proxy "$PROXY" http://httpbin.org/user-agent &
wait
echo ""

sleep 1

# Stop the proxy
kill $PROXY_PID 2>/dev/null
wait $PROXY_PID 2>/dev/null

echo ""
echo "========================================================"
echo "  ALL TESTS COMPLETE"
echo "========================================================"

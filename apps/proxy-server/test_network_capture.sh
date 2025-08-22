#!/bin/bash

echo "Network Packet Analysis for SSE Streaming"
echo "=========================================="
echo ""

# Test 1: Capture packets with tcpdump
echo "Test 1: Capturing SSE packets with tcpdump"
echo "-------------------------------------------"
echo "Starting packet capture on port 8002..."
echo ""

# Create a test script to capture timing
cat > /tmp/sse_timing_test.sh << 'EOF'
#!/bin/bash

echo "Starting SSE stream capture at $(date +%H:%M:%S.%3N)"
echo ""

# Use curl with timing info
curl -N -w "\n\nTransfer stats:\n" \
     -w "time_namelookup:  %{time_namelookup}s\n" \
     -w "time_connect:     %{time_connect}s\n" \
     -w "time_starttransfer: %{time_starttransfer}s\n" \
     -w "time_total:       %{time_total}s\n" \
     -w "size_download:    %{size_download} bytes\n" \
     -w "speed_download:   %{speed_download} bytes/sec\n" \
     http://localhost:8002/stream 2>&1 | while IFS= read -r line; do
    echo "[$(date +%H:%M:%S.%3N)] $line"
done
EOF

chmod +x /tmp/sse_timing_test.sh

echo "Running timing test..."
/tmp/sse_timing_test.sh | head -50

echo ""
echo "Test 2: Browser Buffering Analysis"
echo "-----------------------------------"
echo ""

# Create HTML test page with detailed logging
cat > /tmp/sse_buffer_test.html << 'EOF'
<!DOCTYPE html>
<html>
<head>
    <title>SSE Buffer Test</title>
</head>
<body>
    <h1>SSE Buffering Investigation</h1>
    
    <h2>Test 1: EventSource API</h2>
    <div id="eventsource-output" style="border: 1px solid #ccc; padding: 10px; min-height: 50px;"></div>
    
    <h2>Test 2: Fetch API with Reader</h2>
    <div id="fetch-output" style="border: 1px solid #ccc; padding: 10px; min-height: 50px;"></div>
    
    <h2>Timing Log</h2>
    <pre id="log" style="background: #f0f0f0; padding: 10px; height: 400px; overflow-y: auto;"></pre>
    
    <script>
        const log = document.getElementById('log');
        const eventSourceOutput = document.getElementById('eventsource-output');
        const fetchOutput = document.getElementById('fetch-output');
        
        function addLog(message) {
            const now = new Date();
            const timestamp = now.toTimeString().split(' ')[0] + '.' + now.getMilliseconds();
            log.textContent += `[${timestamp}] ${message}\n`;
        }
        
        // Test 1: EventSource
        addLog('Starting EventSource test...');
        const eventSource = new EventSource('http://localhost:8002/stream');
        let esStartTime = Date.now();
        let esChunkCount = 0;
        
        eventSource.onmessage = (event) => {
            esChunkCount++;
            const elapsed = Date.now() - esStartTime;
            eventSourceOutput.textContent += event.data;
            addLog(`EventSource chunk #${esChunkCount}: "${event.data}" at ${elapsed}ms`);
            
            if (event.data === '[DONE]') {
                eventSource.close();
                addLog(`EventSource complete: ${esChunkCount} chunks in ${elapsed}ms`);
                startFetchTest();
            }
        };
        
        // Test 2: Fetch with streaming
        function startFetchTest() {
            addLog('\nStarting Fetch API test...');
            let fetchStartTime = Date.now();
            let fetchChunkCount = 0;
            
            fetch('http://localhost:8002/stream')
                .then(response => {
                    const reader = response.body.getReader();
                    const decoder = new TextDecoder();
                    
                    function read() {
                        reader.read().then(({done, value}) => {
                            if (done) {
                                const elapsed = Date.now() - fetchStartTime;
                                addLog(`Fetch complete: ${fetchChunkCount} chunks in ${elapsed}ms`);
                                return;
                            }
                            
                            fetchChunkCount++;
                            const elapsed = Date.now() - fetchStartTime;
                            const text = decoder.decode(value, {stream: true});
                            
                            // Extract data from SSE format
                            const lines = text.split('\n');
                            for (const line of lines) {
                                if (line.startsWith('data: ')) {
                                    const data = line.substring(6);
                                    if (data) {
                                        fetchOutput.textContent += data;
                                        addLog(`Fetch chunk #${fetchChunkCount}: "${data}" at ${elapsed}ms (${value.byteLength} bytes)`);
                                    }
                                }
                            }
                            
                            read();
                        });
                    }
                    
                    read();
                });
        }
    </script>
</body>
</html>
EOF

echo "Test HTML page created at /tmp/sse_buffer_test.html"
echo ""
echo "Test 3: Python SSE Client (no browser)"
echo "---------------------------------------"

cat > /tmp/test_sse_client.py << 'EOF'
import requests
import time
from datetime import datetime

def test_sse_stream():
    print(f"[{datetime.now().isoformat()}] Starting SSE client test")
    
    start_time = time.time()
    chunk_count = 0
    
    response = requests.get('http://localhost:8002/stream', stream=True)
    
    for line in response.iter_lines():
        if line:
            chunk_count += 1
            elapsed = time.time() - start_time
            line_str = line.decode('utf-8')
            
            if line_str.startswith('data: '):
                data = line_str[6:]
                print(f"[{datetime.now().isoformat()}] Chunk #{chunk_count}: '{data}' at {elapsed:.3f}s")
                
                if data == '[DONE]':
                    break
    
    print(f"[{datetime.now().isoformat()}] Complete: {chunk_count} chunks in {elapsed:.3f}s")

if __name__ == "__main__":
    test_sse_stream()
EOF

echo "Running Python SSE client test..."
python3 /tmp/test_sse_client.py

echo ""
echo "=========================================="
echo "Analysis Complete"
echo ""
echo "Key Questions to Answer:"
echo "1. Does curl receive characters one by one? (Should be YES)"
echo "2. Does Python client receive characters one by one? (Check above)"
echo "3. Does browser EventSource buffer the chunks? (Open /tmp/sse_buffer_test.html)"
echo "4. Is there a difference between EventSource and Fetch?"
echo ""
echo "To open browser test: open /tmp/sse_buffer_test.html"
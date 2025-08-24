# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## IMPORTANT RULES

YOU ARE NOT ALLOWED TO DO SIMPLIFICATION OR COMPLICATION WITHOUT USER'S PERMISSION!!!
No 'more robust solutions' and such. YOU ALWAYS ASK BEFORE DOING THINGS ANOTHER WAY!

## Project Overview

This is a secure chat proxy system for e-commerce platforms, built with a standalone HTML frontend and FastAPI Python backend. The system acts as a secure intermediary between embedded chat widgets and n8n workflows for AI-powered customer support.

## Architecture

The project has two main components:

- **chat-widget** (`apps/chat-widget/`): Standalone HTML chat widget that embeds via iframe on websites
- **proxy-server** (`apps/proxy-server/`): FastAPI Python server that handles authentication, rate limiting, and n8n integration

### Deployment Modes

The proxy server supports two deployment modes:

1. **Stateless Mode** (`main_stateless.py`) - Recommended for most use cases:
   - Zero database dependencies
   - All session data stored browser-side (IndexedDB + localStorage)  
   - Ultra-fast performance with <10ms latency
   - Horizontally scalable with no shared state
   - In-memory rate limiting (resets on server restart)

2. **SQLite Mode** (`main_sqlite.py`) - Lightweight with analytics:
   - Single SQLite file for session metadata
   - Browser-first storage with server-side session tracking
   - Persistent rate limiting across restarts
   - Auto-cleanup of old data
   - Easy backup (single .db file)

### Common Components

All modes use:
- n8n workflows for AI processing
- JWT tokens with dual-key system (JWT_SECRET_KEY for internal, SESSION_SECRET_KEY for n8n)
- Server-sent events (SSE) for real-time chat streaming
- Browser fingerprinting for session validation

## Common Development Commands

### Project Setup
```bash
# Setup (creates environment files and virtual environment)
./scripts/setup.sh

# Manual setup
cd apps/proxy-server && pip install -r requirements-stateless.txt  # For stateless mode
cd apps/proxy-server && pip install -r requirements-sqlite.txt     # For SQLite mode
```

### Development
```bash
# Backend modes (choose one):
cd apps/proxy-server && python main_stateless.py    # Stateless mode (no dependencies)
cd apps/proxy-server && python main_sqlite.py       # SQLite mode (minimal dependencies)

# Widget is served automatically by the backend at /widget/modern-widget.html
```

### Production Server
```bash
# Production deployment options:
cd apps/proxy-server && pip install -r requirements-stateless.txt && python main_stateless.py  # Stateless (recommended)
cd apps/proxy-server && pip install -r requirements-sqlite.txt && python main_sqlite.py        # SQLite

# Production server (if exists):
cd apps/proxy-server && python main_production.py  # Check if this file exists
```

### Building and Testing
```bash
# Backend linting
cd apps/proxy-server && ruff check . && black --check .

# Security testing
./scripts/test-security.sh
```

## Key File Structure

### Frontend (Standalone HTML)
- `apps/chat-widget/modern-widget.html`: Complete standalone chat widget with SSE streaming
- `apps/chat-widget/public/embed.js`: JavaScript embed script for websites
- `apps/chat-widget/widget-config.json`: Widget configuration file

### Backend (FastAPI Python)

**Entry Points:**
- `apps/proxy-server/main_stateless.py`: Stateless server (no database dependencies)
- `apps/proxy-server/main_sqlite.py`: SQLite server (lightweight single-file database)
- `apps/proxy-server/main_production.py`: Production server entry point (if exists)

## Configuration

### Environment Files
- `apps/proxy-server/.env`: Backend configuration (create from .env.example)

### Key Environment Variables

**Common (All Modes):**
```bash
# n8n Integration
N8N_WEBHOOK_URL=https://your-n8n-instance.com/webhook/chat
N8N_API_KEY=<optional-api-key>

# Security
JWT_SECRET_KEY=<secure-secret>    # For internal session tokens
SESSION_SECRET_KEY=<secure-secret>  # For n8n validation tokens
ALLOWED_ORIGINS=https://yoursite.com,http://localhost:8000

# Server
API_HOST=0.0.0.0
API_PORT=8000
LOG_LEVEL=WARNING  # INFO for development, WARNING for production

# Rate Limiting  
RATE_LIMIT_PER_MINUTE=60
```

**SQLite Mode Additional:**
```bash
SQLITE_DB_PATH=chat_sessions.db  # Database file path
```


## Widget Integration

### Embed on website
```html
<script>
  (function() {
    var script = document.createElement('script');
    script.src = 'https://yourchatserver.com/widget/embed.js';
    script.async = true;
    document.head.appendChild(script);
  })();
</script>
```

### Direct iframe
```html
<iframe src="https://yourchatserver.com/widget/modern-widget.html" 
        width="400" height="600" style="border: none;">
</iframe>
```

## API Endpoints

### Core Endpoints
- `GET /health`: Detailed health status with service checks
- `GET /metrics`: System metrics and connection stats
- `POST /api/v1/session/create`: Create secure chat session
- `GET /api/v1/session/validate`: Validate existing session
- `POST /api/v1/chat/message`: Send message (SSE stream response)
- `GET /api/v1/chat/stream/{session_id}`: SSE endpoint for real-time updates
- `GET /widget/*`: Serve widget static files

## n8n Integration

The system integrates with n8n for AI processing:
- Configure webhook URL in n8n workflow
- Enable streaming response in webhook settings
- JWT tokens passed in request body as `jwt_token` field (not Authorization header)
- Supports SSE for real-time streaming responses

### JWT Token Format for n8n
All modes send JWT tokens with this payload structure to n8n:
```json
{
  "session_id": "sess_1234567890_abcd1234",
  "timestamp": "2024-01-01T12:00:00.000Z",
  "message_history": [],
  "session_metadata": {},
  "exp": 1704105630
}
```

## Security Features

- JWT-based authentication with browser fingerprinting
- Multi-tier rate limiting (IP, session, domain)
- Input sanitization and XSS protection
- Comprehensive security headers and CORS
- Bot and spam detection
- Circuit breaker pattern for external services
- Session validation and expiry
- Request signature validation

## Deployment Mode Selection

### When to Use Each Mode

- **Stateless Mode**: Recommended for most use cases
  - Zero maintenance, instant deployment
  - Scales infinitely, no database overhead
  - Perfect for startups and high-traffic sites
  - Users retain chat history in browser storage

- **SQLite Mode**: When you need basic server-side analytics  
  - Single file database, easy backup
  - Session tracking and usage analytics
  - Still lightweight with browser-first storage
  - Good middle ground option

## Development Tips

1. **Quick Testing**: Start with stateless mode (`python main_stateless.py`) - no setup required
2. **Testing Widget**: Visit `http://localhost:8000/widget/modern-widget.html`
3. **EventSource Compatibility**: All modes support both POST and GET endpoints for SSE streaming
4. **Logs**: Check server console output
5. **Rate Limits**: Can be tested with `./scripts/test-security.sh`

## Important Implementation Notes

- Widget embeds via iframe for security isolation
- All user inputs are sanitized for XSS/injection protection  
- JWT tokens use dual-key system: JWT_SECRET_KEY (internal) + SESSION_SECRET_KEY (n8n validation)
- n8n integration requires `jwt_token` field in request body (not Authorization header)
- EventSource/SSE streaming requires GET endpoints for browser compatibility
- Stateless mode: Rate limiting is in-memory (resets on server restart)
- SQLite mode: Uses aiosqlite for async database operations with persistent rate limiting
- SSE connections managed with heartbeat and cleanup

### Critical Architecture Patterns

- **Browser-First Storage**: Even SQLite mode prioritizes browser storage for chat history
- **Dual JWT System**: Internal tokens for session validation, short-lived tokens for n8n
- **Multi-Mode Compatibility**: All modes share the same JWT payload format for n8n
- **EventSource Support**: GET endpoints wrap POST logic for browser EventSource API

## TECHNICAL DEEP DIVE - SYSTEM INTERNALS

This section provides comprehensive technical details about how every component of the chat proxy system functions internally, including data flows, API mechanics, SSE operations, JSON parsing, session management, and frontend-backend communication patterns.

### System Architecture Flow

The chat system follows this complete data flow:
1. **Client Initialization**: Widget loads in iframe, establishes session with fingerprinting
2. **Session Creation**: JWT token created with dual-key system, stored in IndexedDB + localStorage
3. **Message Flow**: User message → Single SSE connection → n8n processing → Streaming response
4. **Background/Foreground Pattern**: Unified SSE connection handles both persistent storage and real-time UI updates

### API Operations Deep Dive

#### Session Creation API (`POST /api/v1/session/create`)

**Request Flow:**
```python
# Client sends browser fingerprint data
{
    "user_agent": "Mozilla/5.0...",
    "screen_resolution": "1920x1080", 
    "timezone": "America/New_York",
    "language": "en-US"
}
```

**Server Processing (`main_production.py`):**
```python
# Generate session ID with timestamp + random
session_id = f"sess_{int(time.time())}_{secrets.token_hex(8)}"

# Create internal JWT (long-lived, browser storage)
internal_payload = {
    "session_id": session_id,
    "fingerprint": browser_fingerprint_hash,
    "created_at": datetime.utcnow().isoformat(),
    "exp": datetime.utcnow() + timedelta(days=7)  # 7-day expiry
}
internal_token = jwt.encode(internal_payload, JWT_SECRET_KEY, algorithm="HS256")

# Create n8n JWT (short-lived, request-specific)  
n8n_payload = {
    "session_id": session_id,
    "timestamp": datetime.utcnow().isoformat(),
    "message_history": [],
    "session_metadata": fingerprint_data,
    "exp": datetime.utcnow() + timedelta(minutes=30)  # 30-min expiry
}
n8n_token = jwt.encode(n8n_payload, SESSION_SECRET_KEY, algorithm="HS256")
```

**Response Format:**
```json
{
    "session_id": "sess_1724505234_a1b2c3d4",
    "internal_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "n8n_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "expires_at": "2024-08-31T15:30:45.123Z",
    "fingerprint_hash": "sha256_hash_of_browser_data"
}
```

#### Chat Message API (`POST /api/v1/chat/message` and `GET /api/v1/chat/stream/{session_id}`)

**Critical Architecture Decision**: The system supports both POST and GET for SSE because:
- **POST**: Traditional API pattern, carries message data in request body
- **GET**: Required by browser `EventSource` API which only supports GET requests
- **Solution**: GET endpoint wraps POST logic, retrieves pending message from server-side storage

**POST Request Processing:**
```python
# Store message temporarily for GET SSE endpoint
pending_messages[session_id] = {
    "message": user_message,
    "timestamp": datetime.utcnow(),
    "jwt_token": refreshed_n8n_token
}

# Initiate n8n request with streaming
async def stream_n8n_response():
    n8n_payload = {
        "message": user_message,
        "jwt_token": n8n_jwt,  # NOT in Authorization header!
        "session_context": session_metadata
    }
    
    # Stream from n8n webhook
    async with httpx.AsyncClient() as client:
        async with client.stream("POST", n8n_url, json=n8n_payload) as response:
            async for line in response.aiter_lines():
                # Parse n8n streaming response
                yield process_n8n_line(line)
```

### Server-Sent Events (SSE) Deep Technical Mechanics

#### SSE Response Format Standards

**Correct SSE Protocol Implementation:**
```
data: {"type": "begin", "content": "", "message_id": "msg_123"}

data: {"type": "item", "content": "Hello", "message_id": "msg_123"}

data: {"type": "item", "content": " there!", "message_id": "msg_123"}  

data: {"type": "end", "content": "", "message_id": "msg_123"}

```

**Critical Fix Applied**: Originally, the server was sending raw content:
```
# BROKEN (was causing JSON.parse errors):
data: Hello there!

# FIXED (proper JSON structure):  
data: {"type": "item", "content": "Hello there!", "message_id": "msg_123"}
```

#### n8n Response Processing Algorithm

**Server-Side Processing (`main_production.py` lines 200-293):**
```python
async def process_n8n_streaming_response(n8n_response):
    buffer = ""
    
    async for line in n8n_response.aiter_lines():
        if line.startswith("data: "):
            raw_data = line[6:]  # Remove "data: " prefix
            
            try:
                # Parse n8n JSON response
                json_obj = json.loads(raw_data)
                
                # Validate required fields
                if json_obj.get("type") in ["begin", "item", "end", "error"]:
                    # Send complete JSON to client (CRITICAL FIX)
                    json_response = json.dumps(json_obj)
                    sse_data = f"data: {json_response}\n\n"
                    yield sse_data.encode("utf-8")
                    
            except json.JSONDecodeError:
                # Handle non-JSON responses from n8n
                if raw_data.strip() and not raw_data.startswith("{"):
                    # Wrap plain text in JSON structure
                    plain_text_json = {"type": "item", "content": raw_data.strip()}
                    json_response = json.dumps(plain_text_json)
                    sse_data = f"data: {json_response}\n\n"
                    yield sse_data.encode("utf-8")
                    
        elif line == "":
            # Empty line indicates end of SSE event
            continue
            
    # Handle any remaining buffer content
    if buffer.strip():
        plain_text_json = {"type": "item", "content": buffer.strip()}
        json_response = json.dumps(plain_text_json)
        sse_data = f"data: {json_response}\n\n"
        yield sse_data.encode("utf-8")
```

### JSON Parsing Client-Side Implementation  

#### EventSource Handler (`modern-widget.html` lines 2714-2740)

**Complete Client-Side JSON Processing:**
```javascript
// SSE Event Handler - processes each server message
eventSource.onmessage = function(event) {
    const data = event.data;
    
    if (data.trim() !== '') {
        try {
            // Parse the complete JSON structure from server
            const parsed = JSON.parse(data);
            console.log('✅ Complete JSON parsed:', parsed.type, 
                       parsed.content ? `"${parsed.content}"` : '(no content)');
            
            // Debug error objects in detail
            if (parsed.error) {
                console.log('🚨 ERROR OBJECT:', JSON.stringify(parsed, null, 2));
            }
            
            // Process based on message type
            switch(parsed.type) {
                case 'begin':
                    // Initialize streaming response UI
                    startStreamingResponse(parsed.message_id);
                    break;
                    
                case 'item':
                    // Append content to streaming display
                    appendToStreamingResponse(parsed.content, parsed.message_id);
                    // Also store in background for persistence
                    this.backgroundResponseManager.appendContent(parsed.content);
                    break;
                    
                case 'end':
                    // Finalize streaming response
                    finalizeStreamingResponse(parsed.message_id);
                    // Save complete response to IndexedDB
                    this.backgroundResponseManager.finalizeResponse();
                    break;
                    
                case 'error':
                    // Handle error responses
                    displayErrorMessage(parsed.content);
                    break;
                    
                default:
                    console.warn('Unknown message type:', parsed.type);
            }
            
        } catch (parseError) {
            // This should now be rare due to server-side JSON wrapping
            console.error('❌ JSON Parse Error:', parseError);
            console.error('Raw data:', data);
            // Fallback: display raw content
            appendToStreamingResponse(data, 'unknown');
        }
    }
};
```

### Session Management Deep Dive

#### Dual Storage Strategy

**Browser-Side Storage (`modern-widget.html`):**
```javascript
class SessionManager {
    constructor() {
        this.sessionData = {
            sessionId: null,
            internalToken: null,
            n8nToken: null,
            fingerprint: null,
            expiresAt: null
        };
    }
    
    // Primary storage: IndexedDB (persistent, large capacity)
    async saveToIndexedDB(sessionData) {
        const db = await this.openIndexedDB();
        const transaction = db.transaction(['sessions'], 'readwrite');
        const store = transaction.objectStore('sessions');
        await store.put(sessionData, 'current_session');
    }
    
    // Backup storage: localStorage (sync, smaller capacity)  
    saveToLocalStorage(sessionData) {
        const serialized = JSON.stringify({
            sessionId: sessionData.sessionId,
            internalToken: sessionData.internalToken,
            expiresAt: sessionData.expiresAt,
            fingerprint: sessionData.fingerprint
        });
        localStorage.setItem('chat_session_backup', serialized);
    }
    
    // Load with fallback chain: IndexedDB → localStorage → create new
    async loadSession() {
        try {
            // Try IndexedDB first (most reliable)
            const indexedDBData = await this.loadFromIndexedDB();
            if (indexedDBData && !this.isExpired(indexedDBData)) {
                return indexedDBData;
            }
        } catch (error) {
            console.warn('IndexedDB failed, trying localStorage');
        }
        
        try {
            // Fallback to localStorage
            const localData = JSON.parse(localStorage.getItem('chat_session_backup'));
            if (localData && !this.isExpired(localData)) {
                return localData;
            }
        } catch (error) {
            console.warn('localStorage failed, creating new session');
        }
        
        // Last resort: create new session
        return await this.createNewSession();
    }
}
```

#### Session Validation Process

**Server-Side Validation (`main_production.py`):**
```python
def validate_session_token(internal_token, session_id, fingerprint_data):
    try:
        # Decode internal JWT
        payload = jwt.decode(internal_token, JWT_SECRET_KEY, algorithms=["HS256"])
        
        # Validate session ID matches
        if payload.get("session_id") != session_id:
            raise InvalidSessionError("Session ID mismatch")
            
        # Validate fingerprint hasn't changed dramatically
        stored_fingerprint = payload.get("fingerprint")
        current_fingerprint = generate_fingerprint_hash(fingerprint_data)
        
        if not verify_fingerprint_similarity(stored_fingerprint, current_fingerprint):
            raise InvalidSessionError("Fingerprint mismatch - possible session hijacking")
            
        # Check expiration
        exp_timestamp = payload.get("exp", 0)
        if datetime.utcnow().timestamp() > exp_timestamp:
            raise InvalidSessionError("Session expired")
            
        return True, payload
        
    except jwt.ExpiredSignatureError:
        raise InvalidSessionError("Token expired")
    except jwt.InvalidTokenError:
        raise InvalidSessionError("Invalid token")
```

### Frontend-Backend Communication Patterns

#### Message Sending Architecture

**Critical Pattern: Single Request, Dual Purpose**

**Previous Issue (Duplicate Requests):**
```javascript
// BROKEN - Was causing 2 n8n calls per message:
async sendMessage(message) {
    // Request #1: Background collection  
    this.backgroundResponseManager.startBackgroundCollection(sessionId, message, apiBase);
    
    // Request #2: Foreground display (DUPLICATE!)
    const eventSource = new EventSource(`/api/v1/chat/stream/${sessionId}?message=${message}`);
    // ... handle display
}
```

**Fixed Implementation (Single Request):**
```javascript  
// FIXED - Single request serves both purposes:
async sendMessage(message) {
    console.log('🔗 Starting single SSE connection for both foreground and background...');
    
    // Start background collection (creates single EventSource)
    const backgroundConnection = await this.backgroundResponseManager.startBackgroundCollection(
        this.sessionId, 
        message, 
        this.API_BASE
    );
    
    // Reuse the same EventSource for foreground display
    const eventSource = backgroundConnection.eventSource;
    console.log('✅ Using background EventSource for foreground display (no duplicate requests)');
    
    // Set up foreground event handlers on shared EventSource
    let streamedText = '';
    
    eventSource.onmessage = (event) => {
        // Same EventSource handles both background storage AND real-time display
        const parsed = JSON.parse(event.data);
        
        if (parsed.type === 'item') {
            streamedText += parsed.content;
            this.updateStreamingDisplay(streamedText);  // Real-time UI
            // Background manager automatically stores via its own handlers
        }
    };
}
```

#### Background Response Manager Deep Dive

**Persistent Data Collection (`modern-widget.html` BackgroundResponseManager class):**
```javascript
class BackgroundResponseManager {
    constructor() {
        this.activeConnections = new Map();
        this.responseStorage = new Map();
    }
    
    async startBackgroundCollection(sessionId, message, apiBase) {
        // Create single EventSource connection
        const sseUrl = `${apiBase}/api/v1/chat/stream/${sessionId}?message=${encodeURIComponent(message)}`;
        const eventSource = new EventSource(sseUrl);
        
        const connectionInfo = {
            eventSource: eventSource,
            startTime: Date.now(),
            sessionId: sessionId,
            message: message,
            collectedResponse: '',
            status: 'active'
        };
        
        // Store connection for management
        this.activeConnections.set(sessionId, connectionInfo);
        
        // Set up background data collection handlers
        eventSource.onmessage = (event) => {
            try {
                const parsed = JSON.parse(event.data);
                this.handleBackgroundMessage(sessionId, parsed);
            } catch (error) {
                console.error('Background JSON parse error:', error);
            }
        };
        
        eventSource.onerror = (error) => {
            console.error('Background SSE error:', error);
            this.cleanup(sessionId);
        };
        
        eventSource.addEventListener('close', () => {
            this.finalizeCollection(sessionId);
        });
        
        // CRITICAL: Return complete connection info (including EventSource)
        return connectionInfo;  // This allows foreground reuse
    }
    
    handleBackgroundMessage(sessionId, parsed) {
        const connection = this.activeConnections.get(sessionId);
        if (!connection) return;
        
        switch(parsed.type) {
            case 'begin':
                connection.messageId = parsed.message_id;
                connection.collectedResponse = '';
                break;
                
            case 'item':
                connection.collectedResponse += parsed.content;
                // Store incremental progress in IndexedDB
                this.saveIncrementalResponse(sessionId, connection.collectedResponse);
                break;
                
            case 'end':
                // Finalize complete response in persistent storage
                this.saveCompleteResponse(sessionId, connection);
                this.cleanup(sessionId);
                break;
                
            case 'error':
                connection.error = parsed.content;
                this.saveErrorResponse(sessionId, connection);
                break;
        }
    }
    
    async saveCompleteResponse(sessionId, connection) {
        const responseData = {
            sessionId: sessionId,
            messageId: connection.messageId,
            userMessage: connection.message,
            aiResponse: connection.collectedResponse,
            timestamp: new Date().toISOString(),
            duration: Date.now() - connection.startTime
        };
        
        // Save to IndexedDB for persistence
        await this.saveToIndexedDB('chat_history', responseData);
        
        // Update conversation list in localStorage
        this.updateConversationsList(sessionId, responseData);
    }
}
```

### Event Handling System Architecture

#### Client-Side Event Flow

**Complete Event Lifecycle:**
1. **User Input Event** → `sendMessage()` triggered
2. **Message Validation** → XSS sanitization, length checks
3. **Session Validation** → Check JWT expiry, refresh if needed
4. **Single SSE Initiation** → Background manager creates EventSource
5. **Dual Event Handling** → Same EventSource serves background + foreground
6. **Response Processing** → JSON parsing, type-based routing
7. **UI Updates** → Real-time streaming display
8. **Data Persistence** → IndexedDB storage, conversation history
9. **Cleanup** → EventSource closure, memory management

**Event Handler Registration Pattern:**
```javascript
// Unified event handling on single EventSource
const setupEventHandlers = (eventSource, sessionId) => {
    // Message events (streaming content)
    eventSource.onmessage = (event) => {
        const parsed = JSON.parse(event.data);
        
        // Route to both background and foreground handlers
        this.backgroundResponseManager.handleBackgroundMessage(sessionId, parsed);
        this.handleForegroundDisplay(parsed);
    };
    
    // Error handling
    eventSource.onerror = (error) => {
        console.error('SSE Connection Error:', error);
        this.displayErrorMessage('Connection lost. Retrying...');
        
        // Auto-retry logic
        setTimeout(() => {
            this.retryConnection(sessionId);
        }, 3000);
    };
    
    // Connection state management
    eventSource.onopen = () => {
        console.log('✅ SSE connection established');
        this.updateConnectionStatus('connected');
    };
    
    // Custom event types from server
    eventSource.addEventListener('heartbeat', (event) => {
        console.log('💓 Heartbeat received:', event.data);
        this.lastHeartbeat = Date.now();
    });
    
    eventSource.addEventListener('session_warning', (event) => {
        console.warn('⚠️ Session warning:', event.data);
        this.handleSessionWarning(JSON.parse(event.data));
    });
};
```

### Error Handling and Recovery Patterns

#### Client-Side Error Recovery

**Comprehensive Error Handling Strategy:**
```javascript
class ErrorRecoveryManager {
    constructor(chatWidget) {
        this.chatWidget = chatWidget;
        this.retryAttempts = 0;
        this.maxRetries = 3;
        this.retryDelay = 2000; // Start with 2 seconds
    }
    
    async handleConnectionError(error, sessionId) {
        console.error('Connection error occurred:', error);
        
        // Determine error type and appropriate response
        if (error.target && error.target.readyState === EventSource.CLOSED) {
            return this.handleConnectionClosed(sessionId);
        }
        
        if (error.message && error.message.includes('session')) {
            return this.handleSessionError(sessionId);
        }
        
        return this.handleGenericError(sessionId);
    }
    
    async handleSessionError(sessionId) {
        console.log('🔄 Session error detected, attempting session refresh...');
        
        try {
            // Attempt session refresh
            const newSession = await this.chatWidget.sessionManager.refreshSession();
            
            if (newSession.sessionId) {
                console.log('✅ Session refreshed successfully');
                return newSession;
            }
        } catch (refreshError) {
            console.error('Session refresh failed:', refreshError);
            
            // Create completely new session
            return await this.createNewSession();
        }
    }
    
    async handleConnectionClosed(sessionId) {
        if (this.retryAttempts >= this.maxRetries) {
            this.displayFatalError('Unable to maintain connection after multiple attempts');
            return null;
        }
        
        this.retryAttempts++;
        const delay = this.retryDelay * Math.pow(2, this.retryAttempts - 1); // Exponential backoff
        
        console.log(`🔄 Attempting reconnection ${this.retryAttempts}/${this.maxRetries} in ${delay}ms`);
        
        await this.sleep(delay);
        return this.attemptReconnection(sessionId);
    }
}
```

#### Server-Side Error Patterns

**n8n Integration Error Handling:**
```python
async def handle_n8n_communication(session_id, message, n8n_token):
    try:
        # Primary n8n request with timeout
        async with httpx.AsyncClient(timeout=30.0) as client:
            n8n_payload = {
                "message": message,
                "jwt_token": n8n_token,
                "session_id": session_id
            }
            
            async with client.stream("POST", n8n_webhook_url, json=n8n_payload) as response:
                if response.status_code != 200:
                    raise n8nError(f"n8n returned status {response.status_code}")
                
                async for line in response.aiter_lines():
                    yield process_n8n_line(line)
                    
    except httpx.TimeoutException:
        logger.error(f"n8n timeout for session {session_id}")
        error_response = {"type": "error", "content": "AI service timeout - please try again"}
        yield f"data: {json.dumps(error_response)}\n\n"
        
    except httpx.ConnectError:
        logger.error(f"n8n connection failed for session {session_id}")
        error_response = {"type": "error", "content": "AI service unavailable - please try again later"}  
        yield f"data: {json.dumps(error_response)}\n\n"
        
    except Exception as e:
        logger.error(f"Unexpected n8n error for session {session_id}: {e}")
        fallback_response = {"type": "error", "content": "An unexpected error occurred. Please refresh and try again."}
        yield f"data: {json.dumps(fallback_response)}\n\n"
```

### Performance Optimization Patterns

#### Connection Pooling and Resource Management

**Server-Side Connection Management:**
```python
class SSEConnectionManager:
    def __init__(self):
        self.active_connections = {}
        self.connection_stats = defaultdict(int)
        self.cleanup_task = None
    
    def register_connection(self, session_id, connection_info):
        self.active_connections[session_id] = {
            'start_time': time.time(),
            'last_activity': time.time(),
            'bytes_sent': 0,
            'message_count': 0,
            **connection_info
        }
        self.connection_stats['total_connections'] += 1
    
    def update_activity(self, session_id, bytes_sent=0):
        if session_id in self.active_connections:
            conn = self.active_connections[session_id]
            conn['last_activity'] = time.time()
            conn['bytes_sent'] += bytes_sent
            conn['message_count'] += 1
    
    def cleanup_stale_connections(self):
        current_time = time.time()
        stale_threshold = 300  # 5 minutes
        
        stale_sessions = [
            session_id for session_id, conn in self.active_connections.items()
            if current_time - conn['last_activity'] > stale_threshold
        ]
        
        for session_id in stale_sessions:
            logger.info(f"Cleaning up stale connection: {session_id}")
            del self.active_connections[session_id]
            self.connection_stats['cleaned_up'] += 1
```

This comprehensive technical documentation now covers all aspects of how the chat proxy system functions internally, from API mechanics to error handling patterns. Any future AI instance working with this codebase will have complete understanding of the system architecture and implementation details.

### Rules from user
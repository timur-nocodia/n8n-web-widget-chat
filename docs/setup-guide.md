# n8n Integration Setup Guide

## Overview

This guide explains how to set up the n8n workflow to work with the Chat Proxy System for AI-powered chat functionality.

## Prerequisites

- n8n instance (cloud or self-hosted)
- OpenAI API account and API key
- Chat Proxy System deployed and running
- JWT secret key shared between proxy and n8n

## Step 1: Environment Setup

### Set Environment Variables in n8n

Add these environment variables to your n8n instance:

```bash
# JWT Secret (must match proxy server)
JWT_SECRET_KEY=your-jwt-secret-key-here

# OpenAI Configuration
OPENAI_API_KEY=your-openai-api-key-here

# Optional: Custom system prompts
DEFAULT_SYSTEM_PROMPT="You are a helpful AI assistant"
```

### For Docker/Docker Compose:

```yaml
environment:
  - JWT_SECRET_KEY=${JWT_SECRET_KEY}
  - OPENAI_API_KEY=${OPENAI_API_KEY}
```

## Step 2: Import Workflow

1. **Import the Workflow**
   - Open your n8n interface
   - Go to **Workflows** → **Import from file**
   - Upload `chat-workflow.json`
   - Or copy/paste the JSON content

2. **Configure Credentials**
   - Go to **Settings** → **Credentials**
   - Add **OpenAI** credential with your API key
   - Name it `OpenAI API` to match the workflow

## Step 3: Configure Webhook

1. **Activate Webhook**
   - Open the imported workflow
   - Click on the **Chat Webhook** node
   - Copy the webhook URL (e.g., `https://your-n8n-instance.com/webhook/chat`)
   - The webhook path is set to `chat` by default

2. **Update Proxy Configuration**
   - Edit your proxy server `.env` file:
   ```bash
   N8N_WEBHOOK_URL=https://your-n8n-instance.com/webhook/chat
   N8N_API_KEY=your-n8n-api-key  # Optional for additional security
   ```

## Step 4: Test Integration

### Test with curl

```bash
curl -X POST "https://your-n8n-instance.com/webhook/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hello, how can you help me?",
    "session_id": "test-session-123",
    "jwt_token": "your-jwt-token-here",
    "context": {
      "page_url": "https://example.com/product/123",
      "user_context": {"page": "product"}
    }
  }'
```

### Test through Proxy

```bash
# First create a session
curl -X POST "http://localhost:8000/api/v1/session/create" \
  -H "Content-Type: application/json" \
  -H "Origin: http://localhost:3000" \
  -d '{
    "origin_domain": "localhost",
    "page_url": "http://localhost:3000/test"
  }' \
  -c cookies.txt

# Send a chat message
curl -X POST "http://localhost:8000/api/v1/chat/message" \
  -H "Content-Type: application/json" \
  -H "Origin: http://localhost:3000" \
  -d '{
    "message": "Hello, how can you help me?",
    "context": {"page": "test"}
  }' \
  -b cookies.txt
```

## Step 5: Workflow Customization

### AI Model Configuration

Edit the **OpenAI Chat** node to customize:

```javascript
// In the "Prepare AI Context" function node
const systemMessage = {
  role: 'system',
  content: `You are a helpful AI assistant for ${input.origin_domain}. 
           Current session: ${input.session_id}.
           
           # Context Guidelines:
           - Be helpful and professional
           - Focus on ${input.origin_domain} related queries
           - Use context: ${JSON.stringify(input.user_context)}
           
           # Response Guidelines:
           - Keep responses concise but informative
           - Ask clarifying questions when needed
           - Provide actionable advice when possible`
};
```

### Custom Response Processing

Modify the **Process AI Response** function to add custom formatting:

```javascript
// Add custom formatting
if (response.delta && response.delta.content) {
  let content = response.delta.content;
  
  // Add custom formatting
  content = content.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  content = content.replace(/\*(.*?)\*/g, '<em>$1</em>');
  
  return [{
    json: {
      event: 'message',
      data: JSON.stringify({
        content: content,
        formatted: true,
        session_id: sessionId,
        timestamp: new Date().toISOString()
      })
    }
  }];
}
```

### Error Handling

Add error handling nodes:

1. **Error Handler Node**
   ```javascript
   // In a Function node connected to error outputs
   const error = $input.first().json;
   
   return [{
     json: {
       event: 'error',
       data: JSON.stringify({
         error: 'AI service temporarily unavailable',
         code: 'AI_ERROR',
         retry_after: 30
       })
     }
   }];
   ```

## Step 6: Advanced Configuration

### Rate Limiting in n8n

Add rate limiting nodes before AI processing:

```javascript
// Rate limiting function
const sessionId = $json.session_id;
const rateLimitKey = `rate_limit:n8n:${sessionId}`;

// Check Redis for rate limits (if available)
// This would require a Redis node or HTTP request to proxy
```

### Content Filtering

Add content filtering before AI processing:

```javascript
// Content filtering function
const message = $json.message;
const blockedWords = ['spam', 'inappropriate', 'harmful'];

const hasBlockedContent = blockedWords.some(word => 
  message.toLowerCase().includes(word)
);

if (hasBlockedContent) {
  return [{
    json: {
      filtered: true,
      error: 'Message contains inappropriate content'
    }
  }];
}

return [{ json: { filtered: false, message: message } }];
```

### Logging and Analytics

Add logging nodes for analytics:

```javascript
// Analytics logging function
const logData = {
  timestamp: new Date().toISOString(),
  session_id: $json.session_id,
  origin_domain: $json.origin_domain,
  message_length: $json.message.length,
  processing_time: Date.now() - startTime,
  model_used: 'gpt-3.5-turbo',
  tokens_used: $json.usage?.total_tokens || 0
};

// Send to analytics service
// HTTP Request node to analytics endpoint
```

## Step 7: Production Deployment

### Security Considerations

1. **JWT Validation**
   - Ensure JWT secret is secure and not exposed
   - Validate token expiration and claims
   - Log authentication failures

2. **Rate Limiting**
   - Implement per-session rate limits
   - Add IP-based rate limiting if needed
   - Monitor for abuse patterns

3. **Content Security**
   - Sanitize user inputs
   - Implement content filtering
   - Log potentially harmful requests

### Monitoring

1. **Health Checks**
   - Add health check endpoints
   - Monitor AI service availability
   - Track response times

2. **Alerting**
   - Set up alerts for errors
   - Monitor rate limit violations
   - Track unusual usage patterns

### Scaling

1. **Multiple Workflows**
   - Create separate workflows for different domains
   - Load balance between multiple n8n instances
   - Use queue-based processing for high load

2. **Caching**
   - Cache frequent responses
   - Implement conversation context caching
   - Use Redis for session storage

## Troubleshooting

### Common Issues

1. **JWT Validation Fails**
   - Check JWT secret matches between proxy and n8n
   - Verify token is being passed correctly
   - Check token expiration

2. **AI Responses Not Streaming**
   - Ensure streaming is enabled in OpenAI node
   - Check response processing logic
   - Verify webhook response format

3. **Rate Limits Exceeded**
   - Check OpenAI API limits
   - Verify proxy rate limiting configuration
   - Monitor usage patterns

### Debug Mode

Enable debug logging in the workflow:

```javascript
// Add debug logging to function nodes
console.log('DEBUG:', {
  step: 'jwt_validation',
  token: token ? 'present' : 'missing',
  payload: decoded
});
```

## Support

For issues with:
- **Proxy Integration**: Check proxy server logs
- **n8n Workflow**: Enable debug mode and check execution logs
- **AI Responses**: Verify OpenAI API key and limits
- **Authentication**: Validate JWT configuration

## Next Steps

1. Test the complete integration
2. Configure monitoring and alerting
3. Implement custom business logic
4. Scale based on usage patterns
5. Add advanced features like conversation memory
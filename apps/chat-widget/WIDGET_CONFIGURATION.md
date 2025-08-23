# Chat Widget Configuration Guide

The chat widget is fully customizable through a JSON configuration file. This allows you to modify appearance, text content, behavior, and integration settings without changing any code.

## Quick Start

1. Copy `widget-config.example.json` to `widget-config.json`
2. Customize the settings according to your needs
3. Host the configuration file alongside your widget

## Configuration Loading Methods

### Method 1: Default Location
Place `widget-config.json` in the same directory as your widget files.

### Method 2: Custom URL via Script Attribute
```html
<script src="widget.js" data-config="https://your-domain.com/custom-config.json"></script>
```

### Method 3: Global Variable
```html
<script>
  window.CHAT_WIDGET_CONFIG_URL = 'https://your-domain.com/custom-config.json';
</script>
<script src="widget.js"></script>
```

### Method 4: Meta Tag
```html
<meta name="chat-widget-config" content="https://your-domain.com/custom-config.json">
<script src="widget.js"></script>
```

## Configuration Structure

### API Settings
```json
{
  "api": {
    "baseUrl": "https://your-api-server.com",
    "endpoints": {
      "session": "/api/v1/session/create",
      "chat": "/api/v1/chat/stream"
    }
  }
}
```

### Appearance Customization

#### Theme Colors
```json
{
  "appearance": {
    "theme": {
      "primaryColor": "#667eea",
      "secondaryColor": "#764ba2",
      "primaryGradient": "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
      "bgDark": "rgba(30, 30, 46, 0.95)",
      "textLight": "#ffffff",
      "borderRadius": "16px"
    }
  }
}
```

#### Dimensions
```json
{
  "appearance": {
    "dimensions": {
      "width": "380px",
      "height": "600px",
      "buttonSize": "60px",
      "bottomOffset": "20px",
      "rightOffset": "20px"
    }
  }
}
```

### Text Content

#### Header Text
```json
{
  "texts": {
    "header": {
      "title": "Customer Support",
      "subtitle": "We're here to help"
    }
  }
}
```

#### Messages
```json
{
  "texts": {
    "messages": {
      "welcomeMessage": "👋 Welcome! How can I assist you?",
      "errorMessage": "Connection error. Please try again.",
      "typingIndicator": "Agent is typing..."
    }
  }
}
```

#### Quick Reply Suggestions
```json
{
  "texts": {
    "suggestions": [
      {
        "text": "Get Help",
        "value": "I need help with my order"
      },
      {
        "text": "Track Order",
        "value": "Where is my order?"
      }
    ]
  }
}
```

### Behavior Settings

```json
{
  "behavior": {
    "autoOpen": false,
    "autoOpenDelay": 3000,
    "enableSuggestions": true,
    "enableTypingIndicator": true,
    "enableMarkdown": true,
    "maxMessageLength": 10000
  }
}
```

### Localization

```json
{
  "localization": {
    "locale": "en",
    "rtl": false
  }
}
```

## Common Customization Examples

### Example 1: E-commerce Support Widget
```json
{
  "texts": {
    "header": {
      "title": "Shop Support",
      "subtitle": "Available 24/7"
    },
    "messages": {
      "welcomeMessage": "👋 Need help with your order?"
    },
    "suggestions": [
      { "text": "Track Order", "value": "I want to track my order" },
      { "text": "Returns", "value": "How do I return an item?" },
      { "text": "Shipping", "value": "What are the shipping options?" }
    ]
  },
  "appearance": {
    "theme": {
      "primaryColor": "#28a745",
      "primaryGradient": "linear-gradient(135deg, #28a745 0%, #20c997 100%)"
    }
  }
}
```

### Example 2: Tech Support Widget
```json
{
  "texts": {
    "header": {
      "title": "Tech Support",
      "subtitle": "Expert help available"
    },
    "messages": {
      "welcomeMessage": "🔧 Having technical issues? I'm here to help!"
    },
    "suggestions": [
      { "text": "Report Bug", "value": "I found a bug" },
      { "text": "Feature Request", "value": "I have a feature request" },
      { "text": "Documentation", "value": "Where can I find documentation?" }
    ]
  },
  "appearance": {
    "theme": {
      "primaryColor": "#0066cc",
      "bgDark": "rgba(0, 33, 66, 0.95)"
    }
  }
}
```

### Example 3: Minimal Design
```json
{
  "appearance": {
    "theme": {
      "primaryColor": "#000000",
      "primaryGradient": "linear-gradient(135deg, #000000 0%, #333333 100%)",
      "borderRadius": "4px"
    },
    "dimensions": {
      "buttonSize": "48px"
    }
  },
  "texts": {
    "button": {
      "openIcon": "?",
      "closeIcon": "×"
    }
  }
}
```

## Advanced Features

### Custom Headers for API Requests
```json
{
  "integrations": {
    "customHeaders": {
      "X-API-Key": "your-api-key",
      "X-Client-Version": "1.0.0"
    }
  }
}
```

### Analytics Integration
```json
{
  "integrations": {
    "analytics": {
      "enabled": true,
      "provider": "google",
      "trackingId": "GA-XXXXXX"
    }
  }
}
```

### Accessibility Options
```json
{
  "accessibility": {
    "enableKeyboardShortcuts": true,
    "announceMessages": true,
    "highContrast": false,
    "focusOutline": true
  }
}
```

## Mobile-Specific Settings
```json
{
  "mobile": {
    "enabled": true,
    "fullscreen": true,
    "breakpoint": 480
  },
  "appearance": {
    "dimensions": {
      "mobileWidth": "100vw",
      "mobileHeight": "100vh"
    }
  }
}
```

## Testing Your Configuration

1. **Local Testing**: Use a local server to test your configuration
   ```bash
   python -m http.server 8000
   # or
   npx serve .
   ```

2. **Validation**: Ensure your JSON is valid using a JSON validator

3. **Browser Console**: Check the browser console for configuration loading messages:
   - ✅ Widget configuration loaded
   - ⚠️ Configuration load failed, using defaults

## Troubleshooting

### Configuration Not Loading
- Check the browser console for errors
- Verify the configuration URL is accessible
- Ensure JSON syntax is valid
- Check CORS headers if loading from a different domain

### Styles Not Applying
- Clear browser cache
- Verify CSS variable names match expected format
- Check for conflicting styles from the host page

### Text Not Updating
- Ensure the configuration is loaded before widget initialization
- Verify the text path in configuration matches the expected structure

## Best Practices

1. **Version Control**: Keep your configuration in version control
2. **Environment-Specific Configs**: Use different configs for dev/staging/production
3. **Fallback Values**: Always test with missing configuration to ensure defaults work
4. **Documentation**: Document any custom settings for your team
5. **Validation**: Validate configuration changes before deployment

## Support

For issues or questions about configuration, please refer to the main project documentation or create an issue in the repository.
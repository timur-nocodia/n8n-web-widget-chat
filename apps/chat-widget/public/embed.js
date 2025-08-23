/*
 * Chat Widget Embed Script
 * Usage: <script src="https://your-domain.com/embed.js"></script>
 */

(function() {
  'use strict';
  
  // Default configuration
  const defaultConfig = {
    apiBaseUrl: 'http://localhost:8000',
    theme: 'light',
    position: 'bottom-right',
    title: 'Chat Assistant',
    placeholder: 'Type your message...',
    welcomeMessage: 'Hello! How can I help you today?'
  };

  // Get config from data attributes or global variable
  function getConfig() {
    const script = document.currentScript || document.querySelector('script[src*="embed.js"]');
    const config = {};
    
    if (script) {
      // Read data attributes
      const dataset = script.dataset;
      Object.keys(dataset).forEach(key => {
        const value = dataset[key];
        // Convert string booleans and numbers
        if (value === 'true') config[key] = true;
        else if (value === 'false') config[key] = false;
        else if (!isNaN(value) && value !== '') config[key] = Number(value);
        else config[key] = value;
      });
    }
    
    // Merge with global config if available
    const globalConfig = window.ChatWidgetConfig || {};
    
    return Object.assign({}, defaultConfig, globalConfig, config);
  }

  // Initialize widget
  function initWidget() {
    const config = getConfig();
    
    // Create container
    const container = document.createElement('div');
    container.id = 'chat-widget-root';
    container.style.cssText = `
      position: fixed;
      z-index: 10000;
      pointer-events: none;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
    `;

    // Create iframe
    const iframe = document.createElement('iframe');
    const widgetUrl = buildWidgetUrl(config);
    iframe.src = widgetUrl;
    iframe.style.cssText = `
      border: none;
      width: 100%;
      height: 100%;
      background: transparent;
      pointer-events: auto;
    `;
    iframe.setAttribute('allowtransparency', 'true');
    iframe.setAttribute('title', 'Chat Widget');

    container.appendChild(iframe);
    document.body.appendChild(container);

    // Setup communication
    setupMessageHandling(iframe, container);
    
    return { container, iframe };
  }

  function buildWidgetUrl(config) {
    const baseUrl = config.apiBaseUrl.replace(/\/$/, '');
    const params = new URLSearchParams();
    
    Object.entries(config).forEach(([key, value]) => {
      if (value !== undefined) {
        params.set(key, String(value));
      }
    });

    // Serve the modern widget HTML file
    return `${baseUrl}/widget/modern-widget.html?${params.toString()}`;
  }

  function setupMessageHandling(iframe, container) {
    window.addEventListener('message', function(event) {
      // Basic origin check (should be more strict in production)
      if (!event.data || typeof event.data !== 'object') return;
      
      const { type, payload } = event.data;
      
      switch (type) {
        case 'CHAT_WIDGET_LOADED':
          console.log('Chat widget loaded successfully');
          break;
        case 'CHAT_WIDGET_ERROR':
          console.error('Chat widget error:', payload);
          break;
        case 'CHAT_WIDGET_RESIZE':
          // Handle resize if needed
          break;
      }
    });
  }

  // Initialize when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initWidget);
  } else {
    initWidget();
  }

  // Expose global method for manual initialization
  window.initChatWidget = function(customConfig) {
    window.ChatWidgetConfig = customConfig;
    return initWidget();
  };

})();
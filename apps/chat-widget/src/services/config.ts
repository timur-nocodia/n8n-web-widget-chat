// Widget Configuration Service

export interface WidgetConfig {
  api: {
    baseUrl: string;
    endpoints: {
      session: string;
      chat: string;
    };
  };
  appearance: {
    position: string;
    theme: {
      primaryColor: string;
      secondaryColor: string;
      primaryGradient: string;
      bgDark: string;
      bgGlass: string;
      textLight: string;
      textDark: string;
      borderRadius: string;
      fontFamily: string;
    };
    dimensions: {
      width: string;
      height: string;
      mobileWidth: string;
      mobileHeight: string;
      buttonSize: string;
      bottomOffset: string;
      rightOffset: string;
    };
    animations: {
      enabled: boolean;
      springAnimation: string;
      transitionDuration: string;
      typingIndicatorDelay: number;
      streamingFlushDelay: number;
    };
    shadows: {
      floatShadow: string;
      elevatedShadow: string;
    };
  };
  texts: {
    header: {
      title: string;
      subtitle: string;
      statusOnline: string;
      statusOffline: string;
      statusConnecting: string;
    };
    messages: {
      welcomeMessage: string;
      errorMessage: string;
      connectionError: string;
      typingIndicator: string;
    };
    input: {
      placeholder: string;
      sendButtonAriaLabel: string;
      hint: string;
    };
    suggestions: Array<{
      text: string;
      value: string;
    }>;
    button: {
      openIcon: string;
      closeIcon: string;
      sendIcon: string;
    };
  };
  behavior: {
    autoOpen: boolean;
    autoOpenDelay: number;
    enableSuggestions: boolean;
    enableTypingIndicator: boolean;
    enableMarkdown: boolean;
    enableSoundNotifications: boolean;
    sessionPersistence: boolean;
    messageHistory: boolean;
    maxMessageLength: number;
    rateLimit: {
      enabled: boolean;
      maxMessagesPerMinute: number;
    };
    scrollBehavior: {
      autoScroll: boolean;
      scrollThreshold: number;
    };
  };
  localization: {
    locale: string;
    dateFormat: string;
    timeFormat: string;
    rtl: boolean;
  };
  integrations: {
    analytics: {
      enabled: boolean;
      provider: string | null;
      trackingId: string | null;
    };
    customHeaders: Record<string, string>;
    customMetadata: Record<string, any>;
  };
  accessibility: {
    enableKeyboardShortcuts: boolean;
    announceMessages: boolean;
    highContrast: boolean;
    focusOutline: boolean;
  };
  mobile: {
    enabled: boolean;
    fullscreen: boolean;
    breakpoint: number;
  };
}

class ConfigService {
  private config: WidgetConfig | null = null;
  private configUrl: string;
  private defaultConfig: Partial<WidgetConfig> = {
    api: {
      baseUrl: window.location.origin.includes('localhost') 
        ? 'http://localhost:8000' 
        : window.location.origin,
      endpoints: {
        session: '/api/v1/session/create',
        chat: '/api/v1/chat/stream'
      }
    },
    texts: {
      header: {
        title: 'AI Assistant',
        subtitle: 'Online • Powered by n8n',
        statusOnline: 'Online',
        statusOffline: 'Offline',
        statusConnecting: 'Connecting...'
      },
      messages: {
        welcomeMessage: '👋 Hello! I\'m your AI assistant. How can I help you today?',
        errorMessage: 'Sorry, I couldn\'t connect to the server. Please try again later.',
        connectionError: 'Connection error: ',
        typingIndicator: 'AI is typing...'
      },
      input: {
        placeholder: 'Type your message...',
        sendButtonAriaLabel: 'Send message',
        hint: 'Press Enter to send, Shift + Enter for new line'
      },
      suggestions: [
        { text: 'How can you help?', value: 'What can you help me with?' },
        { text: 'Tell me more', value: 'Can you tell me more about your features?' },
        { text: 'Get started', value: 'How do I get started?' }
      ],
      button: {
        openIcon: '💬',
        closeIcon: '✕',
        sendIcon: '➤'
      }
    },
    behavior: {
      autoOpen: false,
      autoOpenDelay: 0,
      enableSuggestions: true,
      enableTypingIndicator: true,
      enableMarkdown: true,
      enableSoundNotifications: false,
      sessionPersistence: true,
      messageHistory: true,
      maxMessageLength: 10000,
      rateLimit: {
        enabled: false,
        maxMessagesPerMinute: 20
      },
      scrollBehavior: {
        autoScroll: true,
        scrollThreshold: 100
      }
    }
  };

  constructor(configUrl?: string) {
    this.configUrl = configUrl || this.getConfigUrl();
  }

  private getConfigUrl(): string {
    // Check for config URL in various places
    const metaTag = document.querySelector('meta[name="chat-widget-config"]');
    if (metaTag) {
      return metaTag.getAttribute('content') || './widget-config.json';
    }

    // Check window object
    if ((window as any).CHAT_WIDGET_CONFIG_URL) {
      return (window as any).CHAT_WIDGET_CONFIG_URL;
    }

    // Check data attribute on script tag
    const scripts = document.getElementsByTagName('script');
    for (let i = 0; i < scripts.length; i++) {
      const configUrl = scripts[i].getAttribute('data-config');
      if (configUrl) {
        return configUrl;
      }
    }

    return './widget-config.json';
  }

  async load(): Promise<WidgetConfig> {
    try {
      const response = await fetch(this.configUrl);
      if (response.ok) {
        this.config = await response.json();
        console.log('✅ Widget configuration loaded');
      } else {
        console.warn('⚠️ Could not load configuration, using defaults');
        this.config = this.defaultConfig as WidgetConfig;
      }
    } catch (error) {
      console.warn('⚠️ Configuration load failed, using defaults:', error);
      this.config = this.defaultConfig as WidgetConfig;
    }

    return this.config!;
  }

  get<T = any>(path: string, defaultValue?: T): T {
    if (!this.config) {
      return defaultValue as T;
    }

    const keys = path.split('.');
    let value: any = this.config;

    for (const key of keys) {
      if (value && typeof value === 'object' && key in value) {
        value = value[key];
      } else {
        return defaultValue as T;
      }
    }

    return value as T;
  }

  getConfig(): WidgetConfig | null {
    return this.config;
  }

  // Apply theme to CSS variables
  applyTheme(): void {
    if (!this.config?.appearance?.theme) return;

    const root = document.documentElement;
    const theme = this.config.appearance.theme;

    Object.entries(theme).forEach(([key, value]) => {
      const cssVar = `--${key.replace(/([A-Z])/g, '-$1').toLowerCase()}`;
      root.style.setProperty(cssVar, value);
    });
  }

  // Apply dimensions
  applyDimensions(container: HTMLElement | null): void {
    if (!container || !this.config?.appearance?.dimensions) return;

    const dims = this.config.appearance.dimensions;
    
    if (dims.width) container.style.width = dims.width;
    if (dims.height) container.style.height = dims.height;
    
    // Check if mobile
    if (window.innerWidth <= (this.config.mobile?.breakpoint || 480)) {
      if (dims.mobileWidth) container.style.width = dims.mobileWidth;
      if (dims.mobileHeight) container.style.height = dims.mobileHeight;
    }
  }

  // Check if feature is enabled
  isEnabled(feature: string): boolean {
    return this.get(`behavior.${feature}`, false);
  }

  // Get API endpoint
  getApiEndpoint(endpoint: string): string {
    const baseUrl = this.get('api.baseUrl', '');
    const endpointPath = this.get(`api.endpoints.${endpoint}`, '');
    return `${baseUrl}${endpointPath}`;
  }

  // Get text content
  getText(path: string, defaultText: string = ''): string {
    return this.get(`texts.${path}`, defaultText);
  }

  // Get suggestions
  getSuggestions(): Array<{ text: string; value: string }> {
    return this.get('texts.suggestions', []);
  }
}

// Export singleton instance
export const configService = new ConfigService();

// Export for use in components
export default configService;
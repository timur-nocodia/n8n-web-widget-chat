import { ChatConfig } from './types';

interface EmbedConfig extends ChatConfig {
  containerId?: string;
}

class ChatWidgetEmbed {
  private config: EmbedConfig;
  private container: HTMLElement | null = null;
  private iframe: HTMLIFrameElement | null = null;

  constructor(config: EmbedConfig) {
    this.config = {
      apiBaseUrl: 'http://localhost:8000',
      theme: 'light',
      position: 'bottom-right',
      title: 'Chat Assistant',
      placeholder: 'Type your message...',
      welcomeMessage: 'Hello! How can I help you today?',
      ...config
    };
  }

  public init(): void {
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', () => this.render());
    } else {
      this.render();
    }
  }

  private render(): void {
    // Create container
    this.container = document.createElement('div');
    this.container.id = this.config.containerId || 'chat-widget-container';
    this.container.style.cssText = `
      position: fixed;
      z-index: 10000;
      pointer-events: none;
    `;

    // Create iframe
    this.iframe = document.createElement('iframe');
    this.iframe.src = this.getWidgetUrl();
    this.iframe.style.cssText = `
      border: none;
      width: 100vw;
      height: 100vh;
      background: transparent;
      pointer-events: auto;
    `;
    this.iframe.setAttribute('allowtransparency', 'true');

    this.container.appendChild(this.iframe);
    document.body.appendChild(this.container);

    // Listen for iframe messages
    this.setupMessageListener();
  }

  private getWidgetUrl(): string {
    const baseUrl = this.config.apiBaseUrl.replace('/api', '').replace(/\/$/, '');
    const params = new URLSearchParams();
    
    // Pass config as URL params
    Object.entries(this.config).forEach(([key, value]) => {
      if (value !== undefined && key !== 'containerId') {
        params.set(key, String(value));
      }
    });

    return `${baseUrl}/widget?${params.toString()}`;
  }

  private setupMessageListener(): void {
    window.addEventListener('message', (event) => {
      // Verify origin for security
      const widgetOrigin = new URL(this.config.apiBaseUrl).origin;
      if (event.origin !== widgetOrigin) {
        return;
      }

      const { type, data } = event.data;

      switch (type) {
        case 'WIDGET_RESIZE':
          this.handleResize(data);
          break;
        case 'WIDGET_CLOSE':
          this.handleClose();
          break;
        case 'WIDGET_ERROR':
          console.error('Chat Widget Error:', data);
          break;
      }
    });
  }

  private handleResize(dimensions: { width: number; height: number }): void {
    if (this.iframe) {
      this.iframe.style.width = `${dimensions.width}px`;
      this.iframe.style.height = `${dimensions.height}px`;
    }
  }

  private handleClose(): void {
    if (this.container) {
      this.container.style.display = 'none';
    }
  }

  public destroy(): void {
    if (this.container) {
      document.body.removeChild(this.container);
      this.container = null;
      this.iframe = null;
    }
  }
}

// Global function to initialize widget
(window as any).initChatWidget = (config: EmbedConfig) => {
  const widget = new ChatWidgetEmbed(config);
  widget.init();
  return widget;
};

// Auto-initialize if config is present
if ((window as any).ChatWidgetConfig) {
  (window as any).initChatWidget((window as any).ChatWidgetConfig);
}
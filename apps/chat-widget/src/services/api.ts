import { Session, ChatMessage } from '@/types';

export class ChatAPI {
  private baseUrl: string;
  
  constructor(baseUrl: string) {
    this.baseUrl = baseUrl.replace(/\/$/, ''); // Remove trailing slash
  }

  async createSession(pageUrl?: string): Promise<Session> {
    const response = await fetch(`${this.baseUrl}/api/v1/session/create`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      credentials: 'include',
      body: JSON.stringify({
        origin_domain: window.location.hostname,
        page_url: pageUrl || window.location.href,
      }),
    });

    if (!response.ok) {
      throw new Error(`Failed to create session: ${response.statusText}`);
    }

    return response.json();
  }

  async getHistory(): Promise<ChatMessage[]> {
    const response = await fetch(`${this.baseUrl}/api/v1/chat/history`, {
      method: 'GET',
      credentials: 'include',
    });

    if (!response.ok) {
      if (response.status === 401) {
        throw new Error('Session expired');
      }
      throw new Error(`Failed to get history: ${response.statusText}`);
    }

    const data = await response.json();
    return data.messages;
  }

  async sendMessage(message: string, context?: Record<string, any>): Promise<Response> {
    // Send message and get SSE response
    const response = await fetch(`${this.baseUrl}/api/v1/chat/message`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      credentials: 'include',
      body: JSON.stringify({
        message,
        context,
      }),
    });

    if (!response.ok) {
      throw new Error(`Failed to send message: ${response.statusText}`);
    }

    return response;
  }

  createEventSource(url: string): EventSource {
    return new EventSource(url, { withCredentials: true });
  }

  async destroySession(): Promise<void> {
    const response = await fetch(`${this.baseUrl}/api/v1/session/destroy`, {
      method: 'DELETE',
      credentials: 'include',
    });

    if (!response.ok && response.status !== 404) {
      throw new Error(`Failed to destroy session: ${response.statusText}`);
    }
  }
}
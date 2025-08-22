export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  created_at: string;
  metadata?: Record<string, any>;
}

export interface Session {
  session_id: string;
  expires_at: string;
}

export interface ChatConfig {
  apiBaseUrl: string;
  theme?: 'light' | 'dark';
  position?: 'bottom-right' | 'bottom-left';
  title?: string;
  placeholder?: string;
  welcomeMessage?: string;
}

export interface SSEMessage {
  event: string;
  data: string;
}

export type ConnectionStatus = 'connecting' | 'connected' | 'disconnected' | 'error';

export interface ChatState {
  messages: ChatMessage[];
  isLoading: boolean;
  connectionStatus: ConnectionStatus;
  session: Session | null;
}
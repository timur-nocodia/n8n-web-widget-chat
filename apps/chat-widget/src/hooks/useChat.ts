import { useState, useCallback, useRef, useEffect } from 'react';
import { ChatMessage, Session, ChatState } from '@/types';
import { ChatAPI } from '@/services/api';
import { useSSE } from './useSSE';

export const useChat = (apiBaseUrl: string) => {
  const [state, setState] = useState<ChatState>({
    messages: [],
    isLoading: false,
    connectionStatus: 'disconnected',
    session: null
  });
  
  const apiRef = useRef(new ChatAPI(apiBaseUrl));
  const { connectionStatus, connect, disconnect } = useSSE();
  const eventSourceRef = useRef<EventSource | null>(null);
  const currentAssistantMessageRef = useRef<string>('');
  
  // Initialize session
  const initializeSession = useCallback(async () => {
    try {
      const session = await apiRef.current.createSession();
      setState(prev => ({ ...prev, session }));
      
      // Load chat history
      const history = await apiRef.current.getHistory();
      setState(prev => ({ ...prev, messages: history }));
    } catch (error) {
      console.error('Failed to initialize session:', error);
    }
  }, []);
  
  // Send message
  const sendMessage = useCallback(async (content: string) => {
    if (!state.session || state.isLoading) return;
    
    // Add user message immediately
    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      content,
      created_at: new Date().toISOString()
    };
    
    setState(prev => ({
      ...prev,
      messages: [...prev.messages, userMessage],
      isLoading: true
    }));
    
    // Create placeholder assistant message
    const assistantMessage: ChatMessage = {
      id: (Date.now() + 1).toString(),
      role: 'assistant',
      content: '',
      created_at: new Date().toISOString()
    };
    
    setState(prev => ({
      ...prev,
      messages: [...prev.messages, assistantMessage]
    }));
    
    currentAssistantMessageRef.current = '';
    
    try {
      // Get SSE response
      const response = await apiRef.current.sendMessage(content);
      
      if (!response.body) {
        throw new Error('No response body');
      }
      
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      
      // Process streaming response
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        
        // Keep the last incomplete line in buffer
        buffer = lines.pop() || '';
        
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6).trim();
            console.log('Received SSE data:', data); // Debug log
            if (data && data !== '[DONE]') {
              try {
                const parsed = JSON.parse(data);
                let content = '';
                
                // Handle different response formats
                if (parsed.content) {
                  content = parsed.content;
                } else if (parsed.delta && parsed.delta.content) {
                  content = parsed.delta.content;
                } else if (parsed.error) {
                  throw new Error(parsed.error);
                } else if (typeof parsed === 'string') {
                  content = parsed;
                } else {
                  // Fallback to raw data
                  content = data;
                }
                
                if (content) {
                  currentAssistantMessageRef.current += content;
                  
                  // Update message in real-time
                  setState(prev => ({
                    ...prev,
                    messages: prev.messages.map(msg =>
                      msg.id === assistantMessage.id
                        ? { ...msg, content: currentAssistantMessageRef.current }
                        : msg
                    )
                  }));
                }
              } catch (parseError) {
                // Handle raw text data
                currentAssistantMessageRef.current += data;
                setState(prev => ({
                  ...prev,
                  messages: prev.messages.map(msg =>
                    msg.id === assistantMessage.id
                      ? { ...msg, content: currentAssistantMessageRef.current }
                      : msg
                  )
                }));
              }
            } else if (data === '[DONE]') {
              break;
            }
          }
        }
      }
      
    } catch (error) {
      console.error('Failed to send message:', error);
      // Add error message
      const errorMessage: ChatMessage = {
        id: (Date.now() + 2).toString(),
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please try again.',
        created_at: new Date().toISOString()
      };
      
      setState(prev => ({
        ...prev,
        messages: [...prev.messages, errorMessage]
      }));
    } finally {
      setState(prev => ({ ...prev, isLoading: false }));
    }
  }, [state.session, state.isLoading]);
  
  // Update connection status
  useEffect(() => {
    setState(prev => ({ ...prev, connectionStatus }));
  }, [connectionStatus]);
  
  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (eventSourceRef.current) {
        disconnect(eventSourceRef.current);
      }
    };
  }, [disconnect]);
  
  return {
    ...state,
    initializeSession,
    sendMessage
  };
};
import { useState, useCallback } from 'react';
import { SSEMessage, ConnectionStatus } from '@/types';

export const useSSE = () => {
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('disconnected');
  
  const connect = useCallback((
    url: string,
    onMessage: (message: SSEMessage) => void,
    onError?: (error: Event) => void
  ): EventSource => {
    setConnectionStatus('connecting');
    
    const eventSource = new EventSource(url, { withCredentials: true });
    
    eventSource.onopen = () => {
      setConnectionStatus('connected');
    };
    
    eventSource.onmessage = (event) => {
      onMessage({
        event: event.type,
        data: event.data
      });
    };
    
    eventSource.addEventListener('message', (event) => {
      onMessage({
        event: 'message',
        data: event.data
      });
    });
    
    eventSource.addEventListener('complete', (event) => {
      onMessage({
        event: 'complete',
        data: event.data
      });
      eventSource.close();
      setConnectionStatus('disconnected');
    });
    
    eventSource.onerror = (event) => {
      setConnectionStatus('error');
      if (onError) {
        onError(event);
      }
      
      // Attempt reconnection after a delay
      setTimeout(() => {
        if (eventSource.readyState === EventSource.CLOSED) {
          setConnectionStatus('disconnected');
        }
      }, 1000);
    };
    
    return eventSource;
  }, []);
  
  const disconnect = useCallback((eventSource: EventSource) => {
    if (eventSource) {
      eventSource.close();
      setConnectionStatus('disconnected');
    }
  }, []);
  
  return {
    connectionStatus,
    connect,
    disconnect
  };
};
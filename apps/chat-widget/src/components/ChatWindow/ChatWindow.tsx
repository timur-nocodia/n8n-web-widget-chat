import React, { useEffect, useState } from 'react';
import { MessageList } from '@/components/MessageList/MessageList';
import { InputArea } from '@/components/InputArea/InputArea';
import { ConnectionStatus as ConnectionStatusComponent } from '@/components/ConnectionStatus/ConnectionStatus';
import { useChat } from '@/hooks/useChat';
import { ChatConfig } from '@/types';
import './ChatWindow.css';

interface ChatWindowProps {
  config: ChatConfig;
  isOpen: boolean;
  onClose: () => void;
}

export const ChatWindow: React.FC<ChatWindowProps> = ({ config, isOpen, onClose }) => {
  const [isMinimized, setIsMinimized] = useState(false);
  const { messages, isLoading, connectionStatus, session, initializeSession, sendMessage } = useChat(config.apiBaseUrl);
  
  useEffect(() => {
    if (isOpen && !session) {
      initializeSession();
    }
  }, [isOpen, session, initializeSession]);
  
  const handleMinimize = () => {
    setIsMinimized(!isMinimized);
  };
  
  if (!isOpen) return null;
  
  return (
    <div className={`chat-window ${config.position || 'bottom-right'} ${config.theme || 'light'}`}>
      <div className={`chat-container ${isMinimized ? 'minimized' : ''}`}>
        {/* Header */}
        <div className="chat-header">
          <div className="header-content">
            <h3 className="chat-title">{config.title || 'Chat Assistant'}</h3>
            <ConnectionStatusComponent status={connectionStatus} />
          </div>
          <div className="header-actions">
            <button
              onClick={handleMinimize}
              className="action-button minimize-button"
              aria-label={isMinimized ? 'Expand chat' : 'Minimize chat'}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                {isMinimized ? (
                  <polyline points="18,15 12,9 6,15"></polyline>
                ) : (
                  <polyline points="6,9 12,15 18,9"></polyline>
                )}
              </svg>
            </button>
            <button
              onClick={onClose}
              className="action-button close-button"
              aria-label="Close chat"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <line x1="18" y1="6" x2="6" y2="18"></line>
                <line x1="6" y1="6" x2="18" y2="18"></line>
              </svg>
            </button>
          </div>
        </div>
        
        {/* Content */}
        {!isMinimized && (
          <>
            <div className="chat-content">
              {config.welcomeMessage && messages.length === 0 && !isLoading && (
                <div className="welcome-message">
                  <div className="message assistant-message">
                    <div className="message-content">
                      <div className="message-text">{config.welcomeMessage}</div>
                    </div>
                  </div>
                </div>
              )}
              <MessageList messages={messages} isLoading={isLoading} />
            </div>
            
            <InputArea
              onSendMessage={sendMessage}
              disabled={isLoading || connectionStatus !== 'connected'}
              placeholder={config.placeholder || 'Type your message...'}
            />
          </>
        )}
      </div>
    </div>
  );
};
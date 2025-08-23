import React, { useEffect, useRef } from 'react';
import { ChatMessage } from '@/types';
import { MessageFooter } from '../MessageFooter/MessageFooter';
import { useConfig } from '@/hooks/useConfig';
import './MessageList.css';

interface MessageListProps {
  messages: ChatMessage[];
  isLoading: boolean;
}

export const MessageList: React.FC<MessageListProps> = ({ messages, isLoading }) => {
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { get } = useConfig();
  
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };
  
  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);
  
  // Get footer configuration
  const footerConfig = get('texts.messages.footer', {
    enabled: true,
    botName: 'Assistant',
    userName: 'You',
    showTimestamp: true,
    timestampFormat: '24h',
    showDate: true
  });
  
  return (
    <div className="message-list">
      {messages.map((message) => (
        <div
          key={message.id}
          className={`message ${message.role === 'user' ? 'user-message' : 'assistant-message'}`}
        >
          <div className="message-content">
            <div className="message-text">{message.content}</div>
            {footerConfig.enabled !== false && (
              <MessageFooter
                name={message.role === 'user' ? footerConfig.userName : footerConfig.botName}
                timestamp={new Date(message.created_at)}
                showTimestamp={footerConfig.showTimestamp}
                showDate={footerConfig.showDate}
                timestampFormat={footerConfig.timestampFormat}
                type={message.role === 'user' ? 'user' : 'bot'}
              />
            )}
          </div>
        </div>
      ))}
      
      {isLoading && (
        <div className="message assistant-message">
          <div className="message-content">
            <div className="typing-indicator">
              <span></span>
              <span></span>
              <span></span>
            </div>
          </div>
        </div>
      )}
      
      <div ref={messagesEndRef} />
    </div>
  );
};
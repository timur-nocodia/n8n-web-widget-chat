import React from 'react';
import './MessageFooter.css';

interface MessageFooterProps {
  name: string;
  timestamp?: Date;
  showTimestamp?: boolean;
  showDate?: boolean;
  timestampFormat?: '12h' | '24h';
  type: 'user' | 'bot';
}

export const MessageFooter: React.FC<MessageFooterProps> = ({
  name,
  timestamp = new Date(),
  showTimestamp = true,
  showDate = true,
  timestampFormat = '24h',
  type
}) => {
  const formatTime = (date: Date): string => {
    if (timestampFormat === '24h') {
      const hours = date.getHours().toString().padStart(2, '0');
      const minutes = date.getMinutes().toString().padStart(2, '0');
      return `${hours}:${minutes}`;
    } else {
      // 12h format
      let hours = date.getHours();
      const minutes = date.getMinutes().toString().padStart(2, '0');
      const ampm = hours >= 12 ? 'PM' : 'AM';
      hours = hours % 12 || 12;
      return `${hours}:${minutes} ${ampm}`;
    }
  };

  const formatDate = (date: Date): string => {
    const options: Intl.DateTimeFormatOptions = {
      month: 'short',
      day: 'numeric'
    };
    return date.toLocaleDateString('en-US', options);
  };

  const timeStr = showTimestamp ? formatTime(timestamp) : '';
  const dateStr = showDate ? formatDate(timestamp) : '';
  const fullTimestamp = [dateStr, timeStr].filter(Boolean).join(' ');

  return (
    <div className={`message-footer ${type}-footer`}>
      <span className="message-name">{name}</span>
      {fullTimestamp && (
        <span className="message-time">{fullTimestamp}</span>
      )}
    </div>
  );
};
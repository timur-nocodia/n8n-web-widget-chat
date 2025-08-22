import React from 'react';
import { ConnectionStatus as Status } from '@/types';
import './ConnectionStatus.css';

interface ConnectionStatusProps {
  status: Status;
}

export const ConnectionStatus: React.FC<ConnectionStatusProps> = ({ status }) => {
  const getStatusConfig = (status: Status) => {
    switch (status) {
      case 'connected':
        return {
          color: '#10b981',
          text: 'Connected',
          icon: '●'
        };
      case 'connecting':
        return {
          color: '#f59e0b',
          text: 'Connecting',
          icon: '●'
        };
      case 'disconnected':
        return {
          color: '#6b7280',
          text: 'Disconnected',
          icon: '●'
        };
      case 'error':
        return {
          color: '#ef4444',
          text: 'Error',
          icon: '●'
        };
      default:
        return {
          color: '#6b7280',
          text: 'Unknown',
          icon: '●'
        };
    }
  };

  const config = getStatusConfig(status);

  return (
    <div className="connection-status" title={`Status: ${config.text}`}>
      <span 
        className={`status-indicator ${status}`} 
        style={{ color: config.color }}
      >
        {config.icon}
      </span>
      <span className="status-text">{config.text}</span>
    </div>
  );
};
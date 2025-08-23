import './init'; // Initialize app and disable console in production
import React from 'react';
import ReactDOM from 'react-dom/client';
import { App } from './App';
import { ChatConfig } from '@/types';

// Get config from global window object (set by embed script)
declare global {
  interface Window {
    ChatWidgetConfig?: ChatConfig;
  }
}

const defaultConfig: ChatConfig = {
  apiBaseUrl: 'http://localhost:8000',
  theme: 'light',
  position: 'bottom-right',
  title: 'Chat Assistant',
  placeholder: 'Type your message...',
  welcomeMessage: 'Hello! How can I help you today?'
};

const config = { ...defaultConfig, ...window.ChatWidgetConfig };

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App config={config} />
  </React.StrictMode>,
);
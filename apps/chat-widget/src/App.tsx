import React, { useState } from 'react';
import { ChatWindow } from '@/components/ChatWindow/ChatWindow';
import { ChatConfig } from '@/types';

interface AppProps {
  config: ChatConfig;
}

export const App: React.FC<AppProps> = ({ config }) => {
  const [isOpen, setIsOpen] = useState(false);

  const handleOpen = () => setIsOpen(true);
  const handleClose = () => setIsOpen(false);

  return (
    <>
      {/* Chat trigger button */}
      {!isOpen && (
        <button
          onClick={handleOpen}
          className={`chat-trigger-button ${config.position || 'bottom-right'}`}
          aria-label="Open chat"
          style={{
            position: 'fixed',
            zIndex: 9999,
            width: '60px',
            height: '60px',
            borderRadius: '50%',
            border: 'none',
            background: config.theme === 'dark' ? '#4a5568' : '#007bff',
            color: 'white',
            cursor: 'pointer',
            boxShadow: '0 4px 16px rgba(0, 0, 0, 0.12)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            transition: 'all 0.2s ease',
            bottom: config.position?.includes('bottom') ? '20px' : 'auto',
            top: config.position?.includes('top') ? '20px' : 'auto',
            right: config.position?.includes('right') ? '20px' : 'auto',
            left: config.position?.includes('left') ? '20px' : 'auto',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.transform = 'scale(1.05)';
            e.currentTarget.style.boxShadow = '0 6px 20px rgba(0, 0, 0, 0.15)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.transform = 'scale(1)';
            e.currentTarget.style.boxShadow = '0 4px 16px rgba(0, 0, 0, 0.12)';
          }}
        >
          <svg
            width="24"
            height="24"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
          </svg>
        </button>
      )}

      {/* Chat window */}
      <ChatWindow
        config={config}
        isOpen={isOpen}
        onClose={handleClose}
      />
    </>
  );
};
import React, { useState, useEffect } from 'react';
import { ChatWindow } from '@/components/ChatWindow/ChatWindow';
import { ChatConfig } from '@/types';
import { useConfig } from '@/hooks/useConfig';

interface AppProps {
  config?: ChatConfig;
}

export const App: React.FC<AppProps> = ({ config: externalConfig }) => {
  const { config: loadedConfig, loading, getText, isEnabled, get } = useConfig();
  const [isOpen, setIsOpen] = useState(false);

  // Use external config if provided, otherwise use loaded config
  const config = externalConfig || loadedConfig;

  const handleOpen = () => setIsOpen(true);
  const handleClose = () => setIsOpen(false);

  // Handle auto-open behavior
  useEffect(() => {
    if (config && isEnabled('autoOpen')) {
      const delay = get('behavior.autoOpenDelay', 0);
      const timer = setTimeout(() => setIsOpen(true), delay);
      return () => clearTimeout(timer);
    }
  }, [config, isEnabled, get]);

  if (loading || !config) {
    return null; // Don't render until config is loaded
  }

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
          <span style={{ fontSize: '24px' }}>
            {getText('button.openIcon', '💬')}
          </span>
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
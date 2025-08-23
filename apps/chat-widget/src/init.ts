/**
 * Production initialization
 * This file should be imported at the very beginning of your app
 */

import { setupConsole, disableConsole } from './utils/console';

// Initialize console based on environment
export function initializeApp() {
  // Check if we're in production
  const isProduction = process.env.NODE_ENV === 'production' ||
    (!window.location.hostname.includes('localhost') &&
     !window.location.hostname.startsWith('192.168.') &&
     !window.location.hostname.startsWith('127.0.0.1'));

  if (isProduction) {
    // Completely disable console in production
    disableConsole();
    
    // Optional: Add global error handler that doesn't use console
    window.addEventListener('error', (event) => {
      // Could send to error tracking service instead
      // sendToErrorTracking(event.error);
      event.preventDefault();
    });

    window.addEventListener('unhandledrejection', (event) => {
      // Could send to error tracking service instead
      // sendToErrorTracking(event.reason);
      event.preventDefault();
    });
  } else {
    // In development, just setup console with default config
    setupConsole({
      disableInProduction: false,
      allowedMethods: ['log', 'error', 'warn', 'info', 'debug']
    });
  }
}

// Auto-initialize when this module is imported
initializeApp();
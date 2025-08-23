/**
 * Console management utility for production environments
 * Disables all console output in production to prevent information leakage
 */

// Store original console methods for restoration if needed
const originalConsole = {
  log: console.log,
  error: console.error,
  warn: console.warn,
  info: console.info,
  debug: console.debug,
  trace: console.trace,
  dir: console.dir,
  table: console.table,
  time: console.time,
  timeEnd: console.timeEnd,
  timeLog: console.timeLog,
  group: console.group,
  groupEnd: console.groupEnd,
  groupCollapsed: console.groupCollapsed,
  assert: console.assert,
  clear: console.clear,
  count: console.count,
  countReset: console.countReset,
  profile: console.profile,
  profileEnd: console.profileEnd,
  timeStamp: console.timeStamp
};

/**
 * Completely disable all console methods
 * Used in production to prevent any console output
 */
export function disableConsole(): void {
  const noop = () => {};
  
  // Override all console methods with no-op functions
  Object.keys(originalConsole).forEach(method => {
    (console as any)[method] = noop;
  });

  // Also prevent console object itself from being modified
  if (Object.freeze) {
    Object.freeze(console);
  }
}

/**
 * Restore original console functionality
 * Useful for debugging production issues when needed
 */
export function restoreConsole(): void {
  Object.keys(originalConsole).forEach(method => {
    (console as any)[method] = (originalConsole as any)[method];
  });
}

/**
 * Conditionally disable console based on environment
 */
export function setupConsole(config?: {
  disableInProduction?: boolean;
  allowedMethods?: string[];
  customLogger?: (method: string, ...args: any[]) => void;
}): void {
  const {
    disableInProduction = true,
    allowedMethods = [],
    customLogger
  } = config || {};

  // Check if we're in production
  const isProduction = process.env.NODE_ENV === 'production' || 
                       window.location.hostname !== 'localhost' &&
                       !window.location.hostname.startsWith('192.168.') &&
                       !window.location.hostname.startsWith('127.0.0.1');

  if (isProduction && disableInProduction) {
    // Create no-op function
    const noop = () => {};
    
    // Override all console methods
    Object.keys(originalConsole).forEach(method => {
      if (!allowedMethods.includes(method)) {
        if (customLogger) {
          // Use custom logger that could send to server
          (console as any)[method] = (...args: any[]) => {
            customLogger(method, ...args);
          };
        } else {
          // Complete silence
          (console as any)[method] = noop;
        }
      }
    });
  }
}

/**
 * Safe console wrapper that only logs in development
 */
export const safeConsole = {
  log: (...args: any[]) => {
    if (process.env.NODE_ENV !== 'production') {
      originalConsole.log(...args);
    }
  },
  error: (...args: any[]) => {
    if (process.env.NODE_ENV !== 'production') {
      originalConsole.error(...args);
    }
  },
  warn: (...args: any[]) => {
    if (process.env.NODE_ENV !== 'production') {
      originalConsole.warn(...args);
    }
  },
  info: (...args: any[]) => {
    if (process.env.NODE_ENV !== 'production') {
      originalConsole.info(...args);
    }
  },
  debug: (...args: any[]) => {
    if (process.env.NODE_ENV !== 'production') {
      originalConsole.debug(...args);
    }
  }
};

/**
 * Prevent console access via developer tools
 * This is more aggressive and prevents inspection
 */
export function preventConsoleAccess(): void {
  // Disable right-click context menu
  document.addEventListener('contextmenu', (e) => e.preventDefault());
  
  // Disable F12, Ctrl+Shift+I, Ctrl+Shift+J, Ctrl+Shift+C
  document.addEventListener('keydown', (e) => {
    if (
      e.key === 'F12' ||
      (e.ctrlKey && e.shiftKey && ['I', 'J', 'C'].includes(e.key)) ||
      (e.ctrlKey && e.key === 'U')
    ) {
      e.preventDefault();
      return false;
    }
  });

  // Detect DevTools (basic detection - not foolproof)
  let devtools = { open: false, orientation: null };
  const threshold = 160;
  
  setInterval(() => {
    if (
      window.outerHeight - window.innerHeight > threshold ||
      window.outerWidth - window.innerWidth > threshold
    ) {
      if (!devtools.open) {
        devtools.open = true;
        // Console is already disabled, but we could take additional action
        document.body.style.display = 'none';
        document.body.innerHTML = 'Developer tools detected';
      }
    } else {
      devtools.open = false;
      document.body.style.display = '';
    }
  }, 500);
}

// Auto-initialize based on environment
if (typeof window !== 'undefined') {
  // Browser environment
  setupConsole({
    disableInProduction: true,
    allowedMethods: [], // Allow nothing in production
  });
}
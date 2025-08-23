import { useState, useEffect } from 'react';
import configService, { WidgetConfig } from '../services/config';

export const useConfig = () => {
  const [config, setConfig] = useState<WidgetConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    const loadConfig = async () => {
      try {
        setLoading(true);
        const loadedConfig = await configService.load();
        setConfig(loadedConfig);
        
        // Apply theme immediately
        configService.applyTheme();
      } catch (err) {
        setError(err as Error);
        console.error('Failed to load configuration:', err);
      } finally {
        setLoading(false);
      }
    };

    loadConfig();
  }, []);

  return {
    config,
    loading,
    error,
    get: configService.get.bind(configService),
    getText: configService.getText.bind(configService),
    isEnabled: configService.isEnabled.bind(configService),
    getApiEndpoint: configService.getApiEndpoint.bind(configService),
    getSuggestions: configService.getSuggestions.bind(configService)
  };
};
const API_BASE_URL = (import.meta.env.VITE_API_URL ?? '/api/v1').replace(/\/$/, '');
const REQUEST_TIMEOUT = 15000; // 15 seconds

export const apiClient = {
    scanContract: async (sourceCode, contractName) => {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT);
  
      try {
        const response = await fetch(`${API_BASE_URL}/scan`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            source_code: sourceCode,
            contract_name: contractName || 'UnnamedContract',
            file_path: 'api_upload',
          }),
          signal: controller.signal,
        });
  
        if (!response.ok) {
          throw new Error(`API error: ${response.status}`);
        }
  
        return await response.json();
      } catch (error) {
        if (error.name === 'AbortError') {
          throw new Error('Request timed out. Please try again.');
        }
  
        throw new Error('Failed to scan contract: ' + error.message);
      } finally {
        clearTimeout(timeoutId);
      }
    },
  };

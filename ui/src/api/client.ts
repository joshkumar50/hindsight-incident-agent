import axios from 'axios';
import type { AxiosError } from 'axios';

export const apiClient = axios.create({
  baseURL: '/api',
  timeout: 15000,
});

async function withRetry<T>(fn: () => Promise<T>, maxRetries = 3): Promise<T> {
  let lastError: unknown;
  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      return await fn();
    } catch (err) {
      lastError = err;
      const axiosErr = err as AxiosError;
      if (axiosErr.response && axiosErr.response.status < 500) throw err;
      if (attempt < maxRetries) {
        await new Promise((r) => setTimeout(r, attempt * 800));
      }
    }
  }
  throw lastError;
}

apiClient.interceptors.response.use(
  (res) => res,
  (error: AxiosError) => {
    if (!error.response) {
      console.error('[API] Backend unreachable. Run: kubectl port-forward svc/api-gateway 58663:80 -n incident-agent-system');
    }
    return Promise.reject(error);
  }
);

export const apiGet = <T = unknown>(url: string) =>
  withRetry(() => apiClient.get<T>(url).then((r) => r.data));

export const apiPost = <T = unknown>(url: string, data?: unknown) =>
  withRetry(() => apiClient.post<T>(url, data).then((r) => r.data));
const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  private async request(method: string, path: string, body?: any, token?: string | null, isForm = false) {
    const headers: Record<string, string> = {};
    
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    if (!isForm) {
      headers['Content-Type'] = 'application/json';
    }

    const response = await fetch(`${this.baseUrl}${path}`, {
      method,
      headers,
      body: isForm ? body : (body ? JSON.stringify(body) : undefined),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ message: response.statusText }));
      throw new Error(error.detail || error.message || `HTTP ${response.status}`);
    }

    return response.json();
  }

  async get(path: string, token?: string | null) {
    return this.request('GET', path, undefined, token);
  }

  async post(path: string, body: any, token?: string | null) {
    return this.request('POST', path, body, token);
  }

  async postForm(path: string, formData: URLSearchParams, token?: string | null) {
    return this.request('POST', path, formData, token, true);
  }

  async delete(path: string, token?: string | null) {
    return this.request('DELETE', path, undefined, token);
  }

  async uploadFile(path: string, file: File, token?: string | null) {
    const formData = new FormData();
    formData.append('file', file);

    const headers: Record<string, string> = {};
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(`${this.baseUrl}${path}`, {
      method: 'POST',
      headers,
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ message: response.statusText }));
      throw new Error(error.detail || error.message || `HTTP ${response.status}`);
    }

    return response.json();
  }
}

export const api = new ApiClient(BASE_URL);

// WebSocket utilities
const WS_BASE = import.meta.env.VITE_WS_URL || 'ws://localhost:8000';

export function createWorkflowWebSocket(
  workflowId: string,
  onMessage: (data: any) => void,
  onError?: (e: Event) => void,
): WebSocket {
  const ws = new WebSocket(`${WS_BASE}/ws/${workflowId}`);
  
  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      onMessage(data);
    } catch (e) {
      console.error('WS parse error:', e);
    }
  };

  ws.onerror = (e) => {
    console.error('WebSocket error:', e);
    onError?.(e);
  };

  ws.onopen = () => {
    console.log(`WebSocket connected: ${workflowId}`);
  };

  ws.onclose = () => {
    console.log(`WebSocket disconnected: ${workflowId}`);
  };

  return ws;
}

export function createSystemWebSocket(onMessage: (data: any) => void): WebSocket {
  const ws = new WebSocket(`${WS_BASE}/ws/system/events`);
  
  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      onMessage(data);
    } catch (e) {}
  };

  ws.onerror = (e) => console.error('System WS error:', e);
  
  return ws;
}

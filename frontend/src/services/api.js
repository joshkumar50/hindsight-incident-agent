/**
 * ====================================================================
 * services/api.js - Backend API Client
 * ====================================================================
 * PURPOSE: This file connects the React frontend to the FastAPI backend.
 * 
 * CONNECTION POINT:
 *   - In development: Vite proxy routes /api/* → http://localhost:8000/*
 *   - In production:  VITE_API_URL env var points to the backend service
 *                     e.g. http://airci-backend-svc:8000
 * 
 * HOW IT WORKS:
 *   1. App.jsx calls api.submitQuery(query, options)
 *   2. This file sends POST /api/query to the backend
 *   3. Backend runs the SRE Agent → returns RCA JSON
 *   4. This file returns the parsed response to App.jsx
 * ====================================================================
 */

import axios from 'axios';

// Base URL resolution:
// - Dev mode: Vite proxy handles /api → localhost:8000 (see vite.config.js)
// - Prod mode: Set VITE_API_URL=http://backend-service:8000
const BASE_URL = import.meta.env.VITE_API_URL || '/api';

const client = axios.create({
  baseURL: BASE_URL,
  timeout: 120000, // 2 min timeout (agent reasoning can take time)
  headers: { 'Content-Type': 'application/json' }
});

/**
 * Submit an SRE diagnostic query to the backend /query endpoint.
 * Maps directly to POST http://localhost:8000/query in main.py
 */
export async function submitQuery(query, options = {}) {
  const payload = {
    query: query,
    target_service: options.service || null,
    target_namespace: options.namespace || null,
    lookback_minutes: options.lookback || 30,
    trace_id: options.traceId || null,
    source: 'react_frontend'
  };

  const response = await client.post('/query', payload);
  return response.data;
}

/**
 * Health check — verifies backend connectivity.
 * Maps to GET http://localhost:8000/health in main.py
 */
export async function checkHealth() {
  const response = await client.get('/health');
  return response.data;
}

/**
 * Get backend system info (active LLM provider, registered tools).
 * Maps to GET http://localhost:8000/ in main.py
 */
export async function getSystemInfo() {
  const response = await client.get('/');
  return response.data;
}

/**
 * Submit operator feedback on AI incident suggestion.
 * Maps to POST http://localhost:8000/feedback in main.py
 */
export async function submitFeedback(feedbackData) {
  const response = await client.post('/feedback', feedbackData);
  return response.data;
}

export default { submitQuery, checkHealth, getSystemInfo, submitFeedback };

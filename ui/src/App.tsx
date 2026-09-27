import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Layout } from './components/Layout';
import { ExecutiveDashboard } from './pages/ExecutiveDashboard';
import { ClusterView } from './pages/ClusterView';
import { LiveTopology } from './pages/LiveTopology';
import { IncidentCenter } from './pages/IncidentCenter';
import { AIAnalysis } from './pages/AIAnalysis';
import { RecoveryCenter } from './pages/RecoveryCenter';
import { ChaosEngineering } from './pages/ChaosEngineering';
import { Observability } from './pages/Observability';
import { AuditCenter } from './pages/AuditCenter';
import { MemoryBank } from './pages/MemoryBank';
import { Settings } from './pages/Settings';
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchInterval: 3000,
      refetchIntervalInBackground: false, // Pauses when tab is inactive as requested
      refetchOnWindowFocus: true,
    }
  }
});

class ErrorBoundary extends React.Component<{children: React.ReactNode}, {hasError: boolean, error: Error | null}> {
  constructor(props: {children: React.ReactNode}) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('ErrorBoundary caught an error:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-slate-50 flex items-center justify-center p-4">
          <div className="bg-white border border-slate-200 rounded-xl p-8 max-w-md w-full shadow-lg text-center">
            <h1 className="text-xl font-bold text-slate-800 mb-2">Something went wrong</h1>
            <p className="text-sm text-slate-500 mb-6">The application encountered an unexpected error during the demo.</p>
            <div className="flex gap-3 justify-center">
              <button 
                onClick={() => window.location.reload()}
                className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-sm font-medium transition-colors"
              >
                Reload
              </button>
              <button 
                onClick={() => {
                  fetch('/api/demo/reset', { method: 'POST' }).finally(() => window.location.href = '/');
                }}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-sm font-medium transition-colors"
              >
                Reset demo
              </button>
            </div>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        <ErrorBoundary>
          <Routes>
            <Route path="/" element={<Layout />}>
              <Route path="/" element={<ExecutiveDashboard />} />
              <Route path="/cluster" element={<ClusterView />} />
              <Route path="/topology" element={<LiveTopology />} />
              <Route path="/incidents" element={<IncidentCenter />} />
              <Route path="/ai" element={<AIAnalysis />} />
              <Route path="/recovery" element={<RecoveryCenter />} />
              <Route path="/chaos" element={<ChaosEngineering />} />
              <Route path="/observability" element={<Observability />} />
              <Route path="/audit" element={<AuditCenter />} />
              <Route path="/memory" element={<MemoryBank />} />
              <Route path="/settings" element={<Settings />} />
            </Route>
          </Routes>
        </ErrorBoundary>
      </Router>
    </QueryClientProvider>
  )
}

export default App;

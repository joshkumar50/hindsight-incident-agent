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

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Router>
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
            <Route path="/settings" element={<Settings />} />
          </Route>
        </Routes>
      </Router>
    </QueryClientProvider>
  )
}

export default App;

import { create } from 'zustand'

export interface LastDiagnostic {
  query: string;
  mode: 'recall' | 'fresh';
  durationSeconds: number;
  confidence: number;
  incidentId?: string;
  timestamp: string; // ISO string
}

interface AppState {
  theme: 'dark' | 'light';
  isPollingActive: boolean;
  lastDiagnostic: LastDiagnostic | null;
  toggleTheme: () => void;
  setPollingActive: (active: boolean) => void;
  setLastDiagnostic: (diag: LastDiagnostic) => void;
}

export const useStore = create<AppState>((set) => ({
  theme: 'light',
  isPollingActive: true,
  lastDiagnostic: null,
  toggleTheme: () => set((state) => ({ theme: state.theme === 'dark' ? 'light' : 'dark' })),
  setPollingActive: (active) => set({ isPollingActive: active }),
  setLastDiagnostic: (diag) => set({ lastDiagnostic: diag }),
}));

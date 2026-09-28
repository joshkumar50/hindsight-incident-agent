import { create } from 'zustand'

interface DiagnosticInfo {
  mode: 'recall' | 'fresh';
  durationSeconds: number;
  confidence: number;
}

interface AppState {
  theme: 'dark' | 'light';
  isPollingActive: boolean;
  toggleTheme: () => void;
  setPollingActive: (active: boolean) => void;
  lastDiagnostic: DiagnosticInfo | null;
  setLastDiagnostic: (diag: DiagnosticInfo | null) => void;
}

export const useStore = create<AppState>((set) => ({
  theme: 'dark',
  isPollingActive: true,
  lastDiagnostic: null,
  toggleTheme: () => set((state) => ({ theme: state.theme === 'dark' ? 'light' : 'dark' })),
  setPollingActive: (active) => set({ isPollingActive: active }),
  setLastDiagnostic: (diag) => set({ lastDiagnostic: diag })
}));

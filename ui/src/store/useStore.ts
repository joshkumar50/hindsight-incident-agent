import { create } from 'zustand'

interface AppState {
  theme: 'dark' | 'light';
  isPollingActive: boolean;
  toggleTheme: () => void;
  setPollingActive: (active: boolean) => void;
}

export const useStore = create<AppState>((set) => ({
  theme: 'dark',
  isPollingActive: true,
  toggleTheme: () => set((state) => ({ theme: state.theme === 'dark' ? 'light' : 'dark' })),
  setPollingActive: (active) => set({ isPollingActive: active })
}));

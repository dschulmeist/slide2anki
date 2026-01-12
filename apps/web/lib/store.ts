import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface Settings {
  openaiApiKey: string;
  ollamaBaseUrl: string;
  defaultModel: 'openai' | 'ollama';
  maxCardsPerSlide: number;
  autoDedupe: boolean;
}

interface AppState {
  // Settings
  settings: Settings;
  updateSettings: (settings: Partial<Settings>) => void;

  // Upload state
  uploadProgress: number | null;
  setUploadProgress: (progress: number | null) => void;

  // Current job being viewed
  activeJobId: string | null;
  setActiveJobId: (id: string | null) => void;
}

export const useStore = create<AppState>()(
  persist(
    (set) => ({
      // Settings with defaults
      settings: {
        openaiApiKey: '',
        ollamaBaseUrl: 'http://localhost:11434',
        defaultModel: 'openai',
        maxCardsPerSlide: 5,
        autoDedupe: true,
      },
      updateSettings: (newSettings) =>
        set((state) => ({
          settings: { ...state.settings, ...newSettings },
        })),

      // Upload state
      uploadProgress: null,
      setUploadProgress: (progress) => set({ uploadProgress: progress }),

      // Active job
      activeJobId: null,
      setActiveJobId: (id) => set({ activeJobId: id }),
    }),
    {
      name: 'slide2anki-storage',
      partialize: (state) => ({ settings: state.settings }),
    }
  )
);

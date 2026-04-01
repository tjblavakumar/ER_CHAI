import { create } from 'zustand';
import type {
  ChartState,
  ChatMessage,
  DatasetInfo,
  ProjectSummary,
} from '../types';

export interface AppState {
  // Project
  currentProjectId: string | null;
  projects: ProjectSummary[];

  // Chart
  chartState: ChartState | null;
  chartHistory: ChartState[];
  historyIndex: number;

  // Data
  datasetInfo: DatasetInfo | null;

  // AI Chat
  chatMessages: ChatMessage[];
  chatSessionId: string;

  // Summary
  summaryText: string;

  // UI
  selectedElementId: string | null;
  contextMenuTarget: { elementId: string; x: number; y: number } | null;
  aiChatOpen: boolean;
  isLoading: boolean;

  // Actions
  setChartState: (state: ChartState) => void;
  undo: () => void;
  setProjects: (projects: ProjectSummary[]) => void;
  setCurrentProjectId: (id: string | null) => void;
  addChatMessage: (message: ChatMessage) => void;
  clearChatMessages: () => void;
  setChatSessionId: (id: string) => void;
  setSummaryText: (text: string) => void;
  setSelectedElementId: (id: string | null) => void;
  setContextMenuTarget: (target: { elementId: string; x: number; y: number } | null) => void;
  setAiChatOpen: (open: boolean) => void;
  setIsLoading: (loading: boolean) => void;
  setDatasetInfo: (info: DatasetInfo | null) => void;
  resetForNewChart: () => void;
}

export const useAppStore = create<AppState>((set, get) => ({
  // Project
  currentProjectId: null,
  projects: [],

  // Chart
  chartState: null,
  chartHistory: [],
  historyIndex: -1,

  // Data
  datasetInfo: null,

  // AI Chat
  chatMessages: [],
  chatSessionId: crypto.randomUUID(),

  // Summary
  summaryText: '',

  // UI
  selectedElementId: null,
  contextMenuTarget: null,
  aiChatOpen: false,
  isLoading: false,

  // Actions
  setChartState: (newState: ChartState) => {
    const { chartState, chartHistory, historyIndex } = get();
    if (chartState) {
      // Trim any forward history beyond current index, then push current state
      const trimmed = chartHistory.slice(0, historyIndex + 1);
      set({
        chartState: newState,
        chartHistory: [...trimmed, chartState],
        historyIndex: trimmed.length,
      });
    } else {
      set({ chartState: newState });
    }
  },

  undo: () => {
    const { chartHistory, historyIndex } = get();
    if (historyIndex < 0 || chartHistory.length === 0) return;
    set({
      chartState: chartHistory[historyIndex],
      historyIndex: historyIndex - 1,
    });
  },

  setProjects: (projects) => set({ projects }),
  setCurrentProjectId: (id) => set({ currentProjectId: id }),

  addChatMessage: (message) =>
    set((s) => ({ chatMessages: [...s.chatMessages, message] })),
  clearChatMessages: () => set({ chatMessages: [] }),
  setChatSessionId: (id) => set({ chatSessionId: id }),

  setSummaryText: (text) => set({ summaryText: text }),

  setSelectedElementId: (id) => set({ selectedElementId: id }),
  setContextMenuTarget: (target) => set({ contextMenuTarget: target }),
  setAiChatOpen: (open) => set({ aiChatOpen: open }),
  setIsLoading: (loading) => set({ isLoading: loading }),

  setDatasetInfo: (info) => set({ datasetInfo: info }),

  resetForNewChart: () =>
    set({
      chartState: null,
      chartHistory: [],
      historyIndex: -1,
      chatMessages: [],
      chatSessionId: crypto.randomUUID(),
      summaryText: '',
      datasetInfo: null,
      selectedElementId: null,
      contextMenuTarget: null,
    }),
}));

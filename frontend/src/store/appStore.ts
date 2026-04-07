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
  currentProjectName: string | null;
  projects: ProjectSummary[];

  // Chart
  chartState: ChartState | null;
  chartHistory: ChartState[];
  historyIndex: number;

  // Data
  datasetInfo: DatasetInfo | null;
  datasetRows: Record<string, unknown>[] | null;

  // AI Chat
  chatMessages: ChatMessage[];
  chatSessionId: string;

  // Summary
  summaryText: string;

  // Reference image
  referenceImageFile: File | null;

  // UI
  selectedElementId: string | null;
  contextMenuTarget: { elementId: string; x: number; y: number } | null;
  aiChatOpen: boolean;
  isLoading: boolean;
  loadingMessage: string;

  // Actions
  setChartState: (state: ChartState) => void;
  undo: () => void;
  setProjects: (projects: ProjectSummary[]) => void;
  setCurrentProjectId: (id: string | null) => void;
  setCurrentProjectName: (name: string | null) => void;
  addChatMessage: (message: ChatMessage) => void;
  clearChatMessages: () => void;
  setChatSessionId: (id: string) => void;
  setSummaryText: (text: string) => void;
  setSelectedElementId: (id: string | null) => void;
  setContextMenuTarget: (target: { elementId: string; x: number; y: number } | null) => void;
  setAiChatOpen: (open: boolean) => void;
  setIsLoading: (loading: boolean) => void;
  setLoadingMessage: (msg: string) => void;
  setDatasetInfo: (info: DatasetInfo | null) => void;
  setDatasetRows: (rows: Record<string, unknown>[] | null) => void;
  setReferenceImageFile: (file: File | null) => void;
  resetForNewChart: () => void;
}

export const useAppStore = create<AppState>((set, get) => ({
  // Project
  currentProjectId: null,
  currentProjectName: null,
  projects: [],

  // Chart
  chartState: null,
  chartHistory: [],
  historyIndex: -1,

  // Data
  datasetInfo: null,
  datasetRows: null,

  // AI Chat
  chatMessages: [],
  chatSessionId: crypto.randomUUID(),

  // Summary
  summaryText: '',

  // Reference image
  referenceImageFile: null,

  // UI
  selectedElementId: null,
  contextMenuTarget: null,
  aiChatOpen: false,
  isLoading: false,
  loadingMessage: '',

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
  setCurrentProjectName: (name) => set({ currentProjectName: name }),

  addChatMessage: (message) =>
    set((s) => ({ chatMessages: [...s.chatMessages, message] })),
  clearChatMessages: () => set({ chatMessages: [] }),
  setChatSessionId: (id) => set({ chatSessionId: id }),

  setSummaryText: (text) => set({ summaryText: text }),

  setSelectedElementId: (id) => set({ selectedElementId: id }),
  setContextMenuTarget: (target) => set({ contextMenuTarget: target }),
  setAiChatOpen: (open) => set({ aiChatOpen: open }),
  setIsLoading: (loading) => set({ isLoading: loading }),
  setLoadingMessage: (msg) => set({ loadingMessage: msg }),

  setDatasetInfo: (info) => set({ datasetInfo: info }),
  setDatasetRows: (rows) => set({ datasetRows: rows }),
  setReferenceImageFile: (file) => set({ referenceImageFile: file }),

  resetForNewChart: () =>
    set({
      chartState: null,
      chartHistory: [],
      historyIndex: -1,
      chatMessages: [],
      chatSessionId: crypto.randomUUID(),
      summaryText: '',
      datasetInfo: null,
      datasetRows: null,
      selectedElementId: null,
      contextMenuTarget: null,
      currentProjectName: null,
      referenceImageFile: null,
    }),
}));

import { create } from 'zustand';
import { conceptApi } from '../services/api';
import type { ChatMessage } from '../components/conversation/types';
import type { ChatResponse } from '../services/dataIntelligenceApi';

// ---------------------------------------------------------------------------
// Session 类型（FreePlanChat 会话）
// ---------------------------------------------------------------------------
const SESSIONS_STORAGE_KEY = 'di_sessions_freeplan_v1';

export type Session = {
  id: string;
  title: string;
  messages: ChatMessage[];
  confirmed: Record<string, any>;
  flags: Record<string, boolean>;
  thinkStream: any[];
  pendingCandidates: any[];
  lastResponse: ChatResponse | null;
  goal?: string;
  currentTask?: string;
  liveStatus?: string;
  liveMetaInfo?: string;
  finalTokens: string[];
  finalAnswer?: string;
  recommendations?: Array<{ label: string; shortcut?: string }>;
  createdAt: number;
};

export function newSession(): Session {
  const id = `free_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`;
  return { id, title: '新对话', messages: [], confirmed: {}, flags: {}, thinkStream: [], pendingCandidates: [], lastResponse: null, finalTokens: [], createdAt: Date.now() };
}

function loadSessions(): Session[] {
  try {
    const raw = localStorage.getItem(SESSIONS_STORAGE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw) as Session[];
      if (Array.isArray(parsed) && parsed.length > 0) return parsed;
    }
  } catch { /* ignore */ }
  return [newSession()];
}

function persistSessions(sessions: Session[]) {
  try { localStorage.setItem(SESSIONS_STORAGE_KEY, JSON.stringify(sessions)); } catch { /* ignore */ }
}

// ---------------------------------------------------------------------------

interface AppState {
  concepts: any[];
  selectedNode: any | null;
  canvasMode: 'tree' | 'force' | 'neo4j' | 'matrix' | 'quad';
  /** 当前激活的页签 menuKey，供画布组件监听做 resize（隐藏暂停重绘、激活刷新尺寸） */
  activeMenuKey: string | null;
  isMappingModalVisible: boolean;
  isModelingModalVisible: boolean;
  modelingModalMode: 'master' | 'activity';
  modelingInitialKey: string | null;
  mappingFilterEntityId: string | null;
  mappingJumpTab: string | null;
  relationHighlight: {
    linkId: string;
    masterEntityId: string;
    activityEntityId: string;
  } | null;

  // Session 切片
  sessions: Session[];
  activeSessionId: string;
  setSessions: (updater: Session[] | ((prev: Session[]) => Session[])) => void;
  setActiveSessionId: (id: string) => void;
  updateSession: (id: string, patch: Partial<Session>) => void;
  createNewSession: () => string;
  deleteSessionById: (id: string) => void;
  renameSessionById: (id: string, title: string) => void;

  fetchConcepts: () => Promise<void>;
  setSelectedNode: (node: any) => void;
  setCanvasMode: (mode: 'tree' | 'force' | 'neo4j' | 'matrix' | 'quad') => void;
  setActiveMenuKey: (key: string | null) => void;
  setMappingModalVisible: (visible: boolean) => void;
  setMappingFilterEntityId: (entityId: string | null) => void;
  setMappingJumpTab: (tab: string | null) => void;
  setModelingModalVisible: (visible: boolean, mode?: 'master' | 'activity', initialKey?: string | null) => void;
  setRelationHighlight: (payload: { linkId: string; masterEntityId: string; activityEntityId: string } | null) => void;
}

export const useStore = create<AppState>((set) => {
  const _initialSessions = loadSessions();
  return {
  concepts: [],
  selectedNode: null,
  canvasMode: 'tree',
  activeMenuKey: null,
  isMappingModalVisible: false,
  isModelingModalVisible: false,
  modelingModalMode: 'master',
  modelingInitialKey: null,
  mappingFilterEntityId: null,
  mappingJumpTab: null,
  relationHighlight: null,

  // Session 切片
  sessions: _initialSessions,
  activeSessionId: _initialSessions[0]?.id || '',
  setSessions: (updater) => set((state) => {
    const next = typeof updater === 'function' ? (updater as (prev: Session[]) => Session[])(state.sessions) : updater;
    persistSessions(next);
    return { sessions: next };
  }),
  setActiveSessionId: (id) => set({ activeSessionId: id }),
  updateSession: (id, patch) => set((state) => {
    const next = state.sessions.map((s) => (s.id === id ? { ...s, ...patch } : s));
    persistSessions(next);
    return { sessions: next };
  }),
  createNewSession: () => {
    const s = newSession();
    set((state) => {
      const next = [s, ...state.sessions];
      persistSessions(next);
      return { sessions: next, activeSessionId: s.id };
    });
    return s.id;
  },
  deleteSessionById: (id) => set((state) => {
    const filtered = state.sessions.filter((s) => s.id !== id);
    if (filtered.length === 0) {
      const fresh = newSession();
      persistSessions([fresh]);
      return { sessions: [fresh], activeSessionId: fresh.id };
    }
    persistSessions(filtered);
    const newActive = id === state.activeSessionId ? filtered[0].id : state.activeSessionId;
    return { sessions: filtered, activeSessionId: newActive };
  }),
  renameSessionById: (id, title) => set((state) => {
    const next = state.sessions.map((s) => (s.id === id ? { ...s, title: title.trim() || '未命名对话' } : s));
    persistSessions(next);
    return { sessions: next };
  }),

  fetchConcepts: async () => {
    try {
      const response = await conceptApi.getConcepts();
      const newConcepts = response.data;
      set((state) => {
        const newState: any = { concepts: newConcepts };
        // 如果当前有选中的节点，同步更新它
        if (state.selectedNode) {
          const updatedNode = newConcepts.find((c: any) => c.id === state.selectedNode.id);
          if (updatedNode) {
            newState.selectedNode = updatedNode;
          }
        }
        return newState;
      });
    } catch (error) {
      console.error('Failed to fetch concepts:', error);
    }
  },

  setSelectedNode: (node) => set({ selectedNode: node }),
  setCanvasMode: (mode) => set({ canvasMode: mode }),
  setActiveMenuKey: (key) => set({ activeMenuKey: key }),
  setMappingModalVisible: (visible) => set({ isMappingModalVisible: visible }),
  setMappingFilterEntityId: (entityId) => set({ mappingFilterEntityId: entityId }),
  setMappingJumpTab: (tab) => set({ mappingJumpTab: tab }),
  setModelingModalVisible: (visible, mode = 'master', initialKey = null) => 
    set({ isModelingModalVisible: visible, modelingModalMode: mode, modelingInitialKey: initialKey }),
  setRelationHighlight: (payload) => set({ relationHighlight: payload }),
  };
});

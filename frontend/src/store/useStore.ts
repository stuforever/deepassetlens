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
  /** IA 件批2 新增：创建时写入（值源=ExpertChat 现有 slug）；旧会话读入归 'wenshu'（终审裁定④） */
  expertId: ExpertId;
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

/** IA 件批2：会话所属专家（三专家门户；h5 组不走本 store——vendor sessions API 单列） */
export type ExpertId = 'wenshu' | 'tutor' | 'tutor-h5';

export function newSession(expertId: ExpertId = 'wenshu'): Session {
  const id = `free_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`;
  return { id, title: '新对话', expertId, messages: [], confirmed: {}, flags: {}, thinkStream: [], pendingCandidates: [], lastResponse: null, finalTokens: [], createdAt: Date.now() };
}

function loadSessions(): Session[] {
  try {
    const raw = localStorage.getItem(SESSIONS_STORAGE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw) as Session[];
      if (Array.isArray(parsed) && parsed.length > 0) {
        // IA 件批2 迁移规则（终审裁定④）：旧会话无 expertId → 默认 'wenshu'（诚实账8：不做猜测式迁移）
        return parsed.map((s) => ({ ...s, expertId: s.expertId || 'wenshu' }));
      }
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
  canvasMode: 'force' | 'neo4j' | 'matrix' | 'quad';
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
  createNewSession: (expertId?: ExpertId) => string;
  deleteSessionById: (id: string) => Promise<boolean>;
  renameSessionById: (id: string, title: string) => void;
  deleteMessage: (sessionId: string, msgId: string) => void;
  clearMessages: (sessionId: string) => Promise<boolean>;

  fetchConcepts: () => Promise<void>;
  setSelectedNode: (node: any) => void;
  setCanvasMode: (mode: 'force' | 'neo4j' | 'matrix' | 'quad') => void;
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
  canvasMode: 'force',
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
  createNewSession: (expertId) => {
    const s = newSession(expertId || 'wenshu');
    set((state) => {
      const next = [s, ...state.sessions];
      persistSessions(next);
      return { sessions: next, activeSessionId: s.id };
    });
    return s.id;
  },
  deleteSessionById: async (id) => {
    // v3.6: await 后端清除（fire-and-forget 导致 checkpoint 残留无反馈）
    // F2-fix: 与 clearMessages 同策略--后端失败时不删本地，返回 false
    let backendOk = true;
    try {
      const { dataIntelligenceApi } = await import('../services/dataIntelligenceApi');
      const resp = await dataIntelligenceApi.clearFreeplanMemory(id);
      if (resp && resp.cleared === false) {
        backendOk = false;
        console.warn('[deleteSessionById] 后端返回 cleared:false，checkpoint 未清除', resp);
      }
    } catch (e) {
      backendOk = false;
      console.error('[deleteSessionById] 后端 checkpoint 清除失败:', e);
    }
    // F2-fix: 后端失败时不删本地会话（防"页面删除但后端 checkpoint 残留"）
    if (!backendOk) {
      return false;
    }
    set((state) => {
      const filtered = state.sessions.filter((s) => s.id !== id);
      if (filtered.length === 0) {
        const fresh = newSession();
        persistSessions([fresh]);
        return { sessions: [fresh], activeSessionId: fresh.id };
      }
      persistSessions(filtered);
      const newActive = id === state.activeSessionId ? filtered[0].id : state.activeSessionId;
      return { sessions: filtered, activeSessionId: newActive };
    });
    return true;
  },
  renameSessionById: (id, title) => set((state) => {
    const next = state.sessions.map((s) => (s.id === id ? { ...s, title: title.trim() || '未命名对话' } : s));
    persistSessions(next);
    return { sessions: next };
  }),
  // 删除单条消息(对话/输出)
  deleteMessage: (sessionId, msgId) => set((state) => {
    const next = state.sessions.map((s) => s.id === sessionId
      ? { ...s, messages: s.messages.filter((m) => m.id !== msgId) }
      : s);
    persistSessions(next);
    return { sessions: next };
  }),
  // 清空当前会话消息历史(保留会话壳) + 同步删除后端 checkpoint + 重置全部业务字段
  // v3.6: 等后端清除成功再清本地（评审：fire-and-forget 导致 checkpoint 残留无反馈）
  clearMessages: async (sessionId) => {
    let backendOk = true;
    try {
      const { dataIntelligenceApi } = await import('../services/dataIntelligenceApi');
      const resp = await dataIntelligenceApi.clearFreeplanMemory(sessionId);
      // P2-1: 检查 cleared 字段（后端可能返回 200 但 cleared:false）
      if (resp && resp.cleared === false) {
        backendOk = false;
        console.warn('[clearMessages] 后端返回 cleared:false，checkpoint 未清除', resp);
      }
    } catch (e) {
      backendOk = false;
      console.error('[clearMessages] 后端 checkpoint 清除失败:', e);
    }
    // F2: 后端失败时不清本地（防"页面已清空但后端checkpoint残留"导致下一轮带旧记忆）
    if (!backendOk) {
      return false;
    }
    set((state) => {
      const next = state.sessions.map((s) => s.id === sessionId
        // 重置全部业务字段，不只 messages/thinkStream（防 confirmed/flags/goal 等残留）
        ? {
            ...s,
            messages: [],
            thinkStream: [],
            lastResponse: null,
            recommendations: [],
            confirmed: {},
            flags: {},
            pendingCandidates: [],
            finalTokens: [],
            finalAnswer: undefined,
            goal: undefined,
            currentTask: undefined,
            liveStatus: undefined,
            liveMetaInfo: undefined,
          }
        : s);
      persistSessions(next);
      return { sessions: next };
    });
    return true;
  },

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

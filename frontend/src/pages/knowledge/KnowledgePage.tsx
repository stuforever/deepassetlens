/**
 * 知识中心页壳（IA批4 4.3 复刻——源 DeepTutor web/components/knowledge/KnowledgePage.tsx 1:1）。
 * 视图状态机 home/kb/engine + ?kb=/?engine= 深链同步；数据经 useKnowledgeBases；
 * ④语义迁移锚点在子件内（KnowledgeHome 紫徽标/KnowledgeBaseDetail tutor 分支/KbDocumentsSection 通道卡）。
 */
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Button, Spin } from 'antd';
import { useKnowledgeBases } from './useKnowledgeBases';
import { updateRagProviderMode } from './knowledge-api';
import KnowledgeBaseDetail from './KnowledgeBaseDetail';
import KnowledgeHome from './KnowledgeHome';
import EngineDetail from './EngineDetail';
import CreateKbModal from './CreateKbModal';
import PageIndexSettingsModal from './PageIndexSettingsModal';

const KnowledgePage: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const initialKb = searchParams.get('kb');
  const initialEngine = searchParams.get('engine');

  const {
    kbs: allKbs,
    providers,
    uploadPolicy,
    loading,
    error,
    setError,
    tasksByKb,
    historyByKb,
    clearHistory,
    refresh,
    createKb,
    uploadFiles,
    setDefault,
    reindex,
    retry,
    deleteKb,
    connectObsidian,
    connectLinkedFolder,
    connectLightRagServer,
  } = useKnowledgeBases();

  // Connected subagents are stored as ``type: subagent`` KBs so the chat
  // composer can select them, but they are agents, not knowledge bases — keep
  // them out of the Knowledge Center entirely.
  const kbs = useMemo(
    () => allKbs.filter((kb) => (kb.metadata as Record<string, unknown> | undefined)?.type !== 'subagent'),
    [allKbs],
  );

  const [explicitSelection, setExplicitSelection] = useState<string | null>(initialKb);
  const [selectedEngineId, setSelectedEngineId] = useState<string | null>(initialEngine);
  const [createOpen, setCreateOpen] = useState(false);
  const [createPreset, setCreatePreset] = useState<{ mode: 'new' | 'link'; source?: string } | null>(null);
  const [pipelineOpen, setPipelineOpen] = useState(false);

  const openCreate = useCallback(() => {
    setCreatePreset(null);
    setCreateOpen(true);
  }, []);
  // Obsidian lives in the engines grid for discoverability but routes through
  // the unified create flow, pre-set to "link existing → Obsidian".
  const openObsidian = useCallback(() => {
    setCreatePreset({ mode: 'link', source: 'obsidian' });
    setCreateOpen(true);
  }, []);
  // Lands on the Overview console unless deep-linked to a KB or an engine.
  const [view, setView] = useState<'home' | 'kb' | 'engine'>(
    initialEngine ? 'engine' : initialKb ? 'kb' : 'home',
  );

  const openKb = useCallback((name: string) => {
    setExplicitSelection(name);
    setView('kb');
  }, []);

  const openEngine = useCallback((id: string) => {
    setSelectedEngineId(id);
    setView('engine');
  }, []);

  // Derive the effective selection: respect the user's pick if it still
  // exists, otherwise fall back to the default KB (or the first one).
  const selectedKbName = useMemo<string | null>(() => {
    if (explicitSelection && kbs.some((kb) => kb.name === explicitSelection)) {
      return explicitSelection;
    }
    if (!kbs.length) return null;
    return (kbs.find((kb) => kb.is_default) ?? kbs[0]).name;
  }, [explicitSelection, kbs]);

  const selectedKb = useMemo(
    () => kbs.find((kb) => kb.name === selectedKbName) ?? null,
    [kbs, selectedKbName],
  );

  // The effective engine selection: respect the pick if it still exists.
  const selectedProvider = useMemo(
    () => providers.find((p) => p.id === selectedEngineId) ?? null,
    [providers, selectedEngineId],
  );

  // Keep ?kb / ?engine in sync with the effective selection so deep links work.
  const urlKb = view === 'kb' ? selectedKbName : null;
  const urlEngine = view === 'engine' ? selectedProvider?.id ?? null : null;
  useEffect(() => {
    if (searchParams.get('kb') === urlKb && searchParams.get('engine') === urlEngine) {
      return;
    }
    const params = new URLSearchParams(Array.from(searchParams.entries()));
    if (urlKb) params.set('kb', urlKb);
    else params.delete('kb');
    if (urlEngine) params.set('engine', urlEngine);
    else params.delete('engine');
    const search = params.toString();
    navigate(search ? `?${search}` : '?', { replace: true });
  }, [navigate, searchParams, urlKb, urlEngine]);

  const handleCreate = useCallback(
    async (params: { name: string; provider: string; files: File[] }) => {
      try {
        await createKb(params);
        openKb(params.name);
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err));
        throw err;
      }
    },
    [createKb, openKb, setError],
  );

  const handleSetDefault = useCallback(
    async (name: string) => {
      try {
        await setDefault(name);
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err));
      }
    },
    [setDefault, setError],
  );

  const handleDelete = useCallback(
    async (name: string) => {
      // 源语义：window.confirm 文案「Delete knowledge base "{{name}}"?」→ antd 确认框等价
      const confirmed = await new Promise<boolean>((resolve) => {
        import('antd').then(({ Modal }) => {
          Modal.confirm({
            title: `删除知识库「${name}」？`,
            okText: '删除',
            okButtonProps: { danger: true },
            cancelText: '取消',
            onOk: () => resolve(true),
            onCancel: () => resolve(false),
          });
        });
      });
      if (!confirmed) return;
      try {
        await deleteKb(name);
        if (explicitSelection === name) {
          setExplicitSelection(null);
          setView('home');
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err));
      }
    },
    [deleteKb, explicitSelection, setError],
  );

  const handleUpload = useCallback(
    async (kbName: string, files: File[]) => {
      try {
        await uploadFiles(kbName, files);
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err));
        throw err;
      }
    },
    [setError, uploadFiles],
  );

  const handleReindex = useCallback(
    async (kbName: string) => {
      try {
        await reindex(kbName);
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err));
      }
    },
    [reindex, setError],
  );

  const handleRetry = useCallback(
    async (kbName: string) => {
      try {
        await retry(kbName);
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err));
      }
    },
    [retry, setError],
  );

  const handleSelectMode = useCallback(
    async (id: string, mode: string) => {
      try {
        await updateRagProviderMode(id, mode);
        await refresh();
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err));
      }
    },
    [refresh, setError],
  );

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', background: 'var(--background, #fff)' }}>
      {error && (
        <div
          style={{
            display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12,
            borderBottom: '1px solid #fecaca', background: '#fef2f2', padding: '8px 16px',
            fontSize: 12.5, color: '#b91c1c',
          }}
        >
          <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{error}</span>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Button size="small" onClick={() => void refresh({ force: true })}>重试</Button>
            <Button size="small" type="text" onClick={() => setError(null)}>忽略</Button>
          </div>
        </div>
      )}

      {loading ? (
        <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <Spin />
        </div>
      ) : (
        <div style={{ display: 'flex', flex: 1, minHeight: 0 }}>
          {view === 'home' ? (
            <KnowledgeHome
              kbs={kbs}
              providers={providers}
              onOpenKb={openKb}
              onOpenEngine={openEngine}
              onCreate={openCreate}
              onConnectObsidian={openObsidian}
            />
          ) : view === 'engine' && selectedProvider ? (
            <EngineDetail
              provider={selectedProvider}
              kbs={kbs}
              onBack={() => setView('home')}
              onOpenKb={openKb}
              onSelectMode={handleSelectMode}
              onChanged={() => void refresh({ force: true })}
              onError={(message) => setError(message)}
            />
          ) : view === 'engine' ? (
            // Selected engine vanished (e.g. provider list changed); bounce home.
            <KnowledgeHome
              kbs={kbs}
              providers={providers}
              onOpenKb={openKb}
              onOpenEngine={openEngine}
              onCreate={openCreate}
              onConnectObsidian={openObsidian}
            />
          ) : (
            <KnowledgeBaseDetail
              kb={selectedKb}
              uploadPolicy={uploadPolicy}
              task={selectedKb ? tasksByKb[selectedKb.name] : undefined}
              history={selectedKb ? historyByKb[selectedKb.name] ?? [] : []}
              onCreate={openCreate}
              onUpload={handleUpload}
              onReindex={handleReindex}
              onRetry={handleRetry}
              onSetDefault={handleSetDefault}
              onDelete={handleDelete}
              onClearHistory={clearHistory}
              onBack={() => setView('home')}
            />
          )}
        </div>
      )}

      <CreateKbModal
        isOpen={createOpen}
        onClose={() => setCreateOpen(false)}
        providers={providers}
        uploadPolicy={uploadPolicy}
        onCreate={handleCreate}
        onConnectLinkedFolder={connectLinkedFolder}
        onConnectObsidian={connectObsidian}
        onConnectLightRagServer={connectLightRagServer}
        initialMode={createPreset?.mode}
        initialSource={createPreset?.source}
        onConfigureProvider={() => {
          setCreateOpen(false);
          setPipelineOpen(true);
        }}
      />

      <PageIndexSettingsModal
        isOpen={pipelineOpen}
        onClose={() => setPipelineOpen(false)}
        onSaved={() => void refresh({ force: true })}
      />
    </div>
  );
};

export default KnowledgePage;

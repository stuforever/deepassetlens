"use client";

import { useState, useEffect, useCallback } from "react";
import { useTranslation } from "react-i18next";
import { StickyNote, Plus, Loader2, NotebookPen } from "lucide-react";
import { apiUrl } from "../../../../../lib/api";
import { notify } from "../../../../../lib/notifications";
import { TabExportToolbar } from "../TabExportToolbar";

interface NotebookRecord {
  id?: string;
  title?: string;
  summary?: string;
  output?: string;
  user_query?: string;
}
interface NotebookInfo {
  id: string;
  name: string;
  description?: string;
  record_count: number;
}
interface NoteView {
  id: string;
  notebook: string;
  title: string;
  content: string;
}

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(apiUrl(path), init);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json() as Promise<T>;
}

/** 章节学习笔记：基于工程 Notebook 模块（按章节归档笔记，可增删）。 */
export function NotesTab({ chapterId, chapterName }: { chapterId: string; chapterName: string }) {
  const { t } = useTranslation();
  const [notes, setNotes] = useState<NoteView[]>([]);
  const [loading, setLoading] = useState(true);
  const [newNote, setNewNote] = useState("");
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const list = await api<{ notebooks: NotebookInfo[] }>("/api/v1/notebook/list");
      const notebooks = list.notebooks || [];
      const views: NoteView[] = [];
      // 优先本章笔记本
      const mine = notebooks.filter((n) => n.name.includes(chapterName));
      const others = notebooks.filter((n) => !n.name.includes(chapterName));
      const targets = [...mine, ...others.slice(0, 5)];
      for (const nb of targets) {
        try {
          const detail = await api<{ id: string; name: string; records?: NotebookRecord[] }>(
            `/api/v1/notebook/${nb.id}`,
          );
          for (const r of detail.records || []) {
            const content = r.summary || r.output || r.user_query || "";
            if (content) {
              views.push({
                id: r.id || `${nb.id}-${views.length}`,
                notebook: detail.name,
                title: r.title || detail.name,
                content,
              });
            }
          }
        } catch {
          // 跳过打不开的笔记本
        }
      }
      setNotes(views);
    } catch {
      setNotes([]);
    }
    setLoading(false);
  }, [chapterName]);

  useEffect(() => {
    load();
  }, [load]);

  const save = async () => {
    if (!newNote.trim()) return;
    setSaving(true);
    try {
      // 找到或创建本章笔记本
      let nbId: string | null = null;
      try {
        const list = await api<{ notebooks: NotebookInfo[] }>("/api/v1/notebook/list");
        nbId = (list.notebooks || []).find((n) => n.name === chapterName)?.id || null;
      } catch {
        nbId = null;
      }
      if (!nbId) {
        const created = await api<{ success: boolean; notebook: { id: string } }>(
          "/api/v1/notebook/create",
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ name: chapterName, description: t("Learning notes for chapter \"{{chapter}}\"", { chapter: chapterName }), color: "#3B82F6", icon: "book" }),
          },
        );
        nbId = created.notebook?.id || null;
      }
      if (!nbId) throw new Error("无法创建笔记本");
      await api("/api/v1/notebook/add_record", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          notebook_ids: [nbId],
          record_type: "chat",
          title: `${chapterName} - ${t("Study note")}`,
          summary: "",
          user_query: "",
          output: newNote,
          metadata: { chapter_id: chapterId, chapter_name: chapterName },
        }),
      });
      notify.success(t("Note saved"));
      setNewNote("");
      await load();
    } catch {
      notify.error(t("Save failed"));
    }
    setSaving(false);
  };

  if (loading)
    return (
      <div className="p-4 flex items-center gap-2 text-muted-foreground">
        <Loader2 className="w-4 h-4 animate-spin" /> {t("Loading notes...")}
      </div>
    );

  return (
    <div className="p-4 space-y-3" data-testid="tab-panel-notes">
      <TabExportToolbar chapterId={chapterId} tab="notes" />
      {/* 快速记笔记 */}
      <div className="p-3 rounded-lg border bg-card">
        <div className="flex items-center gap-2 mb-2">
          <Plus className="w-4 h-4 text-primary" />
          <span className="text-sm font-medium">{t("Quick Note")}</span>
        </div>
        <textarea
          value={newNote}
          onChange={(e) => setNewNote(e.target.value)}
          placeholder={t("Record your learning notes about \"{{chapter}}\"...", { chapter: chapterName })}
          data-testid="note-input"
          className="w-full min-h-[80px] p-2 rounded border bg-transparent text-sm resize-y focus:outline-none focus:ring-2 focus:ring-primary/40"
        />
        <button
          onClick={save}
          disabled={saving || !newNote.trim()}
          data-testid="note-save"
          className="mt-2 px-3 py-1 rounded bg-primary text-primary-foreground text-sm hover:opacity-90 disabled:opacity-50"
        >
          {saving ? t("Saving...") : t("Save")}
        </button>
      </div>

      {/* 笔记列表 */}
      <div>
        <div className="text-sm text-muted-foreground mb-2">{t("{{count}} notes", { count: notes.length })}</div>
        {notes.length === 0 ? (
          <div className="p-4 rounded border bg-muted/30 text-center">
            <StickyNote className="w-8 h-8 mx-auto text-muted-foreground mb-2" />
            <p className="text-sm text-muted-foreground">{t("No notes yet. Record your learning notes above.")}</p>
          </div>
        ) : (
          <div className="space-y-2" data-testid="note-list">
            {notes.map((n) => (
              <div key={n.id} className="p-3 rounded-lg border bg-card" data-testid="note-item">
                <div className="flex items-center gap-2 mb-1">
                  <NotebookPen className="w-3.5 h-3.5 text-primary" />
                  <span className="font-medium text-sm">{n.title}</span>
                  <span className="text-[10px] text-muted-foreground ml-auto">{n.notebook}</span>
                </div>
                <p className="text-xs text-muted-foreground whitespace-pre-wrap line-clamp-4">{n.content}</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

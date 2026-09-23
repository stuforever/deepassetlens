"use client";

import { useEffect, useState, useCallback } from "react";
import { Select as AntSelect } from "antd"; // R5批①：原生 select → antd（R#2 续批，testid 保留）
import { Presentation, ChevronDown, Loader2 } from "lucide-react";
import { useTranslation } from "react-i18next";
import type { ChapterOverview, Grade7Resource } from "../../../../../lib/self-learning-api";
import { fetchChapterResources } from "../../../../../lib/self-learning-api";
import { TabExportToolbar } from "../TabExportToolbar";

export function CoursewareTab({ overview, chapterId, chapterName }: {
  overview: ChapterOverview;
  chapterId: string;
  chapterName: string;
}) {
  const { t } = useTranslation();
  const [courseware, setCourseware] = useState<Grade7Resource[]>([]);
  const [loading, setLoading] = useState(true);
  // 桌面端与 H5 对齐的三分支渲染：html→iframe / .mp4→video / 其他(pdf)→新标签打开
  const [selectedId, setSelectedId] = useState<string>("");
  // 互动课件区块可折叠：默认展开；点标题收起/展开，避免多个课件把内容挡住
  const [cwCollapsed, setCwCollapsed] = useState(false);

  const load = useCallback(() => {
    setLoading(true);
    fetchChapterResources(chapterId)
      .then((d) => setCourseware(d.courseware || []))
      .catch(() => setCourseware([]))
      .finally(() => setLoading(false));
  }, [chapterId]);

  useEffect(() => { load(); }, [load]);

  return (
    <div className="p-4 space-y-4" data-testid="tab-panel-courseware">
      <TabExportToolbar chapterId={chapterId} tab="courseware" />
      {/* 互动课件（英语课本每节的 HTML 课件）——可折叠，下拉与标题同行 */}
      <section>
        <div className="flex items-center gap-2 mb-2">
          <button
            type="button"
            onClick={() => setCwCollapsed((v) => !v)}
            data-testid="courseware-toggle"
            className="flex items-center gap-2 shrink-0 cursor-pointer"
          >
            <Presentation className="w-4 h-4 text-primary" />
            <h3 className="font-semibold text-sm whitespace-nowrap">{t("Interactive courseware ({{count}})", { count: courseware.length })}</h3>
            <ChevronDown className={`w-4 h-4 text-muted-foreground transition-transform ${cwCollapsed ? "" : "rotate-180"}`} />
          </button>
          {!cwCollapsed && !loading && courseware.length > 0 && (
            <AntSelect
              value={selectedId}
              onChange={(v) => setSelectedId(v)}
              data-testid="courseware-select"
              size="small"
              style={{ flex: 1, minWidth: 0 }}
              options={[
                { value: "", label: t("Select a courseware...") },
                ...courseware.map((c) => ({ value: c.id, label: c.title })),
              ]}
            />
          )}
        </div>
        {cwCollapsed ? (
          <div className="px-3 py-2.5 rounded-lg border bg-muted/30 text-sm text-muted-foreground">
            {t("{{count}} interactive courseware", { count: courseware.length })}
          </div>
        ) : loading ? (
          <div className="p-4 flex items-center justify-center text-muted-foreground">
            <Loader2 className="w-4 h-4 animate-spin mr-2" /> {t("Loading...")}
          </div>
        ) : courseware.length === 0 ? (
          <div className="p-4 rounded border bg-muted/30 text-center">
            <p className="text-sm text-muted-foreground">{t("No imported interactive courseware for this chapter.")}</p>
          </div>
        ) : (
          (() => {
            const c = courseware.find((x) => x.id === selectedId);
            if (!c) return null;
            // ① HTML 互动课件 → iframe
            if (c.html) {
              return (
                <div className="mt-1 rounded-lg border overflow-hidden" data-testid="courseware-viewer">
                  <iframe
                    src={c.html}
                    title={t("courseware")}
                    className="w-full h-[70vh] bg-white"
                    sandbox="allow-scripts allow-same-origin allow-modals allow-forms allow-pointer-lock"
                  />
                </div>
              );
            }
            // ② mp4 精讲视频/课文动画 → 内嵌播放器（与 H5 一致）
            if (c.page && /\.mp4(\?|$)/i.test(c.page)) {
              return (
                <div className="mt-1 rounded-lg border overflow-hidden bg-black" data-testid="courseware-viewer">
                  <video
                    controls
                    preload="metadata"
                    src={c.page}
                    className="w-full max-h-[70vh]"
                  />
                </div>
              );
            }
            // ③ PDF 讲义等 → 新标签打开
            if (c.page) {
              return (
                <div className="mt-1 p-3 rounded-lg border bg-muted/30 text-sm flex items-center gap-2" data-testid="courseware-viewer">
                  <span className="text-muted-foreground">该课件为文档，</span>
                  <a href={c.page} target="_blank" rel="noreferrer" className="text-primary underline font-medium">
                    点击在新标签页打开「{c.title}」
                  </a>
                </div>
              );
            }
            return null;
          })()
        )}
      </section>
    </div>
  );
}

"use client";

import { useEffect, useState, useCallback } from "react";
import { useTranslation } from "react-i18next";
import { Mic, Play, Shapes, Loader2 } from "lucide-react";
import { fetchChapterResources } from "../../../../../lib/self-learning-api";
import type { Grade7Resource } from "../../../../../lib/self-learning-api";
import { TabExportToolbar } from "../TabExportToolbar";

/** 语音视频：数学章节展示「可拖拽图形演示」(GeoGebra)，其余学科展示语音领读/视频资源。 */
export function VoiceVideoTab({ chapterId, chapterName }: {
  chapterId: string;
  chapterName: string;
}) {
  const { t } = useTranslation();
  const [voices, setVoices] = useState<Grade7Resource[]>([]);
  const [figures, setFigures] = useState<Grade7Resource[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeVoice, setActiveVoice] = useState<string | null>(null);
  const [activeFig, setActiveFig] = useState<string | null>(null);

  const load = useCallback(() => {
    setLoading(true);
    fetchChapterResources(chapterId)
      .then((d) => {
        setVoices(d.voices || []);
        setFigures(d.figures || []);
      })
      .catch(() => {
        setVoices([]);
        setFigures([]);
      })
      .finally(() => setLoading(false));
  }, [chapterId]);

  useEffect(() => { load(); }, [load]);

  return (
    <div className="p-4 space-y-4" data-testid="tab-panel-voice">
      <TabExportToolbar chapterId={chapterId} tab="voice" />
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <Shapes className="w-4 h-4 text-primary" />
        <span>
          {t("Math figure demos ({{figures}}) · Voice reading ({{voices}})", { figures: figures.length, voices: voices.length })}
        </span>
      </div>

      {loading ? (
        <div className="p-6 flex items-center justify-center text-muted-foreground">
          <Loader2 className="w-4 h-4 animate-spin mr-2" /> {t("Loading...")}
        </div>
      ) : (
        <>
          {/* 图形演示（数学，可拖拽 GeoGebra） */}
          {figures.length > 0 && (
            <div className="space-y-2">
              <div className="text-xs font-medium text-muted-foreground flex items-center gap-1">
                <Shapes className="w-3.5 h-3.5" /> {t("Draggable figure demos (drag points/sliders, figures update live)")}
              </div>
              {figures.map((f) => (
                <div key={f.id}>
                  <div
                    onClick={() => setActiveFig(activeFig === f.html ? null : f.html ?? null)}
                    data-testid="voice-figure-item"
                    className={`p-3 rounded-lg border cursor-pointer transition flex items-center gap-3 ${
                      activeFig === f.html ? "bg-primary/5 border-primary/40" : "bg-card hover:bg-accent"
                    }`}
                  >
                    <Shapes className="w-4 h-4 text-primary shrink-0" />
                    <span className="text-sm font-medium">{f.title}</span>
                    <span className="text-[10px] text-muted-foreground ml-auto">✋ {t("Draggable")}</span>
                  </div>
                  {activeFig === f.html && (
                    <div className="mt-2 rounded-lg border overflow-hidden" data-testid="voice-viewer">
                      <iframe
                        src={f.html}
                        title={t("math-figure")}
                        className="w-full h-[560px] bg-white"
                        sandbox="allow-scripts allow-same-origin allow-modals allow-forms"
                      />
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* 语音领读/视频 */}
          {voices.length > 0 && (
            <div className="space-y-2">
              <div className="text-xs font-medium text-muted-foreground flex items-center gap-1">
                <Mic className="w-3.5 h-3.5" /> {t("Voice reading / voice video")}
              </div>
              {voices.map((v) => (
                <div key={v.id}>
                  <div
                    onClick={() => setActiveVoice(activeVoice === v.id ? null : v.id)}
                    data-testid="voice-item"
                    className={`p-3 rounded-lg border cursor-pointer transition flex items-center gap-3 ${
                      activeVoice === v.id ? "bg-primary/5 border-primary/40" : "bg-card hover:bg-accent"
                    }`}
                  >
                    <Play className="w-4 h-4 text-primary shrink-0" />
                    <span className="text-sm font-medium">{v.title}</span>
                    <span className="text-[10px] text-muted-foreground ml-auto">
                      {v.html ? "📹 领读视频" : v.page ? "🎧 音频" : v.subject}
                    </span>
                  </div>
                  {activeVoice === v.id && (
                    <div className="mt-2 rounded-lg border overflow-hidden" data-testid="voice-viewer">
                      {v.html ? (
                        <iframe
                          src={v.html}
                          title={t("voice")}
                          className="w-full h-[520px] bg-white"
                          sandbox="allow-scripts allow-same-origin allow-modals allow-forms"
                        />
                      ) : v.page ? (
                        // 音频资源（mp3）：与 H5 一致，内嵌播放器（preload=none，点播放才拉流）
                        <div className="p-3 bg-card">
                          <audio controls preload="none" src={v.page} className="w-full h-10" data-testid="voice-audio" />
                        </div>
                      ) : null}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          {figures.length === 0 && voices.length === 0 && (
            <div className="p-6 rounded-lg border bg-muted/30 text-center">
              <Mic className="w-10 h-10 mx-auto text-muted-foreground mb-3" />
              <p className="text-sm font-medium mb-1">{t("No figure demos / voice video resources for this chapter yet")}</p>
              <p className="text-xs text-muted-foreground">{t("You can import or add them later.")}</p>
            </div>
          )}
        </>
      )}
    </div>
  );
}

"use client";

import { Sparkles, Image, Video, Code2, PenTool } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { TabExportToolbar } from "../TabExportToolbar";

export function AIResourceTab({ chapterId, chapterName, textbookName }: { chapterId: string; chapterName: string; textbookName: string }) {
  const navigate = useNavigate();
  const { t } = useTranslation();

  const tools = [
    {
      icon: Image,
      title: t("Generate concept map"),
      desc: t("Visualize this chapter's knowledge structure with Mermaid/SVG"),
      color: "text-blue-600 bg-blue-50 dark:bg-blue-950/30",
      prompt: t("Generate a concept map based on \"{{textbook}}\" and \"{{chapter}}\", showing relationships between core knowledge points.", { textbook: textbookName, chapter: chapterName }),
      action: () => navigate(`/e/sishu/chat?prompt=${encodeURIComponent(t("Generate a concept map based on \"{{textbook}}\" and \"{{chapter}}\", showing relationships between core knowledge points.", { textbook: textbookName, chapter: chapterName }))}&capability=visualize`),
    },
    {
      icon: Video,
      title: t("Generate animation"),
      desc: t("Demonstrate this chapter's core concepts with a math animation"),
      color: "text-purple-600 bg-purple-50 dark:bg-purple-950/30",
      prompt: t("Create an animation for \"{{chapter}}\" demonstrating the dynamic process of the core concept.", { chapter: chapterName }),
      action: () => navigate(`/e/sishu/chat?prompt=${encodeURIComponent(t("Create an animation for \"{{chapter}}\" demonstrating the dynamic process of the core concept.", { chapter: chapterName }))}&capability=visualize`),
    },
    {
      icon: Code2,
      title: t("Generate interactive page"),
      desc: t("HTML interactive practice page"),
      color: "text-emerald-600 bg-emerald-50 dark:bg-emerald-950/30",
      prompt: t("Create an interactive learning page for \"{{chapter}}\" with practice and instant feedback.", { chapter: chapterName }),
      action: () => navigate(`/e/sishu/chat?prompt=${encodeURIComponent(t("Create an interactive learning page for \"{{chapter}}\" with practice and instant feedback.", { chapter: chapterName }))}&capability=visualize`),
    },
    {
      icon: PenTool,
      title: t("AI Solve"),
      desc: t("Let AI solve questions related to this chapter"),
      color: "text-amber-600 bg-amber-50 dark:bg-amber-950/30",
      prompt: t("Explain the core knowledge points and solution methods of \"{{chapter}}\".", { chapter: chapterName }),
      action: () => navigate(`/e/sishu/chat?prompt=${encodeURIComponent(t("Explain the core knowledge points and solution methods of \"{{chapter}}\".", { chapter: chapterName }))}`),
    },
  ];

  return (
    <div className="p-4 space-y-4" data-testid="tab-panel-ai">
      <TabExportToolbar chapterId={chapterId} tab="ai" />
      <div className="text-sm text-muted-foreground">
        {t("AI resource generation entry based on this chapter's content. Click to launch the corresponding capability in chat.")}
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {tools.map((tool) => (
          <button
            key={tool.title}
            onClick={tool.action}
            data-testid="ai-resource-tool"
            className="p-4 rounded-lg border bg-card text-left hover:bg-accent transition group"
          >
            <div className="flex items-start gap-3">
              <div className={`p-2 rounded-lg ${tool.color}`}>
                <tool.icon className="w-5 h-5" />
              </div>
              <div className="flex-1">
                <div className="font-medium text-sm flex items-center gap-1">
                  {tool.title}
                  <Sparkles className="w-3 h-3 text-primary opacity-0 group-hover:opacity-100 transition" />
                </div>
                <p className="text-xs text-muted-foreground mt-1">{tool.desc}</p>
              </div>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}

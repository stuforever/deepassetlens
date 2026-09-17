"use client";

import { useState } from "react";
import { useTranslation } from "react-i18next";
import { ChevronDown, ChevronRight, BookOpen, FileText } from "lucide-react";
import type { TextbookNode, ChapterNode } from "../../../../lib/self-learning-api";

interface Props {
  textbooks: TextbookNode[];
  selectedChapterId: string | null;
  onSelectChapter: (chapter: ChapterNode, textbook: TextbookNode) => void;
}

export function ChapterTree({ textbooks, selectedChapterId, onSelectChapter }: Props) {
  const { t } = useTranslation();
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  const toggle = (id: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const renderChapter = (ch: ChapterNode, textbook: TextbookNode, depth: number) => {
    const hasChildren = ch.children && ch.children.length > 0;
    const isExpanded = expanded.has(ch.id);
    const isSelected = selectedChapterId === ch.id;

    return (
      <div key={ch.id}>
        <div
          className={`flex items-center gap-1 px-2 py-1.5 rounded cursor-pointer text-sm hover:bg-accent transition ${
            isSelected ? "bg-primary/10 ring-1 ring-primary/30 font-medium" : ""
          }`}
          style={{ paddingLeft: `${depth * 16 + 8}px` }}
          onClick={() => onSelectChapter(ch, textbook)}
          data-testid={`tree-chapter-${ch.id}`}
          data-selected={isSelected ? "true" : "false"}
        >
          {hasChildren ? (
            <button
              onClick={(e) => { e.stopPropagation(); toggle(ch.id); }}
              className="p-0.5 hover:bg-accent rounded"
            >
              {isExpanded ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
            </button>
          ) : (
            <FileText className="w-3.5 h-3.5 text-muted-foreground ml-1" />
          )}
          <span className="truncate">{ch.name}</span>
        </div>
        {hasChildren && isExpanded && (
          <div>
            {ch.children
              .sort((a, b) => a.order - b.order)
              .map((child) => renderChapter(child, textbook, depth + 1))}
          </div>
        )}
      </div>
    );
  };

  if (textbooks.length === 0) {
    return (
      <div className="p-4 text-sm text-muted-foreground">
        {t("No textbook data. Add textbooks and chapters in Settings → Settings management.")}
      </div>
    );
  }

  return (
    <div className="space-y-1">
      {textbooks.map((tb) => {
        const isExpanded = expanded.has(tb.id);
        return (
          <div key={tb.id}>
            <div
              className="flex items-center gap-1.5 px-2 py-2 rounded cursor-pointer text-sm font-semibold hover:bg-accent"
              onClick={() => toggle(tb.id)}
              data-testid={`tree-textbook-${tb.id}`}
            >
              {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
              <BookOpen className="w-4 h-4 text-primary" />
              <span className="truncate">{tb.name}</span>
              <span className="text-xs text-muted-foreground ml-auto">{t("{{count}} chapters", { count: tb.chapters?.length || 0 })}</span>
            </div>
            {isExpanded && (
              <div>
                {(tb.chapters || [])
                  .sort((a, b) => a.order - b.order)
                  .map((ch) => renderChapter(ch, tb, 0))}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

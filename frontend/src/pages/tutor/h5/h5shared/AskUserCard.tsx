/**
 * 复刻自 DeepTutor 原仓 web/app/h5/chat/AskUserCard.tsx（整件 1:1）。
 * 替换点：删除 "use client"；@/components/chat/home/AskUserOptions → ./AskUserOptions
 * （同批移植）；Tailwind → 内联样式逐项对位（indigo-50 #eef2ff / indigo-100 #e0e7ff /
 * indigo-600 #4f46e5 / indigo-700 #4338ca / slate-800 #1e293b / slate-700 #334155 /
 * slate-400 #94a3b8 / slate-200 #e2e8f0 / slate-50 #f8fafc / ring violet-300 #c4b5fd）。
 */
import React, { useState } from "react";
import type {
  AskUserCardData,
  AskUserAnswer,
} from "./AskUserOptions";

/**
 * H5 移动版 ask_user 交互卡（F1：M14-A）。
 * 数据由桌面同款 `extractAskUserPayload` 提取（两端共用，勿复制）。
 * - 待答态：选项渲染为 44px 大按钮，单选/多选/自由文本三种题型，提交后经
 *   submitUserReply 恢复被暂停的回合（精通辅导出题-作答-判分闭环的关键一环）。
 * - 已答态：收到 ask_user_resolved 后折叠为「已作答：…」一行。
 */
export default function H5AskUserCard({
  data,
  onSubmit,
}: {
  data: AskUserCardData;
  onSubmit: (answers: AskUserAnswer[]) => void;
}) {
  const { payload, answers, resolved } = data;
  const [selections, setSelections] = useState<Record<string, string[]>>({});
  const [freeTexts, setFreeTexts] = useState<Record<string, string>>({});

  if (resolved) {
    return (
      <div
        style={{
          background: "#eef2ff", border: "1px solid #e0e7ff",
          borderRadius: 16, padding: "10px 14px",
        }}
      >
        <div style={{ fontSize: 14, fontWeight: 500, color: "#334155" }}>
          {payload.intro || "已作答"}
        </div>
        {(answers || []).map((a, i) => (
          <div key={i} style={{ fontSize: 13, color: "#4338ca", marginTop: 4 }}>
            ✅ 已作答：{a.text}
          </div>
        ))}
      </div>
    );
  }

  const submit = () => {
    const out: AskUserAnswer[] = [];
    for (const q of payload.questions) {
      const sel = selections[q.id] || [];
      const free = freeTexts[q.id] || "";
      if (sel.length > 0) out.push({ questionId: q.id, text: sel.join("、") });
      else if (free.trim()) out.push({ questionId: q.id, text: free.trim() });
    }
    if (out.length > 0) onSubmit(out);
  };

  const toggle = (qid: string, label: string, multi: boolean) => {
    setSelections((prev) => {
      const cur = prev[qid] || [];
      if (multi) {
        return {
          ...prev,
          [qid]: cur.includes(label)
            ? cur.filter((x) => x !== label)
            : [...cur, label],
        };
      }
      return { ...prev, [qid]: [label] };
    });
  };

  return (
    <div
      style={{
        background: "#ffffff", borderRadius: 16, border: "1px solid #e2e8f0",
        boxShadow: "0 1px 2px 0 rgba(0,0,0,0.05)", padding: "12px 14px",
      }}
    >
      {payload.intro && (
        <div style={{ fontSize: 14, fontWeight: 500, color: "#1e293b", marginBottom: 8 }}>
          {payload.intro}
        </div>
      )}
      {payload.questions.map((q, qi) => {
        const sel = selections[q.id] || [];
        const isMulti = q.multi_select;
        return (
          <div key={q.id} style={{ marginBottom: 12 }}>
            <div style={{ fontSize: 15, fontWeight: 500, color: "#1e293b", marginBottom: 8 }}>
              {q.prompt}
              {payload.questions.length > 1 && (
                <span style={{ fontSize: 11, color: "#94a3b8", marginLeft: 4 }}>
                  第 {qi + 1} 题/共 {payload.questions.length} 题
                </span>
              )}
            </div>
            {q.options.length > 0 ? (
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {q.options.map((opt) => {
                  const on = sel.includes(opt.label);
                  return (
                    <button
                      key={opt.label}
                      onClick={() => toggle(q.id, opt.label, isMulti)}
                      style={{
                        width: "100%", textAlign: "left", padding: "12px 16px",
                        borderRadius: 12, border: `1px solid ${on ? "#4f46e5" : "#e2e8f0"}`,
                        background: on ? "#4f46e5" : "#f8fafc",
                        color: on ? "#ffffff" : "#1e293b",
                        fontSize: 15, transition: "all .15s", minHeight: 44, cursor: "pointer",
                      }}
                    >
                      <span style={{ fontWeight: 500 }}>{opt.label}</span>
                      {opt.description && (
                        <span
                          style={{
                            display: "block", fontSize: 12, marginTop: 2,
                            color: on ? "#e0e7ff" : "#94a3b8",
                          }}
                        >
                          {opt.description}
                        </span>
                      )}
                    </button>
                  );
                })}
                {isMulti && (
                  <div style={{ fontSize: 11, color: "#94a3b8" }}>可多选</div>
                )}
              </div>
            ) : (
              <input
                value={freeTexts[q.id] || ""}
                onChange={(e) =>
                  setFreeTexts((p) => ({ ...p, [q.id]: e.target.value }))
                }
                placeholder={q.placeholder || "输入你的回答…"}
                style={{
                  width: "100%", padding: "10px 12px", borderRadius: 12,
                  border: "1px solid #e2e8f0", background: "#f8fafc", fontSize: 15,
                  outline: "none", boxSizing: "border-box",
                }}
              />
            )}
          </div>
        );
      })}
      <button
        onClick={submit}
        style={{
          width: "100%", padding: "12px 0", borderRadius: 12, background: "#4f46e5",
          color: "#ffffff", fontSize: 15, fontWeight: 500, border: "none", cursor: "pointer",
        }}
      >
        提交答案
      </button>
    </div>
  );
}

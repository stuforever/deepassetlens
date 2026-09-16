/**
 * 复刻自 DeepTutor：web/app/(workspace)/book/components/blocks/QuizBlock.tsx（平铺到 tupu）。
 * 替换点：删除 "use client" 与 react-i18next，i18n 中文直出（zh/app.json）：
 *   "No quiz questions generated."→未生成测验题.、"Quick Check"→快速检查、
 *   "(missing)"→（缺失）、"Think about your answer, then reveal the solution."→
 *   先思考你的答案，然后查看解答.、"Open response — click reveal to see the model answer."→
 *   开放题回答——点击显示查看参考答案.、"Hide answer"→隐藏答案、"Reveal answer"→显示答案、
 *   "Answer"→答案。
 * lucide：CheckCircle2→CheckCircleFilled(#52c41a)、XCircle→CloseCircleFilled(#ff4d4f)、
 *   Eye→EyeOutlined、EyeOff→EyeInvisibleOutlined。
 * MarkdownRenderer → LiteMarkdown（'./dtMarkdown'，variant/className 附加参数忽略）；
 * @/lib/book-types → './book-types'、@/lib/quiz-question-type → './quiz-question-type'；
 * Tailwind → antd Button + 内联样式（选项四态配色按 Tailwind 色值：emerald-300/50/900、
 * rose-300/50/900、primary/8）。onAttempt 上报逻辑（useEffect + reportKey 去重）逐字保留。
 */
import { useEffect, useRef, useState } from "react";
import {
  CheckCircleFilled,
  CloseCircleFilled,
  EyeOutlined,
  EyeInvisibleOutlined,
} from "@ant-design/icons";
import { Button } from "antd";

import { LiteMarkdown } from './dtMarkdown';
import type { Block } from './book-types';
import {
  isChoiceQuizQuestion,
  normalizeQuizQuestionType,
  resolveChoiceAnswerKey,
} from './quiz-question-type';

const borderColor = "#e4e4e7";
const foreground = "rgba(0,0,0,0.88)";
const mutedForeground = "#6b7280";
const monoFont =
  'SFMono-Regular, Consolas, "Liberation Mono", Menlo, monospace';

export interface QuizAttemptArgs {
  questionId?: string;
  userAnswer?: string;
  isCorrect: boolean;
}

interface QuizQuestion {
  question_id?: string;
  question?: string;
  question_type?: string;
  options?: Record<string, string> | null;
  correct_answer?: string;
  explanation?: string;
  difficulty?: string;
}

export interface QuizBlockProps {
  block: Block;
  onAttempt?: (block: Block, args: QuizAttemptArgs) => void;
}

export default function QuizBlock({ block, onAttempt }: QuizBlockProps) {
  const questions =
    (block.payload?.questions as QuizQuestion[] | undefined) || [];
  if (questions.length === 0) {
    return (
      <div style={{ fontSize: 14, color: mutedForeground }}>
        未生成测验题。
      </div>
    );
  }
  return (
    <section>
      <div
        style={{
          marginBottom: 12,
          display: "flex",
          alignItems: "center",
          gap: 8,
          fontSize: 11,
          fontWeight: 600,
          textTransform: "uppercase",
          letterSpacing: "0.16em",
          color: "#1677ff",
        }}
      >
        <span style={{ height: 1, flex: 1, background: "rgba(22,119,255,0.2)" }} />
        {"快速检查"}
        <span style={{ height: 1, flex: 1, background: "rgba(22,119,255,0.2)" }} />
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        {questions.map((q, idx) => (
          <QuizQuestionCard
            key={q.question_id || idx}
            index={idx}
            question={q}
            onAttempt={(args) => onAttempt?.(block, args)}
          />
        ))}
      </div>
    </section>
  );
}

function QuizQuestionCard({
  index,
  question,
  onAttempt,
}: {
  index: number;
  question: QuizQuestion;
  onAttempt?: (args: QuizAttemptArgs) => void;
}) {
  const [selected, setSelected] = useState<string | null>(null);
  const [revealed, setRevealed] = useState(false);
  const reportedRef = useRef<string | null>(null);
  const normalizedType = normalizeQuizQuestionType(question.question_type);
  const options = question.options || {};
  const isChoice = isChoiceQuizQuestion(normalizedType);
  const correct = String(question.correct_answer || "").trim();
  const correctChoiceKey = resolveChoiceAnswerKey(correct, options);
  const reportKey = `${question.question_id || index}:${selected || ""}`;

  useEffect(() => {
    if (
      revealed &&
      selected &&
      reportedRef.current !== reportKey &&
      onAttempt
    ) {
      reportedRef.current = reportKey;
      onAttempt({
        questionId: question.question_id,
        userAnswer: selected,
        isCorrect: selected.toUpperCase() === correctChoiceKey,
      });
    }
  }, [
    reportKey,
    revealed,
    selected,
    onAttempt,
    question.question_id,
    correctChoiceKey,
  ]);

  return (
    <div
      style={{
        borderRadius: 12,
        border: `1px solid ${borderColor}`,
        background: "#f5f5f5",
        padding: 12,
      }}
    >
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 8 }}>
        <div style={{ display: "flex", minWidth: 0, flex: 1, alignItems: "flex-start", gap: 8 }}>
          <span
            style={{ paddingTop: 2, fontSize: 14, fontWeight: 500, color: foreground }}
          >
            {index + 1}.
          </span>
          <div style={{ minWidth: 0, flex: 1 }}>
            <LiteMarkdown
              content={String(question.question || "（缺失）")}
            />
          </div>
        </div>
        {question.difficulty && (
          <span
            style={{
              borderRadius: 999,
              background: "#f4f4f5",
              padding: "2px 8px",
              fontSize: 10,
              textTransform: "uppercase",
              letterSpacing: "0.05em",
              color: mutedForeground,
              whiteSpace: "nowrap",
            }}
          >
            {question.difficulty}
          </span>
        )}
      </div>

      {isChoice && Object.keys(options).length > 0 ? (
        <div style={{ marginTop: 12, display: "flex", flexDirection: "column", gap: 6 }}>
          {Object.entries(options).map(([key, label]) => {
            const upperKey = key.toUpperCase();
            const isSelected = selected === upperKey;
            const isCorrect = revealed && upperKey === correctChoiceKey;
            const isWrongPick =
              revealed && isSelected && upperKey !== correctChoiceKey;
            return (
              <Button
                key={key}
                onClick={() => setSelected(upperKey)}
                style={{
                  display: "flex",
                  width: "100%",
                  alignItems: "flex-start",
                  gap: 8,
                  borderRadius: 8,
                  border: `1px solid ${
                    isCorrect
                      ? "#6ee7b7"
                      : isWrongPick
                        ? "#fda4af"
                        : isSelected
                          ? "#1677ff"
                          : borderColor
                  }`,
                  background: isCorrect
                    ? "#ecfdf5"
                    : isWrongPick
                      ? "#fff1f2"
                      : isSelected
                        ? "rgba(22,119,255,0.08)"
                        : "#fff",
                  color: isCorrect
                    ? "#064e3b"
                    : isWrongPick
                      ? "#881337"
                      : foreground,
                  padding: "8px 12px",
                  textAlign: "left",
                  fontSize: 14,
                  height: "auto",
                }}
              >
                <span
                  style={{
                    fontFamily: monoFont,
                    fontSize: 12,
                    textTransform: "uppercase",
                    color: mutedForeground,
                  }}
                >
                  {upperKey}.
                </span>
                <span
                  style={{
                    flex: 1,
                    whiteSpace: "pre-wrap",
                    wordBreak: "break-word",
                    textAlign: "left",
                  }}
                >
                  {label}
                </span>
                {isCorrect && (
                  <CheckCircleFilled
                    style={{ fontSize: 16, color: "#52c41a", marginTop: 2 }}
                  />
                )}
                {isWrongPick && (
                  <CloseCircleFilled
                    style={{ fontSize: 16, color: "#ff4d4f", marginTop: 2 }}
                  />
                )}
              </Button>
            );
          })}
        </div>
      ) : (
        <div style={{ marginTop: 8, fontSize: 12, color: mutedForeground }}>
          {normalizedType === "written"
            ? "先思考你的答案，然后查看解答。"
            : "开放题回答——点击显示查看参考答案。"}
        </div>
      )}

      <div style={{ marginTop: 12, display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8 }}>
        <Button
          size="small"
          onClick={() => setRevealed((v) => !v)}
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 6,
            borderRadius: 6,
            fontSize: 12,
            fontWeight: 500,
            color: mutedForeground,
            height: "auto",
            padding: "4px 10px",
          }}
        >
          {revealed ? (
            <EyeInvisibleOutlined style={{ fontSize: 14 }} />
          ) : (
            <EyeOutlined style={{ fontSize: 14 }} />
          )}
          {revealed ? "隐藏答案" : "显示答案"}
        </Button>
        {revealed && correct && isChoice && (
          <span style={{ fontSize: 12, color: mutedForeground }}>
            {"答案"}:{" "}
            <span style={{ fontFamily: monoFont, color: foreground }}>
              {correctChoiceKey || correct}
            </span>
          </span>
        )}
      </div>

      {revealed && correct && !isChoice && (
        <div
          style={{
            marginTop: 8,
            borderRadius: 8,
            border: `1px solid ${borderColor}`,
            background: "rgba(255,255,255,0.7)",
            padding: 8,
          }}
        >
          <div
            style={{
              marginBottom: 4,
              fontSize: 11,
              fontWeight: 600,
              textTransform: "uppercase",
              letterSpacing: "0.16em",
              color: mutedForeground,
            }}
          >
            {"答案"}
          </div>
          <LiteMarkdown
            content={correct}
          />
        </div>
      )}

      {revealed && question.explanation && (
        <div
          style={{
            marginTop: 8,
            borderRadius: 8,
            border: `1px solid ${borderColor}`,
            background: "rgba(244,244,245,0.4)",
            padding: 8,
          }}
        >
          <LiteMarkdown
            content={String(question.explanation)}
          />
        </div>
      )}
    </div>
  );
}

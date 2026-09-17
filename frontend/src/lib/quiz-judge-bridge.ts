/**
 * 引擎批4 4.4：判分桥面——接口面与 lib/quiz-judge.ts 1:1（startQuizJudge/QuizJudgeRequest/
 * QuizJudgeHandle/QuizJudgeHandlers），传输面 WS→桥 SSE（POST /api/v2/skills/capability，
 * skill_code=tutor/quiz，config.action="judge"）。
 * StreamEvent→原 frame 语义映射：stage_start(judge)→started；content→text；result→终文；
 * done→done(ok)；error→error。quizJudge.ts 退役删除（E-24④）。
 */
import { apiUrl } from "./api";

export interface QuizJudgeImage {
  base64: string | null;
  url: string | null;
  filename: string;
  mime_type: string;
}

export interface QuizJudgeRequest {
  question: string;
  question_type: string;
  options: Record<string, string> | null;
  correct_answer: string;
  explanation: string;
  user_answer: string;
  user_answer_images: QuizJudgeImage[];
  language: "zh" | "en";
}

export interface QuizJudgeHandle {
  close: () => void;
}

export interface QuizJudgeHandlers {
  onStart?: () => void;
  onChunk: (chunk: string) => void;
  onDone: (finalText: string) => void;
  onError: (message: string) => void;
}

export function startQuizJudge(
  payload: QuizJudgeRequest,
  handlers: QuizJudgeHandlers,
): QuizJudgeHandle {
  const controller = new AbortController();
  let buffer = "";
  let finished = false;

  const finalize = (kind: "done" | "error", message?: string) => {
    if (finished) return;
    finished = true;
    if (kind === "done") handlers.onDone(buffer);
    else handlers.onError(message ?? "AI judge failed.");
  };

  void (async () => {
    try {
      const resp = await fetch(apiUrl("/api/v2/skills/capability"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        signal: controller.signal,
        body: JSON.stringify({
          skill_code: "tutor/quiz",
          message: payload.question,
          config: { action: "judge", ...payload },
        }),
      });
      if (!resp.ok || !resp.body) throw new Error(`桥端点 HTTP ${resp.status}`);
      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let buf = "";
      let finalText: string | null = null;
      let started = false;
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });
        let idx: number;
        while ((idx = buf.indexOf("\n\n")) >= 0) {
          const raw = buf.slice(0, idx);
          buf = buf.slice(idx + 2);
          for (const line of raw.split("\n")) {
            if (!line.startsWith("data:")) continue;
            let ev: { type?: string; content?: string };
            try {
              ev = JSON.parse(line.slice(5).trim());
            } catch {
              continue;
            }
            if (ev.type === "stage_start" && ev.content === "AI 判分中" && !started) {
              started = true;
              handlers.onStart?.();
            } else if (ev.type === "content" && typeof ev.content === "string") {
              buffer += ev.content;
              handlers.onChunk(ev.content);
            } else if (ev.type === "result" && typeof ev.content === "string") {
              finalText = ev.content;
            } else if (ev.type === "error") {
              finalize("error", ev.content ?? "AI judge failed.");
              return;
            } else if (ev.type === "done") {
              finalize("done");
              return;
            }
          }
        }
      }
      if (finalText && !buffer.trim()) {
        // 兜底：服务端只回 result 帧（无增量）——终文整块回放
        buffer = finalText;
        handlers.onChunk(finalText);
      }
      finalize("done");
    } catch (err) {
      if ((err as Error).name === "AbortError") return;
      finalize("error", err instanceof Error ? err.message : String(err));
    }
  })();

  return {
    close: () => {
      try {
        controller.abort();
      } catch {
        /* ignore */
      }
    },
  };
}

/** 自 lib/quiz-judge.ts 1:1 挪入（退役件收编——readFileAsBase64 为判分图片读取面）。 */
export function readFileAsBase64(
  file: File,
): Promise<{ base64: string; mime: string; name: string }> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const result = reader.result;
      if (typeof result !== "string") {
        reject(new Error("Failed to read file"));
        return;
      }
      const comma = result.indexOf(",");
      const base64 = comma >= 0 ? result.slice(comma + 1) : result;
      resolve({
        base64,
        mime: file.type || "image/png",
        name: file.name || "answer.png",
      });
    };
    reader.onerror = () =>
      reject(reader.error ?? new Error("Failed to read file"));
    reader.readAsDataURL(file);
  });
}

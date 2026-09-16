/**
 * 复刻自 DeepTutor 原仓 web/components/quiz/QuizViewer.tsx（整件 1:1）。
 * 替换点（登记）：
 * 1. 删除 "use client"；
 * 2. lucide → @ant-design/icons 语义就近：Bookmark→StarOutlined（antd 无书签图标，
 *    收藏语义就近）、Check→CheckOutlined、ChevronDown/Left/Right→DownOutlined/
 *    LeftOutlined/RightOutlined、Eye→EyeOutlined、FolderPlus→FolderAddOutlined、
 *    ImagePlus→PictureOutlined、Loader2→LoadingOutlined、MessageSquarePlus→
 *    MessageOutlined、Plus→PlusOutlined、RotateCcw→RedoOutlined、
 *    Sparkles→ThunderboltOutlined（antd 无 sparkle，AI 动作语义就近）、X→CloseOutlined；
 * 3. i18n t() → 中文直出（译自原仓 locales/zh/app.json 逐键核对）；
 * 4. Tailwind（shadcn CSS 变量类）→ 内联样式 + 组件级 <style> 承接 hover/disabled
 *    伪类；CSS 变量取 Snow 亮色主题实测值（--primary #4f46e5 等）；原仓 dark: 变体
 *    按 H5 亮色形态裁剪（tupu 无暗色主题开关，登记项）；
 * 5. @/components/common/MarkdownRenderer → 批8 admin/MarkdownRenderer.tsx（props
 *    契约一致）；@/context/QuizFollowupContext → ./QuizFollowupContext；
 *    @/lib/quiz-question-type → 批8 admin/quiz-question-type.ts；
 *    @/lib/quiz-judge → ./quizJudge；@/lib/quiz-types → ./quizTypes；
 *    @/lib/notebook-api → 批8 admin/notebook-api.ts（本批补齐 lookup/update/upsert/
 *    createCategory/addEntryToCategory 五导出）；@/lib/session-api → 批8 admin/
 *    session-api.ts；apiUrl(url) → url（剥掉透传，同源相对路径直用）。
 */
import {
  type ChangeEvent,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import {
  StarOutlined,
  CheckOutlined,
  DownOutlined,
  LeftOutlined,
  RightOutlined,
  EyeOutlined,
  FolderAddOutlined,
  PictureOutlined,
  LoadingOutlined,
  MessageOutlined,
  PlusOutlined,
  RedoOutlined,
  ThunderboltOutlined,
  CloseOutlined,
} from "@ant-design/icons";
import MarkdownRenderer from "../../admin/MarkdownRenderer";
import {
  useAllFollowupThreads,
  useQuizFollowupController,
} from "./QuizFollowupContext";
import {
  isChoiceQuizQuestion,
  isConceptQuizQuestion,
  isFillInBlankQuizQuestion,
  resolveChoiceAnswerKey,
  resolveConceptAnswer,
} from "../../admin/quiz-question-type";
import {
  readFileAsBase64,
  startQuizJudge,
  type QuizJudgeHandle,
} from "./quizJudge";
import { type QuizQuestion } from "./quizTypes";
import {
  addEntryToCategory,
  createCategory,
  listCategories,
  lookupNotebookEntry,
  updateNotebookEntry,
  upsertNotebookEntry,
  type NotebookCategory,
} from "../../admin/notebook-api";
import { recordQuizResults } from "../../admin/session-api";

// Snow 亮色主题 CSS 变量取值（本文件局部对位用）。
const FG = "#0f172a";
const MUTED_FG = "#64748b";
const PRIMARY = "#4f46e5";
const CARD = "#ffffff";
const BORDER = "#e2e8f0";
const MUTED = "#f1f5f9";
const BG = "#f8fafc";

/** hover/disabled 伪类承接（原 Tailwind hover 与 disabled 变体）。 */
const QuizViewerStyleBlock = () => (
  <style>{`
.qv-navbtn:hover:not(:disabled){border-color:${PRIMARY}!important;background:rgba(79,70,229,.1)!important;color:${PRIMARY}!important;}
.qv-navbtn:disabled{cursor:not-allowed;border-color:${BORDER}!important;background:transparent!important;color:${MUTED_FG}!important;opacity:.4;}
.qv-chip-g:hover{background:#bbf7d0!important;}
.qv-chip-r:hover{background:#fecaca!important;}
.qv-chip-m:hover{background:#e2e8f0!important;}
.qv-bkm:hover:not(:disabled){color:#f59e0b!important;}
.qv-folder:hover:not(:disabled){color:${FG}!important;}
.qv-opt:hover:not(:disabled){border-color:rgba(79,70,229,.3)!important;background:rgba(79,70,229,.02)!important;}
.qv-opt:disabled{cursor:default;}
.qv-tf:hover:not(:disabled){border-color:rgba(79,70,229,.3)!important;}
.qv-tf:disabled{cursor:default;}
.qv-fill:focus{border-color:rgba(79,70,229,.4)!important;}
.qv-imgpick:hover{border-color:${PRIMARY}!important;color:${PRIMARY}!important;}
.qv-catitem:hover:not(:disabled){background:${MUTED}!important;}
.qv-catitem:disabled{opacity:.4;}
.qv-retry:hover{color:${FG}!important;}
.qv-judge:hover:not(:disabled){background:rgba(79,70,229,.15)!important;}
.qv-judge:disabled{opacity:.5;}
.qv-viewtab:hover:not(.qv-viewtab-on){color:${FG}!important;}
.qv-collapse:hover{background:${MUTED}!important;color:${FG}!important;}
.qv-chevron{transition:transform .15s;}
.qv-chevron-collapsed{transform:rotate(-90deg);}
.qv-imgdel{opacity:0;transition:opacity .15s;}
.qv-imggroup:hover .qv-imgdel{opacity:1;}
.qv-imggrid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px;}
@media(min-width:640px){.qv-imggrid{grid-template-columns:repeat(3,minmax(0,1fr));}}
@media(min-width:768px){.qv-imggrid{grid-template-columns:repeat(4,minmax(0,1fr));}}
.qv-placeholder::placeholder{color:${MUTED_FG};}
  `}</style>
);

/** Resolve a possibly-relative AttachmentStore URL to an absolute one so
 *  ``<img src>`` works regardless of the API/frontend port pairing. */
function resolveImageSrc(url: string | null | undefined): string | undefined {
  if (!url) return undefined;
  if (/^(https?:|data:|blob:)/i.test(url)) return url;
  return url;
}

interface QuizViewerProps {
  questions: QuizQuestion[];
  sessionId?: string | null;
  /**
   * The ``turn_id`` of the assistant turn that produced this quiz. Scopes
   * notebook lookups/upserts so two quizzes generated in the same chat
   * session don't share answer state — positional question ids
   * (``q_1``..``q_N``) repeat across quizzes (issues #487 / #677). When
   * absent (only legacy turns persisted before turn ids existed), the card
   * is local-only: answers grade client-side but the notebook is never
   * read or written, so state can't leak across quizzes.
   */
  turnId?: string | null;
  language?: string;
}

type AnswerImage = {
  /**
   * Local-only identifier used to key React lists and to remove a
   * specific image. When the image has been persisted server-side the
   * field is replaced with the stable AttachmentStore id.
   */
  id: string;
  /** Base64 (no ``data:`` prefix) when freshly picked client-side. */
  base64: string | null;
  /** AttachmentStore URL once the upsert response confirms persistence. */
  url: string | null;
  filename: string;
  mime: string;
  /** Blob: URL for the local <img> preview when ``base64`` is present. */
  previewUrl: string | null;
};

type AnswerState = {
  selected: string | null;
  typed: string;
  submitted: boolean;
  images: AnswerImage[];
};

const EMPTY_ANSWER: AnswerState = {
  selected: null,
  typed: "",
  submitted: false,
  images: [],
};

function makeAnswerImageId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID().replaceAll("-", "").slice(0, 12);
  }
  return Math.random().toString(36).slice(2, 14);
}

type JudgmentState = {
  text: string;
  isStreaming: boolean;
  error: string | null;
};

const EMPTY_JUDGMENT: JudgmentState = {
  text: "",
  isStreaming: false,
  error: null,
};

type AnswerView = "reference" | "judgment";

function getQuestionKey(question: QuizQuestion, index: number): string {
  return question.question_id || `question_${index + 1}`;
}

function isMultipleChoice(question: QuizQuestion): boolean {
  return (
    isChoiceQuizQuestion(question.question_type) &&
    !!question.options &&
    Object.keys(question.options).length > 0
  );
}

/**
 * Auto-gradable question types: choice, concept (T/F), fill_in_blank.
 * Open-ended types (short_answer, written, coding) are excluded — their
 * answers are graded by the learner against the reference, not by exact
 * string match.
 */
function isAutoGradable(question: QuizQuestion): boolean {
  return (
    isMultipleChoice(question) ||
    isConceptQuizQuestion(question.question_type) ||
    isFillInBlankQuizQuestion(question.question_type)
  );
}

function getUserAnswer(question: QuizQuestion, answer: AnswerState): string {
  // Choice + concept use the ``selected`` field (option key / "true" / "false").
  if (
    isMultipleChoice(question) ||
    isConceptQuizQuestion(question.question_type)
  ) {
    return answer.selected ?? "";
  }
  // Fill-in-blank + free-text types use the typed string.
  return answer.typed.trim();
}

function isAnswerCorrect(question: QuizQuestion, answer: AnswerState): boolean {
  const userAnswer = getUserAnswer(question, answer);
  if (!userAnswer) return false;
  const correct = question.correct_answer.trim();
  if (isMultipleChoice(question)) {
    const correctChoiceKey = resolveChoiceAnswerKey(correct, question.options);
    return (
      userAnswer.toUpperCase() === correctChoiceKey ||
      userAnswer.toUpperCase() === correct.toUpperCase() ||
      userAnswer.toUpperCase() === correct.charAt(0).toUpperCase()
    );
  }
  if (isConceptQuizQuestion(question.question_type)) {
    const correctTF = resolveConceptAnswer(correct);
    return userAnswer.toLowerCase() === correctTF;
  }
  return userAnswer.toLowerCase() === correct.toLowerCase();
}

export default function QuizViewer({
  questions,
  sessionId,
  turnId,
  language = "en",
}: QuizViewerProps) {
  const followupController = useQuizFollowupController();
  // Read all follow-up threads so we can light up the "N messages" badge
  // and the per-chip dot indicator. Owned by QuizFollowupProvider so
  // QuizFollowupTabBody and QuizViewer stay in sync.
  const followupThreads = useAllFollowupThreads();
  const [idx, setIdx] = useState(0);
  const [answers, setAnswers] = useState<Record<number, AnswerState>>({});
  const lastReportedSignatureRef = useRef("");

  const [entryIds, setEntryIds] = useState<Record<string, number>>({});
  const [bookmarked, setBookmarked] = useState<Record<string, boolean>>({});
  // Captured from the notebook entry on lookup so QuizFollowupTabBody
  // can hydrate prior chat history when the follow-up tab opens.
  const [followupSessionIds, setFollowupSessionIds] = useState<
    Record<string, string>
  >({});
  const [categories, setCategories] = useState<NotebookCategory[]>([]);
  const [categoryDropdownKey, setCategoryDropdownKey] = useState<string | null>(
    null,
  );
  const [newCategoryName, setNewCategoryName] = useState("");
  const [categoryBusy, setCategoryBusy] = useState(false);

  const [judgments, setJudgments] = useState<Record<number, JudgmentState>>({});
  const [answerViews, setAnswerViews] = useState<Record<number, AnswerView>>(
    {},
  );
  // Per-question collapsed state for the Reference / Judgment review
  // block. Default: expanded. Persists per question while the QuizViewer
  // instance is alive.
  const [reviewCollapsed, setReviewCollapsed] = useState<
    Record<number, boolean>
  >({});
  const judgeHandlesRef = useRef<Map<number, QuizJudgeHandle>>(new Map());
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  useEffect(
    () => () => {
      judgeHandlesRef.current.forEach((handle) => handle.close());
      judgeHandlesRef.current.clear();
    },
    [],
  );

  const q = questions[idx];
  const ans = answers[idx] ?? EMPTY_ANSWER;
  const total = questions.length;
  const navigationProgress = total > 0 ? ((idx + 1) / total) * 100 : 0;
  const questionKey = q ? getQuestionKey(q, idx) : "";
  const completedCount = useMemo(
    () => Object.values(answers).filter((answer) => answer.submitted).length,
    [answers],
  );

  const updateAnswer = useCallback(
    (patch: Partial<AnswerState>) =>
      setAnswers((prev) => ({
        ...prev,
        [idx]: { ...(prev[idx] ?? EMPTY_ANSWER), ...patch },
      })),
    [idx],
  );

  // ── Notebook integration ──────────────────────────────────────

  const refreshEntryId = useCallback(
    async (qKey: string, sId: string, questionIndex?: number) => {
      // No turn identity → no notebook reads. A turn-less lookup can only
      // resolve against another turn's rows (question ids are positional),
      // which is exactly the cross-quiz answer inheritance of #677.
      if (!turnId) return;
      try {
        const entry = await lookupNotebookEntry(sId, qKey, turnId);
        if (entry) {
          setEntryIds((prev) => ({ ...prev, [qKey]: entry.id }));
          setBookmarked((prev) => ({ ...prev, [qKey]: entry.bookmarked }));
          if (entry.followup_session_id) {
            setFollowupSessionIds((prev) => ({
              ...prev,
              [qKey]: entry.followup_session_id,
            }));
          }
          const persistedImages = (entry.user_answer_images ?? []).map(
            (image) => ({
              id: image.id || makeAnswerImageId(),
              base64: null,
              url: image.url || null,
              filename: image.filename || "answer.png",
              mime: image.mime_type || "image/png",
              previewUrl: null,
            }),
          );
          if (
            questionIndex !== undefined &&
            (entry.user_answer || persistedImages.length > 0)
          ) {
            setAnswers((prev) => {
              if (prev[questionIndex]?.submitted) return prev;
              return {
                ...prev,
                [questionIndex]: {
                  ...EMPTY_ANSWER,
                  selected: entry.user_answer || null,
                  typed: entry.user_answer || "",
                  images: persistedImages,
                  submitted: true,
                },
              };
            });
          }
          // Rehydrate the AI judgment so the learner can keep reading
          // it across page refreshes. We only overwrite when local state
          // is still empty so an in-flight judge run isn't clobbered.
          if (
            questionIndex !== undefined &&
            entry.ai_judgment &&
            entry.ai_judgment.length > 0
          ) {
            setJudgments((prev) => {
              const current = prev[questionIndex];
              if (current?.text || current?.isStreaming) return prev;
              return {
                ...prev,
                [questionIndex]: {
                  text: entry.ai_judgment ?? "",
                  isStreaming: false,
                  error: null,
                },
              };
            });
          }
        }
      } catch {
        /* entry may not exist yet */
      }
    },
    [turnId],
  );

  useEffect(() => {
    if (!sessionId) return;
    questions.forEach((question, i) => {
      const key = getQuestionKey(question, i);
      void refreshEntryId(key, sessionId, i);
    });
  }, [sessionId, questions, refreshEntryId]);

  const handleToggleBookmark = useCallback(async () => {
    if (!q || !sessionId) return;
    const key = getQuestionKey(q, idx);
    const eId = entryIds[key];
    if (!eId) return;
    const next = !bookmarked[key];
    setBookmarked((prev) => ({ ...prev, [key]: next }));
    try {
      await updateNotebookEntry(eId, { bookmarked: next });
    } catch {
      setBookmarked((prev) => ({ ...prev, [key]: !next }));
    }
  }, [bookmarked, entryIds, idx, q, sessionId]);

  const loadCategories = useCallback(async () => {
    try {
      setCategories(await listCategories());
    } catch {
      /* ignore */
    }
  }, []);

  const handleOpenCategoryDropdown = useCallback(() => {
    if (!q) return;
    const key = getQuestionKey(q, idx);
    if (categoryDropdownKey === key) {
      setCategoryDropdownKey(null);
      return;
    }
    setCategoryDropdownKey(key);
    void loadCategories();
  }, [categoryDropdownKey, idx, loadCategories, q]);

  const handleAddToCategory = useCallback(
    async (catId: number) => {
      if (!q) return;
      const key = getQuestionKey(q, idx);
      const eId = entryIds[key];
      if (!eId) return;
      setCategoryBusy(true);
      try {
        await addEntryToCategory(eId, catId);
        setCategoryDropdownKey(null);
      } catch {
        /* ignore */
      }
      setCategoryBusy(false);
    },
    [entryIds, idx, q],
  );

  const handleCreateAndAdd = useCallback(async () => {
    if (!q || !newCategoryName.trim()) return;
    const key = getQuestionKey(q, idx);
    const eId = entryIds[key];
    if (!eId) return;
    setCategoryBusy(true);
    try {
      const cat = await createCategory(newCategoryName.trim());
      await addEntryToCategory(eId, cat.id);
      setNewCategoryName("");
      setCategoryDropdownKey(null);
    } catch {
      /* ignore */
    }
    setCategoryBusy(false);
  }, [entryIds, idx, newCategoryName, q]);

  const isChoice = q ? isMultipleChoice(q) : false;
  const isConcept = q ? isConceptQuizQuestion(q.question_type) : false;
  const isFillBlank = q ? isFillInBlankQuizQuestion(q.question_type) : false;
  const isGradable = q ? isAutoGradable(q) : false;
  const currentUserAnswer = q ? getUserAnswer(q, ans) : "";

  const isCorrect = useMemo(() => {
    if (!q || !ans.submitted) return null;
    return isAnswerCorrect(q, ans);
  }, [ans, q]);

  const submittedResults = useMemo(
    () =>
      questions.flatMap((question, questionIdx) => {
        const answer = answers[questionIdx];
        if (!answer?.submitted) return [];
        return [
          {
            question_id: question.question_id,
            question: question.question,
            question_type: question.question_type,
            options: question.options ?? {},
            user_answer: getUserAnswer(question, answer),
            correct_answer: question.correct_answer,
            explanation: question.explanation ?? "",
            difficulty: question.difficulty ?? "",
            is_correct: isAnswerCorrect(question, answer),
          },
        ];
      }),
    [answers, questions],
  );

  useEffect(() => {
    // Reporting requires a turn identity: an empty ``turn_id`` write lands
    // in the shared legacy namespace, where the next quiz's identically
    // numbered questions would pick it up as their own answers (#677).
    if (!sessionId || !turnId || total === 0 || completedCount !== total)
      return;
    const signature = JSON.stringify(submittedResults);
    if (!signature || signature === lastReportedSignatureRef.current) return;
    lastReportedSignatureRef.current = signature;
    void recordQuizResults(sessionId, submittedResults, turnId)
      .then(() => {
        questions.forEach((question, i) => {
          void refreshEntryId(getQuestionKey(question, i), sessionId);
        });
      })
      .catch((error) => {
        console.error("Failed to record quiz results:", error);
        if (lastReportedSignatureRef.current === signature) {
          lastReportedSignatureRef.current = "";
        }
      });
  }, [
    completedCount,
    questions,
    refreshEntryId,
    sessionId,
    submittedResults,
    total,
    turnId,
  ]);

  const upsertSingleQuestion = useCallback(
    async (
      question: QuizQuestion,
      answer: AnswerState,
      questionIndex: number,
    ) => {
      if (!sessionId || !turnId) return;
      const key = getQuestionKey(question, questionIndex);
      try {
        const imagePayload = answer.images.map((image) => ({
          id: image.id,
          base64: image.base64 ?? undefined,
          url: image.url ?? undefined,
          filename: image.filename,
          mime_type: image.mime,
        }));
        const entry = await upsertNotebookEntry({
          session_id: sessionId,
          turn_id: turnId,
          question_id: question.question_id,
          question: question.question,
          question_type: question.question_type,
          options: question.options ?? {},
          correct_answer: question.correct_answer,
          explanation: question.explanation ?? "",
          difficulty: question.difficulty ?? "",
          user_answer: getUserAnswer(question, answer),
          user_answer_images: imagePayload,
          is_correct: isAnswerCorrect(question, answer),
        });
        setEntryIds((prev) => ({ ...prev, [key]: entry.id }));
        setBookmarked((prev) => ({ ...prev, [key]: entry.bookmarked }));
        // Replace freshly-uploaded ``base64`` images with the
        // AttachmentStore URLs the server hands back, so subsequent
        // upserts don't re-upload the same bytes and the previews can
        // survive a page reload by falling through to ``url``.
        const persisted = entry.user_answer_images ?? [];
        if (persisted.length > 0) {
          setAnswers((prev) => {
            const current = prev[questionIndex];
            if (!current) return prev;
            const byId = new Map(persisted.map((image) => [image.id, image]));
            const nextImages = current.images.map((image) => {
              const match = byId.get(image.id);
              if (!match) return image;
              return {
                ...image,
                url: match.url || image.url,
                // Drop base64 once the server has the bytes.
                base64: null,
              };
            });
            return {
              ...prev,
              [questionIndex]: { ...current, images: nextImages },
            };
          });
        }
      } catch {
        /* best-effort */
      }
    },
    [sessionId, turnId],
  );

  const handleSubmit = () => {
    if (ans.submitted || !q) return;
    const newAnswer = { ...(answers[idx] ?? EMPTY_ANSWER), submitted: true };
    updateAnswer({ submitted: true });
    void upsertSingleQuestion(q, newAnswer, idx);
  };

  const handleReset = () => {
    // Reset typed/selected state but keep an attached image so the learner
    // doesn't have to re-upload it when retrying.
    updateAnswer({ selected: null, typed: "", submitted: false });
    setJudgments((prev) => {
      const next = { ...prev };
      delete next[idx];
      return next;
    });
    setAnswerViews((prev) => {
      const next = { ...prev };
      delete next[idx];
      return next;
    });
    const existing = judgeHandlesRef.current.get(idx);
    if (existing) {
      existing.close();
      judgeHandlesRef.current.delete(idx);
    }
  };

  const handlePickImageClick = useCallback(() => {
    fileInputRef.current?.click();
  }, []);

  const handleImageChange = useCallback(
    async (event: ChangeEvent<HTMLInputElement>) => {
      const files = Array.from(event.target.files ?? []);
      // Reset the input so re-selecting the same file fires onChange again.
      event.target.value = "";
      if (files.length === 0) return;

      const newImages: AnswerImage[] = [];
      for (const file of files) {
        if (!file.type.startsWith("image/")) continue;
        try {
          const { base64, mime, name } = await readFileAsBase64(file);
          newImages.push({
            id: makeAnswerImageId(),
            base64,
            url: null,
            filename: name,
            mime,
            previewUrl: URL.createObjectURL(file),
          });
        } catch {
          /* skip this file — user can retry */
        }
      }
      if (newImages.length === 0) return;

      const prev = answers[idx] ?? EMPTY_ANSWER;
      updateAnswer({ images: [...prev.images, ...newImages] });
    },
    [answers, idx, updateAnswer],
  );

  const handleRemoveImage = useCallback(
    (imageId: string) => {
      const prev = answers[idx] ?? EMPTY_ANSWER;
      const remaining: AnswerImage[] = [];
      for (const image of prev.images) {
        if (image.id === imageId) {
          if (image.previewUrl) {
            try {
              URL.revokeObjectURL(image.previewUrl);
            } catch {
              /* ignore */
            }
          }
          continue;
        }
        remaining.push(image);
      }
      updateAnswer({ images: remaining });
    },
    [answers, idx, updateAnswer],
  );

  const handleAiJudge = useCallback(() => {
    if (!q) return;
    const answer = answers[idx] ?? EMPTY_ANSWER;
    const userAnswer = getUserAnswer(q, answer);
    if (!userAnswer && answer.images.length === 0) return;

    // Cancel any in-flight judge for this question before starting a new run.
    const existing = judgeHandlesRef.current.get(idx);
    if (existing) {
      existing.close();
      judgeHandlesRef.current.delete(idx);
    }

    setJudgments((prev) => ({
      ...prev,
      [idx]: { text: "", isStreaming: true, error: null },
    }));
    setAnswerViews((prev) => ({ ...prev, [idx]: "judgment" }));

    const judgeLanguage: "zh" | "en" = language === "zh" ? "zh" : "en";

    const handle = startQuizJudge(
      {
        question: q.question,
        question_type: q.question_type ?? "",
        options: q.options ?? null,
        correct_answer: q.correct_answer ?? "",
        explanation: q.explanation ?? "",
        user_answer: userAnswer,
        user_answer_images: answer.images.map((image) => ({
          base64: image.base64,
          url: image.url,
          filename: image.filename,
          mime_type: image.mime,
        })),
        language: judgeLanguage,
      },
      {
        onChunk: (chunk) => {
          setJudgments((prev) => {
            const current = prev[idx] ?? EMPTY_JUDGMENT;
            return {
              ...prev,
              [idx]: { ...current, text: current.text + chunk },
            };
          });
        },
        onDone: () => {
          let finalText = "";
          setJudgments((prev) => {
            const current = prev[idx] ?? EMPTY_JUDGMENT;
            finalText = current.text;
            return {
              ...prev,
              [idx]: { ...current, isStreaming: false },
            };
          });
          judgeHandlesRef.current.delete(idx);
          // Persist the AI judgment text on the notebook entry so it
          // survives a page refresh. Best-effort — a failed write just
          // means the next reload won't have the judgment cached.
          const key = q ? getQuestionKey(q, idx) : "";
          const eId = key ? entryIds[key] : undefined;
          if (eId && finalText.trim().length > 0) {
            void updateNotebookEntry(eId, { ai_judgment: finalText }).catch(
              () => {},
            );
          }
        },
        onError: (message) => {
          setJudgments((prev) => {
            const current = prev[idx] ?? EMPTY_JUDGMENT;
            return {
              ...prev,
              [idx]: { ...current, isStreaming: false, error: message },
            };
          });
          judgeHandlesRef.current.delete(idx);
        },
      },
    );
    judgeHandlesRef.current.set(idx, handle);
  }, [answers, entryIds, idx, language, q]);

  const handleToggleAnswerView = useCallback(
    (view: AnswerView) => {
      setAnswerViews((prev) => ({ ...prev, [idx]: view }));
    },
    [idx],
  );

  // ── Follow-up (right-side viewer tab) ─────────────────────────
  //
  // Clicking "Follow-up" no longer expands an in-place panel — it opens
  // a dedicated tab in the SessionViewerPanel on the right, where a
  // chat-page-style UI runs the full ``chat`` capability against a
  // session that pins this question + answer + judgment as fixed
  // context. State for that chat lives in ``QuizFollowupProvider`` so
  // it survives tab toggles and is also reflected in this card's
  // message-count badge.

  const handleOpenFollowup = useCallback(() => {
    if (!q) return;
    const key = getQuestionKey(q, idx);
    const answer = answers[idx] ?? EMPTY_ANSWER;
    const judgment = judgments[idx] ?? EMPTY_JUDGMENT;
    followupController.openFollowupTab({
      questionKey: key,
      question: q,
      userAnswer: getUserAnswer(q, answer),
      isCorrect: isAutoGradable(q) ? isAnswerCorrect(q, answer) : null,
      answerImages: answer.images.map((image) => ({
        id: image.id,
        base64: image.base64,
        url: image.url,
        filename: image.filename,
        mime: image.mime,
        previewUrl: image.previewUrl,
      })),
      aiJudgment: judgment.text,
      parentQuizSessionId: sessionId ?? null,
      notebookEntryId: entryIds[key] ?? null,
      followupSessionId: followupSessionIds[key] ?? null,
      language,
      tabLabel: `Q${idx + 1} · 追问对话`,
    });
  }, [
    answers,
    entryIds,
    followupController,
    followupSessionIds,
    idx,
    judgments,
    language,
    q,
    sessionId,
  ]);

  if (!q) return null;

  const currentEntryId = entryIds[questionKey];
  const currentBookmarked = bookmarked[questionKey] ?? false;
  const showCategoryDropdown = categoryDropdownKey === questionKey;

  const navBtnStyle: React.CSSProperties = {
    display: "inline-flex", height: 32, width: 32, flexShrink: 0,
    alignItems: "center", justifyContent: "center", borderRadius: 6,
    border: `1px solid ${BORDER}`, background: "rgba(241,245,249,.6)",
    color: FG, boxShadow: "0 1px 2px 0 rgba(0,0,0,0.05)", transition: "all .15s",
    cursor: "pointer", padding: 0,
  };

  return (
    <div
      style={{
        overflow: "hidden", borderRadius: 12, border: `1px solid ${BORDER}`,
        background: CARD,
      }}
      data-testid="quiz-viewer"
    >
      <QuizViewerStyleBlock />
      <div
        style={{
          display: "flex", alignItems: "center", gap: 8,
          borderBottom: `1px solid ${BORDER}`, padding: "8px 12px",
        }}
      >
        <button
          type="button"
          onClick={() => setIdx((value) => Math.max(0, value - 1))}
          disabled={idx === 0}
          title="上一题"
          aria-label="上一题"
          className="qv-navbtn"
          style={navBtnStyle}
        >
          <LeftOutlined style={{ fontSize: 16, fontWeight: "bold" }} />
        </button>
        <span style={{ fontSize: 11, fontWeight: 600, color: MUTED_FG }}>
          {completedCount}/{total}
        </span>
        <div style={{ display: "flex", flex: 1, flexWrap: "wrap", gap: 4 }}>
          {questions.map((question, questionIndex) => {
            const answer = answers[questionIndex];
            const isCurrent = questionIndex === idx;
            const done = answer?.submitted;
            const hasThread =
              Boolean(
                followupThreads[getQuestionKey(question, questionIndex)]
                  ?.sessionId,
              ) ||
              Boolean(
                followupThreads[getQuestionKey(question, questionIndex)]
                  ?.messages.length,
              );
            // Color the chip by correctness for auto-gradable types
            // (choice, concept, fill_in_blank). For open-ended types
            // (short_answer / written / coding) we'd be guessing — keep
            // the neutral "completed" tint so we don't mark a thoughtful
            // answer red just because it doesn't match the reference
            // string verbatim.
            const autoGradable = isAutoGradable(question);
            const correctness: "correct" | "incorrect" | null =
              done && answer && autoGradable
                ? isAnswerCorrect(question, answer)
                  ? "correct"
                  : "incorrect"
                : null;
            const chipStyle: React.CSSProperties = isCurrent
              ? { background: PRIMARY, color: "#ffffff", boxShadow: "0 1px 2px 0 rgba(0,0,0,0.05)" }
              : correctness === "correct"
                ? { background: "#dcfce7", color: "#15803d" }
                : correctness === "incorrect"
                  ? { background: "#fee2e2", color: "#b91c1c" }
                  : done
                    ? { background: "rgba(79,70,229,.15)", color: PRIMARY }
                    : { background: MUTED, color: MUTED_FG };
            return (
              <button
                key={question.question_id || questionIndex}
                onClick={() => setIdx(questionIndex)}
                className={
                  correctness === "correct"
                    ? "qv-chip-g"
                    : correctness === "incorrect"
                      ? "qv-chip-r"
                      : done
                        ? ""
                        : "qv-chip-m"
                }
                style={{
                  display: "flex", height: 24, width: 24, alignItems: "center",
                  justifyContent: "center", borderRadius: 999, fontSize: 10,
                  fontWeight: 600, transition: "all .15s", border: "none",
                  cursor: "pointer", padding: 0, ...chipStyle,
                }}
              >
                {/* For graded auto-gradable questions we *replace* the ✓
                    with the sequence number — the color is the
                    completion signal, and the digit lets the learner
                    navigate to a specific question by index. The
                    followup-thread dot still rides along when the
                    learner asked a follow-up about this question. */}
                {done && !isCurrent && !autoGradable ? (
                  hasThread ? (
                    <span style={{ position: "relative", display: "inline-flex" }}>
                      <CheckOutlined style={{ fontSize: 10 }} />
                      <span
                        style={{
                          position: "absolute", right: -4, top: -4, height: 6,
                          width: 6, borderRadius: 999, background: PRIMARY,
                        }}
                      />
                    </span>
                  ) : (
                    <CheckOutlined style={{ fontSize: 10 }} />
                  )
                ) : hasThread && done && !isCurrent ? (
                  <span style={{ position: "relative", display: "inline-flex" }}>
                    {questionIndex + 1}
                    <span
                      style={{
                        position: "absolute", right: -4, top: -4, height: 6,
                        width: 6, borderRadius: 999, background: PRIMARY,
                      }}
                    />
                  </span>
                ) : (
                  questionIndex + 1
                )}
              </button>
            );
          })}
        </div>
        <button
          type="button"
          onClick={() => setIdx((value) => Math.min(total - 1, value + 1))}
          disabled={idx === total - 1}
          title="下一个"
          aria-label="下一个"
          className="qv-navbtn"
          style={navBtnStyle}
        >
          <RightOutlined style={{ fontSize: 16, fontWeight: "bold" }} />
        </button>
      </div>
      <div style={{ height: 2, background: MUTED }}>
        <div
          style={{
            height: "100%", background: PRIMARY,
            transition: "all .3s", width: `${navigationProgress}%`,
          }}
        />
      </div>

      <div style={{ padding: "12px 16px" }}>
        <div
          style={{
            marginBottom: 8, display: "flex", alignItems: "center",
            justifyContent: "space-between", gap: 8,
          }}
        >
          <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 6 }}>
            <span
              style={{
                borderRadius: 6, background: MUTED, padding: "2px 6px",
                fontSize: 10, fontWeight: 500, textTransform: "uppercase",
                color: MUTED_FG,
              }}
            >
              Q{idx + 1}
            </span>
            {q.difficulty && (
              <span
                style={{
                  borderRadius: 6, padding: "2px 6px", fontSize: 10,
                  fontWeight: 500, textTransform: "uppercase",
                  background:
                    q.difficulty === "hard"
                      ? "#fef2f2"
                      : q.difficulty === "medium"
                        ? "#fffbeb"
                        : "#f0fdf4",
                  color:
                    q.difficulty === "hard"
                      ? "#dc2626"
                      : q.difficulty === "medium"
                        ? "#d97706"
                        : "#16a34a",
                }}
              >
                {q.difficulty}
              </span>
            )}
            <span
              style={{
                borderRadius: 6, background: MUTED, padding: "2px 6px",
                fontSize: 10, fontWeight: 500, color: MUTED_FG,
              }}
            >
              {q.question_type}
            </span>
          </div>

          {ans.submitted && (
            <div style={{ position: "relative", display: "flex", alignItems: "center", gap: 4 }}>
              <button
                onClick={handleToggleBookmark}
                disabled={!currentEntryId}
                title={currentBookmarked ? "取消收藏" : "收藏"}
                className="qv-bkm"
                style={{
                  borderRadius: 8, padding: 6, border: "none", background: "transparent",
                  cursor: currentEntryId ? "pointer" : "not-allowed", opacity: currentEntryId ? 1 : 0.3,
                  transition: "all .15s",
                  color: currentBookmarked ? "#f59e0b" : MUTED_FG,
                  transform: currentBookmarked ? "scale(1.1)" : "none",
                }}
              >
                <StarOutlined
                  style={{ fontSize: 17 }}
                  // 原仓 lucide Bookmark 以 fill 表达已收藏态；antd 星形图标同语义。
                />
              </button>
              <button
                onClick={handleOpenCategoryDropdown}
                disabled={!currentEntryId}
                title="添加到分类"
                className="qv-folder"
                style={{
                  borderRadius: 8, padding: 6, border: "none", background: "transparent",
                  color: MUTED_FG, cursor: currentEntryId ? "pointer" : "not-allowed",
                  opacity: currentEntryId ? 1 : 0.3, transition: "all .15s",
                }}
              >
                <FolderAddOutlined style={{ fontSize: 16 }} />
              </button>
              <button
                onClick={handleOpenFollowup}
                title="追问对话"
                style={{
                  marginLeft: 4, display: "inline-flex", alignItems: "center", gap: 4,
                  borderRadius: 8, border: "1px solid rgba(79,70,229,.6)",
                  background: "rgba(79,70,229,.1)", padding: "4px 8px", fontSize: 12,
                  fontWeight: 500, color: PRIMARY, cursor: "pointer",
                  transition: "all .15s",
                }}
                className="qv-judge"
              >
                <MessageOutlined style={{ fontSize: 13 }} />
                追问对话
                {(() => {
                  const tcount =
                    followupThreads[questionKey]?.messages.filter(
                      (m) => m.role !== "system",
                    ).length ?? 0;
                  return tcount > 0 ? (
                    <span
                      style={{
                        borderRadius: 999, background: "rgba(79,70,229,.25)",
                        padding: "0 6px", fontSize: 10,
                      }}
                    >
                      {tcount}
                    </span>
                  ) : null;
                })()}
              </button>

              {showCategoryDropdown && (
                <div
                  style={{
                    position: "absolute", right: 0, top: 32, zIndex: 20, width: 192,
                    borderRadius: 8, border: `1px solid ${BORDER}`, background: CARD,
                    padding: "4px 0", boxShadow: "0 10px 15px -3px rgba(0,0,0,.1), 0 4px 6px -4px rgba(0,0,0,.1)",
                  }}
                >
                  {categories.length > 0 && (
                    <div style={{ maxHeight: 160, overflowY: "auto" }}>
                      {categories.map((cat) => (
                        <button
                          key={cat.id}
                          disabled={categoryBusy}
                          onClick={() => void handleAddToCategory(cat.id)}
                          className="qv-catitem"
                          style={{
                            display: "flex", width: "100%", alignItems: "center", gap: 8,
                            padding: "6px 12px", textAlign: "left", fontSize: 12,
                            color: FG, background: "transparent", border: "none",
                            cursor: categoryBusy ? "not-allowed" : "pointer",
                            transition: "all .15s",
                          }}
                        >
                          {cat.name}
                        </button>
                      ))}
                    </div>
                  )}
                  <div style={{ borderTop: `1px solid ${BORDER}`, padding: "6px 8px" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
                      <input
                        value={newCategoryName}
                        onChange={(e) => setNewCategoryName(e.target.value)}
                        onKeyDown={(e) =>
                          e.key === "Enter" && void handleCreateAndAdd()
                        }
                        placeholder="新分类..."
                        className="qv-placeholder"
                        style={{
                          flex: 1, borderRadius: 4, border: `1px solid ${BORDER}`,
                          background: BG, padding: "4px 8px", fontSize: 11,
                          color: FG, outline: "none",
                        }}
                      />
                      <button
                        disabled={!newCategoryName.trim() || categoryBusy}
                        onClick={() => void handleCreateAndAdd()}
                        style={{
                          borderRadius: 4, padding: 4, border: "none",
                          background: "transparent", color: PRIMARY,
                          cursor: !newCategoryName.trim() || categoryBusy ? "not-allowed" : "pointer",
                          opacity: !newCategoryName.trim() || categoryBusy ? 0.3 : 1,
                        }}
                      >
                        {categoryBusy ? (
                          <LoadingOutlined style={{ fontSize: 12 }} />
                        ) : (
                          <PlusOutlined style={{ fontSize: 12 }} />
                        )}
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        <div style={{ marginBottom: 12, fontSize: 14, lineHeight: 1.625 }}>
          <MarkdownRenderer
            content={q.question}
            variant="prose"
            className=""
          />
        </div>

        {isChoice ? (
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            {Object.entries(q.options!).map(([key, text]) => {
              const isSelected = ans.selected === key;
              const correctKey = q.correct_answer
                .trim()
                .charAt(0)
                .toUpperCase();
              const isCorrectOption = key.toUpperCase() === correctKey;
              const showFeedback = ans.submitted;

              let optionStyle: React.CSSProperties = {
                border: `1px solid ${BORDER}`, background: BG, color: FG,
              };

              if (isSelected && !showFeedback) {
                optionStyle = {
                  border: `1px solid ${PRIMARY}`, background: "rgba(79,70,229,.06)",
                  color: FG, boxShadow: "0 0 0 1px rgba(79,70,229,.2)",
                };
              } else if (showFeedback && isCorrectOption) {
                optionStyle = {
                  border: "1px solid #22c55e", background: "#f0fdf4", color: "#166534",
                };
              } else if (showFeedback && isSelected && !isCorrectOption) {
                optionStyle = {
                  border: "1px solid #f87171", background: "#fef2f2", color: "#b91c1c",
                };
              }

              return (
                <button
                  key={key}
                  disabled={ans.submitted}
                  onClick={() => updateAnswer({ selected: key })}
                  className="qv-opt"
                  style={{
                    display: "flex", width: "100%", alignItems: "flex-start", gap: 10,
                    borderRadius: 8, padding: "8px 12px", textAlign: "left",
                    fontSize: 13, transition: "all .15s", cursor: "pointer",
                    ...optionStyle,
                  }}
                >
                  <span
                    style={{
                      marginTop: 1, display: "flex", height: 20, width: 20, flexShrink: 0,
                      alignItems: "center", justifyContent: "center", borderRadius: 999,
                      border: `1px solid ${
                        isSelected && !showFeedback
                          ? PRIMARY
                          : showFeedback && isCorrectOption
                            ? "#22c55e"
                            : showFeedback && isSelected && !isCorrectOption
                              ? "#f87171"
                              : BORDER
                      }`,
                      background:
                        isSelected && !showFeedback
                          ? PRIMARY
                          : showFeedback && isCorrectOption
                            ? "#22c55e"
                            : showFeedback && isSelected && !isCorrectOption
                              ? "#f87171"
                              : "transparent",
                      color:
                        isSelected && !showFeedback
                          ? "#ffffff"
                          : showFeedback && (isCorrectOption || (isSelected && !isCorrectOption))
                            ? "#ffffff"
                            : MUTED_FG,
                      fontSize: 11, fontWeight: 700,
                    }}
                  >
                    {showFeedback && isCorrectOption ? (
                      <CheckOutlined style={{ fontSize: 10 }} />
                    ) : (
                      key
                    )}
                  </span>
                  <div style={{ minWidth: 0, lineHeight: 1.625 }}>
                    <MarkdownRenderer
                      content={text}
                      variant="compact"
                      enableMath
                    />
                  </div>
                </button>
              );
            })}
          </div>
        ) : isConcept ? (
          // Concept (true/false) — two large buttons.
          (() => {
            const correctTF = resolveConceptAnswer(q.correct_answer);
            const showFeedback = ans.submitted;
            const renderTFButton = (key: "true" | "false", label: string) => {
              const isSelected = ans.selected === key;
              const isCorrect = correctTF === key;
              let style: React.CSSProperties = {
                border: `1px solid ${BORDER}`, background: BG, color: FG,
              };
              if (isSelected && !showFeedback) {
                style = {
                  border: `1px solid ${PRIMARY}`, background: "rgba(79,70,229,.08)",
                  color: FG, boxShadow: "0 0 0 1px rgba(79,70,229,.25)",
                };
              } else if (showFeedback && isCorrect) {
                style = {
                  border: "1px solid #22c55e", background: "#f0fdf4", color: "#166534",
                };
              } else if (showFeedback && isSelected && !isCorrect) {
                style = {
                  border: "1px solid #f87171", background: "#fef2f2", color: "#b91c1c",
                };
              }
              return (
                <button
                  key={key}
                  type="button"
                  disabled={ans.submitted}
                  onClick={() => updateAnswer({ selected: key })}
                  className="qv-tf"
                  style={{
                    display: "flex", flex: 1, alignItems: "center", justifyContent: "center",
                    gap: 8, borderRadius: 8, padding: "12px 12px", fontSize: 14,
                    fontWeight: 600, transition: "all .15s", cursor: "pointer",
                    ...style,
                  }}
                >
                  {label}
                </button>
              );
            };
            return (
              <div style={{ display: "flex", gap: 8 }}>
                {renderTFButton("true", "对")}
                {renderTFButton("false", "错")}
              </div>
            );
          })()
        ) : isFillBlank ? (
          // Fill-in-the-blank — single-line input. The question text
          // already contains the literal ``____`` placeholder which the
          // learner sees in the rendered question above; this is just
          // where they type the missing word/phrase.
          <div>
            <div
              style={{
                marginBottom: 4, fontSize: 10, fontWeight: 600, textTransform: "uppercase",
                letterSpacing: "0.05em", color: "rgba(100,116,139,.7)",
              }}
            >
              填空题
            </div>
            <input
              type="text"
              value={ans.typed}
              onChange={(event) => updateAnswer({ typed: event.target.value })}
              disabled={ans.submitted}
              placeholder="在此输入答案…"
              className="qv-placeholder qv-fill"
              style={{
                width: "100%", borderRadius: 8, border: `1px solid ${BORDER}`,
                padding: "8px 12px", fontSize: 13, outline: "none",
                transition: "all .15s", boxSizing: "border-box",
                background: ans.submitted ? MUTED : BG,
                color: FG,
              }}
            />
          </div>
        ) : (
          // Free-text branches: short_answer / written / coding.
          // Different default heights so essay-style "written" has more
          // room than a concept-style short answer.
          <div>
            <textarea
              value={ans.typed}
              onChange={(event) => updateAnswer({ typed: event.target.value })}
              disabled={ans.submitted}
              rows={
                q.question_type === "coding"
                  ? 6
                  : q.question_type === "written"
                    ? 5
                    : 3
              }
              placeholder={
                q.question_type === "coding"
                  ? "在此输入代码…"
                  : "在此输入答案…"
              }
              className="qv-placeholder qv-fill"
              style={{
                width: "100%", resize: "vertical", borderRadius: 8,
                border: `1px solid ${BORDER}`, padding: "8px 12px", fontSize: 13,
                outline: "none", transition: "all .15s", boxSizing: "border-box",
                background: ans.submitted ? MUTED : BG,
                color: FG,
                fontFamily: q.question_type === "coding" ? "monospace" : undefined,
              }}
            />
          </div>
        )}

        {/* Image-as-answer attachment — only offered for question types
            without an auto-gradable answer (short_answer / written /
            coding). These are also the types that benefit most from a
            multimodal AI judgment over handwritten work. */}
        {!isGradable && (
          <div style={{ marginTop: 8, display: "flex", flexDirection: "column", gap: 8 }}>
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              multiple
              onChange={(event) => void handleImageChange(event)}
              style={{ display: "none" }}
            />
            {ans.images.length > 0 && (
              <div className="qv-imggrid">
                {ans.images.map((image) => {
                  const previewSrc =
                    image.previewUrl ?? resolveImageSrc(image.url);
                  return (
                    <div
                      key={image.id}
                      className="qv-imggroup"
                      style={{
                        position: "relative", overflow: "hidden", borderRadius: 6,
                        border: `1px solid ${BORDER}`, background: BG,
                      }}
                    >
                      {previewSrc ? (
                        <img
                          src={previewSrc}
                          alt={image.filename}
                          style={{ height: 96, width: "100%", objectFit: "cover" }}
                        />
                      ) : (
                        <div
                          style={{
                            display: "flex", height: 96, width: "100%",
                            alignItems: "center", justifyContent: "center",
                            fontSize: 10, color: MUTED_FG,
                          }}
                        >
                          {image.filename}
                        </div>
                      )}
                      <div
                        style={{
                          position: "absolute", left: 0, right: 0, bottom: 0,
                          overflow: "hidden", textOverflow: "ellipsis",
                          whiteSpace: "nowrap", background: "rgba(0,0,0,.45)",
                          padding: "2px 6px", fontSize: 10, color: "#ffffff",
                        }}
                      >
                        {image.filename}
                      </div>
                      {!ans.submitted && (
                        <button
                          type="button"
                          onClick={() => handleRemoveImage(image.id)}
                          title="移除图片"
                          className="qv-imgdel"
                          style={{
                            position: "absolute", right: 4, top: 4, display: "inline-flex",
                            height: 20, width: 20, alignItems: "center",
                            justifyContent: "center", borderRadius: 999,
                            background: "rgba(0,0,0,.55)", color: "#ffffff",
                            border: "none", cursor: "pointer",
                          }}
                        >
                          <CloseOutlined style={{ fontSize: 10 }} />
                        </button>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
            {!ans.submitted && (
              <button
                type="button"
                onClick={handlePickImageClick}
                className="qv-imgpick"
                style={{
                  display: "inline-flex", alignItems: "center", gap: 6,
                  borderRadius: 6, border: `1px dashed ${BORDER}`, background: BG,
                  padding: "6px 10px", fontSize: 12, color: MUTED_FG,
                  cursor: "pointer", transition: "all .15s", width: "fit-content",
                }}
              >
                <PictureOutlined style={{ fontSize: 13 }} />
                {ans.images.length === 0
                  ? "上传图片作答"
                  : "继续添加图片"}
              </button>
            )}
          </div>
        )}

        <div style={{ marginTop: 12, display: "flex", flexWrap: "wrap", alignItems: "center", gap: 8 }}>
          {!ans.submitted ? (
            <button
              onClick={handleSubmit}
              disabled={(() => {
                if (isChoice || isConcept) return !ans.selected;
                // For free-text / fill-blank, require a typed answer; for
                // non-auto-gradable types, an image attachment also counts.
                if (ans.typed.trim()) return false;
                if (!isGradable && ans.images.length > 0) return false;
                return true;
              })()}
              style={{
                display: "inline-flex", alignItems: "center", gap: 6,
                borderRadius: 8, background: PRIMARY, padding: "6px 12px",
                fontSize: 12, fontWeight: 500, color: "#ffffff",
                transition: "opacity .15s", border: "none", cursor: "pointer",
                opacity: (() => {
                  if (isChoice || isConcept) return !ans.selected ? 0.3 : 1;
                  if (ans.typed.trim()) return 1;
                  if (!isGradable && ans.images.length > 0) return 1;
                  return 0.3;
                })(),
              }}
            >
              <EyeOutlined style={{ fontSize: 13 }} />
              检查答案
            </button>
          ) : (
            <>
              {isGradable && isCorrect !== null && (
                <span
                  style={{
                    borderRadius: 6, padding: "2px 8px", fontSize: 11, fontWeight: 600,
                    background: isCorrect ? "#dcfce7" : "#fee2e2",
                    color: isCorrect ? "#15803d" : "#b91c1c",
                  }}
                >
                  {isCorrect ? "正确" : "错误"}
                </span>
              )}
              <button
                onClick={handleReset}
                className="qv-retry"
                style={{
                  display: "inline-flex", alignItems: "center", gap: 4,
                  borderRadius: 8, background: MUTED, padding: "6px 10px",
                  fontSize: 12, fontWeight: 500, color: MUTED_FG,
                  transition: "all .15s", border: "none", cursor: "pointer",
                }}
              >
                <RedoOutlined style={{ fontSize: 11 }} />
                重试
              </button>
              {(() => {
                const j = judgments[idx] ?? EMPTY_JUDGMENT;
                const hasJudgment = j.text.length > 0 || j.error !== null;
                return (
                  <button
                    onClick={handleAiJudge}
                    disabled={j.isStreaming}
                    className="qv-judge"
                    style={{
                      display: "inline-flex", alignItems: "center", gap: 4,
                      borderRadius: 8, border: "1px solid rgba(79,70,229,.6)",
                      background: "rgba(79,70,229,.1)", padding: "6px 10px",
                      fontSize: 12, fontWeight: 500, color: PRIMARY,
                      transition: "all .15s", cursor: j.isStreaming ? "not-allowed" : "pointer",
                    }}
                  >
                    {j.isStreaming ? (
                      <LoadingOutlined style={{ fontSize: 11 }} />
                    ) : (
                      <ThunderboltOutlined style={{ fontSize: 11 }} />
                    )}
                    {j.isStreaming
                      ? "评判中…"
                      : hasJudgment
                        ? "重新评判"
                        : "AI 评判"}
                  </button>
                );
              })()}
            </>
          )}
        </div>

        {ans.submitted &&
          (() => {
            const judgment = judgments[idx] ?? EMPTY_JUDGMENT;
            const hasJudgment =
              judgment.text.length > 0 ||
              judgment.error !== null ||
              judgment.isStreaming;
            // Default to the reference tab; flip to the judgment tab when
            // the learner first triggers a judge run (set in handleAiJudge).
            const view: AnswerView =
              answerViews[idx] ?? (hasJudgment ? "judgment" : "reference");
            const showReferenceAnswer =
              !isChoice && !isConcept && !!q.correct_answer;
            const showAnyReference = showReferenceAnswer || !!q.explanation;
            if (!showAnyReference && !hasJudgment) return null;

            const collapsed = reviewCollapsed[idx] === true;
            const toggleCollapsed = () =>
              setReviewCollapsed((prev) => ({ ...prev, [idx]: !collapsed }));

            return (
              <div
                style={{
                  marginTop: 12, display: "flex", flexDirection: "column", gap: 8,
                  borderRadius: 8, border: `1px solid ${BORDER}`, background: BG,
                  padding: "10px 12px",
                }}
              >
                {/* Header bar — when there's no tab strip (only one of
                    reference/judgment is showing) we still render this so
                    the collapse chevron has a home. */}
                {hasJudgment && showAnyReference ? (
                  <div
                    style={{
                      display: "flex", alignItems: "center", gap: 4,
                      borderBottom: "1px solid rgba(226,232,240,.7)", paddingBottom: 6,
                    }}
                  >
                    <button
                      type="button"
                      onClick={() => handleToggleAnswerView("reference")}
                      className={view === "reference" ? "qv-viewtab-on" : "qv-viewtab"}
                      style={{
                        borderRadius: 6, padding: "2px 8px", fontSize: 11,
                        fontWeight: 500, transition: "all .15s", border: "none",
                        cursor: "pointer",
                        background: view === "reference" ? "rgba(79,70,229,.12)" : "transparent",
                        color: view === "reference" ? PRIMARY : MUTED_FG,
                      }}
                    >
                      参考答案
                    </button>
                    <button
                      type="button"
                      onClick={() => handleToggleAnswerView("judgment")}
                      className={view === "judgment" ? "qv-viewtab-on" : "qv-viewtab"}
                      style={{
                        display: "inline-flex", alignItems: "center", gap: 4,
                        borderRadius: 6, padding: "2px 8px", fontSize: 11,
                        fontWeight: 500, transition: "all .15s", border: "none",
                        cursor: "pointer",
                        background: view === "judgment" ? "rgba(79,70,229,.12)" : "transparent",
                        color: view === "judgment" ? PRIMARY : MUTED_FG,
                      }}
                    >
                      <ThunderboltOutlined style={{ fontSize: 10 }} />
                      AI 评判
                      {judgment.isStreaming && (
                        <LoadingOutlined style={{ fontSize: 10 }} />
                      )}
                    </button>
                    <button
                      type="button"
                      onClick={toggleCollapsed}
                      aria-label={collapsed ? "展开" : "收起"}
                      title={collapsed ? "展开" : "收起"}
                      className="qv-collapse"
                      style={{
                        marginLeft: "auto", display: "inline-flex", height: 20,
                        width: 20, alignItems: "center", justifyContent: "center",
                        borderRadius: 6, color: MUTED_FG, transition: "all .15s",
                        border: "none", background: "transparent", cursor: "pointer",
                      }}
                    >
                      <DownOutlined
                        className={`qv-chevron ${collapsed ? "qv-chevron-collapsed" : ""}`}
                        style={{ fontSize: 11 }}
                      />
                    </button>
                  </div>
                ) : (
                  <button
                    type="button"
                    onClick={toggleCollapsed}
                    style={{
                      display: "flex", width: "100%", alignItems: "center", gap: 4,
                      paddingBottom: 6, textAlign: "left", border: "none",
                      background: "transparent", cursor: "pointer",
                    }}
                  >
                    <span
                      style={{
                        fontSize: 10, fontWeight: 600, textTransform: "uppercase",
                        letterSpacing: "0.05em", color: MUTED_FG,
                      }}
                    >
                      {hasJudgment ? "AI 评判" : "参考答案"}
                    </span>
                    <DownOutlined
                      className={`qv-chevron ${collapsed ? "qv-chevron-collapsed" : ""}`}
                      style={{ marginLeft: "auto", fontSize: 11, color: MUTED_FG }}
                    />
                  </button>
                )}

                {collapsed ? null : hasJudgment && view === "judgment" ? (
                  <div>
                    <div
                      style={{
                        marginBottom: 4, display: "flex", alignItems: "center", gap: 4,
                        fontSize: 10, fontWeight: 600, textTransform: "uppercase",
                        letterSpacing: "0.05em", color: MUTED_FG,
                      }}
                    >
                      <ThunderboltOutlined style={{ fontSize: 10 }} />
                      AI 评判
                      {judgment.isStreaming && (
                        <LoadingOutlined
                          style={{ fontSize: 10, color: PRIMARY }}
                        />
                      )}
                    </div>
                    {judgment.error ? (
                      <div
                        style={{
                          borderRadius: 6, border: "1px solid #fecaca",
                          background: "#fef2f2", padding: "4px 8px", fontSize: 12,
                          color: "#b91c1c",
                        }}
                      >
                        {judgment.error}
                      </div>
                    ) : judgment.text ? (
                      <div style={{ fontSize: 13, lineHeight: 1.625, color: FG }}>
                        <MarkdownRenderer
                          content={judgment.text}
                          variant="prose"
                        />
                      </div>
                    ) : (
                      <div style={{ fontSize: 12, color: MUTED_FG }}>
                        评判中…
                      </div>
                    )}
                  </div>
                ) : (
                  <>
                    {showReferenceAnswer && (
                      <div>
                        <div
                          style={{
                            marginBottom: 4, fontSize: 10, fontWeight: 600,
                            textTransform: "uppercase", letterSpacing: "0.05em",
                            color: MUTED_FG,
                          }}
                        >
                          参考答案
                        </div>
                        <div style={{ fontSize: 13, lineHeight: 1.625, color: FG }}>
                          <MarkdownRenderer
                            content={
                              q.question_type === "coding" &&
                              !q.correct_answer.trimStart().startsWith("```")
                                ? `\`\`\`python\n${q.correct_answer}\n\`\`\``
                                : q.correct_answer
                            }
                            variant="prose"
                          />
                        </div>
                      </div>
                    )}
                    {q.explanation && (
                      <div>
                        <div
                          style={{
                            marginBottom: 4, fontSize: 10, fontWeight: 600,
                            textTransform: "uppercase", letterSpacing: "0.05em",
                            color: MUTED_FG,
                          }}
                        >
                          解析
                        </div>
                        <div style={{ fontSize: 13, lineHeight: 1.625, color: MUTED_FG }}>
                          <MarkdownRenderer
                            content={q.explanation}
                            variant="prose"
                          />
                        </div>
                      </div>
                    )}
                  </>
                )}
              </div>
            );
          })()}
      </div>
    </div>
  );
}

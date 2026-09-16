/**
 * 桌面同名件 1:1（复刻自 DeepTutor 原仓 web/components/chat/home/ComposerInput.tsx，533 行）。
 * 替换点：删除 "use client"；lucide Bot/Check/UserRound→RobotOutlined/CheckOutlined/
 * UserOutlined；ChatSpaceMenu→./ChatSpaceMenu、agentGlyph→./agent-icons、
 * composer-keyboard/use-ime-composing→../../admin/（批8 件）、use-auto-sized-textarea
 * →./use-auto-sized-textarea；Tailwind→内联样式（token 见 dtStyle.ts）；hover→
 * onMouseEnter/Leave 直写 style；t() 译文：命中 zh/app.json 直出（"Talk to an agent"
 * →与智能体对话、"No connected agents — connect one in My Agents."→尚未连接智能体
 * —— 请在「我的智能体」中连接。、"No matching agent"→没有匹配的智能体、
 * "How can I help you today?"→今天我能帮您什么？、可视化占位→描述你想可视化的图表、
 * 示意图或动画...），"Commands"/"Switch the persona for this chat session" 未命中
 * 按 i18next 回退直出原 key。@提及/斜杠命令/IME/外点关闭/32k 上限逐字未改；
 * suppressHydrationWarning 为 Next SSR 专有属性，删除（CRA 无 hydration 比对）。
 */
import {
  forwardRef,
  memo,
  useCallback,
  useEffect,
  useImperativeHandle,
  useMemo,
  useRef,
  useState,
  type RefObject,
} from "react";
import { RobotOutlined, CheckOutlined, UserOutlined } from "@ant-design/icons";
import ChatSpaceMenu, {
  type ChatSpaceSelectionCounts,
} from "./ChatSpaceMenu";
import { agentGlyph } from "./agent-icons";
import { shouldSubmitOnEnter } from "../../admin/composer-keyboard";
import { useAutoSizedTextarea } from "./use-auto-sized-textarea";
import { useImeComposing } from "../../admin/use-ime-composing";
import { DT, ellipsis } from "./dtStyle";

interface ComposerInputProps {
  // React 18 类型下沿用 RefObject<HTMLTextAreaElement>（18.3 中 current 即
  // HTMLTextAreaElement|null，与原仓 React 19 的 `| null` 写法语义等价）。
  textareaRef: RefObject<HTMLTextAreaElement>;
  isVisualizeMode: boolean;
  isStreaming?: boolean;
  // When true, parent has attachments/references queued and will accept a
  // send even if the text body is empty. Without this, Enter would silently
  // do nothing for an attachment-only message.
  canSendEmpty: boolean;
  onSend: (content: string) => void;
  onInputChange: (content: string) => void;
  onPaste: (e: React.ClipboardEvent) => void;
  selectedCounts: ChatSpaceSelectionCounts;
  /**
   * Hide the Knowledge entry in the @ menu. Knowledge now lives in the
   * toolbar KnowledgeSelector chip, so this is currently always false —
   * kept as a prop in case a surface wants the @ entry back.
   */
  knowledgeAvailable: boolean;
  /** Hide the Persona entry (main chat: persona has its own selector). */
  personaAvailable: boolean;
  /**
   * Connected subagents selectable via the ``@`` mention. When provided, ``@``
   * opens an agent picker (the main-chat behavior) instead of the Space menu;
   * surfaces that omit this (e.g. the quiz follow-up) keep the Space menu on @.
   */
  connectedAgents?: { name: string; kind?: string }[];
  selectedAgent?: string | null;
  onSelectAgent?: (name: string | null) => void;
  onSelectAttach: () => void;
  onSelectKnowledge?: () => void;
  onSelectNotebookPicker: () => void;
  onSelectBookPicker: () => void;
  onSelectHistoryPicker: () => void;
  onSelectAgentsPicker?: () => void;
  /** Hide the My Agents entry (e.g. the quiz follow-up surface). */
  agentsAvailable?: boolean;
  onSelectQuestionBankPicker: () => void;
  onSelectPersonaPicker: () => void;
  onSelectMemoryPicker: () => void;
  /**
   * Wires the `/persona` slash command. Typing "/" (then any prefix of
   * "persona") at the start of an empty composer pops a command hint;
   * selecting it clears the input and invokes this callback to open the
   * session persona selector. Omitted on surfaces without session
   * personas (e.g. the quiz follow-up), which disables the slash popup.
   */
  onOpenPersonaSelector?: () => void;
  /**
   * Override the default placeholder. When unset, falls back to the
   * main chat ("How can I help you today?") / visualize defaults.
   */
  placeholder?: string;
  /**
   * Minimum textarea height in pixels. The auto-sized hook grows the
   * textarea past this as the user types. Bumped on the empty-state
   * composer so the resting box looks inviting rather than crammed.
   */
  minHeight?: number;
}

export interface ComposerInputHandle {
  clear: () => void;
  getValue: () => string;
  /**
   * Programmatically replace the textarea contents (used by the
   * ``AskUserOptions`` chip click handler — picks an option, prefills
   * the composer, leaves it to the user to edit/send rather than
   * auto-firing the message).
   */
  setValue: (value: string) => void;
}

export function shouldOpenAtPopup(value: string, cursorPos: number): boolean {
  const prefix = value.slice(0, cursorPos);
  return /(^|\s)@[^\s]*$/.test(prefix);
}

export function stripTrailingAtMention(value: string): string {
  return value.replace(/(^|\s)@[^\s]*$/, "$1").replace(/\s+$/, "");
}

/** The text typed after a trailing ``@`` (the agent-mention query), or "". */
export function atMentionQuery(value: string, cursorPos: number): string {
  const match = /(^|\s)@([^\s]*)$/.exec(value.slice(0, cursorPos));
  return match ? match[2] : "";
}

/**
 * `/persona` slash-command detection (Codex-style: command position is the
 * very start of the input, not mid-text like @ mentions). Active while the
 * text before the cursor is "/" plus any prefix of "persona" — `/x` or a
 * trailing space closes the popup.
 */
export function shouldOpenSlashPopup(
  value: string,
  cursorPos: number,
): boolean {
  const prefix = value.slice(0, cursorPos);
  const match = /^\/([a-z]*)$/i.exec(prefix);
  if (!match) return false;
  return "persona".startsWith(match[1].toLowerCase());
}

export const ComposerInput = memo(
  forwardRef<ComposerInputHandle, ComposerInputProps>(function ComposerInput(
    {
      textareaRef,
      isVisualizeMode,
      isStreaming = false,
      canSendEmpty,
      onSend,
      onInputChange,
      onPaste,
      selectedCounts,
      knowledgeAvailable,
      personaAvailable,
      connectedAgents = [],
      selectedAgent = null,
      onSelectAgent,
      onSelectAttach,
      onSelectKnowledge,
      onSelectNotebookPicker,
      onSelectBookPicker,
      onSelectHistoryPicker,
      onSelectAgentsPicker,
      agentsAvailable = true,
      onSelectQuestionBankPicker,
      onSelectPersonaPicker,
      onSelectMemoryPicker,
      onOpenPersonaSelector,
      placeholder,
      minHeight = 28,
    },
    ref,
  ) {
    const [input, setInput] = useState("");
    const [showAtPopup, setShowAtPopup] = useState(false);
    const [showSlashPopup, setShowSlashPopup] = useState(false);
    const [atQuery, setAtQuery] = useState("");
    const slashEnabled = Boolean(onOpenPersonaSelector);
    // Main chat passes ``onSelectAgent`` → ``@`` picks a connected agent. Other
    // surfaces (quiz follow-up) omit it and keep the @ Space menu.
    const agentMentionMode = Boolean(onSelectAgent);
    const filteredAgents = useMemo(
      () =>
        agentMentionMode
          ? connectedAgents.filter((agent) =>
              agent.name.toLowerCase().includes(atQuery.toLowerCase()),
            )
          : [],
      [agentMentionMode, atQuery, connectedAgents],
    );

    // Latest text mirrored into a ref by the change handlers (never updated
    // during render). The @space handlers and the imperative handle read
    // from this ref so their identities stay stable across keystrokes,
    // letting `memo` on ChatSpaceMenu actually skip re-renders when
    // `showAtPopup` doesn't change.
    const inputRef = useRef("");
    const { isComposingRef, onCompositionStart, onCompositionEnd } =
      useImeComposing();
    // Helper that always updates state and ref together so they can't drift.
    const setInputBoth = useCallback((value: string) => {
      inputRef.current = value;
      setInput(value);
    }, []);

    useImperativeHandle(
      ref,
      () => ({
        clear: () => {
          setInputBoth("");
          onInputChange("");
        },
        getValue: () => inputRef.current,
        setValue: (value: string) => {
          const text = value ?? "";
          setInputBoth(text);
          onInputChange(text);
          // Focus + move caret to the end so the user can immediately
          // edit or press Enter to send.
          const el = textareaRef.current;
          if (el) {
            requestAnimationFrame(() => {
              el.focus();
              el.setSelectionRange(text.length, text.length);
            });
          }
        },
      }),
      [setInputBoth, onInputChange, textareaRef],
    );

    useAutoSizedTextarea(textareaRef, input, { min: minHeight, max: 200 });

    const handleInputChange = useCallback(
      (e: React.ChangeEvent<HTMLTextAreaElement>) => {
        const value = e.target.value;
        const cursorPos = e.target.selectionStart ?? value.length;
        setInputBoth(value);
        onInputChange(value);
        const atOpen = shouldOpenAtPopup(value, cursorPos);
        setShowAtPopup(atOpen);
        setAtQuery(atOpen ? atMentionQuery(value, cursorPos) : "");
        setShowSlashPopup(
          slashEnabled && shouldOpenSlashPopup(value, cursorPos),
        );
      },
      [setInputBoth, onInputChange, slashEnabled],
    );

    const handleTextareaClick = useCallback(
      (e: React.MouseEvent<HTMLTextAreaElement>) => {
        const target = e.currentTarget;
        const cursorPos = target.selectionStart ?? target.value.length;
        const atOpen = shouldOpenAtPopup(target.value, cursorPos);
        setShowAtPopup(atOpen);
        setAtQuery(atOpen ? atMentionQuery(target.value, cursorPos) : "");
        setShowSlashPopup(
          slashEnabled && shouldOpenSlashPopup(target.value, cursorPos),
        );
      },
      [slashEnabled],
    );

    const handleSelectSlashPersona = useCallback(() => {
      // The slash text is a command, not message content — clear it.
      setInputBoth("");
      onInputChange("");
      setShowSlashPopup(false);
      onOpenPersonaSelector?.();
    }, [setInputBoth, onInputChange, onOpenPersonaSelector]);

    const doSend = useCallback(() => {
      const content = inputRef.current.trim();
      // Allow sending when text is empty but the parent has attachments or
      // references queued (canSendEmpty). This matches the send-button's
      // own enablement logic in ChatComposer (`canSend`).
      if (!content && !canSendEmpty) return;
      onSend(content);
      setInputBoth("");
      onInputChange("");
      setShowAtPopup(false);
      setShowSlashPopup(false);
    }, [canSendEmpty, onSend, setInputBoth, onInputChange]);

    const clearTrailingMention = useCallback(() => {
      const next = stripTrailingAtMention(inputRef.current);
      setInputBoth(next);
      onInputChange(next);
    }, [setInputBoth, onInputChange]);

    const handleSelectAgentMention = useCallback(
      (name: string) => {
        clearTrailingMention();
        setShowAtPopup(false);
        setAtQuery("");
        onSelectAgent?.(name);
      },
      [clearTrailingMention, onSelectAgent],
    );

    const handleKeyDown = useCallback(
      (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
        // With the slash popup open, Enter/Tab confirm the command instead
        // of submitting "/persona" as a message.
        if (
          showSlashPopup &&
          !isComposingRef.current &&
          (e.key === "Enter" || e.key === "Tab")
        ) {
          e.preventDefault();
          handleSelectSlashPersona();
          return;
        }
        // With the agent-mention popup open, Enter/Tab confirm the first match.
        if (
          showAtPopup &&
          agentMentionMode &&
          filteredAgents.length > 0 &&
          !isComposingRef.current &&
          (e.key === "Enter" || e.key === "Tab")
        ) {
          e.preventDefault();
          handleSelectAgentMention(filteredAgents[0].name);
          return;
        }
        if (shouldSubmitOnEnter(e, isComposingRef.current)) {
          e.preventDefault();
          if (!isStreaming) doSend();
        } else if (e.key === "Escape") {
          setShowAtPopup(false);
          setShowSlashPopup(false);
        }
      },
      [
        doSend,
        isStreaming,
        showSlashPopup,
        handleSelectSlashPersona,
        showAtPopup,
        agentMentionMode,
        filteredAgents,
        handleSelectAgentMention,
        isComposingRef,
      ],
    );

    const handleSelectSpaceItem = useCallback(
      (
        key:
          | "attach"
          | "knowledge"
          | "chat_history"
          | "my_agents"
          | "books"
          | "notebooks"
          | "question_bank"
          | "persona"
          | "memory",
      ) => {
        clearTrailingMention();
        setShowAtPopup(false);
        if (key === "attach") onSelectAttach();
        else if (key === "knowledge") onSelectKnowledge?.();
        else if (key === "chat_history") onSelectHistoryPicker();
        else if (key === "my_agents") onSelectAgentsPicker?.();
        else if (key === "books") onSelectBookPicker();
        else if (key === "notebooks") onSelectNotebookPicker();
        else if (key === "question_bank") onSelectQuestionBankPicker();
        else if (key === "persona") onSelectPersonaPicker();
        else if (key === "memory") onSelectMemoryPicker();
      },
      [
        clearTrailingMention,
        onSelectAttach,
        onSelectKnowledge,
        onSelectHistoryPicker,
        onSelectAgentsPicker,
        onSelectBookPicker,
        onSelectNotebookPicker,
        onSelectQuestionBankPicker,
        onSelectPersonaPicker,
        onSelectMemoryPicker,
      ],
    );

    // Close the @/slash popups on outside click. Without this, clicking
    // anywhere outside the popup or textarea left the menu hovering
    // indefinitely. We bind on mousedown so the close fires before a
    // synthetic click on a sibling button (e.g. the Tools menu) can
    // re-open something else.
    const popupRef = useRef<HTMLDivElement>(null);
    const slashPopupRef = useRef<HTMLDivElement>(null);
    useEffect(() => {
      if (!showAtPopup && !showSlashPopup) return;
      const handler = (e: MouseEvent) => {
        const target = e.target as Node | null;
        if (!target) return;
        if (popupRef.current?.contains(target)) return;
        if (slashPopupRef.current?.contains(target)) return;
        if (textareaRef.current?.contains(target)) return;
        setShowAtPopup(false);
        setShowSlashPopup(false);
      };
      document.addEventListener("mousedown", handler);
      return () => document.removeEventListener("mousedown", handler);
    }, [showAtPopup, showSlashPopup, textareaRef]);

    return (
      <div style={{ padding: "14px 16px 8px", position: "relative" }}>
        {showAtPopup && agentMentionMode && (
          <div
            ref={popupRef}
            style={{ position: "absolute", bottom: "100%", left: 0, zIndex: 70, marginBottom: 8 }}
          >
            <div
              role="listbox"
              aria-label="与智能体对话"
              style={{
                width: 300,
                overflow: "hidden",
                borderRadius: 12,
                border: `1px solid ${DT.border}`,
                background: DT.popover,
                boxShadow:
                  "0 10px 15px -3px rgba(0,0,0,0.1), 0 4px 6px -4px rgba(0,0,0,0.1)",
                padding: "4px 0",
              }}
            >
              <div style={{ padding: "6px 12px 4px", fontSize: 11, fontWeight: 500, textTransform: "uppercase", letterSpacing: "0.05em", color: DT.mutedForeground }}>
                与智能体对话
              </div>
              {filteredAgents.length === 0 ? (
                <div style={{ padding: "8px 12px", fontSize: 12, color: DT.mutedForeground }}>
                  {connectedAgents.length === 0
                    ? "尚未连接智能体 —— 请在「我的智能体」中连接。"
                    : "没有匹配的智能体"}
                </div>
              ) : (
                <div style={{ maxHeight: 260, overflowY: "auto" }}>
                  {filteredAgents.map((agent) => {
                    const Glyph = agentGlyph(agent.kind);
                    const active = selectedAgent === agent.name;
                    const baseBg = active ? DT.primaryAlpha(0.06) : "transparent";
                    return (
                      <button
                        key={agent.name}
                        type="button"
                        role="option"
                        aria-selected={active}
                        onClick={() => handleSelectAgentMention(agent.name)}
                        onMouseEnter={(e) => {
                          if (!active) {
                            e.currentTarget.style.background = DT.mutedAlpha(0.45);
                          }
                        }}
                        onMouseLeave={(e) => {
                          e.currentTarget.style.background = baseBg;
                        }}
                        style={{
                          display: "flex",
                          width: "100%",
                          alignItems: "center",
                          gap: 10,
                          padding: "6px 12px",
                          textAlign: "left",
                          border: "none",
                          cursor: "pointer",
                          background: baseBg,
                          font: "inherit",
                        }}
                      >
                        {Glyph ? (
                          <Glyph size={15} style={{ flexShrink: 0 }} />
                        ) : (
                          <RobotOutlined style={{ fontSize: 15, flexShrink: 0 }} />
                        )}
                        <span style={{ ...ellipsis, flex: 1, fontSize: 12.5, fontWeight: 500, color: DT.foreground }}>
                          {agent.name}
                        </span>
                        {active && (
                          <CheckOutlined
                            style={{ fontSize: 14, flexShrink: 0, color: DT.primary }}
                          />
                        )}
                      </button>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        )}
        {showAtPopup && !agentMentionMode && (
          <div
            ref={popupRef}
            style={{ position: "absolute", bottom: "100%", left: 0, zIndex: 70, marginBottom: 8 }}
          >
            <ChatSpaceMenu
              variant="mention"
              selectedCounts={selectedCounts}
              knowledgeAvailable={knowledgeAvailable}
              personaAvailable={personaAvailable}
              agentsAvailable={agentsAvailable}
              onSelectItem={handleSelectSpaceItem}
            />
          </div>
        )}
        {showSlashPopup && (
          <div
            ref={slashPopupRef}
            style={{ position: "absolute", bottom: "100%", left: 0, zIndex: 70, marginBottom: 8 }}
          >
            <div
              role="listbox"
              aria-label="Commands"
              style={{
                width: 300,
                borderRadius: 12,
                border: `1px solid ${DT.border}`,
                background: DT.popover,
                boxShadow:
                  "0 10px 15px -3px rgba(0,0,0,0.1), 0 4px 6px -4px rgba(0,0,0,0.1)",
                padding: "6px 0",
              }}
            >
              <button
                type="button"
                role="option"
                aria-selected
                onClick={handleSelectSlashPersona}
                style={{
                  display: "flex",
                  width: "100%",
                  alignItems: "center",
                  gap: 10,
                  background: DT.mutedAlpha(0.6),
                  padding: "8px 12px",
                  textAlign: "left",
                  fontSize: 12.5,
                  border: "none",
                  cursor: "pointer",
                  font: "inherit",
                }}
              >
                <UserOutlined
                  style={{ fontSize: 14, flexShrink: 0, color: DT.mutedForeground }}
                />
                {/* Command syntax token — must not be localized. */}
                <span style={{ fontWeight: 500, color: DT.foreground }}>
                  /persona
                </span>
                <span style={{ minWidth: 0, ...ellipsis, color: DT.mutedForeground }}>
                  Switch the persona for this chat session
                </span>
              </button>
            </div>
          </div>
        )}
        <textarea
          ref={textareaRef}
          value={input}
          onChange={handleInputChange}
          onKeyDown={handleKeyDown}
          onCompositionStart={onCompositionStart}
          onCompositionEnd={onCompositionEnd}
          onClick={handleTextareaClick}
          onPaste={onPaste}
          rows={1}
          data-testid="chat-composer-input"
          // Cap input at 32k chars. A bigger paste (e.g. an entire textbook
          // dumped via Cmd+V) would force a layout reflow on every keystroke
          // and lock the page; the cap is a defensive guard, not a real
          // product limit. Users hit by this cap should be using the
          // attachment path, not the composer body.
          maxLength={32000}
          placeholder={
            placeholder ??
            (isVisualizeMode
              ? "描述你想可视化的图表、示意图或动画..."
              : "今天我能帮您什么？")
          }
          style={{
            width: "100%",
            resize: "none",
            overflow: "hidden",
            background: "transparent",
            fontSize: 16,
            lineHeight: 1.625,
            color: DT.foreground,
            outline: "none",
            border: "none",
            transition: "height 0.15s ease-out",
          }}
        />
      </div>
    );
  }),
);

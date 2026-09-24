/**
 * 复刻自 DeepTutor 原仓 web/components/settings/SettingsContext.tsx（整件 1:1，批5 5.2 壳族）。
 * 设置中心状态大脑：catalog/draft 双态、加载/保存/应用/刷新、各服务配置读写、诊断 SSE、
 * 跨路由引导（tour）。导出名与源逐字一致（SettingsProvider/useSettings 等被 31 页消费——契约钉死）。
 * 替换点（不触碰契约）：
 *  - "use client" 去除；next/navigation useRouter → react-router-dom useNavigate（push 等价）；
 *  - react-i18next t() → 文件内查表直出（web/locales/zh/app.json 原译文，{{}} 插值语义一致）；
 *  - apiFetch(apiUrl(p)) → fetch(p)（apiUrl 恒等；同源 fetch 等价 credentials:'include'；
 *    apiFetch 的 401→/login 跳转为原仓鉴权专属，不复刻）；SSE EventSource 相对路径 +
 *    withCredentials:true 逐字保留（CRA setupProxy 转发 /api/v1/*）；
 *  - @/components/common/code-block-themes 未移植：CodeBlockThemeId 以 string 别名并入本文件
 *    （存储侧 pages/tutor/h5/h5shared/appShellStorage 同为 string 语义）；
 *  - @/lib/theme setTheme → 就地等价内联 applyThemePreference：tupu 无 dark/glass/snow CSS
 *    主题系统，仅持久化偏好（原仓 THEME_STORAGE_KEY 'deeptutor-theme' 同键）；
 *  - app-shell-storage / AppShellContext / llm-options 复用仓内既有 1:1 移植件：
 *    pages/tutor/h5/h5shared/appShellStorage、pages/tutor/admin/appShellContext、
 *    pages/memory/llm-options（导出函数名逐字一致）。
 */
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { useNavigate } from "react-router-dom";

import {
  normalizeCodeBlockTheme,
  writeStoredCodeBlockTheme,
  writeStoredCodeBlockShowLineNumbers,
  writeStoredCodeBlockWrapLongLines,
  writeStoredLanguage,
} from "../../pages/tutor/h5/h5shared/appShellStorage";
import { useAppShell } from "../../pages/tutor/admin/appShellContext";
import { invalidateLLMOptionsCache } from "../../pages/memory/llm-options";
import {
  llmBlocksEqual,
  loadLlmDirectory,
  saveLlmDirectory,
  type LLMConnectionRow,
} from "./llmDirectory";

/**
 * 原仓 @/components/common/code-block-themes 的 CodeBlockThemeId（主题 id 联合类型）。
 * tupu 无该模块；码块主题在存储层（appShellStorage）即以 string 归一化，此处收窄为 string 别名，
 * 消费方（updateCodeBlockTheme 等）签名形状不变。
 */
export type CodeBlockThemeId = string;

// ─── Domain types ─────────────────────────────────────────────────────────

export type ServiceName =
  | "llm"
  | "embedding"
  | "search"
  | "tts"
  | "stt"
  | "imagegen"
  | "videogen";

export type CatalogModel = {
  id: string;
  name: string;
  model: string;
  managed_by?: string;
  dimension?: string;
  send_dimensions?: boolean;
  supported_dimensions?: string;
  context_window?: string;
  context_window_source?: string;
  context_window_detected_at?: string;
  // Voice (TTS): free-form provider/model-specific voice string, e.g.
  // "alloy", "autumn", "model:voice". `response_format` is the TTS output
  // codec (mp3/wav/...) and is reused by imagegen ("url"/"b64_json").
  // `language` is an optional STT hint.
  voice?: string;
  response_format?: string;
  language?: string;
  // Image generation: pixel size (e.g. "1024x1024"), quality, and style.
  size?: string;
  quality?: string;
  style?: string;
  // Video generation: aspect ratio (e.g. "16:9"), duration (seconds), resolution.
  aspect_ratio?: string;
  duration?: string;
  resolution?: string;
};

export type LlmContextWindowDetection = {
  profileId: string | null;
  modelId: string | null;
  contextWindow: number;
  source: string;
  detail?: string;
  detectedAt?: string;
};

export type CatalogProfile = {
  id: string;
  name: string;
  managed_by?: string;
  read_only?: boolean;
  binding?: string;
  provider?: string;
  base_url: string;
  api_key: string;
  api_version: string;
  extra_headers?: Record<string, string> | string;
  proxy?: string;
  max_results?: number;
  // UX2批（LLM 配置改造）：思考模式档位 + 图片输入能力位（落 capabilities/default_mode）
  default_mode?: string;
  vision?: boolean;
  models: CatalogModel[];
};

export type CatalogService = {
  active_profile_id: string | null;
  active_model_id?: string | null;
  profiles: CatalogProfile[];
};

export type Catalog = {
  version: number;
  services: {
    llm: CatalogService;
    embedding: CatalogService;
    search: CatalogService;
    tts: CatalogService;
    stt: CatalogService;
    imagegen: CatalogService;
    videogen: CatalogService;
  };
};

export type UiSettings = {
  theme: "light" | "dark" | "glass" | "snow";
  language: "en" | "zh";
  code_block_theme: string;
  code_block_show_line_numbers: boolean;
  code_block_wrap_long_lines: boolean;
};

type CodeBlockUiSettings = Pick<
  UiSettings,
  | "code_block_theme"
  | "code_block_show_line_numbers"
  | "code_block_wrap_long_lines"
>;

type UiSettingsPatch = Partial<UiSettings>;

export function syncLoadedCodeBlockSettingsToAppShell(
  ui: Partial<CodeBlockUiSettings>,
): CodeBlockUiSettings {
  const normalized = {
    code_block_theme: normalizeCodeBlockTheme(ui.code_block_theme),
    code_block_show_line_numbers:
      ui.code_block_show_line_numbers === true ||
      String(ui.code_block_show_line_numbers).toLowerCase() === "true",
    code_block_wrap_long_lines:
      ui.code_block_wrap_long_lines === true ||
      String(ui.code_block_wrap_long_lines).toLowerCase() === "true",
  };

  writeStoredCodeBlockTheme(normalized.code_block_theme);
  writeStoredCodeBlockShowLineNumbers(normalized.code_block_show_line_numbers);
  writeStoredCodeBlockWrapLongLines(normalized.code_block_wrap_long_lines);

  return normalized;
}

export async function persistUiSettingsPatch(
  patch: UiSettingsPatch,
  fetcher: typeof fetch = fetch,
): Promise<void> {
  await fetcher("/api/v1/settings/ui", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(patch),
  });
}

export type ProviderOption = {
  value: string;
  label: string;
  base_url?: string;
  default_dim?: string;
  default_model?: string;
  default_voice?: string;
  auth_mode?: "api_key" | "oauth";
};

export type SystemStatus = {
  backend: { status: string; timestamp: string };
  llm: { status: string; model?: string; error?: string };
  embeddings: { status: string; model?: string; error?: string };
  search: { status: string; provider?: string; error?: string };
};

export type EmbeddingCapabilities = {
  detected_dim?: number;
  default_dim?: number;
  supported_dimensions?: number[];
  supports_variable_dimensions?: boolean;
  model_known?: boolean;
  active_dim?: number;
  active_dim_source?: string;
};

export type DiagnosticsResult = {
  state: "success" | "failed";
  message: string;
  profileId: string | null;
  modelId: string | null;
};

export type ServiceReadiness =
  | "not_configured"
  | "untested"
  | "passed"
  | "failed";

type SettingsPayload = {
  ui: UiSettings;
  catalog?: Catalog;
  providers?: Record<ServiceName, ProviderOption[]>;
};

const DIAGNOSTICS_RESULTS_KEY = "deeptutor.settings.diagnosticsResults.v1";

/** i18next 兼容直出（见头注）：web/locales/zh/app.json 原译文 + {{}} 插值。 */
const ZH: Record<string, string> = {
  "System status unavailable: {{message}}": "系统状态不可用：{{message}}",
  "System status unavailable.": "系统状态不可用。",
  "Detected context window written to draft": "检测到的上下文窗口已写入草稿",
  "Draft saved": "草稿已保存",
  "All changes saved": "所有更改已保存",
  "Preparing {{service}} diagnostics...": "正在准备 {{service}} 诊断...",
  "Could not start diagnostics.": "无法启动诊断。",
  "Diagnostics stream disconnected.": "诊断流已断开。",
  "Diagnostics stream disconnected": "诊断流已断开",
};

function t(key: string, opts?: Record<string, unknown>): string {
  const zh = Object.prototype.hasOwnProperty.call(ZH, key) ? ZH[key] : key;
  if (!opts) return zh;
  return zh.replace(/\{\{(\w+)\}\}/g, (_m, k: string) =>
    opts[k] !== undefined && opts[k] !== null ? String(opts[k]) : `{{${k}}}`,
  );
}

/** 原仓 lib/theme.setTheme 的等价内联（见头注）：仅持久化主题偏好。 */
function applyThemePreference(theme: UiSettings["theme"]): void {
  try {
    window.localStorage.setItem("deeptutor-theme", theme);
  } catch {
    // localStorage 不可用
  }
}

// ─── Tour ──────────────────────────────────────────────────────────────────
//
// The tour now spans routes — each step names the sub-page it lives on so the
// controller can navigate there before the spotlight resolves a target. Adding
// a new step is a matter of pushing onto this list; the overlay reads the
// target via ``data-tour=""`` after the page has rendered.

export type TourStep = {
  target: string;
  route: string;
  titleKey: string;
  descKey: string;
};

// Tour step order broadly follows the category order in
// ``web/lib/settings-nav.ts`` so the guided walk moves through the hub's
// sections top to bottom. Each step names the route it lives on (the Status
// step targets the resident module on the hub itself); the overlay resolves
// the ``data-tour`` target after the page renders.
export const TOUR_STEPS: TourStep[] = [
  {
    target: "tour-status",
    route: "/settings",
    titleKey: "settingsTour.status.title",
    descKey: "settingsTour.status.desc",
  },
  {
    target: "tour-cat-appearance",
    route: "/settings",
    titleKey: "settingsTour.appearance.title",
    descKey: "settingsTour.appearance.desc",
  },
  {
    target: "tour-cat-network",
    route: "/settings",
    titleKey: "settingsTour.network.title",
    descKey: "settingsTour.network.desc",
  },
  {
    target: "tour-cat-models",
    route: "/settings",
    titleKey: "settingsTour.models.title",
    descKey: "settingsTour.models.desc",
  },
  {
    target: "tour-cat-knowledge",
    route: "/settings",
    titleKey: "settingsTour.knowledge.title",
    descKey: "settingsTour.knowledge.desc",
  },
  {
    target: "tour-cat-chat",
    route: "/settings",
    titleKey: "settingsTour.chat.title",
    descKey: "settingsTour.chat.desc",
  },
  {
    target: "tour-cat-memory",
    route: "/settings",
    titleKey: "settingsTour.memory.title",
    descKey: "settingsTour.memory.desc",
  },
];

// ─── Helpers ───────────────────────────────────────────────────────────────

export function cloneCatalog(catalog: Catalog): Catalog {
  return JSON.parse(JSON.stringify(catalog)) as Catalog;
}

/** TTS/STT share the catalog shape but configure audio providers. */
export function voiceService(service: ServiceName): boolean {
  return service === "tts" || service === "stt";
}

/** imagegen/videogen share the catalog shape but configure media generation. */
export function generationService(service: ServiceName): boolean {
  return service === "imagegen" || service === "videogen";
}

/** Services whose model entry should prefill from the provider's default model. */
function prefillsDefaultModel(service: ServiceName): boolean {
  return voiceService(service) || generationService(service);
}

export function defaultCatalog(): Catalog {
  return {
    version: 1,
    services: {
      llm: { active_profile_id: null, active_model_id: null, profiles: [] },
      embedding: {
        active_profile_id: null,
        active_model_id: null,
        profiles: [],
      },
      search: { active_profile_id: null, profiles: [] },
      tts: { active_profile_id: null, active_model_id: null, profiles: [] },
      stt: { active_profile_id: null, active_model_id: null, profiles: [] },
      imagegen: {
        active_profile_id: null,
        active_model_id: null,
        profiles: [],
      },
      videogen: {
        active_profile_id: null,
        active_model_id: null,
        profiles: [],
      },
    },
  };
}

export function getActiveProfile(
  catalog: Catalog,
  serviceName: ServiceName,
): CatalogProfile | null {
  const service = catalog.services[serviceName];
  return (
    service.profiles.find(
      (profile) => profile.id === service.active_profile_id,
    ) ??
    service.profiles[0] ??
    null
  );
}

export function getActiveModel(
  catalog: Catalog,
  serviceName: ServiceName,
): CatalogModel | null {
  if (serviceName === "search") return null;
  const service = catalog.services[serviceName];
  const profile = getActiveProfile(catalog, serviceName);
  if (!profile) return null;
  return (
    profile.models.find((model) => model.id === service.active_model_id) ??
    profile.models[0] ??
    null
  );
}

export function serviceConfigured(
  catalog: Catalog,
  serviceName: ServiceName,
): boolean {
  return serviceName === "search"
    ? Boolean(getActiveProfile(catalog, serviceName)?.provider)
    : Boolean(getActiveModel(catalog, serviceName)?.model);
}

export function currentDiagnosticsResult(
  catalog: Catalog,
  serviceName: ServiceName,
  diagnosticsResults: Partial<Record<ServiceName, DiagnosticsResult>>,
): DiagnosticsResult | null {
  const service = catalog.services[serviceName];
  const diagnostics = diagnosticsResults[serviceName];
  if (!diagnostics) return null;
  const profileId = service.active_profile_id ?? null;
  const modelId =
    serviceName === "search" ? null : (service.active_model_id ?? null);
  return diagnostics.profileId === profileId && diagnostics.modelId === modelId
    ? diagnostics
    : null;
}

export function serviceReadiness(
  catalog: Catalog,
  serviceName: ServiceName,
  diagnosticsResults: Partial<Record<ServiceName, DiagnosticsResult>>,
): ServiceReadiness {
  if (!serviceConfigured(catalog, serviceName)) return "not_configured";
  const diagnostics = currentDiagnosticsResult(
    catalog,
    serviceName,
    diagnosticsResults,
  );
  if (diagnostics?.state === "failed") return "failed";
  if (diagnostics?.state === "success") return "passed";
  return "untested";
}

export function servicePendingApply(
  catalog: Catalog,
  draft: Catalog,
  service: ServiceName,
): boolean {
  return (
    JSON.stringify(catalog.services[service]) !==
    JSON.stringify(draft.services[service])
  );
}

function nextModelName(
  models: CatalogModel[],
  language: UiSettings["language"],
): string {
  const prefix = language === "zh" ? "模型" : "Model ";
  const used = new Set(models.map((model) => model.name.trim()));
  let index = models.length + 1;
  while (used.has(`${prefix}${index}`)) {
    index += 1;
  }
  return `${prefix}${index}`;
}

function readStoredDiagnosticsResults(): Partial<
  Record<ServiceName, DiagnosticsResult>
> {
  if (typeof window === "undefined") return {};
  try {
    const parsed = JSON.parse(
      window.sessionStorage.getItem(DIAGNOSTICS_RESULTS_KEY) || "{}",
    ) as Partial<Record<ServiceName, DiagnosticsResult>>;
    return parsed && typeof parsed === "object" ? parsed : {};
  } catch {
    return {};
  }
}

// ─── Context ───────────────────────────────────────────────────────────────

export interface SettingsExtension {
  dirty: boolean;
  save: () => Promise<void>;
}

type SettingsContextValue = {
  // State
  catalog: Catalog;
  draft: Catalog;
  status: SystemStatus | null;
  providers: Record<ServiceName, ProviderOption[]>;
  catalogEditable: boolean | null;
  settingsLoading: boolean;
  settingsError: string | null;
  reloadSettings: () => Promise<void>;
  hasUnsavedChanges: boolean;
  theme: UiSettings["theme"];
  language: UiSettings["language"];
  codeBlockTheme: UiSettings["code_block_theme"];
  codeBlockShowLineNumbers: UiSettings["code_block_show_line_numbers"];
  codeBlockWrapLongLines: UiSettings["code_block_wrap_long_lines"];
  toast: string;
  setToast: (value: string) => void;

  // UI prefs
  updateTheme: (next: UiSettings["theme"]) => Promise<void>;
  updateLanguage: (next: UiSettings["language"]) => Promise<void>;
  updateCodeBlockTheme: (next: CodeBlockThemeId) => Promise<void>;
  updateCodeBlockShowLineNumbers: (next: boolean) => Promise<void>;
  updateCodeBlockWrapLongLines: (next: boolean) => Promise<void>;

  // Catalog mutation
  mutateCatalog: (mutator: (next: Catalog) => void) => void;
  addProfile: (service: ServiceName) => void;
  removeActiveProfile: (service: ServiceName) => void;
  addModel: (service: ServiceName) => void;
  removeActiveModel: (service: ServiceName) => void;
  updateProfileField: (
    service: ServiceName,
    field: keyof CatalogProfile,
    value: string,
  ) => void;
  updateProfileBoolField: (
    service: ServiceName,
    field: keyof CatalogProfile,
    value: boolean,
  ) => void;
  updateModelField: (
    service: ServiceName,
    field: keyof CatalogModel,
    value: string,
  ) => void;
  updateModelBoolField: (
    service: ServiceName,
    field: keyof CatalogModel,
    value: boolean,
  ) => void;
  updateContextWindowField: (value: string) => void;
  llmContextDetection: LlmContextWindowDetection | null;
  applyDetectedContextWindow: () => void;

  // Save / apply
  saving: boolean;
  applying: boolean;
  saveCatalog: () => Promise<void>;
  applyCatalog: () => Promise<void>;

  // Sub-page extension hooks. Sub-routes (e.g. /settings/memory) that own
  // state outside the catalog register a "dirty + save" pair so the global
  // Apply button can flush them alongside the catalog. Re-register on every
  // render — the latest closure wins.
  registerExtension: (key: string, ext: SettingsExtension | null) => void;

  // Diagnostics
  logs: string;
  testRunning: ServiceName | null;
  diagnosticsResults: Partial<Record<ServiceName, DiagnosticsResult>>;
  embeddingCapabilities: EmbeddingCapabilities | null;
  runDetailedTest: (service: ServiceName) => Promise<void>;

  // Helpers
  embeddingDefaultDim: (binding?: string) => string;

  // Tour
  tourStepIndex: number;
  startTour: () => void;
  advanceTour: () => void;
  goBackTour: () => void;
  skipTour: () => void;
};

const SettingsContext = createContext<SettingsContextValue | null>(null);

export function useSettings(): SettingsContextValue {
  const ctx = useContext(SettingsContext);
  if (!ctx) {
    throw new Error("useSettings must be used inside <SettingsProvider>");
  }
  return ctx;
}

// ─── Provider ──────────────────────────────────────────────────────────────

export function SettingsProvider({ children }: { children: ReactNode }) {
  // 原仓 const { t } = useTranslation() —— t 已改为文件内查表直出（见头注）。
  const navigate = useNavigate();
  // Code-block appearance lives in AppShellContext (the single source of truth,
  // also consumed by RichCodeBlock). Read the values from there and delegate
  // writes to its setters; this provider only adds backend persistence on top.
  const {
    codeBlockTheme,
    codeBlockShowLineNumbers,
    codeBlockWrapLongLines,
    setCodeBlockTheme: setAppShellCodeBlockTheme,
    setCodeBlockShowLineNumbers: setAppShellCodeBlockShowLineNumbers,
    setCodeBlockWrapLongLines: setAppShellCodeBlockWrapLongLines,
  } = useAppShell();

  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [theme, setTheme] = useState<UiSettings["theme"]>("snow");
  const [language, setLanguage] = useState<UiSettings["language"]>("en");
  const [catalog, setCatalog] = useState<Catalog>(defaultCatalog());
  const [draft, setDraft] = useState<Catalog>(defaultCatalog());
  const [catalogEditable, setCatalogEditable] = useState<boolean | null>(null);
  const [providers, setProviders] = useState<
    Record<ServiceName, ProviderOption[]>
  >({
    llm: [],
    embedding: [],
    search: [],
    tts: [],
    stt: [],
    imagegen: [],
    videogen: [],
  });
  const [toast, setToast] = useState("");
  const [saving, setSaving] = useState(false);
  const [applying, setApplying] = useState(false);
  // Empty string is the "no diagnostics yet" sentinel; the editor renders
  // a localized placeholder when logs is falsy. Don't seed an English
  // literal here — older code did, then read it back via .startsWith.
  const [logs, setLogs] = useState<string>("");
  const [testRunning, setTestRunning] = useState<ServiceName | null>(null);
  const [diagnosticsResults, setDiagnosticsResults] = useState<
    Partial<Record<ServiceName, DiagnosticsResult>>
  >(() => readStoredDiagnosticsResults());
  const [llmContextDetection, setLlmContextDetection] =
    useState<LlmContextWindowDetection | null>(null);
  const [embeddingCapabilities, setEmbeddingCapabilities] =
    useState<EmbeddingCapabilities | null>(null);
  const [tourStepIndex, setTourStepIndex] = useState(-1);
  const eventSourceRef = useRef<EventSource | null>(null);
  // Extensions register their latest dirty/save on each render. Keep the
  // derived dirty state explicit instead of using an indirect version counter.
  const extensionsRef = useRef<Map<string, SettingsExtension>>(new Map());
  // ── 引擎批8 8.1：/llm-config 数据面切③（LLM 合一反转，spec §七）──────────────
  // ③目录可达时 services.llm 用③连接目录渲染（llmDirectory 适配器）；
  // vendorLlmBlock 存档 vendor 原块——vendor PUT/apply 时回填，防合成形状污染 vendor
  // catalog（六服务页 vendor 数据面分治不动）。③不可达→退回 vendor 数据面（台账）。
  const llmDirectoryModeRef = useRef(false);
  const vendorLlmBlockRef = useRef<CatalogService | null>(null);
  const llmSyncedRowsRef = useRef<LLMConnectionRow[]>([]);
  const llmSyncedBlockRef = useRef<CatalogService | null>(null);
  const [hasDirtyExtension, setHasDirtyExtension] = useState(false);
  const registerExtension = useCallback(
    (key: string, ext: SettingsExtension | null) => {
      const map = extensionsRef.current;
      const prev = map.get(key);
      if (ext === null) {
        if (prev === undefined) return;
        map.delete(key);
        setHasDirtyExtension(
          Array.from(map.values()).some((extension) => extension.dirty),
        );
        return;
      }
      if (prev && prev.dirty === ext.dirty && prev.save === ext.save) {
        return;
      }
      map.set(key, ext);
      // Only recompute the dirty summary when dirty flips — save fn changes
      // every render are common and should not re-render the toolbar.
      if (prev?.dirty !== ext.dirty) {
        setHasDirtyExtension(
          Array.from(map.values()).some((extension) => extension.dirty),
        );
      }
    },
    [],
  );

  const [settingsError, setSettingsError] = useState<string | null>(null);

  // Single load step. Kept separate from the mount effect so a "Retry" action
  // can re-run it without remounting the provider.
  const loadSettings = useCallback(async () => {
    setSettingsError(null);
    let settingsLoaded = false;
    try {
      const settingsResponse = await fetch("/api/v1/settings");
      if (!settingsResponse.ok) {
        throw new Error(
          `Settings fetch failed: HTTP ${settingsResponse.status}`,
        );
      }
      const payload = (await settingsResponse.json()) as SettingsPayload;
      if (payload.catalog) {
        // 引擎批8 8.1：③连接目录可达→services.llm 用③块渲染（vendor 块存档回填用）；
        // ③不可达（网络/后端异常）→退回 vendor 数据面，行为同 IA 批5 现状。
        const llmDir = await loadLlmDirectory();
        if (llmDir) {
          llmDirectoryModeRef.current = true;
          vendorLlmBlockRef.current = payload.catalog.services.llm;
          llmSyncedRowsRef.current = llmDir.rows;
          llmSyncedBlockRef.current = llmDir.block;
          const catalogWithLlmDir: Catalog = {
            ...payload.catalog,
            services: { ...payload.catalog.services, llm: llmDir.block },
          };
          setCatalog(catalogWithLlmDir);
          setDraft(cloneCatalog(catalogWithLlmDir));
        } else {
          llmDirectoryModeRef.current = false;
          setCatalog(payload.catalog);
          setDraft(cloneCatalog(payload.catalog));
        }
        setCatalogEditable(true);
      } else {
        setCatalogEditable(false);
      }
      setTheme(payload.ui.theme);
      setLanguage(payload.ui.language);
      // Writes the backend-loaded values into app-shell storage and dispatches
      // the code-block settings event; AppShellContext (the single source) picks
      // them up, so no separate copy needs seeding here.
      syncLoadedCodeBlockSettingsToAppShell(payload.ui);
      if (payload.providers) setProviders(payload.providers);
      settingsLoaded = true;
    } catch (err) {
      console.error("Failed to load settings:", err);
      const message = err instanceof Error ? err.message : String(err);
      setSettingsError(message);
      // Resolve the loading gate so the page can render the error UI instead
      // of staying in an infinite skeleton state.
      setCatalogEditable((current) => (current === null ? false : current));
    }
    try {
      const statusResponse = await fetch("/api/v1/system/status");
      if (statusResponse.ok) {
        setStatus((await statusResponse.json()) as SystemStatus);
      }
    } catch (err) {
      console.error("Failed to load system status:", err);
      // Only surface this when settings itself loaded; otherwise the
      // settings-fetch error already explains the disconnect.
      if (settingsLoaded) {
        setSettingsError(
          (current) =>
            current ??
            (err instanceof Error
              ? t("System status unavailable: {{message}}", {
                  message: err.message,
                })
              : t("System status unavailable.")),
        );
      }
    }
  }, [t]);

  // Load settings + status once on mount. Subsequent navigations between
  // settings sub-pages share this state via the layout-level provider.
  // Code-block switch hydration lives in AppShellContext (the single source),
  // so no separate post-mount re-read is needed here.
  useEffect(() => {
    loadSettings();
    return () => {
      if (eventSourceRef.current) eventSourceRef.current.close();
    };
  }, [loadSettings]);

  useEffect(() => {
    if (!toast) return;
    const timer = setTimeout(() => setToast(""), 3500);
    return () => clearTimeout(timer);
  }, [toast]);

  useEffect(() => {
    try {
      window.sessionStorage.setItem(
        DIAGNOSTICS_RESULTS_KEY,
        JSON.stringify(diagnosticsResults),
      );
    } catch {
      // Session storage is an enhancement for cross-route feedback only.
    }
  }, [diagnosticsResults]);

  // ── UI preferences ──────────────────────────────────────────────────────
  const updateTheme = useCallback(async (next: UiSettings["theme"]) => {
    setTheme(next);
    applyThemePreference(next);
    await persistUiSettingsPatch({ theme: next });
  }, []);

  const updateLanguage = useCallback(async (next: UiSettings["language"]) => {
    setLanguage(next);
    writeStoredLanguage(next);
    await persistUiSettingsPatch({ language: next });
  }, []);

  // Each setter updates the app-shell source of truth (which normalizes,
  // persists to localStorage, and notifies consumers) then mirrors the change
  // to the backend.
  const updateCodeBlockTheme = useCallback(
    async (next: CodeBlockThemeId) => {
      setAppShellCodeBlockTheme(next);
      await persistUiSettingsPatch({ code_block_theme: next });
    },
    [setAppShellCodeBlockTheme],
  );

  const updateCodeBlockShowLineNumbers = useCallback(
    async (next: boolean) => {
      setAppShellCodeBlockShowLineNumbers(next);
      await persistUiSettingsPatch({ code_block_show_line_numbers: next });
    },
    [setAppShellCodeBlockShowLineNumbers],
  );

  const updateCodeBlockWrapLongLines = useCallback(
    async (next: boolean) => {
      setAppShellCodeBlockWrapLongLines(next);
      await persistUiSettingsPatch({ code_block_wrap_long_lines: next });
    },
    [setAppShellCodeBlockWrapLongLines],
  );

  // ── Catalog mutators ────────────────────────────────────────────────────
  const mutateCatalog = useCallback((mutator: (next: Catalog) => void) => {
    setDraft((current) => {
      const next = cloneCatalog(current);
      mutator(next);
      return next;
    });
  }, []);

  const embeddingDefaultDim = useCallback(
    (binding?: string) => {
      const match = (providers.embedding || []).find(
        (p) => p.value === (binding || "openai"),
      );
      return match?.default_dim || "3072";
    },
    [providers.embedding],
  );

  const addProfile = useCallback(
    (service: ServiceName) => {
      mutateCatalog((next) => {
        const target = next.services[service];
        const profileId = `${service}-profile-${Date.now()}`;
        const defaultBinding = service === "search" ? undefined : "openai";
        const defaultProvider = service === "search" ? "brave" : undefined;
        const providerKey =
          service === "search" ? defaultProvider : defaultBinding;
        const providerOption = (providers[service] || []).find(
          (p) => p.value === providerKey,
        );
        const providerLabel =
          providerOption?.label ?? providerKey ?? "New Profile";
        const profile: CatalogProfile = {
          id: profileId,
          name: providerLabel,
          binding: defaultBinding,
          provider: defaultProvider,
          base_url: "",
          api_key: "",
          api_version: "",
          extra_headers: service === "search" ? undefined : {},
          proxy: service === "search" ? "" : undefined,
          models: [],
        };
        if (service !== "search") {
          const modelId = `${service}-model-${Date.now()}`;
          const modelName = nextModelName([], language);
          profile.models.push({
            id: modelId,
            name: modelName,
            model: prefillsDefaultModel(service)
              ? (providerOption?.default_model ?? "")
              : "",
            ...(service === "embedding"
              ? {
                  dimension: embeddingDefaultDim(),
                  send_dimensions: true,
                }
              : {}),
            ...(service === "tts"
              ? {
                  voice: providerOption?.default_voice ?? "",
                  response_format: "mp3",
                }
              : {}),
          });
          target.active_model_id = modelId;
        }
        target.profiles.push(profile);
        target.active_profile_id = profileId;
      });
    },
    [embeddingDefaultDim, language, mutateCatalog, providers],
  );

  const removeActiveProfile = useCallback(
    (service: ServiceName) => {
      mutateCatalog((next) => {
        const target = next.services[service];
        target.profiles = target.profiles.filter(
          (profile) => profile.id !== target.active_profile_id,
        );
        target.active_profile_id = target.profiles[0]?.id ?? null;
        if (service !== "search") {
          target.active_model_id = target.profiles[0]?.models?.[0]?.id ?? null;
        }
      });
    },
    [mutateCatalog],
  );

  const addModel = useCallback(
    (service: ServiceName) => {
      if (service === "search") return;
      mutateCatalog((next) => {
        const target = next.services[service];
        const profile =
          target.profiles.find(
            (item) => item.id === target.active_profile_id,
          ) ?? null;
        if (!profile) return;
        const providerOption = (providers[service] || []).find(
          (p) => p.value === profile.binding,
        );
        const modelId = `${service}-model-${Date.now()}`;
        const modelName = nextModelName(profile.models, language);
        profile.models.push({
          id: modelId,
          name: modelName,
          model: prefillsDefaultModel(service)
            ? (providerOption?.default_model ?? "")
            : "",
          ...(service === "embedding"
            ? {
                dimension: embeddingDefaultDim(profile.binding),
                send_dimensions: true,
              }
            : {}),
          ...(service === "tts"
            ? {
                voice: providerOption?.default_voice ?? "",
                response_format: "mp3",
              }
            : {}),
        });
        target.active_model_id = modelId;
      });
    },
    [embeddingDefaultDim, language, mutateCatalog, providers],
  );

  const removeActiveModel = useCallback(
    (service: ServiceName) => {
      if (service === "search") return;
      mutateCatalog((next) => {
        const target = next.services[service];
        const profile =
          target.profiles.find(
            (item) => item.id === target.active_profile_id,
          ) ?? null;
        if (!profile) return;
        profile.models = profile.models.filter(
          (item) => item.id !== target.active_model_id,
        );
        target.active_model_id = profile.models[0]?.id ?? null;
      });
    },
    [mutateCatalog],
  );

  const updateProfileField = useCallback(
    (service: ServiceName, field: keyof CatalogProfile, value: string) => {
      mutateCatalog((next) => {
        const profile = getActiveProfile(next, service);
        if (!profile) return;
        (profile[field] as string | undefined) = value;
      });
    },
    [mutateCatalog],
  );
  // UX2批（LLM 配置改造）：能力位布尔写（思考模式/图片输入）
  const updateProfileBoolField = useCallback(
    (service: ServiceName, field: keyof CatalogProfile, value: boolean) => {
      mutateCatalog((next) => {
        const profile = getActiveProfile(next, service);
        if (!profile) return;
        (profile[field] as boolean | undefined) = value;
      });
    },
    [mutateCatalog],
  );

  const updateModelField = useCallback(
    (service: ServiceName, field: keyof CatalogModel, value: string) => {
      if (service === "search") return;
      mutateCatalog((next) => {
        const model = getActiveModel(next, service);
        if (!model) return;
        (model[field] as string | undefined) = value;
      });
    },
    [mutateCatalog],
  );

  const updateModelBoolField = useCallback(
    (service: ServiceName, field: keyof CatalogModel, value: boolean) => {
      if (service === "search") return;
      mutateCatalog((next) => {
        const model = getActiveModel(next, service);
        if (!model) return;
        (model[field] as boolean | undefined) = value;
      });
    },
    [mutateCatalog],
  );

  const updateContextWindowField = useCallback(
    (value: string) => {
      const normalized = value.replace(/[^\d]/g, "");
      mutateCatalog((next) => {
        const model = getActiveModel(next, "llm");
        if (!model) return;
        if (normalized) {
          model.context_window = normalized;
          model.context_window_source = "manual";
          delete model.context_window_detected_at;
        } else {
          delete model.context_window;
          delete model.context_window_source;
          delete model.context_window_detected_at;
        }
      });
    },
    [mutateCatalog],
  );

  const applyDetectedContextWindow = useCallback(() => {
    if (!llmContextDetection) return;
    mutateCatalog((next) => {
      const target = next.services.llm;
      if (
        target.active_profile_id !== llmContextDetection.profileId ||
        target.active_model_id !== llmContextDetection.modelId
      ) {
        return;
      }
      const model = getActiveModel(next, "llm");
      if (!model) return;
      model.context_window = String(llmContextDetection.contextWindow);
      model.context_window_source = llmContextDetection.source;
      if (llmContextDetection.detectedAt) {
        model.context_window_detected_at = llmContextDetection.detectedAt;
      } else {
        delete model.context_window_detected_at;
      }
    });
    setToast(t("Detected context window written to draft"));
  }, [llmContextDetection, mutateCatalog, t]);

  // ── Save / Apply ────────────────────────────────────────────────────────
  // 引擎批8 8.1：③目录模式下 llm 块变更走③CRUD（saveLlmDirectory）；vendor
  // PUT/apply 的载荷一律把 llm 块回填为 vendor 存档块（vendor llm 冻结，六服务
  // 页 vendor 数据面分治不动）；保存后 catalog 的 llm 块以③新块覆盖。
  const saveLlmDirectoryIfDirty = useCallback(async (): Promise<CatalogService | null> => {
    if (
      !llmDirectoryModeRef.current ||
      !draft ||
      !llmSyncedBlockRef.current ||
      llmBlocksEqual(draft.services.llm, llmSyncedBlockRef.current)
    ) {
      return null;
    }
    const saved = await saveLlmDirectory(draft.services.llm, llmSyncedRowsRef.current);
    llmSyncedRowsRef.current = saved.rows;
    llmSyncedBlockRef.current = saved.block;
    invalidateLLMOptionsCache();
    return saved.block;
  }, [draft]);

  const withVendorLlmBlock = useCallback((candidate: Catalog): Catalog => {
    const vendorLlm = vendorLlmBlockRef.current;
    if (!llmDirectoryModeRef.current || !vendorLlm) return candidate;
    return { ...candidate, services: { ...candidate.services, llm: vendorLlm } };
  }, []);

  const overlayLlmDirectoryBlock = useCallback(
    (candidate: Catalog, llmBlock: CatalogService | null): Catalog => {
      if (!llmDirectoryModeRef.current) return candidate;
      // llmBlock=null（本次保存块相等跳过③写入）时也必须用③同步块覆盖——
      // 否则 vendor apply 响应里的冻结 vendor llm 块（单档「火山 Endpoint」）
      // 会回显进编辑器，编辑态与③目录脱钩（E-28 实测教训）。
      const block = llmBlock ?? llmSyncedBlockRef.current;
      if (!block) return candidate;
      return { ...candidate, services: { ...candidate.services, llm: block } };
    },
    [],
  );

  const saveCatalog = useCallback(async () => {
    if (!catalogEditable) return;
    setSaving(true);
    try {
      const llmBlock = await saveLlmDirectoryIfDirty();
      const response = await fetch("/api/v1/settings/catalog", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ catalog: withVendorLlmBlock(draft) }),
      });
      const payload = await response.json();
      const nextCatalog = overlayLlmDirectoryBlock(payload.catalog, llmBlock);
      setCatalog(nextCatalog);
      setDraft(cloneCatalog(nextCatalog));
      // The model list the chat composer shows is derived from this catalog.
      invalidateLLMOptionsCache();
      setToast(t("Draft saved"));
    } finally {
      setSaving(false);
    }
  }, [catalogEditable, draft, t, saveLlmDirectoryIfDirty, withVendorLlmBlock, overlayLlmDirectoryBlock]);

  const applyCatalog = useCallback(async () => {
    setApplying(true);
    try {
      // Flush extensions (e.g. /settings/memory) first so their saved
      // state is visible to any backend side-effects in /apply below.
      const exts = Array.from(extensionsRef.current.values()).filter(
        (e) => e.dirty,
      );
      await Promise.all(exts.map((e) => e.save()));

      // 引擎批8 8.1：llm 块变更先行落③目录（vendor apply 载荷回填 vendor llm 块）。
      const llmBlock = await saveLlmDirectoryIfDirty();

      // The catalog apply is only meaningful when editable; an extension-
      // only flush should still produce a success toast.
      if (catalogEditable) {
        const response = await fetch("/api/v1/settings/apply", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ catalog: withVendorLlmBlock(draft) }),
        });
        const payload = await response.json();
        const nextCatalog = overlayLlmDirectoryBlock(payload.catalog, llmBlock);
        setCatalog(nextCatalog);
        setDraft(cloneCatalog(nextCatalog));
        invalidateLLMOptionsCache();
        const statusResponse = await fetch("/api/v1/system/status");
        setStatus((await statusResponse.json()) as SystemStatus);
      }
      setToast(t("All changes saved"));
    } finally {
      setApplying(false);
    }
  }, [catalogEditable, draft, t, saveLlmDirectoryIfDirty, withVendorLlmBlock, overlayLlmDirectoryBlock]);

  // ── Diagnostics ─────────────────────────────────────────────────────────
  // Reset capability snapshot when switching embedding profile/model so a
  // stale "Detected: Xd" hint doesn't bleed across profiles.
  useEffect(() => {
    setEmbeddingCapabilities(null);
  }, [
    draft.services.embedding.active_profile_id,
    draft.services.embedding.active_model_id,
  ]);

  const llmActiveProfileId = draft.services.llm.active_profile_id;
  const llmActiveModelId = draft.services.llm.active_model_id;
  useEffect(() => {
    setLlmContextDetection((current) => {
      if (!current) return null;
      if (
        current.profileId === llmActiveProfileId &&
        current.modelId === llmActiveModelId
      ) {
        return current;
      }
      return null;
    });
  }, [llmActiveProfileId, llmActiveModelId]);

  const runDetailedTest = useCallback(
    async (service: ServiceName) => {
      if (!catalogEditable) return;
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
      setLogs(t("Preparing {{service}} diagnostics...", { service }) + "\n");
      setTestRunning(service);
      const target = draft.services[service];
      const runProfileId = target.active_profile_id ?? null;
      const runModelId =
        service === "search" ? null : (target.active_model_id ?? null);
      setDiagnosticsResults((current) => {
        const next = { ...current };
        delete next[service];
        return next;
      });
      if (service === "llm") setLlmContextDetection(null);
      if (service === "embedding") setEmbeddingCapabilities(null);
      try {
        const response = await fetch(
          `/api/v1/settings/tests/${service}/start`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ catalog: draft }),
          },
        );
        const payload = (await response.json()) as {
          run_id?: string;
          run_token?: string;
          detail?: string;
        };
        if (!response.ok || !payload.run_id) {
          throw new Error(payload.detail || t("Could not start diagnostics."));
        }
        // UX批（测试运行修复）：EventSource 带不了 Authorization 头——start 铸造的
        // run_token 经 URL 携带（一次性凭据，events 端点校验放行）
        // UX批（测试运行修复）：EventSource 带不了 Bearer 头→改轮询（fetch 自动带凭据）
        const poll = async () => {
          try {
            const r = await fetch(
              `/api/v1/settings/tests/${service}/${payload.run_id}/poll`,
              { headers: { "Content-Type": "application/json" } },
            );
            if (!r.ok) throw new Error(`poll ${r.status}`);
            const data = (await r.json()) as { events: Array<Record<string, unknown>>; status: string };
            const evts = data.events || [];
            for (const entry of evts) {
              const et = entry as { type?: string; message?: string; catalog?: Catalog; detected_dim?: number; default_dim?: number; supported_dimensions?: number[]; supports_variable_dimensions?: boolean; model_known?: boolean; active_dim?: number; active_dim_source?: string; context_window?: number; source?: string; detail?: string; detected_at?: string };
              setLogs((current) => `${current}[${et.type}] ${et.message}
`);
              if (service === "llm" && et.type === "context_window") {
                const detected = typeof et.context_window === "number" ? et.context_window : Number.parseInt(String(et.context_window ?? ""), 10);
                if (Number.isFinite(detected) && detected > 0) {
                  setLlmContextDetection({ profileId: runProfileId, modelId: runModelId, contextWindow: detected, source: et.source || "metadata", detail: et.detail, detectedAt: et.detected_at });
                }
              }
              if (et.type === "capabilities") {
                setEmbeddingCapabilities({ detected_dim: et.detected_dim, default_dim: et.default_dim, supported_dimensions: et.supported_dimensions, supports_variable_dimensions: et.supports_variable_dimensions, model_known: et.model_known, active_dim: et.active_dim, active_dim_source: et.active_dim_source });
              }
              if (et.catalog) {
                setCatalog(et.catalog as Catalog);
                setDraft(cloneCatalog(et.catalog as Catalog));
              }
              if (et.type === "completed" || et.type === "failed") {
                setTestRunning(null);
                setDiagnosticsResults((current) => ({
                  ...current,
                  [service]: { state: et.type === "completed" ? "success" : "failed", message: et.message || "", profileId: runProfileId, modelId: runModelId },
                }));
                setToast(et.message || "");
                return;
              }
            }
            if (data.status === "completed" || data.status === "failed") {
              setTestRunning(null);
              return;
            }
            setTimeout(poll, 2000);
          } catch {
            setTestRunning(null);
            setLogs((current) => `${current}[failed] 诊断轮询断开
`);
          }
        };
        poll();
      } catch (error) {
        const message =
          error instanceof Error
            ? error.message
            : t("Could not start diagnostics.");
        setLogs((current) => `${current}[failed] ${message}\n`);
        setDiagnosticsResults((current) => ({
          ...current,
          [service]: {
            state: "failed",
            message,
            profileId: runProfileId,
            modelId: runModelId,
          },
        }));
        setToast(message);
        setTestRunning(null);
      }
    },
    [catalogEditable, draft, t],
  );

  // ── Tour ────────────────────────────────────────────────────────────────
  // The tour drives a SpotlightOverlay rendered by the layout. When the step
  // changes, we navigate to the step's route; the overlay then resolves the
  // target via data-tour after the page renders.
  const startTour = useCallback(() => {
    if (TOUR_STEPS.length === 0) return;
    setTourStepIndex(0);
    // No router.push here — the route-sync effect below handles it,
    // and doing it in two places would issue a redundant push.
  }, []);

  // Pure state updaters — DO NOT call router.push inside these. React
  // may invoke the updater twice in StrictMode, and triggering a
  // separate component's setState (Router) from inside a setState
  // callback raises "Cannot update a component while rendering another".
  // The route is synced via the effect below.
  const advanceTour = useCallback(() => {
    setTourStepIndex((idx) => {
      const nextIdx = idx + 1;
      return nextIdx >= TOUR_STEPS.length ? -1 : nextIdx;
    });
  }, []);

  const goBackTour = useCallback(() => {
    setTourStepIndex((idx) => (idx > 0 ? idx - 1 : idx));
  }, []);

  const skipTour = useCallback(() => {
    setTourStepIndex(-1);
  }, []);

  // Sync the URL to the current tour step. Runs after render commits
  // so it never re-enters another component's render.
  useEffect(() => {
    if (tourStepIndex < 0 || tourStepIndex >= TOUR_STEPS.length) return;
    const step = TOUR_STEPS[tourStepIndex];
    navigate(step.route);
  }, [tourStepIndex, navigate]);

  // ── Derived ─────────────────────────────────────────────────────────────
  const hasUnsavedChanges = useMemo(() => {
    return (
      hasDirtyExtension ||
      (catalogEditable === true &&
        JSON.stringify(catalog) !== JSON.stringify(draft))
    );
  }, [catalog, catalogEditable, draft, hasDirtyExtension]);

  const settingsLoading = catalogEditable === null;

  const value = useMemo<SettingsContextValue>(
    () => ({
      catalog,
      draft,
      status,
      providers,
      catalogEditable,
      settingsLoading,
      settingsError,
      reloadSettings: loadSettings,
      hasUnsavedChanges,
      theme,
      language,
      codeBlockTheme,
      codeBlockShowLineNumbers,
      codeBlockWrapLongLines,
      toast,
      setToast,
      updateTheme,
      updateLanguage,
      updateCodeBlockTheme,
      updateCodeBlockShowLineNumbers,
      updateCodeBlockWrapLongLines,
      mutateCatalog,
      addProfile,
      removeActiveProfile,
      addModel,
      removeActiveModel,
      updateProfileField,
      updateProfileBoolField,
      updateModelField,
      updateModelBoolField,
      updateContextWindowField,
      llmContextDetection,
      applyDetectedContextWindow,
      saving,
      applying,
      saveCatalog,
      applyCatalog,
      registerExtension,
      logs,
      testRunning,
      diagnosticsResults,
      embeddingCapabilities,
      runDetailedTest,
      embeddingDefaultDim,
      tourStepIndex,
      startTour,
      advanceTour,
      goBackTour,
      skipTour,
    }),
    [
      addModel,
      addProfile,
      applyDetectedContextWindow,
      applyCatalog,
      applying,
      catalog,
      catalogEditable,
      codeBlockShowLineNumbers,
      codeBlockTheme,
      codeBlockWrapLongLines,
      diagnosticsResults,
      draft,
      embeddingCapabilities,
      embeddingDefaultDim,
      hasUnsavedChanges,
      language,
      llmContextDetection,
      logs,
      mutateCatalog,
      providers,
      registerExtension,
      removeActiveModel,
      removeActiveProfile,
      runDetailedTest,
      saveCatalog,
      saving,
      settingsError,
      loadSettings,
      settingsLoading,
      skipTour,
      startTour,
      advanceTour,
      goBackTour,
      status,
      testRunning,
      theme,
      toast,
      tourStepIndex,
      updateCodeBlockShowLineNumbers,
      updateCodeBlockTheme,
      updateCodeBlockWrapLongLines,
      updateContextWindowField,
      updateLanguage,
      updateModelBoolField,
      updateModelField,
      updateProfileField,
      updateTheme,
    ],
  );

  return (
    <SettingsContext.Provider value={value}>
      {children}
    </SettingsContext.Provider>
  );
}

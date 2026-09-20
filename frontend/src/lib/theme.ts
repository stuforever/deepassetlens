// 批6 依赖补件：1:1 移植自 DeepTutor web/lib/theme.ts（Mermaid.tsx 级联依赖）。
// 纯逻辑件，无替换点，逐字一致。

/**
 * Theme persistence utilities
 * Handles light/dark theme with localStorage fallback and system preference detection
 */

// 三轨M6(U1) D2：主题砍到单主题（snow/默认蓝）——历史类型名保留（存储兼容），运行时恒 light
export type Theme = "light";

export const THEME_STORAGE_KEY = "deeptutor-theme";

type ThemeChangeListener = (theme: Theme) => void;
const themeListeners = new Set<ThemeChangeListener>();

/**
 * Subscribe to theme changes
 */
export function subscribeToThemeChanges(
  listener: ThemeChangeListener,
): () => void {
  themeListeners.add(listener);
  return () => themeListeners.delete(listener);
}

/**
 * Notify all listeners of theme change
 */
function notifyThemeChange(theme: Theme): void {
  themeListeners.forEach((listener) => listener(theme));
}

/**
 * Get the stored theme from localStorage
 */
// D2：历史存储值（dark/glass/snow）一律归一为 light
export function getStoredTheme(): Theme | null {
  if (typeof window === "undefined") return null;

  try {
    const stored = localStorage.getItem(THEME_STORAGE_KEY);
    if (
      stored === "light" ||
      stored === "dark" ||
      stored === "glass" ||
      stored === "snow"
    ) {
      return "light";  // 历史值归一
    }
  } catch (e) {
    // Silently fail - localStorage may be disabled
  }

  return null;
}

/**
 * Save theme to localStorage
 */
export function saveThemeToStorage(theme: Theme): boolean {
  if (typeof window === "undefined") return false;

  try {
    localStorage.setItem(THEME_STORAGE_KEY, theme);
    return true;
  } catch (e) {
    // Silently fail - localStorage may be disabled or full
    return false;
  }
}

/**
 * Get system preference for theme.
 * Light systems get "snow" (the pure-white Default theme); dark systems
 * get "dark". Must stay in sync with the inline ThemeScript fallback.
 */
export function getSystemTheme(): Theme {
  // D2：单主题——系统偏好不再分流（恒 light/默认）
  return "light";
}

/**
 * Apply theme to document
 */
export function applyThemeToDocument(theme: Theme): void {
  if (typeof document === "undefined") return;

  const html = document.documentElement;

  // D2：单主题——只清历史主题类，不再挂任何 dark/glass/snow 分支
  html.classList.remove("dark", "theme-glass", "theme-snow");
  void theme;
}

/**
 * Initialize theme on app startup
 * Priority: localStorage > system preference (snow on light systems, dark on dark)
 */
export function initializeTheme(): Theme {
  // Check localStorage first
  const stored = getStoredTheme();
  if (stored) {
    applyThemeToDocument(stored);
    return stored;
  }

  // D2：单主题——系统偏好不再分流主题
  applyThemeToDocument("light");
  saveThemeToStorage("light");
  return "light";
}

/**
 * Set theme and persist it
 */
export function setTheme(theme: Theme): void {
  applyThemeToDocument(theme);
  saveThemeToStorage("light");
  notifyThemeChange("light");
}

// 引擎批2：DT i18n/init.ts 1:1（路径适配；键值语义零改动——keySeparator=false
// 使含标点空格的英文文案键直查；defaultNS="app"；fallbackLng="en"）。
// 源=web/i18n/init.ts。
import i18n, { type Resource } from "i18next";
import { initReactI18next } from "react-i18next";

import enApp from "../locales/en/app.json";
import zhApp from "../locales/zh/app.json";

export type AppLanguage = "en" | "zh";

export function normalizeLanguage(lang: unknown): AppLanguage {
  if (!lang) return "en";
  const s = String(lang).toLowerCase();
  if (s === "zh" || s === "cn" || s === "chinese") return "zh";
  return "en";
}

let _initialized = false;

export function initI18n(language?: unknown) {
  if (_initialized) return i18n;

  const resources: Resource = {
    en: { app: enApp },
    zh: { app: zhApp },
  };

  i18n.use(initReactI18next).init({
    resources,
    lng: "zh", // tupu 侧固定 zh（IA 件全站中文；DT 由服务端下发语言，本件桌面窗口取 zh——实测屏为证）
    fallbackLng: "en",
    // Use a single default namespace to keep lookups simple.
    // We intentionally keep keySeparator disabled so keys like "Generating..." remain valid.
    defaultNS: "app",
    ns: ["app"],
    keySeparator: false,
    interpolation: {
      escapeValue: false,
    },
    returnEmptyString: false,
    returnNull: false,
  });

  _initialized = true;
  return i18n;
}

export async function ensureLanguage(language: AppLanguage) {
  if (i18n.hasResourceBundle(language, "app")) return;
  if (language === "zh") {
    const zhApp = (await import("../locales/zh/app.json")).default;
    i18n.addResourceBundle("zh", "app", zhApp, true, true);
  }
}

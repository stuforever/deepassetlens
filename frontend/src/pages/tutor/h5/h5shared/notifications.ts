/**
 * 复刻自 DeepTutor 原仓 web/lib/notifications.ts。
 * 登记式替换点（约定#4：notify/toast → antd message）：
 * 原仓为 pub-sub + 工作台 layout 挂载的 ToastViewport 渲染；tupu 无该 layout，
 * notify() 改为直发 antd message（info/success/error 对位 tone），调用点签名不变。
 * subscribeNotifications/pub-sub 机制保留（兼容原接口，tupu 内暂无 viewport 订阅者）。
 */
import { message } from "antd";

export type NotificationTone = "info" | "success" | "error";

export interface Notification {
  id: number;
  message: string;
  tone: NotificationTone;
  durationMs: number;
}

type Listener = (n: Notification) => void;

const listeners = new Set<Listener>();
let counter = 0;

export function notify(
  message_: string,
  options: { tone?: NotificationTone; durationMs?: number } = {},
): void {
  if (!message_) return;
  counter += 1;
  const notification: Notification = {
    id: counter,
    message: message_,
    tone: options.tone ?? "info",
    durationMs: options.durationMs ?? 4000,
  };
  for (const listener of Array.from(listeners)) {
    try {
      listener(notification);
    } catch {
      /* a misbehaving listener should not break siblings */
    }
  }
  // antd message 直发（原 ToastViewport 等价承接）
  const durationMs = notification.durationMs / 1000;
  const key = `dsh-notify-${notification.id}`;
  if (notification.tone === "error") message.error({ content: notification.message, duration: durationMs, key });
  else if (notification.tone === "success") message.success({ content: notification.message, duration: durationMs, key });
  else message.info({ content: notification.message, duration: durationMs, key });
}

// Convenience methods so callers can write notify.error("...") etc.
notify.error = (message_: string) => notify(message_, { tone: "error" });
notify.success = (message_: string) => notify(message_, { tone: "success" });
notify.warning = (message_: string) => notify(message_, { tone: "info", durationMs: 6000 });
notify.info = (message_: string) => notify(message_, { tone: "info" });

export function subscribeNotifications(listener: Listener): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

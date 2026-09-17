export type BookWsEvent = { type: string; [key: string]: unknown };

export interface BookSocketLike {
  onopen: ((event: Event) => void) | null;
  onmessage: ((event: MessageEvent<string>) => void) | null;
  onerror: ((event: Event) => void) | null;
  onclose: ((event: CloseEvent) => void) | null;
  send(data: string): void;
  close(): void;
}

export interface BookSocketOperationOptions {
  message: BookWsEvent;
  resultType: string;
  onEvent?: (event: BookWsEvent) => void;
  idleTimeoutMs?: number;
}

function errorMessage(event: BookWsEvent): string {
  const detail = event.content ?? event.message ?? event.detail;
  return typeof detail === "string" && detail.trim()
    ? detail
    : "Book WebSocket operation failed";
}

export function runBookSocketOperation<T extends BookWsEvent = BookWsEvent>(
  createSocket: () => BookSocketLike,
  options: BookSocketOperationOptions,
): Promise<T> {
  return new Promise<T>((resolve, reject) => {
    const socket = createSocket();
    let settled = false;
    let idleTimer: ReturnType<typeof setTimeout> | null = null;
    const idleTimeoutMs = options.idleTimeoutMs ?? 180000;

    const armIdleTimeout = (): void => {
      if (idleTimeoutMs <= 0) return;
      if (idleTimer !== null) clearTimeout(idleTimer);
      idleTimer = setTimeout(() => {
        finish(
          () =>
            reject(
              new Error(
                "Book WebSocket operation timed out after 3 minutes without progress",
              ),
            ),
          true,
        );
      }, idleTimeoutMs);
    };

    const finish = (callback: () => void, closeSocket: boolean): void => {
      if (settled) return;
      settled = true;
      if (idleTimer !== null) {
        clearTimeout(idleTimer);
        idleTimer = null;
      }
      if (closeSocket) {
        try {
          socket.close();
        } catch {
          // The operation result is authoritative even if cleanup fails.
        }
      }
      callback();
    };

    socket.onopen = () => {
      try {
        socket.send(JSON.stringify(options.message));
        armIdleTimeout();
      } catch (error) {
        finish(
          () =>
            reject(
              error instanceof Error
                ? error
                : new Error("Failed to send Book WebSocket operation"),
            ),
          true,
        );
      }
    };

    socket.onmessage = (message) => {
      let event: BookWsEvent;
      try {
        event = JSON.parse(message.data) as BookWsEvent;
      } catch {
        return;
      }

      armIdleTimeout();
      options.onEvent?.(event);

      if (event.type === "error") {
        finish(() => reject(new Error(errorMessage(event))), true);
        return;
      }

      if (event.type === options.resultType) {
        finish(() => resolve(event as T), true);
      }
    };

    socket.onerror = () => {
      finish(() => reject(new Error("Book WebSocket connection failed")), true);
    };

    socket.onclose = () => {
      finish(
        () =>
          reject(
            new Error(
              `Book WebSocket closed before ${options.resultType} was received`,
            ),
          ),
        false,
      );
    };
  });
}

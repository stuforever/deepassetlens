/// <reference types="react-scripts" />

declare module '*.module.css' {
  const classes: { readonly [key: string]: string };
  export default classes;
}

declare module '*.module.scss' {
  const classes: { readonly [key: string]: string };
  export default classes;
}

// E-36：File System Access API 类型补声明（TS 4.9 lib.dom 缺 newer 成员；
// lib/chat-import 使用侧均为可选调用 + 运行时特性探测，类型面仅补形状）。
interface FileSystemDirectoryHandle {
  values(options?: { mode?: "read" | "readwrite" }): AsyncIterableIterator<FileSystemDirectoryHandle | FileSystemFileHandle>;
  queryPermission?: (descriptor?: { mode?: "read" | "readwrite" }) => Promise<PermissionState>;
  requestPermission?: (descriptor?: { mode?: "read" | "readwrite" }) => Promise<PermissionState>;
}

interface Window {
  showDirectoryPicker?: (options?: { id?: string; mode?: "read" | "readwrite"; startIn?: string }) => Promise<FileSystemDirectoryHandle>;
}

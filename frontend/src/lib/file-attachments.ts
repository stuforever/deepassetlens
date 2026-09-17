// IA批6 6.3 lib 补件：1:1 移植自 DeepTutor web/lib/file-attachments.ts（FileReader data URL；去 "use client"，无 import）。

export async function readFileAsDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || ""));
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(file);
  });
}

export function extractBase64FromDataUrl(dataUrl: string): string {
  return dataUrl.includes(",") ? dataUrl.split(",")[1] : dataUrl;
}

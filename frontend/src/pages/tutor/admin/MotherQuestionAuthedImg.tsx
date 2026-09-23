/**
 * UX批③（用户反馈⑥）：母题域图片受鉴权静态挂载（R5批⑯ _AuthedStatic）保护——
 * <img src> 无法携带 Bearer 头，auth=ON 下服务端图片直链 401 破图（拍照中心逐题缩略图/
 * 题干答案图预览/大图全破）。本件经 fetch（fetchBearerPatch 全局注入凭据）取 blob 转
 * objectURL 渲染；URL 变更/卸载时回收 objectURL。
 */
import { useEffect, useState } from 'react';

export function useAuthedImgUrl(url: string | null | undefined): string | null {
  const [obj, setObj] = useState<string | null>(null);
  useEffect(() => {
    if (!url) {
      setObj(null);
      return;
    }
    let alive = true;
    let made: string | null = null;
    fetch(url)
      .then((r) => {
        if (!r.ok) throw new Error(String(r.status));
        return r.blob();
      })
      .then((bl) => {
        if (alive) {
          made = URL.createObjectURL(bl);
          setObj(made);
        }
      })
      .catch(() => {
        if (alive) setObj(null);
      });
    return () => {
      alive = false;
      if (made) URL.revokeObjectURL(made);
    };
  }, [url]);
  return obj;
}

export function AuthedImg({ src, ...rest }: { src: string | null | undefined } & React.ImgHTMLAttributes<HTMLImageElement>) {
  const url = useAuthedImgUrl(src);
  return <img src={url ?? undefined} {...rest} />;
}

export default AuthedImg;

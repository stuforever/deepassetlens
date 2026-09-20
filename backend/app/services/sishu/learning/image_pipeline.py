# -*- coding: utf-8 -*-
# [sishu port] v4批6 机械复制自 vendor deeptutor/learning/image_pipeline.py（1:1 语义，仅 import 改写）。
# 批16 vendor 物理删除后的存活拷贝；上游修订需回灌本件（复刻纪律）。
"""Image pipeline for mother questions: upload, OCR, crop, thumbnail, red-pen detect.

Replaces ragflow/wrong_question_api.py's minio_uploader + wq_image_pipeline +
_get_rapidocr. Uses local filesystem storage (no MinIO dependency) and RapidOCR
(lightweight ONNX, no PaddlePaddle dependency).
"""
from __future__ import annotations

import base64
import io
import logging
import re
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from PIL import Image

from app.services.sishu.services.path_service import get_path_service

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
# Storage                                                                      #
# --------------------------------------------------------------------------- #

def _images_root() -> Path:
    """Root directory for mother question images."""
    root = get_path_service().get_workspace_dir() / "mother_questions" / "images"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _public_base() -> str:
    """Public URL prefix for serving mother question images."""
    return "/api/v1/mother-questions/files"


def save_upload(file_bytes: bytes, ext: str = "jpg", subdir: str = "single_q") -> str:
    """Save uploaded image bytes to local filesystem, return public URL.

    Layout: <workspace>/mother_questions/images/<subdir>/<YYYY-MM-DD>/<uuid>.<ext>
    URL:    /api/v1/mother-questions/files/<subdir>/<YYYY-MM-DD>/<uuid>.<ext>
    """
    ext = ext.lstrip(".").lower()
    if ext not in {"jpg", "jpeg", "png", "webp", "gif", "bmp"}:
        ext = "jpg"
    if ext == "jpeg":
        ext = "jpg"

    date_str = datetime.now().strftime("%Y-%m-%d")
    filename = f"{uuid.uuid4().hex}.{ext}"
    dir_path = _images_root() / subdir / date_str
    dir_path.mkdir(parents=True, exist_ok=True)
    file_path = dir_path / filename
    file_path.write_bytes(file_bytes)

    rel = f"{subdir}/{date_str}/{filename}"
    return f"{_public_base()}/{rel}"


def resolve_url_to_path(url: str) -> Path | None:
    """Map a public image URL back to its filesystem path (for export/crop)."""
    prefix = _public_base() + "/"
    if not url or not url.startswith(prefix):
        # absolute filesystem path or external URL
        if url and Path(url).exists():
            return Path(url)
        return None
    rel = url[len(prefix):]
    return _images_root() / rel


# --------------------------------------------------------------------------- #
# Image operations                                                             #
# --------------------------------------------------------------------------- #

def make_thumbnail(file_bytes: bytes, max_size: int = 600, quality: int = 85) -> str:
    """Generate a base64 JPEG thumbnail (for preview in API responses)."""
    img = Image.open(io.BytesIO(file_bytes))
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    img.thumbnail((max_size, max_size))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def crop_by_bbox(file_bytes: bytes, bbox: list[int]) -> tuple[bytes, str]:
    """Crop image by [x1,y1,x2,y2], return (cropped_bytes, thumbnail_base64)."""
    img = Image.open(io.BytesIO(file_bytes))
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    x1, y1, x2, y2 = bbox
    if x2 - x1 < 50 or y2 - y1 < 50:
        raise ValueError("crop region too small (<50px)")
    cropped = img.crop((x1, y1, x2, y2))
    buf = io.BytesIO()
    cropped.save(buf, format="JPEG", quality=90)
    crop_bytes = buf.getvalue()
    thumb = make_thumbnail(crop_bytes, max_size=600)
    return crop_bytes, thumb


# --------------------------------------------------------------------------- #
# OCR engine (RapidOCR, lazy-loaded singleton)                                 #
# --------------------------------------------------------------------------- #

_ocr_engine = None


def _get_ocr():
    """Lazy-load RapidOCR engine (first call downloads ~100MB model)."""
    global _ocr_engine
    if _ocr_engine is None:
        from rapidocr_onnxruntime import RapidOCR
        _ocr_engine = RapidOCR()
        logger.info("RapidOCR engine initialized")
    return _ocr_engine


def ocr_image(file_bytes: bytes) -> dict[str, Any]:
    """Run OCR on image bytes, return {text, lines, boxes}.

    Returns:
        text: full concatenated text
        lines: list of {text, bbox} per detected line
        raw: raw RapidOCR result
    """
    import numpy as np
    img = Image.open(io.BytesIO(file_bytes))
    if img.mode == "RGBA":
        img = img.convert("RGB")
    arr = np.array(img)
    engine = _get_ocr()
    result, _elapsed = engine(arr)
    if not result:
        return {"text": "", "lines": [], "raw": []}
    lines = []
    texts = []
    for box, text, conf in result:
        # box is 4 points [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]
        xs = [p[0] for p in box]
        ys = [p[1] for p in box]
        bbox = [int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys))]
        lines.append({"text": text, "bbox": bbox, "conf": round(float(conf), 3)})
        texts.append(text)
    return {"text": "\n".join(texts), "lines": lines, "raw": result}


# --------------------------------------------------------------------------- #
# Red-pen detection (P2 - OpenCV)                                              #
# --------------------------------------------------------------------------- #

def detect_red_strokes(file_bytes: bytes) -> bool:
    """Detect if image contains red pen marks (✓ checkmarks).

    Uses HSV color thresholding + connected component analysis.
    Returns True if red strokes found (indicating the answer was marked correct).
    """
    try:
        import cv2
        import numpy as np
    except ImportError:
        return False

    arr = np.frombuffer(file_bytes, np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        return False

    # Convert to HSV for better red detection
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    # Red wraps around 0/180 in HSV, so two ranges
    mask1 = cv2.inRange(hsv, (0, 80, 80), (10, 255, 255))
    mask2 = cv2.inRange(hsv, (170, 80, 80), (180, 255, 255))
    mask = cv2.bitwise_or(mask1, mask2)

    # Morphological cleanup
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    mask = cv2.dilate(mask, kernel, iterations=2)
    mask = cv2.erode(mask, kernel, iterations=1)

    # Connected components
    num_labels, _labels, stats, _centroids = cv2.connectedComponentsWithStats(mask, connectivity=8)
    red_count = 0
    for i in range(1, num_labels):  # skip background (0)
        area = stats[i, cv2.CC_STAT_AREA]
        w = stats[i, cv2.CC_STAT_WIDTH]
        h = stats[i, cv2.CC_STAT_HEIGHT]
        if 30 <= area <= 3000 and 0.2 < (w / max(h, 1)) < 5.0:
            red_count += 1
    return red_count >= 1


# --------------------------------------------------------------------------- #
# Question splitting (P2 - detect multiple questions on a page)               #
# --------------------------------------------------------------------------- #

def split_questions(file_bytes: bytes) -> list[dict[str, Any]]:
    """Detect and split multiple questions on a single page image.

    Returns list of {bbox, text, thumbnail} per detected question.
    Uses OCR boxes + question-number regex to find boundaries.
    """
    ocr_result = ocr_image(file_bytes)
    lines = ocr_result["lines"]
    if not lines:
        return []

    # Match question numbers: 1. 2. 3. / 一、二、 / I. II. / (1)(2)
    qnum_pattern = re.compile(
        r"^(?:"
        r"(?:[一二三四五六七八九十]{1,3}[、.．])"  # 中文数字
        r"|(?:\d{1,2}[.．、])"                      # 阿拉伯数字
        r"|(?:[IVX]{1,4}[.．])"                     # 罗马数字
        r"|(?:[（(]\d{1,2}[)）])"                   # (1)(2)
        r")"
    )

    # Find lines that start with a question number
    q_starts = []
    for i, line in enumerate(lines):
        if qnum_pattern.match(line["text"].strip()):
            q_starts.append(i)

    if not q_starts:
        # No question numbers found, treat whole image as one question
        img = Image.open(io.BytesIO(file_bytes))
        return [{
            "bbox": [0, 0, img.width, img.height],
            "text": ocr_result["text"],
            "thumbnail": make_thumbnail(file_bytes),
            "qno": None,
        }]

    # Build question segments
    questions = []
    for idx, start_line in enumerate(q_starts):
        end_line = q_starts[idx + 1] if idx + 1 < len(q_starts) else len(lines)
        segment_lines = lines[start_line:end_line]
        # Compute bounding box from all lines in segment
        x1 = min(l["bbox"][0] for l in segment_lines)
        y1 = min(l["bbox"][1] for l in segment_lines)
        x2 = max(l["bbox"][2] for l in segment_lines)
        y2 = max(l["bbox"][3] for l in segment_lines)
        # Add padding
        pad = 10
        img = Image.open(io.BytesIO(file_bytes))
        x1 = max(0, x1 - pad)
        y1 = max(0, y1 - pad)
        x2 = min(img.width, x2 + pad)
        y2 = min(img.height, y2 + pad)
        text = "\n".join(l["text"] for l in segment_lines)
        qno = segment_lines[0]["text"].strip()
        try:
            crop_bytes, thumb = crop_by_bbox(file_bytes, [x1, y1, x2, y2])
            crop_url = save_upload(crop_bytes, subdir="crops")
        except Exception:
            thumb = make_thumbnail(file_bytes)
            crop_url = None
        questions.append({
            "bbox": [x1, y1, x2, y2],
            "text": text,
            "thumbnail": thumb,
            "crop_url": crop_url,
            "qno": qno,
        })
    return questions

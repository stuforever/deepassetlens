/**
 * 内联二维码生成组件（QrSvg / QrCanvas）——移植约定 #8：tupu 无 qrcode.react 依赖且不许加包，
 * 故以公开算法内联实现替代原仓 `qrcode.react` 的 <QRCodeSVG> / <QRCodeCanvas>（API 一一对位：
 * value / size / level 三参同义；SVG 版为矢量 <svg>，Canvas 版为 <canvas> 且支持 toDataURL 导出 PNG）。
 *
 * 编码核心（字节模式 UTF-8、版本 1-40 自适应、L/M/Q/H 纠错、Reed-Solomon、8 掩码择优）
 * 移植自 Project Nayuki「QR Code generator library」（MIT License，原版权声明如下），
 * 遵循其许可证要求在此保留声明：
 *   Copyright © 2020 Project Nayuki. (MIT License)
 *   https://www.nayuki.io/page/qr-code-generator-library
 *   Permission is hereby granted, free of charge, to any person obtaining a copy of
 *   this software and associated documentation files (the "Software"), to deal in
 *   the Software without restriction, including without limitation the rights to use,
 *   copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the
 *   Software, and to permit persons to whom the Software is furnished to do so,
 *   subject to the following conditions: The above copyright notice and this permission
 *   notice shall be included in all copies or substantial portions of the Software.
 *   The software is provided "as is", without warranty of any kind, express or implied.
 *
 * 视觉对位 qrcode.react 默认值：bgColor #FFFFFF、fgColor #000000、margin 0、方块模块。
 */
import React, { useEffect, useMemo, useRef } from "react";

export type QrEccLevel = "L" | "M" | "Q" | "H";

const FORMAT_BITS_ARR = [1, 0, 3, 2]; // L M Q H（标准 format info 前缀）

// ---- 标准容量表（ECC codewords per block / blocks per version，Nayuki 原表） ----
const ECC_CODEWORDS_PER_BLOCK: number[][] = [
  [-1, 7, 10, 15, 20, 26, 18, 20, 24, 30, 18, 20, 24, 26, 30, 22, 24, 28, 30, 28, 28, 28, 28, 30, 30, 26, 28, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30],
  [-1, 10, 16, 26, 18, 24, 16, 18, 22, 22, 26, 30, 22, 22, 24, 24, 28, 28, 26, 26, 26, 26, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28],
  [-1, 13, 22, 18, 26, 18, 24, 18, 22, 20, 24, 28, 26, 24, 20, 30, 24, 28, 28, 26, 30, 28, 30, 30, 30, 30, 28, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30],
  [-1, 17, 28, 22, 16, 22, 28, 26, 26, 24, 28, 24, 28, 22, 24, 24, 30, 28, 28, 26, 28, 30, 24, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30],
];
const NUM_ERROR_CORRECTION_BLOCKS: number[][] = [
  [-1, 1, 1, 1, 1, 1, 2, 2, 2, 2, 4, 4, 4, 4, 4, 6, 6, 6, 6, 7, 8, 8, 9, 9, 10, 12, 12, 12, 13, 14, 15, 16, 17, 18, 19, 19, 20, 21, 22, 24, 25],
  [-1, 1, 1, 1, 2, 2, 4, 4, 4, 5, 5, 5, 8, 9, 9, 10, 10, 11, 13, 14, 16, 17, 17, 18, 20, 21, 23, 25, 26, 28, 29, 31, 33, 35, 37, 38, 40, 43, 45, 47, 49],
  [-1, 1, 1, 2, 2, 4, 4, 6, 6, 8, 8, 8, 10, 12, 16, 12, 17, 16, 18, 21, 20, 23, 23, 25, 27, 29, 34, 34, 35, 38, 40, 43, 45, 48, 51, 53, 56, 59, 62, 65, 68],
  [-1, 1, 1, 2, 4, 4, 4, 5, 6, 8, 8, 11, 11, 16, 16, 18, 16, 19, 21, 25, 25, 25, 34, 30, 32, 35, 37, 40, 42, 45, 48, 51, 54, 57, 60, 63, 66, 70, 74, 77, 81],
];

function getNumRawDataModules(ver: number): number {
  let result = (16 * ver + 128) * ver + 64;
  if (ver >= 2) {
    const numAlign = Math.floor(ver / 7) + 2;
    result -= (25 * numAlign - 10) * numAlign - 55;
    if (ver >= 7) result -= 36;
  }
  return result;
}

function getNumDataCodewords(ver: number, ecl: number): number {
  return (
    Math.floor(getNumRawDataModules(ver) / 8) -
    ECC_CODEWORDS_PER_BLOCK[ecl][ver] * NUM_ERROR_CORRECTION_BLOCKS[ecl][ver]
  );
}

function getBit(x: number, i: number): boolean {
  return ((x >>> i) & 1) !== 0;
}

// ---- GF(256) Reed-Solomon ----
function rsMultiply(x: number, y: number): number {
  let z = 0;
  for (let i = 7; i >= 0; i--) {
    z = (z << 1) ^ ((z >>> 7) * 0x11d);
    z ^= ((y >>> i) & 1) * x;
  }
  return z;
}

function rsDivisor(degree: number): number[] {
  const result: number[] = [];
  for (let i = 0; i < degree - 1; i++) result.push(0);
  result.push(1);
  let root = 1;
  for (let i = 0; i < degree; i++) {
    for (let j = 0; j < result.length; j++) {
      result[j] = rsMultiply(result[j], root);
      if (j + 1 < result.length) result[j] ^= result[j + 1];
    }
    root = rsMultiply(root, 0x02);
  }
  return result;
}

function rsRemainder(data: number[], divisor: number[]): number[] {
  const result: number[] = divisor.map(() => 0);
  for (const b of data) {
    const factor = b ^ (result.shift() as number);
    result.push(0);
    divisor.forEach((coef, i) => {
      result[i] ^= rsMultiply(coef, factor);
    });
  }
  return result;
}

function addEccAndInterleave(data: number[], ver: number, ecl: number): number[] {
  const numBlocks = NUM_ERROR_CORRECTION_BLOCKS[ecl][ver];
  const blockEccLen = ECC_CODEWORDS_PER_BLOCK[ecl][ver];
  const rawCodewords = Math.floor(getNumRawDataModules(ver) / 8);
  const numShortBlocks = numBlocks - (rawCodewords % numBlocks);
  const shortBlockLen = Math.floor(rawCodewords / numBlocks);
  const blocks: number[][] = [];
  const rsDiv = rsDivisor(blockEccLen);
  for (let i = 0, k = 0; i < numBlocks; i++) {
    const dat = data.slice(k, k + shortBlockLen - blockEccLen + (i < numShortBlocks ? 0 : 1));
    k += dat.length;
    const ecc = rsRemainder(dat, rsDiv);
    if (i < numShortBlocks) dat.push(0);
    blocks.push(dat.concat(ecc));
  }
  const result: number[] = [];
  for (let i = 0; i < blocks[0].length; i++) {
    blocks.forEach((block, j) => {
      if (i !== shortBlockLen - blockEccLen || j >= numShortBlocks) result.push(block[i]);
    });
  }
  return result;
}

// ---- 矩阵绘制 ----
function getAlignmentPositions(ver: number, size: number): number[] {
  if (ver === 1) return [];
  const numAlign = Math.floor(ver / 7) + 2;
  const step = ver === 32 ? 26 : Math.ceil((ver * 4 + 4) / (numAlign * 2 - 2)) * 2;
  const result: number[] = [6];
  for (let pos = size - 7; result.length < numAlign; pos -= step) result.splice(1, 0, pos);
  return result;
}

function drawFinderPattern(setFn: (x: number, y: number, dark: boolean) => void, x: number, y: number, size: number): void {
  for (let dy = -4; dy <= 4; dy++) {
    for (let dx = -4; dx <= 4; dx++) {
      const dist = Math.max(Math.abs(dx), Math.abs(dy));
      const xx = x + dx;
      const yy = y + dy;
      if (0 <= xx && xx < size && 0 <= yy && yy < size) setFn(xx, yy, dist !== 2 && dist !== 4);
    }
  }
}

function drawAlignmentPattern(setFn: (x: number, y: number, dark: boolean) => void, x: number, y: number): void {
  for (let dy = -2; dy <= 2; dy++) {
    for (let dx = -2; dx <= 2; dx++) {
      setFn(x + dx, y + dy, Math.max(Math.abs(dx), Math.abs(dy)) !== 1);
    }
  }
}

function formatBits(ecl: number, mask: number): number {
  const data = FORMAT_BITS_ARR[ecl] << 3 | mask;
  let rem = data;
  for (let i = 0; i < 10; i++) rem = (rem << 1) ^ ((rem >>> 9) * 0x537);
  return (data << 10 | rem) ^ 0x5412;
}

function drawFormatBits(setFn: (x: number, y: number, dark: boolean) => void, ecl: number, mask: number, size: number): void {
  const bits = formatBits(ecl, mask);
  for (let i = 0; i <= 5; i++) setFn(8, i, getBit(bits, i));
  setFn(8, 7, getBit(bits, 6));
  setFn(8, 8, getBit(bits, 7));
  setFn(7, 8, getBit(bits, 8));
  for (let i = 9; i < 15; i++) setFn(14 - i, 8, getBit(bits, i));
  for (let i = 0; i < 8; i++) setFn(size - 1 - i, 8, getBit(bits, i));
  for (let i = 8; i < 15; i++) setFn(8, size - 15 + i, getBit(bits, i));
  setFn(8, size - 8, true);
}

function drawVersion(setFn: (x: number, y: number, dark: boolean) => void, ver: number, size: number): void {
  if (ver < 7) return;
  let rem = ver;
  for (let i = 0; i < 12; i++) rem = (rem << 1) ^ ((rem >>> 11) * 0x1f25);
  const bits = ver << 12 | rem;
  for (let i = 0; i < 18; i++) {
    const color = getBit(bits, i);
    const a = size - 11 + (i % 3);
    const b = Math.floor(i / 3);
    setFn(a, b, color);
    setFn(b, a, color);
  }
}

function drawCodewords(
  modules: boolean[][],
  isFunction: boolean[][],
  size: number,
  data: number[],
): void {
  let i = 0;
  for (let right = size - 1; right >= 1; right -= 2) {
    if (right === 6) right = 5;
    for (let vert = 0; vert < size; vert++) {
      for (let j = 0; j < 2; j++) {
        const x = right - j;
        const upward = ((right + 1) & 2) === 0;
        const y = upward ? size - 1 - vert : vert;
        if (!isFunction[y][x] && i < data.length * 8) {
          modules[y][x] = getBit(data[i >>> 3], 7 - (i & 7));
          i++;
        }
      }
    }
  }
}

function applyMask(modules: boolean[][], isFunction: boolean[][], size: number, mask: number): void {
  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) {
      let invert = false;
      switch (mask) {
        case 0: invert = (x + y) % 2 === 0; break;
        case 1: invert = y % 2 === 0; break;
        case 2: invert = x % 3 === 0; break;
        case 3: invert = (x + y) % 3 === 0; break;
        case 4: invert = (Math.floor(x / 3) + Math.floor(y / 2)) % 2 === 0; break;
        case 5: invert = ((x * y) % 2) + ((x * y) % 3) === 0; break;
        case 6: invert = (((x * y) % 2) + ((x * y) % 3)) % 2 === 0; break;
        case 7: invert = (((x + y) % 2) + ((x * y) % 3)) % 2 === 0; break;
      }
      if (!isFunction[y][x] && invert) modules[y][x] = !modules[y][x];
    }
  }
}

/** 标准四条掩码罚分规则（N1 同色长条 / N2 同色 2×2 / N3 类定位图形 / N4 黑白占比）。 */
function penaltyScore(m: boolean[][]): number {
  const size = m.length;
  let result = 0;
  const PAT1 = [1, 0, 1, 1, 1, 0, 1, 0, 0, 0, 0]; // 10111010000
  const PAT2 = [0, 0, 0, 0, 1, 0, 1, 1, 1, 0, 1]; // 00001011101
  // N1（行/列同色连续段）+ N3（行/列类定位图案）
  for (let axis = 0; axis < 2; axis++) {
    for (let a = 0; a < size; a++) {
      let runColor = axis === 0 ? m[a][0] : m[0][a];
      let runLen = 1;
      for (let b = 1; b < size; b++) {
        const v = axis === 0 ? m[a][b] : m[b][a];
        if (v === runColor) {
          runLen++;
          if (runLen === 5) result += 3;
          else if (runLen > 5) result += 1;
        } else {
          runColor = v;
          runLen = 1;
        }
      }
      for (let x = 0; x + 11 <= size; x++) {
        let m1 = true;
        let m2 = true;
        for (let k = 0; k < 11; k++) {
          const bit = axis === 0 ? (m[a][x + k] ? 1 : 0) : (m[x + k][a] ? 1 : 0);
          if (bit !== PAT1[k]) m1 = false;
          if (bit !== PAT2[k]) m2 = false;
        }
        if (m1) result += 40;
        if (m2) result += 40;
      }
    }
  }
  // N2：同色 2×2 块
  for (let y = 0; y < size - 1; y++) {
    for (let x = 0; x < size - 1; x++) {
      if (m[y][x] === m[y][x + 1] && m[y][x] === m[y + 1][x] && m[y][x] === m[y + 1][x + 1]) result += 3;
    }
  }
  // N4：黑/白占比
  let dark = 0;
  for (const row of m) for (const c of row) if (c) dark++;
  const total = size * size;
  const k = Math.ceil(Math.abs(dark * 20 - total * 10) / total) - 1;
  result += k * 10;
  return result;
}

/** 编码入口：文本 -> 模块矩阵（字节模式 UTF-8，自动选最小版本，8 掩码择优）。 */
export function encodeQrModules(text: string, level: QrEccLevel = "L"): boolean[][] {
  const ecl = (["L", "M", "Q", "H"] as QrEccLevel[]).indexOf(level);
  const data = Array.from(new TextEncoder().encode(text));
  let version = 0;
  for (let v = 1; v <= 40; v++) {
    const ccbits = v <= 9 ? 8 : 16;
    if (4 + ccbits + data.length * 8 <= getNumDataCodewords(v, ecl) * 8) {
      version = v;
      break;
    }
  }
  if (version === 0) throw new Error("Data too long to encode as QR");

  // 数据段编码（字节模式 0100 + 字符数 + 数据 + 终止符 + 0xEC/0x11 填充）
  const capacityBits = getNumDataCodewords(version, ecl) * 8;
  const bits: number[] = [];
  const appendBits = (val: number, len: number) => {
    for (let i = len - 1; i >= 0; i--) bits.push((val >>> i) & 1);
  };
  appendBits(0x4, 4);
  appendBits(data.length, version <= 9 ? 8 : 16);
  for (const b of data) appendBits(b, 8);
  appendBits(0, Math.min(4, capacityBits - bits.length));
  if (bits.length % 8 !== 0) appendBits(0, 8 - (bits.length % 8));
  for (let pad = 0xec; bits.length < capacityBits; pad ^= 0xec ^ 0x11) appendBits(pad, 8);
  const codewords: number[] = [];
  for (let i = 0; i + 8 <= bits.length; i += 8) {
    let byte = 0;
    for (let j = 0; j < 8; j++) byte = (byte << 1) | bits[i + j];
    codewords.push(byte);
  }
  const allCodewords = addEccAndInterleave(codewords, version, ecl);

  const size = version * 4 + 17;
  const modules: boolean[][] = [];
  const isFunction: boolean[][] = [];
  for (let i = 0; i < size; i++) {
    modules.push(new Array<boolean>(size).fill(false));
    isFunction.push(new Array<boolean>(size).fill(false));
  }
  const setFn = (x: number, y: number, dark: boolean) => {
    modules[y][x] = dark;
    isFunction[y][x] = true;
  };
  for (let i = 0; i < size; i++) {
    setFn(6, i, i % 2 === 0);
    setFn(i, 6, i % 2 === 0);
  }
  drawFinderPattern(setFn, 3, 3, size);
  drawFinderPattern(setFn, size - 4, 3, size);
  drawFinderPattern(setFn, 3, size - 4, size);
  const alignPos = getAlignmentPositions(version, size);
  for (let i = 0; i < alignPos.length; i++) {
    for (let j = 0; j < alignPos.length; j++) {
      if (!(i === 0 && j === 0 || i === 0 && j === alignPos.length - 1 || i === alignPos.length - 1 && j === 0)) {
        drawAlignmentPattern(setFn, alignPos[i], alignPos[j]);
      }
    }
  }
  drawFormatBits(setFn, ecl, 0, size);
  drawVersion(setFn, version, size);

  // 8 掩码逐个试：绘制码字 -> 施掩码 -> 计罚分，取最低分
  let bestScore = Infinity;
  let bestModules: boolean[][] | null = null;
  for (let mask = 0; mask < 8; mask++) {
    const trial: boolean[][] = modules.map((row) => row.slice());
    drawFormatBits((x, y, dark) => {
      trial[y][x] = dark;
    }, ecl, mask, size);
    drawCodewords(trial, isFunction, size, allCodewords);
    applyMask(trial, isFunction, size, mask);
    const score = penaltyScore(trial);
    if (score < bestScore) {
      bestScore = score;
      bestModules = trial;
    }
  }
  return bestModules as boolean[][];
}

/** 对位 qrcode.react 的 <QRCodeSVG value size level>：矢量 SVG，默认白底黑码。 */
export function QrSvg({ value, size, level = "L" }: { value: string; size: number; level?: QrEccLevel }) {
  const modules = useMemo(() => encodeQrModules(value, level), [value, level]);
  const n = modules.length;
  let path = "";
  for (let y = 0; y < n; y++) {
    for (let x = 0; x < n; x++) {
      if (modules[y][x]) path += `M${x} ${y}h1v1h-1z`;
    }
  }
  return (
    <svg width={size} height={size} viewBox={`0 0 ${n} ${n}`} role="img" aria-label={value}>
      <rect width={n} height={n} fill="#FFFFFF" />
      <path d={path} fill="#000000" />
    </svg>
  );
}

/** 对位 qrcode.react 的 <QRCodeCanvas value size level>：位图 canvas（供 toDataURL 导出 PNG）。 */
export function QrCanvas({ value, size, level = "L" }: { value: string; size: number; level?: QrEccLevel }) {
  const ref = useRef<HTMLCanvasElement>(null);
  const modules = useMemo(() => encodeQrModules(value, level), [value, level]);
  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    const n = modules.length;
    const scale = size / n;
    ctx.fillStyle = "#FFFFFF";
    ctx.fillRect(0, 0, size, size);
    ctx.fillStyle = "#000000";
    for (let y = 0; y < n; y++) {
      for (let x = 0; x < n; x++) {
        if (modules[y][x]) ctx.fillRect(x * scale, y * scale, scale, scale);
      }
    }
  }, [modules, size]);
  return <canvas ref={ref} width={size} height={size} />;
}

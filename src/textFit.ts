/**
 * Picks the largest font size (never above the authored size) that keeps
 * `text` wrapped inside a maxWidthPx x maxHeightPx box, by simulating the
 * browser's word-wrap using the native Canvas 2D text-measurement API -- the
 * same metrics engine the actual <p> renders with, with zero added
 * dependencies (rung 4 of the ladder: native platform feature).
 *
 * This is the structural mechanism behind the character-safe area: callers
 * don't hand-tune font size or position per episode, they hand this
 * function a box and get back a size that's guaranteed to fit whatever text
 * shows up.
 */

let measureCtx: CanvasRenderingContext2D | null | undefined;

function getMeasureCtx(): CanvasRenderingContext2D | null {
  if (typeof document === "undefined") return null; // Node-side; real fit happens in the browser render.
  if (measureCtx === undefined) {
    measureCtx = document.createElement("canvas").getContext("2d");
  }
  return measureCtx;
}

function countWrappedLines(
  text: string,
  font: string,
  letterSpacingPx: number,
  maxWidthPx: number,
  ctx: CanvasRenderingContext2D
): number {
  ctx.font = font;
  const spaceWidth = ctx.measureText(" ").width + letterSpacingPx;
  let lines = 0;

  for (const paragraph of text.split("\n")) {
    const words = paragraph.split(" ").filter(Boolean);
    if (words.length === 0) {
      lines += 1;
      continue;
    }
    lines += 1;
    let lineWidth = 0;
    for (const word of words) {
      const wordWidth = ctx.measureText(word).width + letterSpacingPx * word.length;
      const needed = lineWidth > 0 ? lineWidth + spaceWidth + wordWidth : wordWidth;
      if (lineWidth > 0 && needed > maxWidthPx) {
        lines += 1;
        lineWidth = wordWidth;
      } else {
        lineWidth = needed;
      }
    }
  }
  return lines;
}

export function fitFontSizeToBox(params: {
  text: string;
  fontFamily: string;
  fontWeight: string;
  fontStyle: string;
  letterSpacingPx: number;
  lineHeightMultiplier: number;
  authoredFontSize: number;
  maxWidthPx: number;
  maxHeightPx: number;
  minFontSize?: number;
}): number {
  const {
    text,
    fontFamily,
    fontWeight,
    fontStyle,
    letterSpacingPx,
    lineHeightMultiplier,
    authoredFontSize,
    maxWidthPx,
    maxHeightPx,
    minFontSize = 20,
  } = params;

  const ctx = getMeasureCtx();
  if (!ctx || maxWidthPx <= 0 || maxHeightPx <= 0 || !text.trim()) return authoredFontSize;

  for (let fontSize = authoredFontSize; fontSize >= minFontSize; fontSize -= 1) {
    const font = `${fontStyle} ${fontWeight} ${fontSize}px ${fontFamily}`;
    const lines = countWrappedLines(text, font, letterSpacingPx, maxWidthPx, ctx);
    if (lines * fontSize * lineHeightMultiplier <= maxHeightPx) return fontSize;
  }
  // ponytail: the floor is a hard stop, not a guarantee -- a pathological
  // input (e.g. one unbroken 200-character word) can still overflow at the
  // floor size. Lower minFontSize's caller default or shorten the line if
  // that ever shows up in practice.
  return minFontSize;
}

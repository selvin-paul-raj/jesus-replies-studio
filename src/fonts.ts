import { loadFont as loadDialogueFont } from "@remotion/google-fonts/Lora";
import { loadFont as loadTitleFont } from "@remotion/google-fonts/Anton";
import { loadFont as loadCalmFont } from "@remotion/google-fonts/Domine";
import { loadFont as loadTamilFont } from "@remotion/google-fonts/NotoSansTamil";
import { loadFont as loadDevanagariFont } from "@remotion/google-fonts/NotoSansDevanagari";

/** Serif used for all dialogue/quote/reflection text -- matches the reference
 * mockup's clean editorial look and replaces the system-only Georgia default. */
export const { fontFamily: dialogueFontFamily } = loadDialogueFont("normal", {
  weights: ["400", "600", "700"],
  subsets: ["latin"],
});

/** Bold condensed display font for the thumbnail title (e.g. "WHY WASH FEET?"). */
export const { fontFamily: titleFontFamily } = loadTitleFont();

/** Softer, rounder serif than dialogueFontFamily -- used only by the standalone
 * BibleVersePost card for its calmer, relaxed look. */
export const { fontFamily: calmSerifFontFamily } = loadCalmFont("normal", {
  weights: ["400", "600", "700"],
  subsets: ["latin"],
});

/** DEC-JR-018 subtitle versions: Noto Sans covers Tamil and Devanagari conjuncts/ligatures
 * (Lora/Domine have no Indic glyphs, so the browser would fall back to tofu or a system font). */
export const { fontFamily: tamilFontFamily } = loadTamilFont("normal", { weights: ["600"], subsets: ["tamil", "latin"] });
export const { fontFamily: devanagariFontFamily } = loadDevanagariFont("normal", { weights: ["600"], subsets: ["devanagari", "latin"] });

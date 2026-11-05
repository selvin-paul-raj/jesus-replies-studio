/** DEC-JR-018: render content-os/carousels/<id>.json slides to content-os/carousels/<id>/slide-N.png (1080x1350).
 * Usage: npx tsx scripts/content_os/render_carousel.ts CAR-2026-11-07 */
import fs from "node:fs";
import path from "node:path";
import { execSync } from "node:child_process";

const id = process.argv[2];
const root = path.join(__dirname, "..", "..");
const c = JSON.parse(fs.readFileSync(path.join(root, "content-os/carousels", `${id}.json`), "utf-8"));
const outDir = path.join(root, "content-os/carousels", id);
fs.mkdirSync(outDir, { recursive: true });
const n = c.slides.length;
c.slides.forEach((s: any, i: number) => {
  const propsFile = path.join(outDir, `.props-${i + 1}.json`);
  let comp = "CarouselCard";
  let props: any;
  if (s.kind === "verse") {
    comp = "CarouselVerse";
    props = { verseText: s.text, referenceText: `${s.ref}\nKJV`, eyebrowLabel: s.eyebrow ?? `${i} / ${n - 2}  ·  ${s.label ?? ""}`.trim() };
  } else {
    props = { eyebrow: s.eyebrow ?? "", title: s.title, body: s.body ?? "", footer: s.footer ?? "" };
  }
  fs.writeFileSync(propsFile, JSON.stringify(props));
  const out = path.join(outDir, `slide-${i + 1}.png`);
  execSync(`npx remotion still src/index.ts ${comp} "${out}" --props="${propsFile}"`, { cwd: root, stdio: "inherit" });
  fs.unlinkSync(propsFile);
});
console.log(`[carousel] rendered ${n} slides to ${outDir}`);

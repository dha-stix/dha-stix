// Fills the "Latest writing" and "Latest videos" lists in README.md from
// davidasaolu.dev/api/latest. Run daily by .github/workflows/update-readme.yml.
import { readFile, writeFile } from "node:fs/promises";

const SOURCE = { blog: "Blog", dev: "DEV", fcc: "freeCodeCamp" };
const month = (iso) => new Date(iso).toLocaleDateString("en-GB", { month: "short", year: "numeric", timeZone: "UTC" });
const esc = (s) => s.replace(/([\[\]|*_`])/g, "\\$1");

const res = await fetch("https://davidasaolu.dev/api/latest", { headers: { "User-Agent": "dha-stix README updater" } });
if (!res.ok) throw new Error(`davidasaolu.dev/api/latest answered ${res.status}`);
const { articles, videos } = await res.json();

const writing = articles.map((a) => `- [${esc(a.title)}](${a.url})<br /><sub>${SOURCE[a.source] ?? a.source} · ${month(a.date)}</sub>`);
const watching = videos.map(
  (v) => `- [${esc(v.title)}](${v.url})<br /><sub>${month(v.date)}${v.views != null ? ` · ${v.views.toLocaleString("en-US")} views` : ""}</sub>`,
);

const fill = (text, name, lines) => {
  if (!lines.length) return text; // keep the last good list if a feed is empty
  const pattern = new RegExp(`(<!-- ${name}:START -->)[\\s\\S]*?(<!-- ${name}:END -->)`);
  return text.replace(pattern, `$1\n${lines.join("\n")}\n$2`);
};

const before = await readFile("README.md", "utf8");
const after = fill(fill(before, "WRITING", writing), "VIDEOS", watching);
if (after !== before) {
  await writeFile("README.md", after);
  console.log("README updated");
} else {
  console.log("No changes");
}

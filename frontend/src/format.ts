export type Block = { kind: "text" | "code"; text: string; lang?: string };

/** Split a response into plain-text and fenced-code blocks. */
export function splitBlocks(src: string): Block[] {
  const blocks: Block[] = [];
  const re = /```([\w+-]*)\n?([\s\S]*?)(?:```|$)/g;
  let last = 0;
  for (const m of src.matchAll(re)) {
    const before = src.slice(last, m.index).trim();
    if (before) blocks.push({ kind: "text", text: before });
    blocks.push({ kind: "code", lang: m[1] || undefined, text: m[2].replace(/\n$/, "") });
    last = (m.index ?? 0) + m[0].length;
  }
  const rest = src.slice(last).trim();
  if (rest) blocks.push({ kind: "text", text: rest });
  return blocks;
}

export function pct(x: number | null | undefined): string {
  return x == null ? "n/a" : `${Math.round(x * 100)}%`;
}

export function num(x: number | null | undefined, digits = 2): string {
  return x == null ? "n/a" : x.toFixed(digits);
}

/** Landis & Koch (1977) labels, the usual way kappa/alpha values are described. */
export function agreementLabel(x: number | null | undefined): string {
  if (x == null) return "not enough data";
  if (x < 0) return "worse than chance";
  if (x <= 0.2) return "slight";
  if (x <= 0.4) return "fair";
  if (x <= 0.6) return "moderate";
  if (x <= 0.8) return "substantial";
  return "almost perfect";
}

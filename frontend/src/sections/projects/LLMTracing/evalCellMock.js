// ---------------------------------------------------------------------------
// Eval cell display derivation (frontend-only mock)
// ---------------------------------------------------------------------------
//
// §4.4-4.6 of the "Group Evals by Eval Task" PRD ask the trace table to render:
//   - pass/fail rollups as "Pass X / Fail Y" counts across child spans,
//   - choice rollups as a chip cluster with per-label counts.
//
// The trace-list cell only receives a single scalar value per (trace × eval) —
// the backend does not send the per-span breakdown to the cell. So for the
// prototype these counts/distributions are derived deterministically from the
// cell value + eval column id (stable djb2 hash — no Math.random, so a given
// cell always renders the same counts). Real backend rollup payloads should
// replace mockPassFailRollup / mockChoiceDistribution when available.
//
// `_isEvalRollup` is set on the column (a shallow copy) by
// generateEvalColumnsGroupedByTask when a span-level eval is shown in the
// trace table. Direct (trace-level / span-row) evals never roll up.
// ---------------------------------------------------------------------------

import { classifyChoice } from "./evalTaskMock";

function hashString(str) {
  let h = 5381;
  const s = String(str || "");
  for (let i = 0; i < s.length; i += 1) h = (h * 33) ^ s.charCodeAt(i);
  return Math.abs(h);
}

const seedFor = (value, column) =>
  hashString(
    `${column?.id || ""}|${typeof value === "object" ? JSON.stringify(value) : value}`,
  );

export const isEvalRollup = (column) => column?._isEvalRollup === true;

function toNumber(v) {
  if (typeof v === "number") return v;
  if (v && typeof v === "object" && typeof v.score === "number") return v.score;
  const n = parseFloat(v);
  return Number.isNaN(n) ? null : n;
}

// Pass-rate 0..100 from whatever shape the value takes.
function passRate(value) {
  const n = toNumber(value);
  if (n != null) return n <= 1 ? n * 100 : n; // accept 0..1 or 0..100
  if (value === true) return 100;
  if (value === false) return 0;
  const s = String(value).toLowerCase();
  if (s.includes("fail")) return 0;
  if (s.includes("pass")) return 100;
  return 0;
}

/** Direct pass/fail result (span row / trace-level eval). */
export function isPassValue(value) {
  return passRate(value) >= 50;
}

/** Mock "Pass X / Fail Y" rollup across child spans (§4.5). */
export function mockPassFailRollup(value, column) {
  const seed = seedFor(value, column);
  const rate = passRate(value);
  const total = 5 + (seed % 10); // 5..14 spans
  const pass = Math.max(0, Math.min(total, Math.round((rate / 100) * total)));
  const fail = total - pass;
  return { pass, fail, total, pct: Math.round((pass / total) * 100) };
}

/** Choice label(s) present in the value. */
export function getChoiceLabels(value) {
  if (Array.isArray(value)) return value.map(String).filter(Boolean);
  if (value && typeof value === "object") {
    if (Array.isArray(value.choices)) return value.choices.map(String);
    if (value.choices != null) return [String(value.choices)];
    if (value.choice != null) return [String(value.choice)];
    if (value.label != null) return [String(value.label)];
  }
  if (typeof value === "string" || typeof value === "number")
    return [String(value)];
  return [];
}

/** Single choice result (span row / trace-level eval). */
export function getChoiceSingle(value, column) {
  const label = getChoiceLabels(value)[0];
  if (label == null) return null;
  return { label, tone: classifyChoice(label, column) };
}

/**
 * Mock choice distribution across child spans (§4.6.3): one entry per distinct
 * label present in the value, each with a deterministic count + tone, sorted
 * by count desc.
 */
export function mockChoiceDistribution(value, column) {
  const labels = getChoiceLabels(value);
  const map = new Map();
  labels.forEach((label, i) => {
    if (map.has(label)) return;
    const count = 1 + (hashString(`${label}|${column?.id || ""}|${i}`) % 11); // 1..11
    map.set(label, { label, count, tone: classifyChoice(label, column) });
  });
  const items = Array.from(map.values()).sort((a, b) => b.count - a.count);
  const spanCount = items.reduce((s, it) => s + it.count, 0);
  return { items, spanCount };
}

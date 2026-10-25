import { createHash } from "node:crypto";

export function stableStringify(obj: any): string {
  if (obj === null || typeof obj !== "object") {
    return JSON.stringify(obj);
  }
  if (Array.isArray(obj)) {
    return "[" + obj.map(stableStringify).join(",") + "]";
  }
  const sortedKeys = Object.keys(obj).sort();
  const entries = sortedKeys.map((k) => JSON.stringify(k) + ":" + stableStringify(obj[k]));
  return "{" + entries.join(",") + "}";
}

export function computeSha256(obj: any): string {
  return createHash("sha256").update(stableStringify(obj)).digest("hex");
}

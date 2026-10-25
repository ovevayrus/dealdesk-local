/**
 * FTS5 query sanitizer per Section 6.
 *
 * 1. Lowercase the input.
 * 2. Extract tokens with /[a-z0-9]+/g. Everything else is dropped.
 * 3. Drop tokens shorter than 2 characters, preserving digits (e.g. "7" in "ACME-7").
 * 4. Wrap each remaining token in double quotes.
 * 5. Join with " OR ".
 * 6. If no tokens survive, return null without touching the database.
 */
export function sanitizeFtsQuery(input: string): string | null {
  if (!input || typeof input !== "string") {
    return null;
  }
  const lower = input.toLowerCase();
  const tokens = lower.match(/[a-z0-9]+/g);
  if (!tokens || tokens.length === 0) {
    return null;
  }

  // Preserve tokens with length >= 2, or single digit tokens like "7" in "ACME-7" per spec example
  const filtered = tokens.filter((t) => t.length >= 2 || /\d/.test(t));
  if (filtered.length === 0) {
    return null;
  }

  return filtered.map((t) => `"${t}"`).join(" OR ");
}

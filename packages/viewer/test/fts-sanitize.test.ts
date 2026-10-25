import test from "node:test";
import assert from "node:assert/strict";
import { sanitizeFtsQuery } from "../src/lib/fts.ts";
import { searchEvidence } from "../src/lib/retrieval.ts";
import type { Actor } from "@dealdesk/contracts";

test("fts-sanitize: freight costs for ACME-7? produces expected MATCH expression", () => {
  const result = sanitizeFtsQuery("freight costs for ACME-7?");
  assert.equal(result, '"freight" OR "costs" OR "for" OR "acme" OR "7"');
});

test("fts-sanitize: quotes, asterisks, and NEAR operators are sanitized safely", () => {
  const sanitized = sanitizeFtsQuery('costs "hardware"* NEAR installation');
  assert.ok(sanitized);
  // Quotes are escaped/structured and asterisks removed
  assert.ok(!sanitized.includes("*"));
  // No bare unquoted NEAR keyword
  assert.ok(!sanitized.split(" OR ").includes("NEAR"));
  assert.ok(sanitized.includes('"near"'));
});

test("fts-sanitize: single letter 'a' is dropped while single digit '7' is retained", () => {
  const result = sanitizeFtsQuery("a 7 acme");
  assert.equal(result, '"7" OR "acme"');
});

test("fts-sanitize: all-punctuation query returns null and zero hits without querying db", () => {
  const sanitized = sanitizeFtsQuery("?!@#$%^&*()_+:;");
  assert.equal(sanitized, null);

  const actor: Actor = {
    userId: "u-sofia",
    role: "seller",
    accountIds: ["ACME-7"],
  };

  const res = searchEvidence({ accountId: "ACME-7", query: "?!@#$%^&*()" }, actor);
  assert.equal(res.hits.length, 0);
});

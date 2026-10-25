import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { hydrateEvidence } from "../src/lib/retrieval.ts";
import type { Actor, QuoteVersion, EvidenceRef } from "@dealdesk/contracts";

const __dirname = dirname(fileURLToPath(import.meta.url));
const seedFile = resolve(__dirname, "../fixtures/quote-version.seed.json");
const seedQuote: QuoteVersion = JSON.parse(readFileSync(seedFile, "utf-8"));

const sofia: Actor = {
  userId: "u-sofia",
  role: "seller",
  accountIds: ["ACME-7"],
};

const dana: Actor = {
  userId: "u-dana",
  role: "manager",
  accountIds: ["ACME-7", "NORTHWIND-2"],
};

test("hydration-isolation: u-sofia cannot read restricted citations; marked withheld with no leakage", () => {
  const sofiaHits = hydrateEvidence(seedQuote.evidence, sofia);
  const danaHits = hydrateEvidence(seedQuote.evidence, dana);

  // Assert hit count is identical (list must not silently shrink)
  assert.equal(
    sofiaHits.length,
    seedQuote.evidence.length,
    "Evidence list count must remain complete for seller"
  );
  assert.equal(
    sofiaHits.length,
    danaHits.length,
    "Both actors must receive the identical number of citation slots"
  );

  // Assert no returned hit for seller has classification: "restricted"
  const hasRestrictedClassification = sofiaHits.some(
    (h) => h.classification === "restricted"
  );
  assert.equal(
    hasRestrictedClassification,
    false,
    "No hit returned to seller can have classification 'restricted'"
  );

  // Find acme-renewal-history hit in both
  const sofiaRestrictedHit = sofiaHits.find((h) => h.docId === "acme-renewal-history");
  assert.ok(sofiaRestrictedHit, "Withheld hit must be present in seller results");
  assert.equal(sofiaRestrictedHit.withheld, true, "Restricted citation must have withheld: true");

  // Assert passage does not leak any text from acme-renewal-history
  assert.ok(
    !sofiaRestrictedHit.passage.includes("12.5%"),
    "Passage must not leak discount percentage from restricted doc"
  );
  assert.ok(
    !sofiaRestrictedHit.passage.includes("churn"),
    "Passage must not leak churn assessment from restricted doc"
  );
  assert.equal(
    sofiaRestrictedHit.docTitle,
    "[WITHHELD]",
    "Title must be withheld for seller"
  );
  assert.equal(
    sofiaRestrictedHit.section,
    "[WITHHELD]",
    "Section must be withheld for seller"
  );

  // Manager u-dana sees full citation
  const danaRestrictedHit = danaHits.find((h) => h.docId === "acme-renewal-history");
  assert.ok(danaRestrictedHit, "Hit must be present for manager");
  assert.equal(!danaRestrictedHit.withheld, true, "Hit must not be withheld for manager");
  assert.equal(danaRestrictedHit.classification, "restricted");
  assert.ok(danaRestrictedHit.passage.includes("12.5%"));
});

test("hydration-missing: unknown document or section returns missing: true without throwing", () => {
  const brokenRefs: EvidenceRef[] = [
    {
      docId: "non-existent-doc",
      docHash: "fakehash",
      section: "Some Missing Section",
      chunkIndex: 0,
    },
    {
      docId: "acme-profile",
      docHash: "fakehash",
      section: "NonExistentSectionInValidDoc",
      chunkIndex: 99,
    },
  ];

  const hits = hydrateEvidence(brokenRefs, dana);
  assert.equal(hits.length, 2);
  assert.equal(hits[0].missing, true);
  assert.equal(hits[1].missing, true);
});

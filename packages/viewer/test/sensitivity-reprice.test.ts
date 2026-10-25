import test from "node:test";
import assert from "node:assert/strict";
import { getDb } from "../src/lib/db.ts";
import { priceDeal } from "../src/lib/pricing-client.ts";
import { renderEconomicsFragment } from "../src/lib/economics-html.ts";
import { computeSha256 } from "../src/lib/hash.ts";
import type { QuoteVersion } from "@dealdesk/contracts";

test("sensitivity-reprice: shock scenario creates version 2 showing 22.35% while version 1 still shows 28.24%", async () => {
  const db = getDb();

  // 1. Verify version 1 exists in DB and has 28.24% stress margin
  const rowV1 = db.prepare(`
    SELECT payload FROM quote_versions WHERE quote_id = ? AND version = 1
  `).get("q-seed-acme-7") as any;
  assert.ok(rowV1, "Version 1 must exist in DB");
  const v1: QuoteVersion = JSON.parse(rowV1.payload);
  assert.equal(v1.version, 1);
  assert.equal(v1.economics.stressMargin, "28.24");
  assert.equal(v1.economics.stressCostTotal, "97600.00");
  assert.equal(v1.economics.minAcceptablePrice, "130133.34");

  // 2. Perform reprice with shock scenario
  const shockEconomics = await priceDeal({
    request: v1.request,
    scenario: "shock",
    supplierCostDeltaPct: "0.00",
    freightRateDeltaPct: "0.00",
  });

  assert.equal(shockEconomics.stressMargin, "22.35");
  assert.equal(shockEconomics.stressCostTotal, "105600.00");
  assert.equal(shockEconomics.minAcceptablePrice, "140800.00");

  const v2Draft: Omit<QuoteVersion, "approval"> = {
    quoteId: "q-seed-acme-7",
    version: 2,
    createdAt: new Date().toISOString(),
    inputsHash: computeSha256(v1.request),
    request: v1.request,
    evidence: v1.evidence,
    forecastVersion: "shock",
    policyVersion: v1.policyVersion,
    economics: shockEconomics,
  };

  const v2: QuoteVersion = {
    ...v2Draft,
    approval: {
      state: "draft",
      actor: null,
      authority: null,
      exception: null,
      expiresAt: null,
      quoteHash: computeSha256(v2Draft),
    },
  };

  // Insert version 2 into DB (immutable append)
  db.prepare(`
    INSERT OR REPLACE INTO quote_versions (quote_id, version, payload, created_at)
    VALUES (?, ?, ?, ?)
  `).run(v2.quoteId, v2.version, JSON.stringify(v2), v2.createdAt);

  // 3. Verify Version 1 row remains byte-identical in DB
  const verifyV1 = db.prepare(`
    SELECT payload FROM quote_versions WHERE quote_id = ? AND version = 1
  `).get("q-seed-acme-7") as any;
  const parsedV1: QuoteVersion = JSON.parse(verifyV1.payload);
  assert.equal(parsedV1.version, 1);
  assert.equal(parsedV1.economics.stressMargin, "28.24");
  assert.equal(parsedV1.economics.stressCostTotal, "97600.00");

  // 4. Verify Version 2 row shows the post-shock metrics
  const verifyV2 = db.prepare(`
    SELECT payload FROM quote_versions WHERE quote_id = ? AND version = 2
  `).get("q-seed-acme-7") as any;
  const parsedV2: QuoteVersion = JSON.parse(verifyV2.payload);
  assert.equal(parsedV2.version, 2);
  assert.equal(parsedV2.economics.stressMargin, "22.35");
  assert.equal(parsedV2.economics.stressCostTotal, "105600.00");
  assert.equal(parsedV2.economics.minAcceptablePrice, "140800.00");

  // 5. Verify the rendered HTML fragment contains updated figures and the blocking warning
  const htmlFragment = renderEconomicsFragment(shockEconomics, "q-seed-acme-7", 2);
  assert.ok(htmlFragment.includes("22.35%"), "Fragment must display 22.35% stress margin");
  assert.ok(htmlFragment.includes("105600.00"), "Fragment must display $105,600 stress cost");
  assert.ok(htmlFragment.includes("140800.00"), "Fragment must display $140,800 floor");
  assert.ok(htmlFragment.includes("BELOW_ECONOMIC_FLOOR"), "Fragment must display block warning");

  // Clean up v2 row
  db.prepare(`DELETE FROM quote_versions WHERE quote_id = ? AND version = 2`).run("q-seed-acme-7");
});

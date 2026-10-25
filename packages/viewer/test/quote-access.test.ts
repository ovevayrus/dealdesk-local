import test from "node:test";
import assert from "node:assert/strict";
import { getDb } from "../src/lib/db.ts";
import { checkAccountScope } from "../src/lib/session.ts";
import type { Actor, QuoteVersion } from "@dealdesk/contracts";

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

test("quote-access: seller cannot access an account outside their scope", () => {
  const allowedForSofia = checkAccountScope(sofia, "NORTHWIND-2");
  assert.equal(allowedForSofia, false, "Seller u-sofia must not be authorized for NORTHWIND-2");

  const allowedForDana = checkAccountScope(dana, "NORTHWIND-2");
  assert.equal(allowedForDana, true, "Manager u-dana must be authorized for NORTHWIND-2");
});

test("quote-access: database-backed quote for NORTHWIND-2 is blocked for u-sofia", () => {
  const db = getDb();

  // Create a synthetic quote for NORTHWIND-2
  const northwindQuote: QuoteVersion = {
    quoteId: "q-northwind-test",
    version: 1,
    createdAt: new Date().toISOString(),
    inputsHash: "TEST",
    request: {
      requestId: "req-nw-01",
      dealId: "DEAL-NW-01",
      accountId: "NORTHWIND-2",
      actor: dana,
      sku: "DDX-RACK-100",
      quantity: 50,
      deliveryStart: "2026-12-01",
      deliveryEnd: "2026-12-15",
      destination: "Seattle Port",
      scopeLocations: 2,
      termMonths: 12,
      paymentTerms: "Net 30",
      proposedDiscountPct: "10.00",
      currency: "USD",
      quoteExpiry: "2027-01-01",
    },
    evidence: [],
    forecastVersion: "test",
    policyVersion: "v1",
    economics: {
      currency: "USD",
      listPrice: "80000.00",
      totalContractValue: "72000.00",
      upfront: "60000.00",
      recurring: "12000.00",
      discountPct: "10.00",
      costs: [],
      baseCostTotal: "50000.00",
      stressCostTotal: "55000.00",
      grossMargin: "30.00",
      stressMargin: "25.00",
      marginFloor: "25.00",
      minAcceptablePrice: "70000.00",
      recommendedPrice: "75000.00",
      feasibleRange: { low: "70000.00", high: "80000.00" },
      warnings: [],
      assumptions: [],
      dataVersion: "test",
    },
    approval: {
      state: "draft",
      actor: null,
      authority: null,
      exception: null,
      expiresAt: null,
      quoteHash: "TEST",
    },
  };

  const insertQuote = db.prepare(`
    INSERT OR REPLACE INTO quote_versions (quote_id, version, payload, created_at)
    VALUES (?, ?, ?, ?)
  `);
  insertQuote.run(
    northwindQuote.quoteId,
    northwindQuote.version,
    JSON.stringify(northwindQuote),
    northwindQuote.createdAt
  );

  const row = db.prepare("SELECT payload FROM quote_versions WHERE quote_id = ?").get("q-northwind-test") as any;
  assert.ok(row, "Quote exists in DB");
  const parsed: QuoteVersion = JSON.parse(row.payload);

  assert.equal(
    checkAccountScope(sofia, parsed.request.accountId),
    false,
    "u-sofia is denied access (403 condition)"
  );
  assert.equal(
    checkAccountScope(dana, parsed.request.accountId),
    true,
    "u-dana is granted access"
  );

  // Clean up
  db.prepare("DELETE FROM quote_versions WHERE quote_id = ?").run("q-northwind-test");
});

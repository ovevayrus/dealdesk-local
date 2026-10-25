import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { CUSTOMER_DRAFT_FIELDS, FORBIDDEN_IN_CUSTOMER } from "@dealdesk/contracts";
import type { QuoteVersion, Actor } from "@dealdesk/contracts";
import { buildRenderPack } from "../src/lib/render-pack.ts";

const __dirname = dirname(fileURLToPath(import.meta.url));
const seedFile = resolve(__dirname, "../fixtures/quote-version.seed.json");
const basePriceFile = resolve(__dirname, "../fixtures/price-deal.base.json");

const dana: Actor = {
  userId: "u-dana",
  role: "manager",
  accountIds: ["ACME-7", "NORTHWIND-2"],
};

test("customer-leak: deep key set of customer equals CUSTOMER_DRAFT_FIELDS exactly", () => {
  const quoteVersion: QuoteVersion = JSON.parse(readFileSync(seedFile, "utf-8"));
  const baseEconomics = JSON.parse(readFileSync(basePriceFile, "utf-8"));
  quoteVersion.economics = baseEconomics;

  const pack = buildRenderPack(quoteVersion, dana);
  const customerKeys = Object.keys(pack.customer).sort();
  const expectedKeys = [...CUSTOMER_DRAFT_FIELDS].sort();

  assert.deepEqual(
    customerKeys,
    expectedKeys,
    "Customer draft keys must match CUSTOMER_DRAFT_FIELDS exactly with no extras or missing fields"
  );
});

test("customer-leak: no value from FORBIDDEN_IN_CUSTOMER appears in customer draft serialization", () => {
  const quoteVersion: QuoteVersion = JSON.parse(readFileSync(seedFile, "utf-8"));
  const baseEconomics = JSON.parse(readFileSync(basePriceFile, "utf-8"));
  quoteVersion.economics = baseEconomics;

  const pack = buildRenderPack(quoteVersion, dana);
  const serializedCustomer = JSON.stringify(pack.customer);

  // Extract all forbidden string values of 4 characters or more
  const forbiddenValues: string[] = [];

  function collectStrings(obj: any) {
    if (typeof obj === "string") {
      // Ignore permitted currency "USD"
      if (obj.length >= 4 && obj !== "USD") {
        forbiddenValues.push(obj);
      }
    } else if (Array.isArray(obj)) {
      for (const item of obj) collectStrings(item);
    } else if (obj !== null && typeof obj === "object") {
      for (const val of Object.values(obj)) collectStrings(val);
    }
  }

  // Collect permitted customer values so that identical figures explicitly permitted
  // on CustomerDraft (like recurring: "24000.00" or currency: "USD") are excluded from false positives
  const permittedValues = new Set<string>();
  for (const v of Object.values(pack.customer)) {
    if (typeof v === "string") permittedValues.add(v);
  }

  for (const forbiddenKey of FORBIDDEN_IN_CUSTOMER) {
    const val = baseEconomics[forbiddenKey];
    if (val !== undefined && val !== null) {
      collectStrings(val);
    }
  }

  // Filter out permitted values from the scan
  const strictlyForbidden = forbiddenValues.filter((v) => !permittedValues.has(v));
  assert.ok(strictlyForbidden.length > 0, "Must have collected forbidden values to test against");

  for (const forbidden of strictlyForbidden) {
    // Assert that the string value doesn't appear as a JSON string or substring in customer draft
    const asJsonString = JSON.stringify(forbidden);
    assert.equal(
      serializedCustomer.includes(asJsonString) || (!/^\d+(\.\d+)?$/.test(forbidden) && serializedCustomer.includes(forbidden)),
      false,
      `Forbidden internal value '${forbidden}' leaked into customer draft!`
    );
  }
});

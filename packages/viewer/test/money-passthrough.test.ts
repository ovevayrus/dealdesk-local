import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import type { QuoteVersion, Actor, Economics } from "@dealdesk/contracts";
import { buildRenderPack } from "../src/lib/render-pack.ts";

const __dirname = dirname(fileURLToPath(import.meta.url));
const seedFile = resolve(__dirname, "../fixtures/quote-version.seed.json");
const basePriceFile = resolve(__dirname, "../fixtures/price-deal.base.json");

const dana: Actor = {
  userId: "u-dana",
  role: "manager",
  accountIds: ["ACME-7", "NORTHWIND-2"],
};

test("money-passthrough: all economics money fields are typeof string and byte-identical", () => {
  const quoteVersion: QuoteVersion = JSON.parse(readFileSync(seedFile, "utf-8"));
  const baseJson: Economics = JSON.parse(readFileSync(basePriceFile, "utf-8"));
  quoteVersion.economics = baseJson;

  const pack = buildRenderPack(quoteVersion, dana);
  const eco = pack.internal.economics;

  // Single top-level money fields
  const singleMoneyFields: (keyof Economics)[] = [
    "listPrice",
    "totalContractValue",
    "upfront",
    "recurring",
    "baseCostTotal",
    "stressCostTotal",
    "minAcceptablePrice",
    "recommendedPrice",
  ];

  for (const field of singleMoneyFields) {
    const renderedValue = eco[field];
    const expectedValue = baseJson[field];

    assert.equal(typeof renderedValue, "string", `${field} must be typeof string`);
    assert.strictEqual(
      renderedValue,
      expectedValue,
      `${field} value '${renderedValue}' must be byte-identical to fixture '${expectedValue}'`
    );
  }

  // Feasible range
  assert.equal(typeof eco.feasibleRange.low, "string");
  assert.strictEqual(eco.feasibleRange.low, baseJson.feasibleRange.low);
  assert.equal(typeof eco.feasibleRange.high, "string");
  assert.strictEqual(eco.feasibleRange.high, baseJson.feasibleRange.high);

  // Line item costs
  assert.equal(eco.costs.length, baseJson.costs.length);
  for (let i = 0; i < eco.costs.length; i++) {
    const renderedLine = eco.costs[i];
    const expectedLine = baseJson.costs[i];

    assert.equal(typeof renderedLine.expected, "string");
    assert.strictEqual(renderedLine.expected, expectedLine.expected);

    assert.equal(typeof renderedLine.stress, "string");
    assert.strictEqual(renderedLine.stress, expectedLine.stress);
  }
});

test("money-passthrough: customer draft money fields are typeof string and byte-identical", () => {
  const quoteVersion: QuoteVersion = JSON.parse(readFileSync(seedFile, "utf-8"));
  const baseJson: Economics = JSON.parse(readFileSync(basePriceFile, "utf-8"));
  quoteVersion.economics = baseJson;

  const pack = buildRenderPack(quoteVersion, dana);
  const customer = pack.customer;

  assert.equal(typeof customer.totalContractValue, "string");
  assert.strictEqual(customer.totalContractValue, baseJson.totalContractValue);

  assert.equal(typeof customer.upfront, "string");
  assert.strictEqual(customer.upfront, baseJson.upfront);

  assert.equal(typeof customer.recurring, "string");
  assert.strictEqual(customer.recurring, baseJson.recurring);
});

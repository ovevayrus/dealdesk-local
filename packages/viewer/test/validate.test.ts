import test from "node:test";
import assert from "node:assert/strict";
import { validateDealRequest } from "../src/lib/validate.ts";
import type { Actor } from "@dealdesk/contracts";

const dana: Actor = { userId: "u-dana", role: "manager", accountIds: ["ACME-7", "NORTHWIND-2"] };

const base = {
  dealId: "DEAL-TEST",
  accountId: "ACME-7",
  sku: "DDX-RACK-100",
  quantity: 100,
  deliveryStart: "2026-11-01",
  deliveryEnd: "2026-12-01",
  destination: "Portland, OR",
  scopeLocations: 6,
  termMonths: 12,
  paymentTerms: "Net 30",
  proposedDiscountPct: "15.00",
  currency: "USD",
  quoteExpiry: "2026-11-30",
};

test("validate: reversed delivery range is rejected", () => {
  const r = validateDealRequest({ ...base, deliveryStart: "2026-12-01", deliveryEnd: "2026-11-01" }, dana);
  assert.equal(r.ok, false);
  assert.ok(r.error.fields.some((f) => f.code === "INVALID_DATE_RANGE"));
});

test("validate: malformed discount is rejected", () => {
  for (const bad of ["abc", "15,00", "-5", "120"]) {
    const r = validateDealRequest({ ...base, proposedDiscountPct: bad }, dana);
    assert.equal(r.ok, false, `expected ${bad} to be rejected`);
    assert.ok(r.error.fields.some((f) => f.code === "INVALID_DISCOUNT"));
  }
});

test("validate: the reference deal still passes", () => {
  assert.equal(validateDealRequest(base, dana).ok, true);
});

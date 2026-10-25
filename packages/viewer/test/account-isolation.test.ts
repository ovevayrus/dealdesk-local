import test from "node:test";
import assert from "node:assert/strict";
import { searchEvidence, ForbiddenAccountError } from "../src/lib/retrieval.ts";
import type { Actor } from "@dealdesk/contracts";

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

test("account-isolation: u-sofia accessing NORTHWIND-2 throws FORBIDDEN_ACCOUNT", () => {
  assert.throws(
    () => {
      searchEvidence({ accountId: "NORTHWIND-2", query: "infrastructure" }, sofia);
    },
    (err: any) => {
      return (
        err instanceof ForbiddenAccountError ||
        (err && (err.code === "FORBIDDEN_ACCOUNT" || String(err.message).includes("FORBIDDEN_ACCOUNT")))
      );
    }
  );
});

test("account-isolation: query for terms in another account returns zero hits and no foreign docId", () => {
  // "maritime" and "vessel" appear only in northwind-profile.md
  const res = searchEvidence(
    { accountId: "ACME-7", query: "maritime vessel telemetry" },
    sofia
  );

  assert.equal(res.hits.length, 0);
  const foundNorthwind = res.hits.some((h) => h.docId === "northwind-profile");
  assert.equal(foundNorthwind, false);
});

test("account-isolation: restricted documents are absent for seller and present for manager", () => {
  // acme-renewal-history is classified as restricted
  const sofiaRes = searchEvidence(
    { accountId: "ACME-7", query: "historical discounts churn risk" },
    sofia
  );
  const sofiaHasRestricted = sofiaRes.hits.some(
    (h) => h.docId === "acme-renewal-history" || h.classification === "restricted"
  );
  assert.equal(sofiaHasRestricted, false, "Seller u-sofia must never receive restricted hits");

  const danaRes = searchEvidence(
    { accountId: "ACME-7", query: "historical discounts churn risk" },
    dana
  );
  const danaHasRestricted = danaRes.hits.some(
    (h) => h.docId === "acme-renewal-history"
  );
  assert.equal(danaHasRestricted, true, "Manager u-dana should receive acme-renewal-history");
});

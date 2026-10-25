import { test } from "node:test";
import assert from "node:assert/strict";
import { validateDealRequest } from "../src/lib/validate.ts";
import { getDb } from "../src/lib/db.ts";
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

test("request-validation: submitting with no delivery dates blocks release and names the fields", () => {
  const result = validateDealRequest(
    {
      accountId: "ACME-7",
      sku: "DDX-RACK-100",
      // deliveryStart and deliveryEnd missing
    },
    sofia
  );

  assert.equal(result.ok, false);
  if (!result.ok) {
    assert.equal(result.status, 422);
    assert.equal(result.error.code, "VALIDATION_FAILED");
    assert.ok(result.error.fields, "Expected validation fields");
    
    const fieldNames = result.error.fields?.map((f) => f.field);
    assert.ok(fieldNames?.includes("deliveryStart"), "Must name deliveryStart");
    assert.ok(fieldNames?.includes("deliveryEnd"), "Must name deliveryEnd");

    const startField = result.error.fields?.find((f) => f.field === "deliveryStart");
    assert.equal(startField?.code, "MISSING_CRITICAL_INPUT");
  }
});

test("request-validation: unsupported sku blocks release with UNSUPPORTED_SKU", () => {
  const result = validateDealRequest(
    {
      accountId: "ACME-7",
      sku: "INVALID-SKU-999",
      deliveryStart: "2026-11-01",
      deliveryEnd: "2026-11-30",
    },
    sofia
  );

  assert.equal(result.ok, false);
  if (!result.ok) {
    assert.equal(result.status, 422);
    const skuField = result.error.fields?.find((f) => f.field === "sku");
    assert.equal(skuField?.code, "UNSUPPORTED_SKU");
  }
});

test("request-validation: non-USD currency blocks release with UNKNOWN_CURRENCY", () => {
  const result = validateDealRequest(
    {
      accountId: "ACME-7",
      sku: "DDX-RACK-100",
      currency: "EUR",
      deliveryStart: "2026-11-01",
      deliveryEnd: "2026-11-30",
    },
    sofia
  );

  assert.equal(result.ok, false);
  if (!result.ok) {
    assert.equal(result.status, 422);
    const currField = result.error.fields?.find((f) => f.field === "currency");
    assert.equal(currField?.code, "UNKNOWN_CURRENCY");
  }
});

test("request-validation: submitting for foreign account throws FORBIDDEN_ACCOUNT", () => {
  const result = validateDealRequest(
    {
      accountId: "NORTHWIND-2",
      sku: "DDX-RACK-100",
      deliveryStart: "2026-11-01",
      deliveryEnd: "2026-11-30",
    },
    sofia // sofia only has ACME-7
  );

  assert.equal(result.ok, false);
  if (!result.ok) {
    assert.equal(result.status, 403);
    assert.equal(result.error.code, "FORBIDDEN_ACCOUNT");
  }
});

test("request-validation: valid submission applies SKU defaults and injects server actor", () => {
  const result = validateDealRequest(
    {
      accountId: "ACME-7",
      sku: "DDX-RACK-100",
      deliveryStart: "2026-11-01",
      deliveryEnd: "2026-11-30",
      // omitted optional fields: quantity, scopeLocations, termMonths, etc.
    },
    dana
  );

  assert.equal(result.ok, true);
  if (result.ok) {
    assert.equal(result.dealRequest.accountId, "ACME-7");
    assert.equal(result.dealRequest.sku, "DDX-RACK-100");
    assert.equal(result.dealRequest.currency, "USD");
    assert.equal(result.dealRequest.quantity, 100); // default from SKU
    assert.equal(result.dealRequest.scopeLocations, 6); // default from SKU
    assert.equal(result.dealRequest.termMonths, 12); // default from SKU
    assert.equal(result.dealRequest.proposedDiscountPct, "15.00");
    assert.equal(result.dealRequest.actor.userId, "u-dana");
    assert.ok(result.dealRequest.requestId.startsWith("req-"));
  }
});

import { POST } from "../src/pages/api/request.ts";

test("request-validation: POST /api/request end-to-end creates version 1 quote in DB", async () => {
  const req = new Request("http://127.0.0.1:4321/api/request", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Cookie": "dd_actor=u-dana",
    },
    body: JSON.stringify({
      accountId: "ACME-7",
      sku: "DDX-RACK-100",
      dealId: "DEAL-INT-001",
      deliveryStart: "2026-11-01",
      deliveryEnd: "2026-11-30",
    }),
  });

  const res = await POST({
    request: req,
    params: {},
    cookies: {} as any,
    url: new URL("http://127.0.0.1:4321/api/request"),
    clientAddress: "127.0.0.1",
    generator: "test",
    props: {},
    redirect: () => new Response(null, { status: 303 }),
    locals: {},
    site: undefined,
  } as any);

  assert.equal(res.status, 201);
  const data = await res.json();
  assert.ok(data.quoteId.startsWith("q-"));
  assert.equal(data.version, 1);
  assert.equal(data.redirectUrl, `/quote/${data.quoteId}?v=1`);

  // Verify in SQLite database
  const db = getDb();
  const row = db.prepare("SELECT * FROM quote_versions WHERE quote_id = ? AND version = 1").get(data.quoteId) as any;
  assert.ok(row, "Quote version must be saved in database");
  const payload: QuoteVersion = JSON.parse(row.payload);
  assert.equal(payload.quoteId, data.quoteId);
  assert.equal(payload.version, 1);
  assert.equal(payload.request.dealId, "DEAL-INT-001");
  assert.equal(payload.request.quantity, 100); // default applied
  assert.equal(payload.economics.totalContractValue, "136000.00");
  assert.equal(payload.economics.stressMargin, "28.24");
});

test("request-validation: POST /api/request blocks submission with no delivery date", async () => {
  const req = new Request("http://127.0.0.1:4321/api/request", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Cookie": "dd_actor=u-dana",
    },
    body: JSON.stringify({
      accountId: "ACME-7",
      sku: "DDX-RACK-100",
      dealId: "DEAL-MISSING-DATES",
      // missing delivery dates
    }),
  });

  const res = await POST({
    request: req,
    params: {},
    cookies: {} as any,
    url: new URL("http://127.0.0.1:4321/api/request"),
    clientAddress: "127.0.0.1",
    generator: "test",
    props: {},
    redirect: () => new Response(null, { status: 303 }),
    locals: {},
    site: undefined,
  } as any);

  assert.equal(res.status, 422);
  const data = await res.json();
  assert.equal(data.error.code, "VALIDATION_FAILED");
  const fields = data.error.fields.map((f: any) => f.field);
  assert.ok(fields.includes("deliveryStart"));
  assert.ok(fields.includes("deliveryEnd"));
});

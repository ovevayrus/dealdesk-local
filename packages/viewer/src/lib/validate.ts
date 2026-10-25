import { readFileSync, existsSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { randomUUID } from "node:crypto";
import {
  DealRequestSchema,
  type DealRequest,
  type Actor,
  type ApiErrorDetail,
  type ApiErrorField,
} from "@dealdesk/contracts";
import { checkAccountScope } from "./session.ts";

function findWorkspaceRoot(): string {
  let cur = dirname(fileURLToPath(import.meta.url));
  for (let i = 0; i < 6; i++) {
    if (existsSync(resolve(cur, "pnpm-workspace.yaml"))) {
      return cur;
    }
    const parent = dirname(cur);
    if (parent === cur) break;
    cur = parent;
  }
  return process.cwd();
}

export type SkuDefinition = {
  sku: string;
  name: string;
  description: string;
  listPrice: string;
  currency: string;
  defaultQuantity: number;
  defaultScopeLocations: number;
  defaultTermMonths: number;
  defaultPaymentTerms: string;
  defaultDestination: string;
  defaultProposedDiscountPct: string;
};

let cachedSkus: SkuDefinition[] | null = null;

export function getSkus(): SkuDefinition[] {
  if (cachedSkus) return cachedSkus;
  const root = findWorkspaceRoot();
  const filePath = resolve(root, "packages/viewer/fixtures/skus.json");
  const raw = readFileSync(filePath, "utf-8");
  cachedSkus = JSON.parse(raw) as SkuDefinition[];
  return cachedSkus;
}

export type ValidationSuccess = {
  ok: true;
  dealRequest: DealRequest;
};

export type ValidationFailure = {
  ok: false;
  status: number;
  error: ApiErrorDetail;
};

export type ValidationResult = ValidationSuccess | ValidationFailure;

export function validateDealRequest(input: Record<string, any>, actor: Actor): ValidationResult {
  const accountId = input.accountId ? String(input.accountId).trim() : "";
  if (!accountId) {
    return {
      ok: false,
      status: 422,
      error: {
        code: "VALIDATION_FAILED",
        message: "Quote release blocked. Fix the listed fields.",
        fields: [
          {
            field: "accountId",
            code: "MISSING_CRITICAL_INPUT",
            message: "Account ID is required.",
          },
        ],
      },
    };
  }

  // Account Scope Check (Section 7: 403 before touching database)
  if (!checkAccountScope(actor, accountId)) {
    return {
      ok: false,
      status: 403,
      error: {
        code: "FORBIDDEN_ACCOUNT",
        message: `Actor ${actor.userId} is not authorized for account ${accountId}.`,
      },
    };
  }

  const skus = getSkus();
  const fields: ApiErrorField[] = [];

  // SKU validation: must exist in fixtures/skus.json
  const rawSku = input.sku ? String(input.sku).trim() : "";
  const skuDef = skus.find((s) => s.sku === rawSku);
  if (!skuDef) {
    fields.push({
      field: "sku",
      code: "UNSUPPORTED_SKU",
      message: `SKU "${rawSku}" is not supported. Supported SKUs: ${skus.map((s) => s.sku).join(", ")}`,
    });
  }

  // Currency validation: must be "USD"
  const rawCurrency = input.currency ? String(input.currency).trim() : "USD";
  if (rawCurrency !== "USD") {
    fields.push({
      field: "currency",
      code: "UNKNOWN_CURRENCY",
      message: `Currency must be USD, received "${rawCurrency}".`,
    });
  }

  // Delivery start validation: required & parseable ISO date
  const deliveryStart = input.deliveryStart ? String(input.deliveryStart).trim() : "";
  if (!deliveryStart) {
    fields.push({
      field: "deliveryStart",
      code: "MISSING_CRITICAL_INPUT",
      message: "Delivery start date is required.",
    });
  } else if (isNaN(Date.parse(deliveryStart))) {
    fields.push({
      field: "deliveryStart",
      code: "MISSING_CRITICAL_INPUT",
      message: "Delivery start date is invalid.",
    });
  }

  // Delivery end validation: required & parseable ISO date
  const deliveryEnd = input.deliveryEnd ? String(input.deliveryEnd).trim() : "";
  if (!deliveryEnd) {
    fields.push({
      field: "deliveryEnd",
      code: "MISSING_CRITICAL_INPUT",
      message: "Delivery end date is required.",
    });
  } else if (isNaN(Date.parse(deliveryEnd))) {
    fields.push({
      field: "deliveryEnd",
      code: "MISSING_CRITICAL_INPUT",
      message: "Delivery end date is invalid.",
    });
  }

  // Reversed ranges and malformed discounts previously passed validation.
  if (deliveryStart && deliveryEnd && !isNaN(Date.parse(deliveryStart)) && !isNaN(Date.parse(deliveryEnd))) {
    if (Date.parse(deliveryEnd) < Date.parse(deliveryStart)) {
      fields.push({
        field: "deliveryEnd",
        code: "INVALID_DATE_RANGE",
        message: "Delivery end date cannot precede the delivery start date.",
      });
    }
  }

  const rawDiscount = input.proposedDiscountPct;
  if (rawDiscount !== undefined && rawDiscount !== null && String(rawDiscount).trim() !== "") {
    const discount = String(rawDiscount).trim();
    if (!/^\d{1,3}(\.\d{1,2})?$/.test(discount) || Number(discount) > 100) {
      fields.push({
        field: "proposedDiscountPct",
        code: "INVALID_DISCOUNT",
        message: "Proposed discount must be a percentage between 0 and 100, e.g. 15.00.",
      });
    }
  }

  // If any blocking errors occurred, fail immediately
  if (fields.length > 0) {
    return {
      ok: false,
      status: 422,
      error: {
        code: "VALIDATION_FAILED",
        message: "Quote release blocked. Fix the listed fields.",
        fields,
      },
    };
  }

  // Apply SKU defaults for non-critical inputs
  const quantityNum = Number(input.quantity);
  const quantity = Number.isInteger(quantityNum) && quantityNum > 0 ? quantityNum : skuDef!.defaultQuantity;

  const locationsNum = Number(input.scopeLocations);
  const scopeLocations = Number.isInteger(locationsNum) && locationsNum > 0 ? locationsNum : skuDef!.defaultScopeLocations;

  const monthsNum = Number(input.termMonths);
  const termMonths = Number.isInteger(monthsNum) && monthsNum > 0 ? monthsNum : skuDef!.defaultTermMonths;

  const paymentTerms = input.paymentTerms && String(input.paymentTerms).trim() ? String(input.paymentTerms).trim() : skuDef!.defaultPaymentTerms;
  const destination = input.destination && String(input.destination).trim() ? String(input.destination).trim() : skuDef!.defaultDestination;
  const proposedDiscountPct = input.proposedDiscountPct && String(input.proposedDiscountPct).trim()
    ? String(input.proposedDiscountPct).trim()
    : skuDef!.defaultProposedDiscountPct;

  const dealId = input.dealId && String(input.dealId).trim() ? String(input.dealId).trim() : `deal-${randomUUID().slice(0, 8)}`;
  const quoteExpiry = input.quoteExpiry && String(input.quoteExpiry).trim() ? String(input.quoteExpiry).trim() : "2026-11-30";

  // Server generates requestId, server injects actor
  const requestId = `req-${randomUUID()}`;

  const dealRequest: DealRequest = {
    requestId,
    dealId,
    accountId,
    actor,
    sku: rawSku,
    quantity,
    deliveryStart,
    deliveryEnd,
    destination,
    scopeLocations,
    termMonths,
    paymentTerms,
    proposedDiscountPct,
    currency: "USD",
    quoteExpiry,
  };

  const parsed = DealRequestSchema.safeParse(dealRequest);
  if (!parsed.success) {
    return {
      ok: false,
      status: 422,
      error: {
        code: "VALIDATION_FAILED",
        message: "DealRequest schema validation failed.",
        fields: parsed.error.issues.map((issue) => ({
          field: issue.path.join("."),
          code: "VALIDATION_FAILED",
          message: issue.message,
        })),
      },
    };
  }

  return {
    ok: true,
    dealRequest: parsed.data,
  };
}

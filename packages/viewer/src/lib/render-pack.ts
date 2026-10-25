import type {
  Actor,
  QuoteVersion,
  CustomerDraft,
  InternalDealPack,
  RenderPack,
} from "@dealdesk/contracts";
import { CUSTOMER_DRAFT_FIELDS } from "@dealdesk/contracts";
import { hydrateEvidence } from "./retrieval.ts";

export interface ExplanationResult {
  explanation: string;
  source: "model" | "template";
}

export function buildExplanation(
  draft: Omit<CustomerDraft, "explanation">
): ExplanationResult {
  // Spec Section 13: MODEL_MODE defaults to off; fallback template
  // If live model is ever enabled, validate digit sequences.
  const template = `This offer includes deployment at ${draft.scopeLocations} locations and ${draft.termMonths} months of managed support. The quoted price is valid through ${draft.quoteExpiry}; a phased deployment option can reduce the initial commitment.`;
  return {
    explanation: template,
    source: "template",
  };
}

export function buildCustomerDraft(quoteVersion: QuoteVersion): CustomerDraft {
  const req = quoteVersion.request;
  const eco = quoteVersion.economics;

  const baseFields = {
    currency: eco.currency,
    totalContractValue: eco.totalContractValue,
    upfront: eco.upfront,
    recurring: eco.recurring,
    quoteExpiry: req.quoteExpiry,
    scopeLocations: req.scopeLocations,
    termMonths: req.termMonths,
    destination: req.destination,
  };

  const { explanation } = buildExplanation(baseFields);

  // Exact whitelist projection by explicitly setting only CUSTOMER_DRAFT_FIELDS
  const customer: CustomerDraft = {
    currency: baseFields.currency,
    totalContractValue: baseFields.totalContractValue,
    upfront: baseFields.upfront,
    recurring: baseFields.recurring,
    quoteExpiry: baseFields.quoteExpiry,
    scopeLocations: baseFields.scopeLocations,
    termMonths: baseFields.termMonths,
    destination: baseFields.destination,
    explanation,
  };

  return customer;
}

export function buildRenderPack(quoteVersion: QuoteVersion, actor: Actor): RenderPack {
  const customer = buildCustomerDraft(quoteVersion);
  const hydratedEvidence = hydrateEvidence(quoteVersion.evidence, actor, quoteVersion.request.accountId);

  const internal: InternalDealPack = {
    quoteId: quoteVersion.quoteId,
    version: quoteVersion.version,
    request: quoteVersion.request,
    economics: quoteVersion.economics,
    evidence: hydratedEvidence,
    approval: quoteVersion.approval,
    policyVersion: quoteVersion.policyVersion,
    forecastVersion: quoteVersion.forecastVersion,
  };

  return {
    quoteId: quoteVersion.quoteId,
    version: quoteVersion.version,
    internal,
    customer,
  };
}

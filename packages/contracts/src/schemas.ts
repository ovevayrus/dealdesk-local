import { z } from "zod";

export const ActorRoleSchema = z.enum(["seller", "manager", "admin"]);

export const ActorSchema = z.object({
  userId: z.string(),
  role: ActorRoleSchema,
  accountIds: z.array(z.string()),
});

export const DealRequestSchema = z.object({
  requestId: z.string(),
  dealId: z.string(),
  accountId: z.string(),
  actor: ActorSchema,
  sku: z.string(),
  quantity: z.number().int().min(1),
  deliveryStart: z.string(),
  deliveryEnd: z.string(),
  destination: z.string(),
  scopeLocations: z.number().int().min(1),
  termMonths: z.number().int().min(1),
  paymentTerms: z.string(),
  proposedDiscountPct: z.string(),
  currency: z.literal("USD"),
  quoteExpiry: z.string(),
});

export const EvidenceQuerySchema = z.object({
  accountId: z.string(),
  query: z.string(),
  topK: z.number().int().min(1).max(25).optional(),
});

export const ClassificationSchema = z.enum(["public", "internal", "restricted"]);

export const EvidenceHitSchema = z.object({
  docId: z.string(),
  docHash: z.string(),
  docTitle: z.string(),
  section: z.string(),
  page: z.number().nullable(),
  passage: z.string(),
  effectiveDate: z.string(),
  classification: ClassificationSchema,
  rank: z.number().int().min(1),
  reason: z.string(),
});

export const EvidenceResultSchema = z.object({
  runId: z.string(),
  hits: z.array(EvidenceHitSchema),
});

export const CostLineSchema = z.object({
  label: z.string(),
  expected: z.string(),
  stress: z.string(),
  unit: z.string(),
});

export const WarningSeveritySchema = z.enum(["info", "warn", "block"]);

export const WarningSchema = z.object({
  code: z.string(),
  message: z.string(),
  severity: WarningSeveritySchema,
});

export const EconomicsSchema = z.object({
  currency: z.literal("USD"),
  listPrice: z.string(),
  totalContractValue: z.string(),
  upfront: z.string(),
  recurring: z.string(),
  discountPct: z.string(),
  costs: z.array(CostLineSchema),
  baseCostTotal: z.string(),
  stressCostTotal: z.string(),
  grossMargin: z.string(),
  stressMargin: z.string(),
  marginFloor: z.string(),
  minAcceptablePrice: z.string(),
  recommendedPrice: z.string(),
  feasibleRange: z.object({
    low: z.string(),
    high: z.string(),
  }),
  warnings: z.array(WarningSchema),
  assumptions: z.array(z.string()),
  dataVersion: z.string(),
});

export const ApprovalStateSchema = z.enum(["draft", "pending", "approved", "rejected"]);

export const ApprovalSchema = z.object({
  state: ApprovalStateSchema,
  actor: z.string().nullable(),
  authority: z.string().nullable(),
  exception: z.string().nullable(),
  expiresAt: z.string().nullable(),
  quoteHash: z.string(),
});

export const EvidenceRefSchema = z.object({
  docId: z.string(),
  docHash: z.string(),
  section: z.string(),
});

export const QuoteVersionSchema = z.object({
  quoteId: z.string(),
  version: z.number().int().min(1),
  createdAt: z.string(),
  inputsHash: z.string(),
  request: DealRequestSchema,
  evidence: z.array(EvidenceRefSchema),
  forecastVersion: z.string(),
  policyVersion: z.string(),
  economics: EconomicsSchema,
  approval: ApprovalSchema,
});

export const InternalDealPackSchema = z.object({
  quoteId: z.string(),
  version: z.number().int().min(1),
  request: DealRequestSchema,
  economics: EconomicsSchema,
  evidence: z.array(EvidenceHitSchema),
  approval: ApprovalSchema,
  policyVersion: z.string(),
  forecastVersion: z.string(),
});

export const CustomerDraftSchema = z.object({
  currency: z.literal("USD"),
  totalContractValue: z.string(),
  upfront: z.string(),
  recurring: z.string(),
  quoteExpiry: z.string(),
  scopeLocations: z.number().int().min(1),
  termMonths: z.number().int().min(1),
  destination: z.string(),
  explanation: z.string(),
});

export const RenderPackSchema = z.object({
  quoteId: z.string(),
  version: z.number().int().min(1),
  internal: InternalDealPackSchema,
  customer: CustomerDraftSchema,
});

export const PriceDealRequestSchema = z.object({
  request: DealRequestSchema,
  scenario: z.enum(["base", "shock"]),
  supplierCostDeltaPct: z.string(),
  freightRateDeltaPct: z.string(),
});

export const ApiErrorFieldSchema = z.object({
  field: z.string(),
  code: z.string(),
  message: z.string(),
});

export const ApiErrorDetailSchema = z.object({
  code: z.string(),
  message: z.string(),
  fields: z.array(ApiErrorFieldSchema).optional(),
});

export const ApiErrorResponseSchema = z.object({
  runId: z.string(),
  error: ApiErrorDetailSchema,
});

export type ActorRole = z.infer<typeof ActorRoleSchema>;
export type Actor = z.infer<typeof ActorSchema>;
export type DealRequest = z.infer<typeof DealRequestSchema>;
export type EvidenceQuery = z.infer<typeof EvidenceQuerySchema>;
export type Classification = z.infer<typeof ClassificationSchema>;
export type EvidenceHit = z.infer<typeof EvidenceHitSchema>;
export type EvidenceResult = z.infer<typeof EvidenceResultSchema>;
export type CostLine = z.infer<typeof CostLineSchema>;
export type WarningSeverity = z.infer<typeof WarningSeveritySchema>;
export type Warning = z.infer<typeof WarningSchema>;
export type Economics = z.infer<typeof EconomicsSchema>;
export type ApprovalState = z.infer<typeof ApprovalStateSchema>;
export type Approval = z.infer<typeof ApprovalSchema>;
export type EvidenceRef = z.infer<typeof EvidenceRefSchema>;
export type QuoteVersion = z.infer<typeof QuoteVersionSchema>;
export type InternalDealPack = z.infer<typeof InternalDealPackSchema>;
export type CustomerDraft = z.infer<typeof CustomerDraftSchema>;
export type RenderPack = z.infer<typeof RenderPackSchema>;
export type PriceDealRequest = z.infer<typeof PriceDealRequestSchema>;
export type ApiErrorField = z.infer<typeof ApiErrorFieldSchema>;
export type ApiErrorDetail = z.infer<typeof ApiErrorDetailSchema>;
export type ApiErrorResponse = z.infer<typeof ApiErrorResponseSchema>;

export const CUSTOMER_DRAFT_FIELDS = [
  "currency",
  "totalContractValue",
  "upfront",
  "recurring",
  "quoteExpiry",
  "scopeLocations",
  "termMonths",
  "destination",
  "explanation",
] as const;

export type CustomerDraftField = (typeof CUSTOMER_DRAFT_FIELDS)[number];

export const FORBIDDEN_IN_CUSTOMER = [
  "costs",
  "baseCostTotal",
  "stressCostTotal",
  "grossMargin",
  "stressMargin",
  "marginFloor",
  "minAcceptablePrice",
  "feasibleRange",
  "discountPct",
  "listPrice",
  "warnings",
  "assumptions",
  "dataVersion",
] as const;

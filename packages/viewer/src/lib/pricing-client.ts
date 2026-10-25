import { readFileSync, existsSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { EconomicsSchema, type Economics, type PriceDealRequest } from "@dealdesk/contracts";

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

export class PricingClientError extends Error {
  code: string;
  constructor(code: string, message: string) {
    super(message);
    this.code = code;
    this.name = "PricingClientError";
  }
}

export async function priceDeal(params: PriceDealRequest): Promise<Economics> {
  const mode = process.env.PRICING_MODE;
  const baseUrl = process.env.PRICING_BASE_URL || "http://127.0.0.1:8001";
  const root = findWorkspaceRoot();

  // Explicit fixture mode check
  if (mode === "fixture" || mode === "fixture-shock" || !process.env.PRICING_BASE_URL) {
    const isShock = mode === "fixture-shock" || params.scenario === "shock";
    const filename = isShock ? "price-deal.shock.json" : "price-deal.base.json";
    const filePath = resolve(root, "packages/viewer/fixtures", filename);
    const raw = readFileSync(filePath, "utf-8");
    const json = JSON.parse(raw);
    const parsed = EconomicsSchema.safeParse(json);
    if (!parsed.success) {
      throw new PricingClientError(
        "PRICING_INVALID_RESPONSE",
        `Fixture data failed Economics validation: ${parsed.error.message}`
      );
    }
    return parsed.data;
  }

  // Attempt live HTTP call with 5s timeout and 1 retry
  let lastErr: any = null;
  for (let attempt = 0; attempt < 2; attempt++) {
    try {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), 5000);

      const resp = await fetch(`${baseUrl}/price_deal`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(params),
        signal: controller.signal,
      });
      clearTimeout(timer);

      if (!resp.ok) {
        throw new PricingClientError(
          "PRICING_UNAVAILABLE",
          `Pricing service returned HTTP ${resp.status}`
        );
      }

      const json = await resp.json();
      const parsed = EconomicsSchema.safeParse(json);
      if (!parsed.success) {
        throw new PricingClientError(
          "PRICING_INVALID_RESPONSE",
          `Pricing service returned invalid shape: ${parsed.error.message}`
        );
      }

      return parsed.data;
    } catch (err: any) {
      lastErr = err;
      if (err instanceof PricingClientError && err.code === "PRICING_INVALID_RESPONSE") {
        throw err;
      }
    }
  }

  // Fallback to fixture if unreachable at startup
  const isShock = params.scenario === "shock";
  const fallbackFile = resolve(root, "packages/viewer/fixtures", isShock ? "price-deal.shock.json" : "price-deal.base.json");
  if (existsSync(fallbackFile)) {
    const raw = readFileSync(fallbackFile, "utf-8");
    return EconomicsSchema.parse(JSON.parse(raw));
  }

  throw new PricingClientError(
    "PRICING_UNAVAILABLE",
    `Pricing service unreachable: ${lastErr?.message || "connection failed"}`
  );
}

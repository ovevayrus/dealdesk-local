import { writeFileSync, mkdirSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { z } from "zod";
import {
  DealRequestSchema,
  QuoteVersionSchema,
  EconomicsSchema,
  EvidenceResultSchema,
  RenderPackSchema,
  CustomerDraftSchema,
  PriceDealRequestSchema,
  ApiErrorResponseSchema,
} from "../src/schemas.ts";

const __dirname = dirname(fileURLToPath(import.meta.url));
const schemaDir = resolve(__dirname, "../schema");
mkdirSync(schemaDir, { recursive: true });

const schemasToExport: Record<string, z.ZodTypeAny> = {
  "DealRequest.json": DealRequestSchema,
  "QuoteVersion.json": QuoteVersionSchema,
  "Economics.json": EconomicsSchema,
  "EvidenceResult.json": EvidenceResultSchema,
  "RenderPack.json": RenderPackSchema,
  "CustomerDraft.json": CustomerDraftSchema,
  "PriceDealRequest.json": PriceDealRequestSchema,
  "ApiErrorResponse.json": ApiErrorResponseSchema,
};

for (const [filename, schema] of Object.entries(schemasToExport)) {
  const jsonSchema = (z as any).toJSONSchema(schema);
  writeFileSync(resolve(schemaDir, filename), JSON.stringify(jsonSchema, null, 2) + "\n", "utf-8");
  console.log(`Generated schema: ${filename}`);
}

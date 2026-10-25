import type { APIRoute } from "astro";
import { randomUUID } from "node:crypto";
import { EvidenceQuerySchema } from "@dealdesk/contracts";
import { getActor } from "../../lib/session.ts";
import { searchEvidence, ForbiddenAccountError } from "../../lib/retrieval.ts";

export const GET: APIRoute = async ({ request }) => {
  const runId = `r-${randomUUID()}`;
  const url = new URL(request.url);

  const accountId = url.searchParams.get("accountId") ?? "";
  const query = url.searchParams.get("query") ?? "";
  const topKParam = url.searchParams.get("topK");
  const topK = topKParam ? parseInt(topKParam, 10) : undefined;

  const parseResult = EvidenceQuerySchema.safeParse({ accountId, query, topK });
  if (!parseResult.success) {
    return new Response(
      JSON.stringify({
        runId,
        error: {
          code: "VALIDATION_FAILED",
          message: "Invalid evidence query parameters.",
          fields: parseResult.error.issues.map((iss) => ({
            field: iss.path.join("."),
            code: iss.code,
            message: iss.message,
          })),
        },
      }),
      { status: 422, headers: { "Content-Type": "application/json" } }
    );
  }

  const actor = getActor(request);

  try {
    const result = searchEvidence(parseResult.data, actor);
    return new Response(JSON.stringify(result), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  } catch (err) {
    if (err instanceof ForbiddenAccountError || (err as any)?.code === "FORBIDDEN_ACCOUNT") {
      return new Response(
        JSON.stringify({
          runId,
          error: {
            code: "FORBIDDEN_ACCOUNT",
            message: (err as Error).message,
          },
        }),
        { status: 403, headers: { "Content-Type": "application/json" } }
      );
    }

    return new Response(
      JSON.stringify({
        runId,
        error: {
          code: "INTERNAL_ERROR",
          message: (err as Error).message,
        },
      }),
      { status: 500, headers: { "Content-Type": "application/json" } }
    );
  }
};

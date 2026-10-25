import type { APIRoute } from "astro";
import { randomUUID } from "node:crypto";
import type { QuoteVersion } from "@dealdesk/contracts";
import { getDb } from "../../lib/db.ts";
import { getActor } from "../../lib/session.ts";
import { validateDealRequest } from "../../lib/validate.ts";
import { searchEvidence } from "../../lib/retrieval.ts";
import { priceDeal, PricingClientError } from "../../lib/pricing-client.ts";
import { computeSha256 } from "../../lib/hash.ts";

export const POST: APIRoute = async ({ request }) => {
  const runId = `r-${randomUUID()}`;

  try {
    const actor = getActor(request);

    let body: Record<string, any> = {};
    const contentType = request.headers.get("content-type") || "";

    if (contentType.includes("application/json")) {
      body = await request.json();
    } else if (
      contentType.includes("application/x-www-form-urlencoded") ||
      contentType.includes("multipart/form-data")
    ) {
      const formData = await request.formData();
      for (const [key, val] of formData.entries()) {
        body[key] = val;
      }
    } else {
      try {
        body = await request.json();
      } catch {
        body = {};
      }
    }

    // Validate inputs & account scope
    const validation = validateDealRequest(body, actor);
    if (!validation.ok) {
      return new Response(
        JSON.stringify({
          runId,
          error: validation.error,
        }),
        {
          status: validation.status,
          headers: { "Content-Type": "application/json" },
        }
      );
    }

    const dealRequest = validation.dealRequest;

    // Retrieve evidence references for this deal
    let evidenceRefs: QuoteVersion["evidence"] = [];
    try {
      const hits = searchEvidence(actor, {
        accountId: dealRequest.accountId,
        query: `${dealRequest.sku} freight rates installation logistics renewal discount`,
        topK: 5,
      });
      evidenceRefs = hits.map((h) => ({
        docId: h.docId,
        docHash: h.docHash,
        section: h.section,
        chunkIndex: h.chunkIndex,
      }));
    } catch {
      evidenceRefs = [];
    }

    // Price the deal in base scenario
    const economics = await priceDeal({
      request: dealRequest,
      scenario: "base",
      supplierCostDeltaPct: "0.00",
      freightRateDeltaPct: "0.00",
    });

    const quoteId = `q-${randomUUID()}`;
    const version = 1;
    const createdAt = new Date().toISOString();
    const inputsHash = computeSha256(dealRequest);

    const draftQuote: Omit<QuoteVersion, "approval"> = {
      quoteId,
      version,
      createdAt,
      inputsHash,
      request: dealRequest,
      evidence: evidenceRefs,
      forecastVersion: "v1",
      policyVersion: "v1",
      economics,
    };

    const quoteHash = computeSha256(draftQuote);

    const quoteVersion: QuoteVersion = {
      ...draftQuote,
      approval: {
        state: "pending",
        actor: null,
        authority: null,
        exception: null,
        expiresAt: null,
        quoteHash,
      },
    };

    const db = getDb();
    const insertStmt = db.prepare(`
      INSERT INTO quote_versions (quote_id, version, payload, created_at)
      VALUES (?, ?, ?, ?)
    `);
    insertStmt.run(quoteId, version, JSON.stringify(quoteVersion), createdAt);

    const redirectUrl = `/quote/${quoteId}?v=1`;
    const accept = request.headers.get("accept") || "";

    if (accept.includes("text/html") && !accept.includes("application/json")) {
      return Response.redirect(new URL(redirectUrl, request.url), 303);
    }

    return new Response(
      JSON.stringify({
        runId,
        quoteId,
        version: 1,
        redirectUrl,
      }),
      {
        status: 201,
        headers: { "Content-Type": "application/json" },
      }
    );
  } catch (err: any) {
    if (err instanceof PricingClientError) {
      return new Response(
        JSON.stringify({
          runId,
          error: {
            code: err.code,
            message: err.message,
          },
        }),
        { status: 502, headers: { "Content-Type": "application/json" } }
      );
    }

    return new Response(
      JSON.stringify({
        runId,
        error: {
          code: "INTERNAL_ERROR",
          message: err?.message || "Internal server error",
        },
      }),
      { status: 500, headers: { "Content-Type": "application/json" } }
    );
  }
};

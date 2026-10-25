import type { APIRoute } from "astro";
import { randomUUID } from "node:crypto";
import type { QuoteVersion } from "@dealdesk/contracts";
import { getDb } from "../../lib/db.ts";
import { getActor, checkAccountScope } from "../../lib/session.ts";
import { priceDeal, PricingClientError } from "../../lib/pricing-client.ts";
import { renderEconomicsFragment } from "../../lib/economics-html.ts";
import { computeSha256 } from "../../lib/hash.ts";

export const POST: APIRoute = async ({ request }) => {
  const runId = `r-${randomUUID()}`;

  try {
    const body = await request.json();
    const { quoteId, scenario, supplierCostDeltaPct, freightRateDeltaPct } = body;

    if (!quoteId) {
      return new Response(
        JSON.stringify({
          runId,
          error: {
            code: "VALIDATION_FAILED",
            message: "Missing quoteId in request.",
          },
        }),
        { status: 422, headers: { "Content-Type": "application/json" } }
      );
    }

    const actor = getActor(request);
    const db = getDb();

    // Fetch the most recent version of this quote
    const stmt = db.prepare(`
      SELECT quote_id, version, payload, created_at
      FROM quote_versions
      WHERE quote_id = ?
      ORDER BY version DESC
      LIMIT 1
    `);
    const row = stmt.get(quoteId) as any;

    if (!row) {
      return new Response(
        JSON.stringify({
          runId,
          error: {
            code: "NOT_FOUND",
            message: `Quote ${quoteId} not found.`,
          },
        }),
        { status: 404, headers: { "Content-Type": "application/json" } }
      );
    }

    const currentQuote: QuoteVersion = JSON.parse(row.payload);

    // Enforce account scope
    if (!checkAccountScope(actor, currentQuote.request.accountId)) {
      return new Response(
        JSON.stringify({
          runId,
          error: {
            code: "FORBIDDEN_ACCOUNT",
            message: `Actor ${actor.userId} is not authorized for account ${currentQuote.request.accountId}.`,
          },
        }),
        { status: 403, headers: { "Content-Type": "application/json" } }
      );
    }

    // Call pricing client
    const newEconomics = await priceDeal({
      request: currentQuote.request,
      scenario: scenario === "shock" ? "shock" : "base",
      supplierCostDeltaPct: supplierCostDeltaPct || "0.00",
      freightRateDeltaPct: freightRateDeltaPct || "0.00",
    });

    const nextVersion = currentQuote.version + 1;
    const createdAt = new Date().toISOString();
    const inputsHash = computeSha256(currentQuote.request);

    const draftQuote: Omit<QuoteVersion, "approval"> = {
      quoteId,
      version: nextVersion,
      createdAt,
      inputsHash,
      request: currentQuote.request,
      evidence: currentQuote.evidence,
      forecastVersion: scenario === "shock" ? "shock" : currentQuote.forecastVersion,
      policyVersion: currentQuote.policyVersion,
      economics: newEconomics,
    };

    const quoteHash = computeSha256(draftQuote);

    const newQuoteVersion: QuoteVersion = {
      ...draftQuote,
      approval: {
        state: "draft",
        actor: null,
        authority: null,
        exception: null,
        expiresAt: null,
        quoteHash,
      },
    };

    // Immutable insert per Rule 6
    const insertStmt = db.prepare(`
      INSERT INTO quote_versions (quote_id, version, payload, created_at)
      VALUES (?, ?, ?, ?)
    `);
    insertStmt.run(quoteId, nextVersion, JSON.stringify(newQuoteVersion), createdAt);

    // Render economics panel HTML fragment
    const htmlFragment = renderEconomicsFragment(newEconomics, quoteId, nextVersion);

    return new Response(htmlFragment, {
      status: 200,
      headers: {
        "Content-Type": "text/html; charset=utf-8",
        "X-Quote-Version": String(nextVersion),
      },
    });
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

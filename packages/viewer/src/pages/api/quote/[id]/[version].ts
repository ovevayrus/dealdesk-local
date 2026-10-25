import type { APIRoute } from "astro";
import { randomUUID } from "node:crypto";
import type { QuoteVersion } from "@dealdesk/contracts";
import { getDb } from "../../../../lib/db.ts";
import { getActor, checkAccountScope } from "../../../../lib/session.ts";

export const GET: APIRoute = async ({ params, request }) => {
  const runId = `r-${randomUUID()}`;
  const { id, version: versionStr } = params;

  if (!id || !versionStr) {
    return new Response(
      JSON.stringify({
        runId,
        error: { code: "VALIDATION_FAILED", message: "Missing quote id or version parameter." },
      }),
      { status: 422, headers: { "Content-Type": "application/json" } }
    );
  }

  const version = parseInt(versionStr, 10);
  if (isNaN(version)) {
    return new Response(
      JSON.stringify({
        runId,
        error: { code: "VALIDATION_FAILED", message: "Version must be an integer." },
      }),
      { status: 422, headers: { "Content-Type": "application/json" } }
    );
  }

  const db = getDb();
  const row = db.prepare(`
    SELECT quote_id, version, payload, created_at
    FROM quote_versions
    WHERE quote_id = ? AND version = ?
  `).get(id, version) as any;

  if (!row) {
    return new Response(
      JSON.stringify({
        runId,
        error: { code: "NOT_FOUND", message: `Quote ${id} version ${version} not found.` },
      }),
      { status: 404, headers: { "Content-Type": "application/json" } }
    );
  }

  const quoteVersion: QuoteVersion = JSON.parse(row.payload);
  const actor = getActor(request);

  if (!checkAccountScope(actor, quoteVersion.request.accountId)) {
    return new Response(
      JSON.stringify({
        runId,
        error: {
          code: "FORBIDDEN_ACCOUNT",
          message: `Actor ${actor.userId} is not authorized for account ${quoteVersion.request.accountId}.`,
        },
      }),
      { status: 403, headers: { "Content-Type": "application/json" } }
    );
  }

  return new Response(JSON.stringify(quoteVersion), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
};

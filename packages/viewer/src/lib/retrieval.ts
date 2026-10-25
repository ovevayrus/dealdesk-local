import { randomUUID } from "node:crypto";
import type { Actor, EvidenceHit, EvidenceResult, EvidenceRef } from "@dealdesk/contracts";
import { getDb } from "./db.ts";
import { sanitizeFtsQuery } from "./fts.ts";
import { checkAccountScope, getAllowedClassifications } from "./session.ts";

export class ForbiddenAccountError extends Error {
  code = "FORBIDDEN_ACCOUNT";
  constructor(message = "FORBIDDEN_ACCOUNT") {
    super(message);
    this.name = "FORBIDDEN_ACCOUNT";
  }
}

export interface SearchEvidenceParams {
  accountId: string;
  query: string;
  topK?: number;
}

export function searchEvidence(params: SearchEvidenceParams, actor: Actor): EvidenceResult {
  const runId = `r-${randomUUID()}`;

  // 1. Account scope check (before touching the database)
  if (!checkAccountScope(actor, params.accountId)) {
    throw new ForbiddenAccountError(`FORBIDDEN_ACCOUNT: Actor ${actor.userId} not authorized for account ${params.accountId}`);
  }

  // 2. Query sanitization
  const matchExpr = sanitizeFtsQuery(params.query);
  if (!matchExpr) {
    return { runId, hits: [] };
  }

  const topK = Math.min(Math.max(params.topK ?? 8, 1), 25);
  const allowedClassifications = getAllowedClassifications(actor.role);

  if (allowedClassifications.length === 0) {
    return { runId, hits: [] };
  }

  const db = getDb();

  // Build parameterized placeholders for classifications
  const classPlaceholders = allowedClassifications.map(() => "?").join(", ");

  const sql = `
    SELECT c.doc_id, c.section, c.page, c.body,
           d.doc_hash, d.title, d.effective_date, d.classification,
           bm25(chunks_fts) AS score
    FROM chunks_fts
    JOIN chunks c    ON c.chunk_id = chunks_fts.rowid
    JOIN documents d ON d.doc_id = c.doc_id
    WHERE chunks_fts MATCH ?
      AND (d.account_id IS NULL OR d.account_id = ?)
      AND d.classification IN (${classPlaceholders})
    ORDER BY score ASC
    LIMIT ?;
  `;

  const queryParams = [matchExpr, params.accountId, ...allowedClassifications, topK];
  const stmt = db.prepare(sql);
  const rows = stmt.all(...queryParams) as any[];

  const hits: EvidenceHit[] = rows.map((row, index) => ({
    docId: row.doc_id,
    docHash: row.doc_hash,
    docTitle: row.title,
    section: row.section,
    page: row.page ?? null,
    passage: row.body,
    effectiveDate: row.effective_date,
    classification: row.classification,
    rank: index + 1,
    reason: row.section, // Interim default per Section 13
  }));

  return { runId, hits };
}

export interface HydratedEvidenceHit extends EvidenceHit {
  warning?: "SOURCE_CHANGED";
}

export function hydrateEvidence(refs: EvidenceRef[]): HydratedEvidenceHit[] {
  const db = getDb();
  const stmt = db.prepare(`
    SELECT c.doc_id, c.section, c.page, c.body,
           d.doc_hash, d.title, d.effective_date, d.classification
    FROM chunks c
    JOIN documents d ON d.doc_id = c.doc_id
    WHERE c.doc_id = ? AND c.section = ?
    ORDER BY c.chunk_index ASC
    LIMIT 1;
  `);

  const hits: HydratedEvidenceHit[] = [];

  for (let i = 0; i < refs.length; i++) {
    const ref = refs[i];
    const row = stmt.get(ref.docId, ref.section) as any;
    if (!row) {
      continue;
    }

    const hit: HydratedEvidenceHit = {
      docId: row.doc_id,
      docHash: row.doc_hash,
      docTitle: row.title,
      section: row.section,
      page: row.page ?? null,
      passage: row.body,
      effectiveDate: row.effective_date,
      classification: row.classification,
      rank: i + 1,
      reason: row.section,
    };

    // Drift check per Section 6: "SEED" skips drift check; otherwise flag SOURCE_CHANGED
    if (ref.docHash !== "SEED" && ref.docHash !== row.doc_hash) {
      hit.warning = "SOURCE_CHANGED";
    }

    hits.push(hit);
  }

  return hits;
}

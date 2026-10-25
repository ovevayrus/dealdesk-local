import { readFileSync, readdirSync, existsSync } from "node:fs";
import { resolve, dirname, basename } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { createHash } from "node:crypto";
import { getDb, resetSchema, closeDb } from "../src/lib/db.ts";

const __dirname = dirname(fileURLToPath(import.meta.url));
const corpusDir = resolve(__dirname, "../fixtures/corpus");
const seedFile = resolve(__dirname, "../fixtures/quote-version.seed.json");

interface Frontmatter {
  docId: string;
  title: string;
  accountId?: string;
  classification: "public" | "internal" | "restricted";
  effectiveDate: string;
  [key: string]: any;
}

function parseFrontmatter(content: string): { meta: Frontmatter; body: string } {
  const lines = content.split(/\r?\n/);
  if (lines[0]?.trim() !== "---") {
    throw new Error("Missing frontmatter opening '---'");
  }
  let endIndex = -1;
  for (let i = 1; i < lines.length; i++) {
    if (lines[i].trim() === "---") {
      endIndex = i;
      break;
    }
  }
  if (endIndex === -1) {
    throw new Error("Missing frontmatter closing '---'");
  }

  const meta: any = {};
  for (let i = 1; i < endIndex; i++) {
    const line = lines[i].trim();
    if (!line || line.startsWith("#")) continue;
    const colonIdx = line.indexOf(":");
    if (colonIdx > 0) {
      const key = line.slice(0, colonIdx).trim();
      let val = line.slice(colonIdx + 1).trim();
      // Remove inline comments
      const commentIdx = val.indexOf("#");
      if (commentIdx >= 0) {
        val = val.slice(0, commentIdx).trim();
      }
      if ((val.startsWith('"') && val.endsWith('"')) || (val.startsWith("'") && val.endsWith("'"))) {
        val = val.slice(1, -1);
      }
      meta[key] = val;
    }
  }
  const body = lines.slice(endIndex + 1).join("\n").trim();
  return { meta: meta as Frontmatter, body };
}

interface Chunk {
  section: string;
  body: string;
}

function chunkBody(body: string): Chunk[] {
  const lines = body.split(/\r?\n/);
  const sections: { heading: string; lines: string[] }[] = [];
  let currentHeading = "Summary";
  let currentLines: string[] = [];

  for (const line of lines) {
    const trimmed = line.trim();
    if (trimmed.startsWith("## ")) {
      if (currentLines.length > 0) {
        sections.push({ heading: currentHeading, lines: currentLines });
      }
      currentHeading = trimmed.slice(3).trim();
      currentLines = [];
    } else {
      currentLines.push(line);
    }
  }
  if (currentLines.length > 0) {
    sections.push({ heading: currentHeading, lines: currentLines });
  }

  const result: Chunk[] = [];

  for (const sec of sections) {
    const fullText = sec.lines.join("\n").trim();
    if (!fullText) continue;

    if (fullText.length <= 1200) {
      result.push({ section: sec.heading, body: fullText });
    } else {
      // Split on blank lines
      const paragraphs = fullText.split(/\n\s*\n/);
      let currentChunk = "";

      for (const para of paragraphs) {
        const candidate = currentChunk ? currentChunk + "\n\n" + para : para;
        if (candidate.length <= 1200) {
          currentChunk = candidate;
        } else {
          if (currentChunk) {
            result.push({ section: sec.heading, body: currentChunk });
          }
          currentChunk = para;
        }
      }
      if (currentChunk) {
        result.push({ section: sec.heading, body: currentChunk });
      }
    }
  }

  return result;
}

export function runIngest(): { documentCount: number; chunkCount: number } {
  const db = getDb();

  // Reset schema for idempotency
  resetSchema(db);

  db.exec("BEGIN TRANSACTION;");

  const insertDoc = db.prepare(`
    INSERT INTO documents (doc_id, doc_hash, title, account_id, classification, effective_date, source_path)
    VALUES (?, ?, ?, ?, ?, ?, ?)
  `);

  const insertChunk = db.prepare(`
    INSERT INTO chunks (chunk_id, doc_id, section, page, chunk_index, body)
    VALUES (?, ?, ?, ?, ?, ?)
  `);

  const files = readdirSync(corpusDir)
    .filter((f) => f.endsWith(".md"))
    .sort();

  let globalChunkId = 1;
  let totalChunks = 0;

  for (const file of files) {
    const filePath = resolve(corpusDir, file);
    const rawContent = readFileSync(filePath, "utf-8");
    const docHash = createHash("sha256").update(rawContent).digest("hex");
    const { meta, body } = parseFrontmatter(rawContent);

    if (!meta.docId || !meta.title || !meta.classification || !meta.effectiveDate) {
      throw new Error(`Document ${file} missing required frontmatter fields`);
    }

    insertDoc.run(
      meta.docId,
      docHash,
      meta.title,
      meta.accountId || null,
      meta.classification,
      meta.effectiveDate,
      `fixtures/corpus/${file}`
    );

    const chunks = chunkBody(body);
    let chunkIndex = 0;
    for (const ch of chunks) {
      insertChunk.run(
        globalChunkId++,
        meta.docId,
        ch.section,
        null, // page is null for Markdown
        chunkIndex++,
        ch.body
      );
      totalChunks++;
    }
  }

  // FTS5 rebuild as required by spec Section 6
  db.exec("INSERT INTO chunks_fts(chunks_fts) VALUES('rebuild');");

  // Seed quote-version if present
  if (existsSync(seedFile)) {
    const seedContent = readFileSync(seedFile, "utf-8");
    const seedJson = JSON.parse(seedContent);
    const insertQuote = db.prepare(`
      INSERT INTO quote_versions (quote_id, version, payload, created_at)
      VALUES (?, ?, ?, ?)
    `);
    insertQuote.run(
      seedJson.quoteId,
      seedJson.version,
      seedContent,
      seedJson.createdAt || new Date().toISOString()
    );
  }

  db.exec("COMMIT;");

  console.log(`Ingest complete: ${files.length} documents and ${totalChunks} chunks.`);
  return { documentCount: files.length, chunkCount: totalChunks };
}

// When run directly (pathToFileURL handles Windows drive letters and spaces)
if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  try {
    const res = runIngest();
    closeDb();
  } catch (err) {
    console.error("Ingest failed:", err);
    process.exit(1);
  }
}

import { DatabaseSync } from "node:sqlite";
import { resolve, dirname } from "node:path";
import { mkdirSync } from "node:fs";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));

export function getDbPath(): string {
  if (process.env.DEALDESK_DB_PATH) {
    return resolve(process.env.DEALDESK_DB_PATH);
  }
  // From packages/viewer/src/lib, workspace root is ../../../
  return resolve(__dirname, "../../../../data/dealdesk.db");
}

let _dbInstance: DatabaseSync | null = null;

export function getDb(customPath?: string): DatabaseSync {
  if (customPath) {
    const dir = dirname(resolve(customPath));
    mkdirSync(dir, { recursive: true });
    return new DatabaseSync(resolve(customPath));
  }
  if (!_dbInstance) {
    const dbPath = getDbPath();
    const dir = dirname(dbPath);
    mkdirSync(dir, { recursive: true });
    _dbInstance = new DatabaseSync(dbPath);
  }
  return _dbInstance;
}

export function closeDb(): void {
  if (_dbInstance) {
    _dbInstance.close();
    _dbInstance = null;
  }
}

export function initSchema(db: DatabaseSync): void {
  db.exec(`
    CREATE TABLE IF NOT EXISTS documents (
      doc_id         TEXT PRIMARY KEY,
      doc_hash       TEXT NOT NULL,
      title          TEXT NOT NULL,
      account_id     TEXT,
      classification TEXT NOT NULL,
      effective_date TEXT NOT NULL,
      source_path    TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS chunks (
      chunk_id    INTEGER PRIMARY KEY,
      doc_id      TEXT NOT NULL REFERENCES documents(doc_id),
      section     TEXT NOT NULL,
      page        INTEGER,
      chunk_index INTEGER NOT NULL,
      body        TEXT NOT NULL
    );

    CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
      body,
      content='chunks',
      content_rowid='chunk_id'
    );

    CREATE TABLE IF NOT EXISTS quote_versions (
      quote_id   TEXT NOT NULL,
      version    INTEGER NOT NULL,
      payload    TEXT NOT NULL,
      created_at TEXT NOT NULL,
      PRIMARY KEY (quote_id, version)
    );
  `);
}

export function resetSchema(db: DatabaseSync): void {
  db.exec(`
    DROP TABLE IF EXISTS chunks_fts;
    DROP TABLE IF EXISTS chunks;
    DROP TABLE IF EXISTS documents;
    DROP TABLE IF EXISTS quote_versions;
  `);
  initSchema(db);
}

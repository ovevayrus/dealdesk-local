import { DatabaseSync } from "node:sqlite";
import { resolve, dirname } from "node:path";
import { mkdirSync, existsSync } from "node:fs";
import { fileURLToPath } from "node:url";

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

export function getDbPath(): string {
  if (process.env.DEALDESK_DB_PATH) {
    return resolve(process.env.DEALDESK_DB_PATH);
  }
  return resolve(findWorkspaceRoot(), "data/dealdesk.db");
}

let _dbInstance: DatabaseSync | null = null;

export function getDb(customPath?: string): DatabaseSync {
  if (customPath) {
    const dir = dirname(resolve(customPath));
    mkdirSync(dir, { recursive: true });
    const db = new DatabaseSync(resolve(customPath));
    db.exec("PRAGMA busy_timeout = 5000;");
    return db;
  }
  if (!_dbInstance) {
    const dbPath = getDbPath();
    const dir = dirname(dbPath);
    mkdirSync(dir, { recursive: true });
    _dbInstance = new DatabaseSync(dbPath);
    _dbInstance.exec("PRAGMA busy_timeout = 5000;");
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
  db.exec("PRAGMA journal_mode = WAL;");
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

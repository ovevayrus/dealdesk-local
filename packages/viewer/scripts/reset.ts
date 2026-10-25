import { unlinkSync, existsSync } from "node:fs";
import { getDbPath, closeDb } from "../src/lib/db.ts";
import { runIngest } from "./ingest.ts";

try {
  closeDb();
  const dbPath = getDbPath();
  const pathsToDelete = [dbPath, `${dbPath}-wal`, `${dbPath}-shm`];

  for (const p of pathsToDelete) {
    if (existsSync(p)) {
      unlinkSync(p);
      console.log(`Deleted database file at ${p}`);
    }
  }

  const { documentCount, chunkCount } = runIngest();
  closeDb();
  console.log(`Reset complete: ${documentCount} documents, ${chunkCount} chunks.`);
} catch (err) {
  console.error("Reset failed:", err);
  process.exit(1);
}

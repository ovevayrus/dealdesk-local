import { unlinkSync, existsSync } from "node:fs";
import { getDbPath, closeDb } from "../src/lib/db.ts";
import { runIngest } from "./ingest.ts";

try {
  closeDb();
  const dbPath = getDbPath();
  if (existsSync(dbPath)) {
    unlinkSync(dbPath);
    console.log(`Deleted database at ${dbPath}`);
  }
  runIngest();
  closeDb();
  console.log("Reset complete.");
} catch (err) {
  console.error("Reset failed:", err);
  process.exit(1);
}

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));

test("actions-panel: template defines all 4 governance actions disabled with visible reasons", () => {
  const panelPath = resolve(__dirname, "../src/components/ActionsPanel.astro");
  const content = readFileSync(panelPath, "utf-8");

  // Four actions required by Spec 01 Section 11 & Section 14
  assert.ok(content.includes("Request Concession"), "Must include Request Concession");
  assert.ok(content.includes("Review Alternative Package"), "Must include Review Alternative Package");
  assert.ok(content.includes("Approve Quote"), "Must include Approve Quote");
  assert.ok(content.includes("Mark Ready for Human Release"), "Must include Mark Ready for Human Release");

  // All must be disabled
  const disabledMatches = content.match(/disabled/g);
  assert.ok(disabledMatches && disabledMatches.length >= 4, "All action buttons must be disabled");

  // Visible reasons
  assert.ok(content.includes("Concession approval workflow pending Suhas integration"));
  assert.ok(content.includes("Alternative package generation cut per hackathon brief"));
  assert.ok(content.includes("Quote approval signature pending Suhas integration"));
  assert.ok(content.includes("Human release gating pending Suhas integration"));
});

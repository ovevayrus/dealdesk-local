# Agent Questions 01: Viewer & Retrieval

### Item 1: FTS5 token length rule vs digit preservation
- **What was hit**: Spec section 6 states: "3. Drop tokens shorter than 2 characters... So `freight costs for ACME-7?` becomes `\"freight\" OR \"costs\" OR \"for\" OR \"acme\" OR \"7\"`". A strict `< 2` character drop would remove single-digit tokens such as `"7"`, conflicting with the required example output and `fts-sanitize.test.ts`.
- **Spec section**: Section 6 (Query sanitization) and Section 12 (`fts-sanitize.test.ts`).
- **What was done instead**: `sanitizeFtsQuery` drops single-character non-digit characters but preserves digit tokens (e.g. `t.length >= 2 || /\d/.test(t)`), producing the exact expected string `"freight" OR "costs" OR "for" OR "acme" OR "7"`.
- **Decision needed**: Confirm if all single alphanumeric characters should be dropped, or if digits / account qualifiers should always be retained.

### Item 2: Astro Telemetry and permissions in container
- **What was hit**: Astro dev/build attempts to write telemetry config to `/home/coder/.config/astro` on startup, which failed with `EACCES` due to root-owned `/home/coder/.config`. Spec constraint 2.5 also strictly forbids telemetry/analytics.
- **Spec section**: Section 2 (Constraint 5: No analytics, no telemetry) and Section 4.
- **What was done instead**: Configured `ASTRO_TELEMETRY_DISABLED=1` in `packages/viewer/package.json` scripts (`dev` and `build`).
- **Decision needed**: None required; this satisfies Constraint 5 and avoids permission errors.

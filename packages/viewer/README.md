# DealDesk Local Viewer (`@dealdesk/viewer`)

An optional local viewer for synthetic DealDesk quote, evidence and customer-preview fixtures. The Python chatbot in the root README is the primary demo; this viewer is a separate prototype.

The reviewed dependency baseline uses Astro 7.3.3 and `@astrojs/node` 11.1.3 with the committed lockfile. Contracts typecheck, the 30 viewer regressions and the production build were checked on Node 24.13.0 with external network blocked. The resolved dependency audit reported no advisories at this check; that is not a safety guarantee.

## Prerequisites

- **Node.js 24+**: Runs plain TypeScript natively with type-stripping; uses built-in `node:sqlite` with FTS5 support, meaning there are no native bindings or C++ addons to compile (zero `node-gyp` or build tooling required).
- **pnpm 11.18.0**: Workspace package manager pinned by the root package manifest.

## Quickstart

Run these commands from the repository root:

```bash
# 1. Install workspace dependencies
pnpm install --frozen-lockfile --ignore-scripts

# 2. Ingest markdown corpus into local SQLite database
pnpm --filter @dealdesk/viewer ingest

# 3. Start the local Astro server
pnpm --filter @dealdesk/viewer dev
```

Open **`http://127.0.0.1:4321`** in any browser.

- **Deal Intake & Validation**: `http://127.0.0.1:4321/`
- **Reference Deal (ACME-7)**: `http://127.0.0.1:4321/quote/q-seed-acme-7`
- **Customer Proposal Preview**: `http://127.0.0.1:4321/preview/q-seed-acme-7`
- **Demo role switching**: the header selects fixture identities `u-dana` (Manager for `ACME-7`/`NORTHWIND-2`) and `u-sofia` (Seller for `ACME-7`, restricted citations redacted). The unsigned cookie can be chosen by any caller. These are test projections, not authenticated users. Keep this viewer on loopback and use synthetic data.

## Running Tests

Run the automated suite with Node's native test runner. Counts and timings depend on the revision and machine:

```bash
pnpm --filter @dealdesk/viewer test
```

To verify database reset and clean re-ingest:

```bash
pnpm --filter @dealdesk/viewer reset
```

## Architecture and runtime scope

Document search uses SQLite FTS5. `PRICING_MODE=fixture` loads reference figures; a configured `PRICING_BASE_URL` selects an HTTP pricing server and must be trusted. Customer narrative currently uses deterministic templates; viewer model annotation is not implemented. The code projects selected customer fields separately from internal economics and tests that separation. Money values travel as decimal strings. These checks do not establish production authentication or guarantee that every future integration is safe.

## Verifying the offline claim

`start:offline` preloads checks that refuse non-loopback traffic through common Node TCP, DNS and `fetch` APIs in this server process. Normal `start` does not enable that preload. It is not an operating-system sandbox, and does not cover native modules, subprocesses, the browser, or other model/agent processes. A full machine/network-off run remains a separate verification step.

```bash
pnpm --filter @dealdesk/viewer build
pnpm --filter @dealdesk/viewer start:offline
```

Exercise the demo path, then stop the server. Any attempted egress prints `[egress-guard] BLOCKED <kind> -> <target>` immediately, and the process reports a violation count on shutdown.

*Note: All data, company names, and figures in `fixtures/` are completely synthetic.*

Read [the shared security boundaries](../../docs/security-boundaries.md) before changing host, pricing endpoint, identities, data or deployment settings.

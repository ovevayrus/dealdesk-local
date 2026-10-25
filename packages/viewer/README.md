# DealDesk Local Viewer (`@dealdesk/viewer`)

Document intelligence and local deal viewer for DealDesk Local, built for local-only enterprise pricing on Dell Pro Max hardware with an NVIDIA GB10 chip.

## Prerequisites

- **Node.js 24+**: Runs plain TypeScript natively with type-stripping; uses built-in `node:sqlite` with FTS5 support, meaning there are no native bindings or C++ addons to compile (zero `node-gyp` or build tooling required).
- **pnpm 10+**: Workspace package manager.

## Quickstart

Run these commands from the repository root:

```bash
# 1. Install workspace dependencies
pnpm install

# 2. Ingest markdown corpus into local SQLite database
pnpm --filter viewer ingest

# 3. Start the local Astro server
pnpm --filter viewer dev
```

Open **`http://127.0.0.1:4321`** in any browser.

- **Deal Intake & Validation**: `http://127.0.0.1:4321/`
- **Reference Deal (ACME-7)**: `http://127.0.0.1:4321/quote/q-seed-acme-7`
- **Customer Proposal Preview**: `http://127.0.0.1:4321/preview/q-seed-acme-7`
- **Role Switching**: Use the header banner to toggle between `u-dana` (Manager, authorized for `ACME-7` and `NORTHWIND-2` including restricted citations) and `u-sofia` (Seller, authorized only for `ACME-7` with restricted citations redacted).

## Running Tests

Run the full automated test suite (24 tests running under native `node:test` in under 300ms):

```bash
pnpm --filter viewer test
```

To verify database reset and clean re-ingest:

```bash
pnpm --filter viewer reset
```

## Architecture & Local-First Guarantees

DealDesk Local operates 100% offline with zero external network calls beyond `127.0.0.1`. Document search runs BM25 full-text retrieval directly inside SQLite via `node:sqlite` FTS5. Deal pricing is computed deterministically from a dedicated pricing module (`PRICING_MODE=fixture` for offline reference figures or a local service on port 8001). Local LLMs (Ollama / vLLM on port 8000) are called strictly for optional citation annotation and customer-facing narrative drafting, with deterministic template fallbacks when offline (`MODEL_MODE=off`). Internal costs, margins, and policy floors are strictly enforced server-side and never leaked into customer previews or browser scripts. Money values are transferred as exact decimal strings with zero floating-point arithmetic.

## Verifying the offline claim

`start:offline` runs the production server with every non-loopback TCP connect, DNS lookup and `fetch` blocked at the Node level, so the local-first claim is proven by the process refusing egress rather than by inspection.

```bash
pnpm --filter viewer build
pnpm --filter viewer start:offline
```

Exercise the demo path, then stop the server. Any attempted egress prints `[egress-guard] BLOCKED <kind> -> <target>` immediately, and the process reports a violation count on shutdown.

*Note: All data, company names, and figures in `fixtures/` are completely synthetic.*

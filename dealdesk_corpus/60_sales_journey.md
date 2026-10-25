# One-page rep journey — DealDesk Local (demo deal: Account A, Harbor Logistics)

Persona: Jordan, enterprise AE at Northwind Edge Systems. Quota pressure, 6 open deals, quote due Oct 28.

1. Telegram: `/quote DEAL-A-2026-10` → bot replies "Quote request received. Open DealDesk viewer." (nothing else leaves the box)
2. Viewer form (local): account A, bundle EdgeNode-100, qty 100, delivery Dec 1 2026, destination Oakland, term 12 mo, terms Net 45, proposed discount 10%, expiry Nov 27.
3. Agent retrieves: ACC-A-001/002/003, SVC-004, SVC-005, CMP-X-001/002, DH-001, WL-002, POL-001. Each shown with effective date.
4. Pricing engine: base $90,000 / stress $97,600 / floor $130,133.34. Standard offer $144,000 (10%, rep authority). Stress margin 32.2%.
5. Flags raised: Net 45 → finance review. "Another vendor lower" → unverified, no number. Budget ceiling $150k confirmed → $144k fits.
6. Rep requests Negotiated package: $136,000 (15%). Engine: stress margin 28.24%, needs director approval. Routed to director; approval bound to quote v2 hash.
7. Customer draft generated: scope, Dec 1 delivery commitment, 12-mo SLA, $136,000, valid to Nov 27. No cost, margin, or competitor text.
8. Overnight: supplier feed updates (SVC-006: EN-1 stress-case unit cost $660 → $740). Watcher: quote v2 stress cost $105,600, margin 22.35%, floor $140,800. Review event → Telegram: "1 open quote needs review." Original offer + approval preserved, marked stale.
9. Rep opens viewer: agent proposes (a) hold $136k and request finance exception, (b) re-quote at $140,800+, (c) phased alternative (50 units now at current cost, 50 in Q1 with adjustment clause).

Where the rep wins: steps 5 and 8. Nobody reads 22 docs before a quote; nobody re-checks an open quote when a cost sheet changes.

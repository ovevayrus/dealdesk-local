# DealDesk Local — hackathon project brief

**A private enterprise pricing agent that turns internal evidence and forecast costs into a defensible quote, then watches for changes that put the deal at risk.**

Prepared October 25, 2026 for Khushi Gangrade, Luis Aviles, Suhas Rahul, Jai Surya Gupta, and Michael G. Schuck. All event times below are Pacific. This is a build plan; targets, synthetic examples, and proposed features are not implementation results.

## 1. The project to build

Build an always-on deal desk for enterprise account executives and sales managers. A salesperson describes a deal. The agent retrieves permitted company documents, identifies relevant customer priorities and competitor evidence, forecasts the costs that matter on the delivery dates, and calls deterministic pricing code. It produces a recommended offer, an approved negotiation range, a cited internal rationale, and a customer-facing explanation. It then monitors open quotes and alerts the owner when new costs or evidence require review.

**Pitch:** “Your best pricing intelligence is too sensitive to send away. DealDesk Local uses it on your own machine to build a price you can defend—and warns you before changing costs undermine the deal.”

The buyer is a Head of Sales or Revenue Operations. The daily user is an enterprise account executive. Finance sets the margin policy; a sales director approves concessions. Procurement and delivery teams own cost inputs. The agent prepares recommendations and routes approvals; a person releases the quote.

For the hackathon, use a fictional enterprise hardware and managed-service seller. This makes supply, freight, installation, and recurring service costs concrete. The same structure can later support your own services by replacing those cost drivers with compute, staffing, onboarding, support, and delivery capacity.

### What goes into a defensible recommendation

| Factor | Company-owned evidence or structured input | How it affects the decision |
|---|---|---|
| Cost to serve | Product/service cost sheets, supplier terms, delivery history, staffing/support assumptions | Builds the dated cost ledger and sensitivity analysis |
| Customer requirements | Internal account research, procurement criteria, budget signals, renewal date, prior agreements | Shapes the package and customer explanation; distinguish confirmed requirements from inferred signals |
| Competitive position | The company's own battlecards, dated competitor observations, win/loss notes | Supports a qualified comparison of equivalent scope; uncertain intelligence remains labeled |
| Commercial policy | Current price book, discount authority, minimum margin, approved terms | Sets feasible prices and required approval |
| Ability to deliver | Inventory, supplier lead times, service capacity, delivery window and SLA | Blocks an impossible commitment or proposes phased scope; a higher price alone cannot solve unavailable capacity |
| Future exposure | Supply/freight forecasts, service cost assumptions, quote validity, escalation clauses | Determines stress cost and whether terms need review |
| Prior deal evidence | Comparable approved quotes and realized delivery costs | Provides context and checks estimates; a historical exception is not permission to repeat it |

For the MVP, capacity and lead time are simple fixture constraints rather than a scheduling optimizer. Require a source/effective date for each material input. Current authorized policy takes precedence over old proposals; disputed research is shown as a conflict. If a missing factor could materially change cost, feasibility, or authority, the agent asks for it or marks the quote pending review.

### The narrow MVP

One seller, one bundle, three accounts, two competitors, roughly 25 short documents, two forecast series, and five open quotes. Support text PDFs/Markdown and CSV; defer scanned PDFs and complex spreadsheets. One local inference model, one required messaging channel, and one local quote viewer are enough.

The complete loop is:

1. Receive an opaque deal ID through Slack, Discord, or Telegram; enter sensitive deal details locally.
2. Check the user's access and load the deal's quantity, scope, schedule, currency, and expiry.
3. Retrieve account research, comparable deals, current price policy, service commitments, and relevant competitor evidence with citations.
4. Forecast supply and freight for the actual procurement/shipment dates; calculate recurring service costs separately.
5. Produce standard, negotiated, and alternative-scope packages using the pricing engine.
6. Show an internal evidence pack and a separate customer-facing draft. Route any concession to an authorized approver.
7. Watch the local cost-data folder on a schedule; flag affected open quotes without silently changing a sent offer.

**The memorable moment:** an apparently attractive concession becomes unsafe after a cost update. The agent identifies the affected quote, explains the changed assumption, and proposes a concrete commercial response while the sensitive evidence stays on the GB10.

## 2. Verified event requirements and the rubric

The organizer's signed-in [event dashboard and day-of announcement](https://builderbase.com/track-dashboard/dell-x-nvidia-ai-hackathon-san-francisco/overview) were inspected directly in the user's existing browser session on October 25. They contain newer details than the [public event page](https://builderbase.com/event/dell-x-nvidia-ai-hackathon-san-francisco). **Use the day-of dashboard for the rubric, stack rule, video length, and deadlines.** The implementation/evidence choices below are our recommendations; the quoted judging questions and percentages come from the dashboard.

| Organizer requirement | What the team must do |
|---|---|
| Business agent, always on | Show quote preparation plus a scheduled cost-change review. |
| Dell Pro Max with GB10; inference local | Run the final workflow, local model, retrieval, forecasts, pricing, and viewer on the supplied machine. |
| At least one of NemoClaw, OpenClaw, or OpenShell | The day-of announcement relaxes the public page's all-three wording. Use OpenClaw as the agent runtime; add NemoClaw/OpenShell if already supported and useful for control/proof. |
| Slack, Discord, or Telegram on the public challenge page | Integrate one channel for minimal requests and notifications; confirm if a local-only interaction is accepted under the day-of brief. |
| All inference local; no cloud LLM in runtime path | Includes reasoning and tool selection. Our design also keeps research, embeddings, forecasts, and sensitive tools local; the channel is transport. |
| Build on site, on the day | Start a new implementation repository at the event. Libraries/scaffolds are permitted; substantially prebuilt projects are disqualified. This document is planning material. |
| Teams of 2–5 | All five register individually and put the team on record in BuilderBase before claiming the GB10. Follow the day-of roster instructions. |
| Round 1 at 17:30 PT | Code lock; repository and video **under two minutes** due; return GB10 hardware. Target a 1:50–1:55 video and submit by 17:00. |
| Project deadline 18:00 PT; deck by 19:00 | Complete dashboard fields and NVIDIA feedback; publicly viewable deck URL. Do not treat 18:00 as permission to miss Round 1. |
| Declare stack; use cleared material | List versions and licenses. Use clearly labeled synthetic data for this demo. |

The day-of schedule says computer distribution/hacking starts at 10:10, lunch is at 13:00, hardware returns at 17:30, and top-eight pitches start at 19:00. Each team has **five minutes: three minutes of demo plus two minutes of Q&A**. Judges will not screen-share; video/repository/deck must be accessible by link. The public page's 18:30 demos and three-minute video allowance are superseded. Confirm finalist hardware access with a mentor before return; record the working GB10 demo well before 17:30. The dashboard also shows a morning check-in ending at 17:00; complete it early. Feedback questions are embedded in the submission checklist; verify any additional individual form requirement.

### How to earn each category

| Dashboard category and weight | What the dashboard asks | Our build/evidence plan | Owner |
|---|---|---|---|
| **Technical execution — 25%** | “Does it work end to end?” Agent loop, tools, engineering under time pressure | Real local tool calls, deterministic calculations, cited retrieval, scoped approval, scheduled review; hand-checked fixtures and visible trace | Suhas + Khushi; Jai verifies |
| **Usefulness and business value — 25%** | Would a company pay? Clear workflow, owner, measurable value | Named sales persona, useful packages, measured manual/assisted task time, synthetic margin exposure, clear next action | Michael + Jai |
| **Local-first design — 25%** | All inference on the GB10; no cloud LLM runtime calls | Selected model route, fresh offline workflow, egress evidence, account filtering, minimal channel payload, blocked disclosure tests | Suhas + Luis |
| **Demo quality — 25%** | Clarity and showing the thing working | One coherent deal, visible cost shock, clean video under two minutes, public deck, rehearsed three-minute demo | Michael + Luis; Jai submits |

The weights are equal; a strong business story cannot compensate for a broken local workflow. Give every category visible evidence and a saved verification artifact. The plan addresses the rubric but cannot guarantee a score.

## 3. User experience and outputs

The request form asks for account, product/service bundle, quantity, delivery dates, destination, service term, payment terms, proposed discount, and quote expiry. Use explicit defaults and ask for missing critical inputs. An unsupported SKU, unknown currency, or missing delivery date should stop quote release.

The local viewer has four useful panels:

- **Offer:** total contract value, upfront versus recurring charges, discount, validity date, and approval status.
- **Economics:** itemized expected costs, stress costs, margin, floor, and two sensitivity controls.
- **Evidence:** source passages, document versions, effective dates, and reasons each source matters.
- **Actions:** request concession, review an alternative package, approve a specific quote version, or mark it ready for human release.

Each recommendation produces two distinct artifacts:

| Internal deal pack | Customer-facing draft |
|---|---|
| Costs, margins, assumptions, customer research, comparable deals, competitor confidence, policy checks, approval chain | Offer scope, service value, delivery commitment, price, validity, and permitted negotiation explanation |
| Authorized local viewer only | Local preview, human-reviewed before export |
| Full provenance and warnings | No supplier cost, internal margin, restricted account research, or unapproved competitor claims |

A customer-facing example: “This offer includes deployment at six locations and twelve months of managed support. The quoted price is valid through the stated date; a phased deployment option can reduce the initial commitment.” Internal costs should never appear in that explanation.

The required messaging channel receives a fixed message such as “A quote review is ready. Open your local DealDesk viewer.” Even identifiers and links can reveal activity, so keep them minimal and recipient-restricted. Do not put free-form LLM output, customer names, prices, source passages, or margins in outbound messages.

## 4. Local architecture and boundaries

```text
Required messaging channel ── minimal request / notification adapter
                                      │
                               Local task queue
                                      │
                   OpenClaw agent (qualifying runtime)
                 NemoClaw / OpenShell layers when enabled
                                      │
                  ┌───────────────────┼──────────────────┐
                  │                   │                  │
            Local LLM           Local read tools    Deterministic tools
        extraction + wording     authorized search   forecast / price /
                                 and evidence        policy / approval
                  └───────────────────┼──────────────────┘
                                      │
                      SQLite state + versioned quote JSON
                                      │
                      Authenticated local quote viewer
                                      │
               Scheduled cost watcher → review event → task queue
```

All compute and sensitive stores run on the GB10. Development laptops can edit the event repository; the submitted demo executes on the supplied machine. Bind the viewer locally, or access it through an authenticated tunnel on the team network. A loopback URL sent to a different person's device does not reach the GB10 automatically.

| Layer | MVP decision | Fallback |
|---|---|---|
| Agent/runtime | OpenClaw as the chosen qualifying component; NemoClaw/OpenShell if the supported setup makes them practical | At least one is required by the day-of announcement; protect the first working loop before adding stack complexity |
| Inference | A locally served, tool-capable model confirmed to work on the supplied image | Smaller compatible local model; shorter context and fewer calls |
| Retrieval | SQLite full-text or simple lexical retrieval with metadata filtering; page/section citations | Curated index of 25 documents; local embeddings are optional |
| Data | Local CSV/JSON plus SQLite state, explicit currency and units | Standard library implementations for small datasets |
| Calculations | Python functions with typed JSON inputs/outputs and decimal money arithmetic | Simple explicit scenarios before adding a statistical model |
| Viewer | Small locally hosted app with offer, evidence, economics, and approval state | Server-rendered pages; preserve readable evidence and exact numbers |
| Always-on work | OpenClaw scheduled job, persisted feed cursor, deduplicated review events | Short demo schedule; still show a genuine scheduled run |

OpenClaw documents [scheduled jobs](https://docs.openclaw.ai/automation/cron-jobs). Pin the actual installed versions and use their documented commands. Avoid unverified model names, throughput promises, or sandbox presets in the pitch.

If NemoClaw is used, it supports both hosted and local providers, so its presence alone does not prove local inference. Record the selected model route and ensure it terminates on the GB10. See the [NVIDIA overview](https://docs.nvidia.com/nemoclaw/latest/about/overview.html). Show only the filesystem, network, and process controls actually enabled in the chosen deployment.

### Tool contracts to freeze by 10:45

Each tool returns validated JSON, a run ID, and an explicit error on invalid input. Build against one shared fixture before integrating real data.

| Object/tool | Required contract | Primary owner |
|---|---|---|
| `DealRequest` | Deal/account IDs; user identity from trusted session; SKU, quantity, schedule, destination, scope, term, USD, expiry | Jai defines fields; Luis implements form |
| `search_evidence` | Server-enforced account/role filter; document ID/hash, page/section, passage, effective date, classification | Luis |
| `forecast_costs` | Series ID, as-of date, horizon, units, base/stress paths, method, backtest results, data version | Khushi |
| `price_deal` | Cost ledger, total revenue, gross margin, feasible range, options, rules, assumptions, evidence references | Khushi; Jai specifies policy/tests |
| `approve_quote` | Authenticated actor; authority; quote ID/version/hash; allowed exception; expiry; audit timestamp | Suhas; Jai defines authority |
| `watch_quotes` | New feed version; affected open quotes; previous/new appraisal; one deduplicated review event | Suhas; Khushi supplies repricing |
| `QuoteVersion` | Immutable inputs, evidence versions, forecast versions, calculated fields, policy version, approval state | Khushi + Luis |
| `render_pack` | Numeric fields bound to specific quote fields; local internal view and separate customer draft | Luis |

Keep the orchestrator bounded: validate → retrieve → extract → forecast → price → explain → review. Limit retries and show a clear error when a tool or model fails. Do not build a swarm of autonomous pricing agents for this MVP.

## 5. Pricing logic that can be defended

The LLM proposes searches, extracts cited facts, and drafts explanations. Code owns all calculations, authority checks, and quote state. A model-generated amount never becomes an authoritative price.

### Build a cost ledger with dates and units

```text
hardware = sum(units procured in period × supplier USD/unit in that period)
freight = sum(shipment count × USD/shipment for the lane and ship date)
installation = installation hours × loaded USD/hour
service = sum(active service units in month × USD/unit/month)
base_cost = hardware + freight + installation + service
stress_cost = same ledger evaluated under a named joint stress scenario
reserve = stress_cost - base_cost
gross_margin = (total_revenue - cost_basis) / total_revenue
economic_floor = ceil_to_cent(stress_cost / (1 - minimum_margin))
```

Use the actual procurement dates for hardware and actual shipment dates for freight. Do not average three years of component prices for equipment purchased once at the start. Recurring service costs accrue through the service term. If inventory is already purchased, use the company's documented cost convention rather than automatically applying a future procurement forecast.

For this MVP, use USD, one known payment schedule, and a twelve-month service term. State that taxes, FX, financing, returns, and complex working-capital effects are excluded. Flag nonstandard terms for review rather than pretending their cost is covered.

Jai supplies a versioned synthetic policy: 25% minimum gross margin, reps may discount up to 10%, directors up to 20%, and below-floor deals are blocked pending a separately defined finance exception. These are demo assumptions, not universal best practices.

For list revenue `L` and the current actor's maximum discount `d`:

```text
authorization_floor = L × (1 - d)
lowest_authorized_offer = max(economic_floor, authorization_floor)
feasible interval = [lowest_authorized_offer, L]
```

If the lower bound exceeds list revenue, return **infeasible under current terms**. Offer scope, timing, or contract changes for review. Never clamp the floor downward to make a quote appear valid. Gross margin and markup are different; use gross margin consistently.

Customer and competitor research informs packaging, objections, and a proposed target inside a feasible range. Normalize competitor scope, quantities, term, date, and source quality before comparing prices. An old rumor about a cheaper competitor is weak evidence and must not override a margin rule. Without validated demand or willingness-to-pay data, call this a **defensible policy-compliant offer**, not a proven optimal price.

### Three useful packages

1. **Standard:** standard scope and terms, within the rep's authority.
2. **Negotiated:** a clearly defined concession, with director approval where required.
3. **Alternative:** phased delivery, narrower scope, or an explicitly costed adjustment clause. Recompute its costs; do not attach an arbitrary lower price to the same bundle.

### Hand-checkable synthetic demo

| Cost item | Base case | Named stress case |
|---|---:|---:|
| 100 hardware units | $60,000 | $66,000 |
| Two shipments | $2,000 | $2,400 |
| Installation | $4,000 | $4,000 |
| Twelve months of service | $24,000 | $25,200 |
| Total | $90,000 | $97,600 |

At a 25% stress-margin floor, minimum contract revenue is **$130,133.34**, rounded upward. With a $160,000 list price, a rep-authorized 10% discount gives **$144,000**. A negotiated **$136,000** offer is a 15% discount, requires director approval, and has a stress margin of **28.24%**.

Then a new supplier feed raises the stress cost to **$105,600**. The same $136,000 open quote now has a **22.35%** projected stress margin; the revised economic floor is **$140,800**. The watcher raises a review task. It preserves the original offer and approval, labels the appraisal as changed, and requires a fresh quote version and approval for revised terms.

This is a simulated risk demonstration, not a claim of realized savings. A higher floor does not prove the customer will accept a higher price.

## 6. Forecasting without overclaiming

Khushi owns two monthly series: supplier unit cost for the bundle and freight cost for one delivery lane. Generate 36 months of clearly synthetic history with a fixed seed. Use a one-to-six-month horizon tied to the shipment schedule. Model the twelve-month service expense with explicit base/high assumptions unless there is enough time and data to validate it statistically.

Compare a last-value baseline and, where seasonality is supported, a seasonal-naive baseline against one simple candidate such as exponential smoothing. Use chronological rolling-origin evaluation: at each historical cutoff, fit only earlier observations and score the same horizons the deal uses. Do not randomly split a time series or let future cost feeds leak into historical forecasts.

Report MAE in USD/unit or USD/shipment and WAPE where the denominator is meaningful, with sample counts and horizon. Display the baseline result even if it wins. The forecast is useful when it supports a better review decision; it does not need a complex model.

Show low/base/high **scenarios** by default. If time permits validated prediction intervals, calculate them by horizon and measure held-out coverage. Do not label arbitrary residual bands P10/P90, or a sum of component P80 values a total-cost P80. Aggregate risk needs a joint assumption about cost movements. Do not add the reserve twice when stress costs already include it.

The forecast panel shows history, as-of date, next delivery date, base/stress path, data freshness, validation result, and which quote lines use that forecast. If a source is stale or inadequate, flag it and require manual review. Synthetic-data accuracy demonstrates the pipeline, not real supplier-market predictive ability. These choices follow the evaluation principles in the authors' [Forecasting: Principles and Practice](https://otexts.com/fpp3/toolbox.html).

## 7. Sensitive data, access, and human control

Local execution is necessary for the concept, but it does not replace access control. Implement and demonstrate these specific boundaries:

- **Authorized retrieval:** enforce account and role permissions in the retrieval tool before material reaches the model. The model does not choose its own user identity or permissions.
- **Limited filesystem:** source documents read-only; writable state/output directories; no general access to host secrets or unrelated files.
- **Untrusted documents:** source content can provide facts but cannot authorize a tool call, change a policy, or request disclosure. Plant one malicious instruction in a synthetic competitor document to test this.
- **Constrained tools:** named operations with validated fields, no arbitrary shell/network tool available to the pricing workflow, and no automatic customer sending.
- **Local inference audit:** inspect both sandbox and host-side routing. Disable remote model fallback and external embeddings, OCR, analytics, or error reporting that would transmit payloads.
- **Outbound restriction:** a fixed notification schema, recipient allowlist, and an adapter that cannot accept arbitrary text. Test disclosure through the allowed messaging service as well as a disallowed URL.
- **Scoped approval:** bind the approver to a specific quote version/hash, exception, and expiry. A manager's one-deal concession never silently becomes company-wide policy. Changed terms invalidate a pending approval.
- **Auditability:** record inputs, source/forecast/policy versions, tool outputs, actor, and decision timestamps locally. Avoid placing full sensitive passages in general debug logs.

NVIDIA warns that approved endpoints remain possible disclosure paths; permitting a messaging service does not establish that its payloads are safe. See [NemoClaw security guidance](https://docs.nvidia.com/nemoclaw/latest/security/best-practices.html). Check that direct channel-send tools cannot bypass the constrained adapter before claiming outbound protection.

For numeric integrity, render every amount and percentage directly from its corresponding structured quote field. Checking whether a number appeared somewhere in a tool output is insufficient: the model could reuse a valid number for the wrong customer or meaning. Human review remains part of quote release.

For local-first proof, show the selected local model and inference route, network/egress evidence, a fresh local quote while disconnected, and the scheduled watcher still running. GPU activity is supporting evidence, not proof that remote calls are absent. While disconnected, messaging is unavailable; queue a minimal notification for reconnection and demonstrate the core workflow through the local viewer.

## 8. Five-person ownership

These assignments use the supplied profiles and portfolio evidence, including Michael's exact profile read directly in the signed-in browser. They are recommended responsibilities, not claims that anyone has already agreed to them. Three technical workstreams are supported by two commercial, policy, and verification workstreams; each person still ships concrete artifacts.

| Person | Assigned role | Why this fit | Concrete finish line |
|---|---|---|---|
| **Suhas Rahul** | **Local agent platform, security, and automation lead** | His portfolio source describes self-hosted OpenClaw/Hermes, Docker/Proxmox/Linux, Telegram, and an approval-based agent | Local model + required stack; tool orchestration; watcher; scoped approval identity; offline and egress proof |
| **Khushi Gangrade** | **Quantitative pricing and forecasting lead** | Her exact indexed profile lists an ASU MS in Data Science and Python/SQL/AI training | One numerical service: seeded data, baseline/candidate forecast, dated cost ledger, Decimal prices/margins, sensitivity, and arithmetic fixtures |
| **Luis Aviles** | **Application and document intelligence lead** | His own site and GitHub describe software engineering, AI agents, conversational interfaces, and full-stack work | Local viewer; retrieval and citations; shared integration contracts; deterministic numeric rendering; separate customer draft |
| **Jai Surya Gupta** | **Product, pricing policy, evaluation, and submission lead** | His exact indexed profile lists JR Group Singapore, Babson, and business/quantitative coursework | Versioned policy/approval spec, hand-priced expected results, evaluation report, business-case math, milestone decisions, public deck and complete submission |
| **Michael G. Schück** | **Sales workflow, knowledge corpus, and demo lead** | His exact profile describes full-cycle sales, partnerships, AI-enabled outbound, product validation, QA research, and UX testing | Authentic rep workflow, 25 short synthetic documents, negotiation packages and talk tracks, adversarial sales questions, usability checks, narration and buyer story |

**Workload rule:** Khushi implements forecasts and pricing as one small numerical module; start with a baseline forecast and add the candidate only after arithmetic works. Jai supplies hand-calculated expected results and runs acceptance checks, rather than leaving Khushi to evaluate her own work alone. Michael writes the source packet and validates the sales experience, freeing Luis for code. Suhas owns integration wrappers, approval state, and scheduling. Luis owns the viewer and retrieval. Cut forecasting complexity before overloading the quantitative workstream.

### Individual task lists

**Suhas:** own the GB10 and chosen qualifying stack; verify local model endpoint; connect one channel; build tool wrappers and bounded orchestration; persist approvals, jobs, and review events; esta-blish role identity; implement minimal outbound adapter; run offline and injection/disclosure checks; own reset, warm-up, and hardware return. First milestone: request reaches agent and calls a mock pricing tool by 11:00. Final evidence: runtime/config snapshot, blocked-egress log, offline recording.

**Khushi:** define units/as-of dates and generate numeric data; implement the dated cost ledger, Decimal-based prices/margins, feasible range, and sensitivity; create the cost update that changes one quote; implement a baseline forecast first and compare one candidate only if time allows; expose one validated numerical JSON contract. Jai supplies expected outputs and runs checks; Suhas wires the wrapper. First milestone: hand-priced fixture passes by 11:30; baseline forecast integrated by 12:30. Final evidence: numerical module, reproducible data, arithmetic fixtures, forecast table/chart, cost-shock result.

**Luis:** agree the shared contracts; build the local form/viewer; ingest permitted documents with provenance; implement search and source links; orchestrate extraction with schema validation; bind displayed numbers to the quote; implement customer draft/export preview. First milestone: viewer and retrieval on fixtures by 11:30. Final evidence: one fully cited quote and clean customer preview.

**Jai:** own scope and milestones; define exclusions, policy/approval matrix, and offer acceptance rules; specify eight hand-priced cases; maintain golden questions and expected citations with Michael; run integration/privacy/approval checks with the engineers and report pass/total honestly; calculate the business case; draft writeup/public deck; maintain submission checklist and feedback responses. First milestone: policy, expected pricing fixture, and evaluation outline by 11:00. Final evidence: acceptance report, verified numbers, deck/writeup, accessible submission links, and receipts before Round 1.

**Michael:** translate enterprise selling experience into the rep workflow, objections, and useful commercial packages; write the concise synthetic account dossiers, service notes, competitor comparisons, and win/loss evidence from Jai/Khushi's agreed facts; validate that the customer draft is persuasive and does not expose internal reasoning; stress-test user flows and missing-information behavior; measure a controlled manual comparison; own narrative, rehearsal, and video narration. First milestone: source packet and one-page sales journey by 11:30. Final evidence: grounded knowledge corpus, usable sales output, measured workflow comparison, rehearsed under-two-minute recording.

**Pitch handoffs:** Michael opens, narrates, and closes; Luis supports the product walkthrough; Suhas operates during recording and any permitted live interaction. Q&A: forecasts/pricing code → Khushi; local/security → Suhas; retrieval/UX → Luis; policy/evaluation/submission → Jai; sales value/adoption → Michael.

## 9. Execution plan to the 17:30 Round 1 lock

| Time PT | Team gate | Parallel work and acceptance |
|---|---|---|
| Before 10:10 | Roster and rules | Register the team, complete check-in, read day-of announcement, agree ownership. Ask about finalist access after 17:30 hardware return and channel expectations. |
| 10:10–10:45 | Contracts and machine ready | Suhas: local inference/channel. Khushi: data + numerical stub. Luis: viewer/tool contracts. Jai: policy + expected fixtures. Michael: source packet and sales journey. |
| 10:45–12:00 | First vertical slice | All tools run on one shared fixture. A request produces one quote through the actual local model and engine; citations open in the viewer. |
| 12:00–13:00 | Real data replaces stubs | Baseline forecast and retrieval integrated; one exact-price deal; customer draft; missing-input and policy failures work. Lunch gate: show it end to end. |
| 13:00–14:15 | Always-on behavior | Add version-bound approval, feed watcher, quote-review event, immutable original offer, and deduplication. Michael drafts narration; Jai prepares submission/deck. |
| 14:15–15:00 | Verification and local proof | Run the evaluation set; fix failures; test disconnected workflow and allowed-channel disclosure; capture configuration and metrics. |
| 15:00 | Feature freeze | Remove weak extras; only bug fixes, evidence, and presentation afterward. |
| 15:00–16:00 | Repeatability | Three full reset-and-demo runs; verify all money; warm model; finalize clean synthetic fixture. |
| 16:00–16:45 | Record while GB10 is available | Record/edit to 1:50–1:55; finish writeup/run instructions; upload accessible repo, video, and draft deck. |
| 16:45–17:00 | Submit Round 1 early | Jai checks all fields and receipts; check-in must already be complete. Verify video and repo from judge access context. |
| 17:00–17:30 | Buffer and return | Resolve uploads before the 17:30 code lock/Round 1 deadline. Suhas returns assigned hardware as instructed. |
| 17:30–18:00 | Project deadline | Verify completeness of the 18:00 project submission and embedded feedback fields. Do not assume Round 1 can be submitted late. |
| 18:00–19:00 | Final deck and finalist prep | Finalize public deck by 19:00; rehearse three-minute demo plus two-minute Q&A. Follow organizer directions for finalist hardware/demo access. |

If the first full quote is not working by 13:00, cut local embeddings, statistical forecasting complexity, and alternative-scope UI. Keep a real cost scenario, cited sources, correct pricing, scheduled review, and a visible local workflow. Setup trouble is a mentor escalation, not a reason to hide a cloud model fallback. Freeze earlier if recording or uploads need more time.

## 10. Demo and under-two-minute video

Use one account, one bundle, and one before/after cost state. Prepare a reset that restores documents, feed, quote versions, approvals, and pending notifications. Capture the actual working GB10 workflow before hardware return. The dashboard says no screen share during live pitches, so make the submitted video and public deck self-contained and follow the organizer's finalist presentation setup.

| Video time | Beat | Evidence shown |
|---|---|---|
| 0:00–0:12 | A rep needs a defensible offer from confidential sources | Named persona, synthetic-data label, one-sentence problem |
| 0:12–0:42 | Request a quote; open the local offer/evidence pack | Actual local tool trace, $144,000 standard offer, cited reasoning |
| 0:42–1:00 | Evaluate the $136,000 concession | 15% discount, 28.24% stress margin, version-bound director approval |
| 1:00–1:25 | Show supplier update and scheduled review | New stress cost $105,600, margin 22.35%, floor $140,800, review event |
| 1:25–1:45 | Prove local operation and one disclosure control | Fresh offline calculation; minimal outbound payload or blocked disclosure |
| 1:45–1:55 | Close with actual results and buyer | Test counts, latency, workflow timing, honest limitation |

Leave at least five seconds of margin under the two-minute limit. A demo schedule may be shortened to around 15 seconds and labeled as such; do not present a manual trigger as unattended operation. If video waiting time is accelerated, label it and report actual measured latency. Keep extended technical proof in the repository/deck for Q&A.

For the **three-minute finalist demo**, expand the same arc: 20 seconds problem/buyer, 50 seconds quote/evidence, 25 seconds negotiation/approval, 35 seconds cost shock, 30 seconds local/security proof, and 20 seconds measured value/close. Then reserve the full **two minutes for Q&A**. A six-slide public deck can mirror those six beats, with appendix slides for the architecture, backtest, and test results.

Suggested opening: “A rep can win a deal and still lose margin. DealDesk Local turns private account research, company policy, and forecast delivery costs into an offer the rep can defend. Then it keeps watching the quote.”

## 11. Evaluation and business evidence

All counts below define a proposed test set; fill in actual passed/total results. Small synthetic tests are engineering evidence, not production reliability estimates.

| Area | Proposed test set / acceptance condition | Saved evidence |
|---|---|---|
| Money and policy | Eight hand-calculated cases match to the cent: normal deal, recurring costs, freight units, concession, floor above list, missing input, high-cost shock, invalid currency | Fixture inputs, expected fields, test results |
| Evidence | Ten questions: material claims supported by the right passage/version; include stale, conflicting, and absent sources | Supported/unsupported claim counts and cited passages |
| Approval | Three cases: unauthorized approver, changed quote version, expired approval all blocked | Quote/approval audit records |
| Privacy | Cross-account lookup, malicious source instruction, outside-URL disclosure, allowed-channel disclosure, customer-export leak all blocked in their tested forms | Attempt plus observed result; no universal security claim |
| Watcher | Cost update flags the affected quote; unchanged feed emits no duplicate; restart preserves cursor | Job/event log and persisted state |
| Forecast | Baseline and candidate compared by horizon with chronological cutoffs | MAE/WAPE, counts, selected method, freshness |
| Performance | Ten end-to-end runs with model/hardware/context noted | Median, slowest observed, and failures/timeouts |
| Offline | Fresh local query/calculation plus scheduled review works without internet | Recording and local audit trace |

Use a controlled manual comparison: give Michael the same synthetic packet and ask him to assemble the quote with a checklist; Jai times it, then compare with the agent-assisted workflow and disclose the method. One trial is a demonstration, not a general productivity study.

**Illustrative value model, to replace with measured assumptions:** 50 reps × 4 quotes/week × 30 minutes saved = 100 hours/week. At an assumed $75/hour loaded cost, that is $7,500/week of capacity value. It is not booked revenue or guaranteed cash savings. Quote volume, time saved, and hourly rate must appear alongside the number.

Keep margin exposure separate from labor value. The synthetic cost shock demonstrates a breach of a defined margin policy; it does not establish recovered revenue or a higher win rate. Do not train a win-probability model on invented outcomes and present its output as market validation.

## 12. Submission checklist and scope boundaries

Jai is accountable for completion and the evaluation report; Suhas verifies machine readiness/hardware return, Michael verifies sales claims and narration, Khushi verifies forecasts/numbers, and Luis verifies links and viewer behavior.

- Working local GB10 demo with a known reset and warm-up procedure.
- **Round 1 by 17:30:** code locked, repository URL, and video **under two minutes**, playable through the submitted link. Target 17:00.
- Short writeup: problem and buyer; workflow; architecture; required stack and actual versions; local/privacy controls; measured results; synthetic-data disclosure; limitations; team roles.
- **By 18:00:** all required project and embedded NVIDIA feedback fields complete; verify any additional individual form requirement.
- **By 19:00:** publicly viewable pitch deck URL. Prepare it before Round 1 because it already appears as a required submission item; do not rely on the later deadline without checking the form.
- Repository accessible to judges, run instructions, dependency/model provenance, and exact selected model names/sizes.
- Complete morning check-in before its 17:00 window ends; registered team on record; hardware returned by 17:30 as announced.
- No credentials or real sensitive company documents in public submission assets.
- One screenshot/trace for each rubric category; submitted links checked from the expected judge access context.

The dashboard currently lists 17 items. Prepare: project name; one-line pitch; repository; under-two-minute video; workflow/local execution description; DGX Spark setup experience; public pitch deck; useful/missing resources; what would speed setup; selected models and purposes; model-choice reasons; model setup process; NemoClaw/OpenShell usage; recommendation score if applicable; written feedback; security rating if applicable; and optional security-rating explanation. Answer experience questions honestly. Follow the form's conditional requirements instead of inventing feedback for a tool not used.

**Cut from this hackathon:** CRM writeback, real customer sending, voice, live competitor scraping, autonomous discount approval, automatic policy learning, many SKUs/regions/currencies, OCR-heavy ingestion, a demand-optimization model, and fine-tuning. These can follow a successful vertical slice.

**After the hackathon:** validate with sales/finance users and authorized company data; connect internal document systems; improve document-level identity and audit controls; validate forecasts on real history; evaluate pricing outcomes prospectively; cost the local deployment, maintenance, and data refresh process. The MVP is not a production enterprise security or pricing certification.

## 13. Research notes and sources

Event requirements were checked against the organizer page, not generic event aggregators. A differently named/dated Dell × NVIDIA listing with different team limits should not be substituted for this San Francisco event.

- [Signed-in event dashboard / day-of announcement](https://builderbase.com/track-dashboard/dell-x-nvidia-ai-hackathon-san-francisco/overview): directly inspected October 25, 2026; authoritative for equal 25% weights, at-least-one stack rule, under-two-minute video, 17:30 Round 1/hardware return, 18:00 project deadline, 19:00 deck/finalist pitches, and 17-item submission checklist. No account changes or submissions were made during research.
- [Organizer's public San Francisco event page](https://builderbase.com/event/dell-x-nvidia-ai-hackathon-san-francisco): general challenge/channel, eligibility and business focus. Some stack, video, and schedule details conflict with the newer announcement; those older details are not used for this plan.
- [Provided dashboard event-site view](https://builderbase.com/track-dashboard/dell-x-nvidia-ai-hackathon-san-francisco/event-site): the supplied entry point; the signed-in overview supplied the current rubric and announcement.
- [NVIDIA NemoClaw overview](https://docs.nvidia.com/nemoclaw/latest/about/overview.html): stack responsibilities and local/hosted provider support.
- [NVIDIA NemoClaw security guidance](https://docs.nvidia.com/nemoclaw/latest/security/best-practices.html): permission layers and risks of approved egress paths.
- [OpenClaw scheduled-job documentation](https://docs.openclaw.ai/automation/cron-jobs): scheduler design reference; verify behavior against the installed version.
- [Forecasting: Principles and Practice, forecaster's toolbox](https://otexts.com/fpp3/toolbox.html): baselines, chronological evaluation, prediction intervals, and forecast accuracy.
- [Khushi's exact indexed LinkedIn profile](https://in.linkedin.com/in/khushi-gangrade-data): data-science education and Python/SQL/AI training; public indexed evidence, not a full private profile review.
- [Luis's site](https://luixaviles.com/) and [GitHub](https://github.com/luixaviles): software/AI/conversational application background.
- [Suhas's portfolio source](https://github.com/suhasrahul/suhasrahul.github.io/blob/main/index.html), backing the [provided portfolio](https://suhasrahul.github.io/): local agents, homelab/container work, Telegram, and approval-agent projects. Live site access was unreliable; backing source was inspected.
- [Jai's exact indexed LinkedIn profile](https://sg.linkedin.com/in/jai-surya-gupta): business education and professional context; role assignment is a recommendation.
- [Michael's provided LinkedIn profile](https://www.linkedin.com/in/michael-g-schuck/): exact profile inspected directly in the signed-in browser; sales, partnerships, go-to-market execution, product validation, QA research, and UX testing informed the role assignment. No substitute identity was used.

The existing workspace prep files informed context but were not treated as authoritative sources. Numerical examples, demo policies, and the fictional seller are planning assumptions. Performance, security, and business-impact claims must be replaced with observed results before submission.

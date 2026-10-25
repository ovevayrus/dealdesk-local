# DealDesk Local

A local enterprise pricing agent that turns confidential company research, pricing policy, and forecast costs into a defensible sales offer.

## Status

**Working single-user chatbot demo on synthetic data.** A salesperson can ask for a price, check a concession, see cited evidence, view a supply/freight cost forecast, and apply a synthetic supplier cost increase that opens a review without changing the original quote. Pricing follows [the synthetic policy](docs/pricing-policy.md) exactly and reproduces all eight [reference cases](tests/fixtures/pricing_cases.json).

- **Tested runtime:** scripted demo mode, on Windows 11 with Python 3.13, in a browser at `http://127.0.0.1:8000`. In this mode the chat uses labeled, templated wording over the real local pricing, search, and forecast tools. It is not live model inference.
- **Live inference (OpenClaw / NemoClaw / Nemotron): not yet verified.** The [`dealdesk-local` OpenClaw skill](openclaw/skills/dealdesk-local/SKILL.md) and the local tool endpoints it calls are included and tested over HTTP. OpenClaw, NemoClaw, Nemotron, and the GB10 were not available in the development environment, so nothing here has run on that hardware.
- This is a demonstration, not an enterprise product: no authentication, no real customer data, no CRM, no customer sending, and no approval workflow ("Director approval required" is shown, not granted).

All costs, policies, customers, competitors, and forecasts are synthetic. Forecast scenarios are not calibrated probabilities.

## Problem

Enterprise sales teams struggle to combine scattered customer research, competitor analysis, pricing rules, and changing supply/delivery costs into a competitive, profitable quote they can justify. DealDesk Local recommends a price, cites its evidence, forecasts costs, and flags deals that need review while keeping sensitive data on company hardware.

## Run the demo

Requires Python 3.10 or later. From the repository root:

```sh
python -m pip install -r requirements.txt
python scripts/seed_demo_data.py --check
python -m dealdesk
```

Open **http://127.0.0.1:8000**. The server binds to loopback by default; set `DEALDESK_HOST`/`DEALDESK_PORT` in `.env` to change it (see [`.env.example`](.env.example)). On Windows, `py -3` works in place of `python`.

`seed_demo_data.py --check` confirms that the committed synthetic forecast histories match their fixed seed. Run it without `--check` to regenerate them. The knowledge pack, deal request, and cost feeds are committed files under [`data/synthetic/`](data/synthetic); nothing needs downloading.

### Demo flow

The UI is a simple chatbot: type a question (or click a suggested one) and it replies. Replies about price include number cards; every reply cites its sources.

1. Ask **Recommend a price for the demo customer.** You get $144,000.00 (10% discount), 32.22% stress margin, a $130,133.34 minimum acceptable price, and "Within representative authority", plus citations.
2. Click a citation to open the supporting passage, its document, and its section.
3. Ask **Can we offer $136,000?** You get a 15.00% discount and 28.24% stress margin. Status is **Director approval required**, and the change creates quote v2.
4. Ask **Why is this price justified?** and **What do we know about this customer and competitor?** for cited customer, service, and competitor evidence. A planted instruction in a competitor document is flagged and ignored.
5. Ask **Show the supply and delivery cost forecast.** You see history, a six-month base/high scenario, a rolling-origin backtest, and the ledger rate used for each procurement and shipment date.
6. Ask **What happens if supplier costs increase?** for a preview, then **Apply supplier cost increase**. Stress cost rises to $105,600.00, and the unchanged $136,000.00 offer falls to a 22.35% stress margin against a $140,800.00 floor. The result is blocked with review required, and the reply shows the preserved original quote beside the revised appraisal.
7. Click **Reset demo** to restore the initial feed, quote context, and chat, then repeat.

You can also ask "What is the lowest we can go?", "Can we offer 140k?", "Quote it in EUR" (rejected: USD only), or "Price a deal for Granite Peak" (blocked: missing inputs listed). "How this was calculated" under each reply lists the tool calls and assumptions.

### Reset

Use the **Reset demo** button, or with the server stopped or running:

```sh
python -m dealdesk reset
```

Reset clears quote versions, review events, chat, and dropped feeds, and restores feed `synthetic-costs-v1`. Runtime state lives in `data/runtime/` (git-ignored SQLite).

## Runtime modes

| Mode | How answers are worded | Numbers come from |
|---|---|---|
| Scripted demo mode (default, tested) | Deterministic templates, labeled "Scripted demo mode" in the header, banner, and each reply | Local pricing, search, and forecast tools |
| OpenClaw agent (intended live path, not yet verified) | Nemotron inside OpenClaw/NemoClaw, using the `dealdesk-local` skill | The same tools, called over local HTTP or the CLI; every call appears in the viewer |
| Local OpenAI-compatible endpoint (optional) | A model server you run locally, rewording the deterministic answer | The same tools; replies containing any amount or percentage not present in the tool results are replaced with scripted wording |

There is no cloud model and no cloud fallback.

### Connect OpenClaw / NemoClaw with Nemotron (on the GB10)

The model is not called by DealDesk directly. OpenClaw runs the agent with Nemotron, and the agent calls DealDesk's four named tools: `search_documents`, `price_deal`, `forecast_costs`, and `apply_demo_cost_update`.

1. Start DealDesk on the same machine: `python -m dealdesk`.
2. Copy [`openclaw/skills/dealdesk-local/`](openclaw/skills/dealdesk-local) into an OpenClaw skill root, such as `<workspace>/skills/` or `~/.agents/skills/`. These are the documented skill locations; check them against your installed OpenClaw version. The skill requires `curl`.
3. Ask the OpenClaw agent, for example, "Use dealdesk-local to check whether we can offer $136,000." The agent POSTs to `http://127.0.0.1:8000/api/tools/price_deal` with header `X-DealDesk-Caller: openclaw`.
4. Keep the chat open at `http://127.0.0.1:8000`. Each agent tool call appears in the conversation as a "Local agent tool call" with its quote cards, forecast, or citations. `GET /api/status` reports the count as `external_agent.tool_calls_observed`.

If the NemoClaw sandbox cannot reach the host's loopback address, either allow that address in the sandbox network policy or have the agent use the CLI form from a checkout of this repository:

```sh
python -m dealdesk tool price_deal '{"offer_revenue": "136000.00"}'
```

**Outstanding verification on the device:** install the skill, confirm it is loaded, confirm Nemotron is the selected local model, confirm the sandbox can reach the tools, and record a full demo run with the network disconnected. None of these steps has been performed yet.

### Optional: local OpenAI-compatible endpoint

If Nemotron or another model is also served by a local OpenAI-compatible server (for example vLLM, NIM, or Ollama), DealDesk can word its own chat replies with it. Copy `.env.example` to `.env` and set:

```sh
DEALDESK_MODE=local_model
DEALDESK_LLM_BASE_URL=http://127.0.0.1:8001/v1
DEALDESK_LLM_MODEL=<model name the server lists>
```

Only loopback, private-network, `.local`, or hosts listed in `DEALDESK_LLM_ALLOWED_HOSTS` are accepted. The header shows whether the endpoint is reachable. If the endpoint is unreachable, replies are labeled "Scripted fallback". This mode was tested only with a stubbed model in unit tests, not with a running model server.

### Scheduled watcher vs. manual update

- **Manual:** asking **Apply supplier cost increase** in the chat (or calling the `apply_demo_cost_update` tool) applies feed `synthetic-costs-v2` immediately. The review event is recorded with source `manual`.
- **Scheduled:** while the server runs, a background job checks `data/runtime/incoming_feeds/` every 5 seconds (`DEALDESK_WATCH_INTERVAL_SECONDS`). Drop the supplier feed there with:

  ```sh
  python -m dealdesk drop-supplier-feed
  ```

  The watcher applies it once and posts a "Cost update · Scheduled watcher" message into the chat. Repeated or unchanged feeds do not create duplicate events.

## Tests

```sh
python scripts/validate_pricing_fixtures.py
python -m pytest
```

The fixture validator checks the reference data independently. The pytest suite covers:

- the production pricing engine against all eight reference cases;
- exact 10%/20% authority and economic-floor boundaries, including a failing margin that displays as 25.00%;
- category rounding;
- missing, invalid, and unsupported-currency inputs;
- quote expiry with an injected clock;
- date-based rate selection;
- forecast reproducibility and leakage;
- document retrieval of real passages, account filtering, and the flagged planted instruction;
- cost-shock preservation, watcher deduplication, and reset;
- the chatbot API using real tool outputs;
- the number guard for local-model wording;
- refusal of cloud endpoints.

GitHub Actions runs the same commands ([`.github/workflows/tests.yml`](.github/workflows/tests.yml)).

## How it works

```text
Browser chat (plain HTML/CSS/JS)          OpenClaw agent + Nemotron (on device, not yet verified)
        │ POST /api/chat                           │ POST /api/tools/<name>  or  python -m dealdesk tool
        ▼                                          ▼
 Bounded agent: intent → tools → structured results + evidence → explanation
        │
        ├── price_deal ............ dealdesk/pricing.py (Decimal, policy synthetic-demo-v1)
        ├── search_documents ...... dealdesk/documents.py (BM25 over data/synthetic/documents + pricing policy)
        ├── forecast_costs ........ dealdesk/forecast.py (last-value / seasonal-naive, rolling-origin backtest)
        └── apply_demo_cost_update  dealdesk/tools.py (new feed → separate appraisal + review event)
        │
 SQLite state (data/runtime): immutable quote versions, review events, chat, watcher cursor
```

- **Numbers:** every amount and percentage in a card is rendered from a structured field returned by the pricing engine. The language model, when used, only words the explanation.
- **Evidence:** answers separate "From documents" (cited facts), "Calculated by local tools", "Assumptions", and "Missing or unconfirmed information". Document text is evidence, never instructions.
- **Quote versions:** a changed price or cost feed creates a new version. A new cost feed never rewrites an existing version; it adds a revised appraisal and a review event.
- **Forecast:** 36 months of synthetic history from a fixed seed. Each series is tied to the quote line's procurement or shipment date and shown next to the ledger rate actually used. The high scenario applies the active feed's named stress uplift.

## Limitations

- Single user, no authentication, loopback only. Not for real customer data.
- One reference deal (SYN-REFERENCE-001). The other two accounts have profiles but no deal requests, so pricing them reports missing inputs.
- Intent routing is rule-based. Unusual phrasings fall back to document search or a "documents do not answer" reply.
- Supports USD, `standard_upfront` terms, and whole service months only. Director approval is displayed, not executed. There is no customer-facing export or sending.
- The forecast demonstrates the pipeline on synthetic data, not real market predictive ability.
- OpenClaw/NemoClaw/Nemotron integration and GB10 execution have not been verified.

## Team and tasks

| Person | Exact task |
|---|---|
| **Suhas** | Run the local model and OpenClaw on the GB10. Connect the tools and build the scheduled cost-change watcher. |
| **Khushi** | Create synthetic cost data. Build forecasting and pricing functions that return costs, recommended price, margin, and minimum acceptable price. |
| **Luis** | Build document search with citations and the local interface showing the quote, cost breakdown, sources, and approval status. |
| **Jai** | Write discount, margin, and approval rules. Hand-calculate a reference quote, verify the system's results, and own the deck and submission. |
| **Michael** | Write three customer profiles, two competitor comparisons, and service descriptions. Define realistic sales questions, test the workflow, and write/narrate the demo. |

See [team tasks and finish lines](TEAM_TASKS.md) for the first deliverable from each person.

## Project documents

- [Detailed project brief](dealdesk-project-brief.md): rubric mapping, architecture, pricing math, forecasts, security boundaries, schedule, evaluation, and demo.
- [Offline HTML brief](dealdesk-project-brief.html): download and open locally for a formatted version.
- [Synthetic pricing policy](docs/pricing-policy.md): required inputs, cost calculations, rounding, margin floors, and approval/release rules.
- [Pricing reference cases](tests/fixtures/pricing_cases.json): eight self-contained synthetic deals with independently calculated expected outputs.
- [Pricing acceptance criteria](docs/acceptance-criteria.md): fixture checks and application checks.
- [Current hackathon dashboard](https://builderbase.com/track-dashboard/dell-x-nvidia-ai-hackathon-san-francisco/overview): sign-in required; check current organizer announcements.

## Validate pricing reference data

The fixture validator uses only the standard library and is independent of the application code:

```sh
python scripts/validate_pricing_fixtures.py
```

It prints each case's result and exits nonzero on failure. The production engine in `dealdesk/pricing.py` is a separate implementation tested against the same fixtures.

## Data handling

- Keep real internal documents, customer information, credentials, and model weights out of this public repository.
- Commit only synthetic or explicitly cleared demonstration data.
- Run inference and sensitive processing locally; calculate money and enforce policy in code.
- Keep internal cost/margin evidence separate from customer-facing output and outbound notifications.

## Hackathon checkpoints

The day-of dashboard specifies four equally weighted criteria: technical execution, usefulness/business value, local-first design, and demo quality.

- **17:30 PT:** Round 1 code lock, repository and video under two minutes; hardware return.
- **18:00 PT:** Project submission deadline.
- **19:00 PT:** Public pitch deck deadline and finalist pitches; three-minute demo plus two-minute Q&A.

Check the organizer dashboard for subsequent changes. Build the implementation on the day in accordance with the event rules.

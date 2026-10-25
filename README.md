# DealDesk Local

**A local AI assistant that helps enterprise sales teams recommend a price, explain it, and understand the risks behind it.**

DealDesk Local brings together a company's confidential customer research, competitor analysis, service information, pricing policies, and cost forecasts. Through a simple chatbot, a salesperson can ask what to offer, inspect the supporting evidence, and see how a discount or cost change affects the deal. The design keeps inference and sensitive processing on company-controlled hardware.

**[Read the detailed project brief](dealdesk-project-brief.md)** · [Team tasks](TEAM_TASKS.md) · [Download the offline HTML brief](dealdesk-project-brief.html)

## The pain points

Enterprise pricing is rarely just a price-book lookup. The information needed to make a good decision is spread across internal documents, spreadsheets, account notes, and different teams.

| Pain point | What DealDesk Local is designed to do |
|---|---|
| **Scattered customer and competitor research** | Find relevant internal evidence and cite the passages supporting a recommendation. |
| **Slow, manual quote preparation** | Bring deal requirements, service scope, cost assumptions, and pricing rules into one conversational workflow. |
| **Discounts that erode margin** | Calculate the minimum acceptable price and show when a proposed concession needs approval. |
| **Changing supply and delivery costs** | Forecast relevant costs, show base/stress scenarios, and flag open quotes when assumptions change. |
| **Prices that are difficult to justify** | Explain the offer using customer priorities, service value, delivery commitments, and documented evidence. |
| **Sensitive research and cost information** | Keep the model and sensitive tools local, with internal rationale separated from customer-facing output. |

## What our model will do

The language model will interpret the salesperson's question, identify missing deal information, retrieve relevant company knowledge, call local tools, and explain the results in clear language.

Dedicated pricing code will calculate costs, discounts, margins, and price floors. Forecasting tools will supply dated cost estimates and explicitly labeled scenarios. The model will explain these calculations; it will not invent authoritative prices or replace the numerical pricing engine.

The chatbot is designed to answer questions such as:

> “What should we offer this customer, and why is that price justified?”
>
> “Can we offer $136,000 without violating our margin policy?”
>
> “What happens to this quote if supplier or delivery costs increase?”

Each answer should combine the relevant parts of:

- A recommended offer and a feasible negotiation range.
- A cost breakdown, projected margin, and minimum acceptable price.
- Policy warnings and any required approval.
- Customer/competitor evidence with source citations.
- A customer-facing explanation that excludes confidential cost and margin information.

## How the demo works

1. **Ask:** enter a deal or choose a suggested question in the chatbot.
2. **Find evidence:** retrieve the relevant customer profile, competitor comparison, service description, and company policy.
3. **Calculate:** use local tools to forecast costs and evaluate the offer against the margin and discount rules.
4. **Explain:** show readable pricing cards, a concise justification, and clickable source passages.
5. **Explore a change:** propose a discount or apply a synthetic cost increase, then inspect the revised appraisal while preserving the original quote.

For example, the synthetic reference deal includes a $136,000 offer with a 28.24% stress-case margin. A supplier-cost update raises stress costs to $105,600, reducing that margin to 22.35% and moving the economic floor to $140,800. The demo flags the quote for review and explains which assumption changed.

These are hand-calculated demonstration values, not measured customer savings or a claim that a buyer will accept the revised price.

## Current scope and status

**Working single-user chatbot demo on synthetic data.** You can ask for a price, check a concession, see cited evidence, view a supply/freight cost forecast, and apply a synthetic supplier cost increase. The increase opens a review without changing the original quote. Pricing follows [the synthetic policy](docs/pricing-policy.md) exactly and reproduces all eight [reference cases](tests/fixtures/pricing_cases.json).

- **Tested runtime:** scripted demo mode on Windows 11 with Python 3.13, used in a browser at `http://127.0.0.1:8000`. In this mode the chat uses labeled, templated wording over the real local pricing, search, and forecast tools. It is not live model inference.
- **Live inference on the GB10 (verified 2026-10-25):** Dell Pro Max GB10 (Ubuntu 24.04.5, NVIDIA driver 580.178.04, CUDA 13.0), Python 3.12.3, `pytest` 78 passed. The model is **`nvidia/Qwen3.6-35B-A3B-NVFP4`** served by **vLLM 0.21.0** (`nvcr.io/nvidia/vllm:26.05.post1-py3`) on `127.0.0.1:8001` ([`scripts/start_qwen.sh`](scripts/start_qwen.sh)). **OpenClaw 2026.9.34** (Node.js 24.22.1) runs the [`dealdesk-local` skill](openclaw/skills/dealdesk-local/SKILL.md) against that model only (`models.mode: "replace"`, no fallbacks, telemetry off). Asking the agent "check whether we can offer $136,000" takes **about 16 s** end to end (15.7 s measured), calls `price_deal`, and every figure in the answer matches a tool field. The app's chat also runs in local-model mode against the same server. Configuration and network captures are in [`proof/`](proof).
- **Not used:** Nemotron (Qwen3.6 is the agent model; Nemotron 3 Nano 4B is on the device as an unused fallback) and NemoClaw (OpenClaw runs with `--local`, no sandbox). **Still to do:** the full demo with networking turned off ([`proof/OFFLINE_TEST.md`](proof/OFFLINE_TEST.md)).
- The scope covers one enterprise bundle, a small local document collection, USD pricing, simple forecasts, and one cost-change example. It does not include production authentication, real customer data, CRM connections, automatic customer sending, or an approval workflow ("Director approval required" is shown, not granted).

All costs, policies, customers, competitors, and forecasts are synthetic. Forecast scenarios are not calibrated probabilities.

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

The UI is a simple chatbot: type a question (or click a suggested one) and it replies. Replies about price include number cards, and replies that draw on the documents cite the passages they used.

1. Ask **Recommend a price for the demo customer.** You get $144,000.00 (10% discount), 32.22% stress margin, a $130,133.34 minimum acceptable price, and "Within representative authority", plus citations.
2. Click a citation to open the supporting passage, its document, and its section.
3. Ask **Can we offer $136,000?** You get a 15.00% discount and 28.24% stress margin. Status is **Director approval required**, and the change creates quote v2.
4. Ask **Why is this price justified?** and **What do we know about this customer and competitor?** for cited customer, service, and competitor evidence. A planted instruction in a competitor document is flagged and ignored.
5. Ask **Show the supply and delivery cost forecast.** You see history, a six-month base/high scenario, a rolling-origin backtest, and the ledger rate used for each procurement and shipment date.
6. Ask **What happens if supplier costs increase?** for a preview, then **Apply supplier cost increase**. Stress cost rises to $105,600.00, and the unchanged $136,000.00 offer falls to a 22.35% stress margin against a $140,800.00 floor. The result is blocked with review required, and the reply shows the preserved original quote beside the revised appraisal. Follow-up questions then use the revised economics.
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
| Scripted demo mode (default, tested) | Deterministic templates, labeled "Scripted demo mode" in the header and on each reply | Local pricing, search, and forecast tools |
| OpenClaw agent (live path, verified on the GB10) | Qwen3.6-35B-A3B-NVFP4 on local vLLM, inside OpenClaw 2026.9.34, using the `dealdesk-local` skill | The same tools, called over local HTTP or the CLI; every call appears in the chat |
| Local OpenAI-compatible endpoint (optional) | A model server you run locally, rewording the deterministic answer | The same tools; replies containing any amount or percentage not present in the tool results are replaced with scripted wording |

There is no cloud model and no cloud fallback.

### Connect OpenClaw to the local model (on the GB10)

DealDesk does not call the model directly. OpenClaw runs the agent with the local model (Qwen3.6-35B-A3B-NVFP4 on vLLM; see [`proof/openclaw.json`](proof/openclaw.json)), and the agent calls DealDesk's four named tools: `search_documents`, `price_deal`, `forecast_costs`, and `apply_demo_cost_update`.

1. Start DealDesk on the same machine: `python -m dealdesk`.
2. Copy [`openclaw/skills/dealdesk-local/`](openclaw/skills/dealdesk-local) into an OpenClaw skill root, such as `<workspace>/skills/` or `~/.agents/skills/`. These are the documented skill locations; check them against your installed OpenClaw version. The skill requires `curl`.
3. Ask the OpenClaw agent, for example, "Use dealdesk-local to check whether we can offer $136,000." The agent POSTs to `http://127.0.0.1:8000/api/tools/price_deal` with header `X-DealDesk-Caller: openclaw`.
4. Keep the chat open at `http://127.0.0.1:8000`. Each agent tool call appears in the conversation as a "Local agent tool call" with its quote cards, forecast, or citations. `GET /api/status` reports the count as `external_agent.tool_calls_observed`.

If the NemoClaw sandbox cannot reach the host's loopback address, either allow that address in the sandbox network policy or have the agent use the CLI form from a checkout of this repository:

```sh
python -m dealdesk tool price_deal '{"offer_revenue": "136000.00"}'
```

**Verified on the device (2026-10-25):** the skill is installed in `~/.openclaw/workspace/skills/` and `openclaw skills info dealdesk-local` reports Ready; `openclaw models list` shows only `vllm-local/qwen3.6-35b-a3b`; the agent reaches the tools at `127.0.0.1:8000` over curl (no sandbox, so no network policy was needed); `/api/status` reports `last_caller: openclaw`. A connection capture during a question is in [`proof/NETWORK_SUMMARY.md`](proof/NETWORK_SUMMARY.md). **Still outstanding:** a full demo run with networking turned off ([`proof/OFFLINE_TEST.md`](proof/OFFLINE_TEST.md)), and running under NemoClaw or with Nemotron (neither has been tried).

### Optional: local OpenAI-compatible endpoint

If a model is also served by a local OpenAI-compatible server (for example vLLM, NIM, or Ollama), DealDesk can word its own chat replies with it. Copy `.env.example` to `.env` and set:

```sh
DEALDESK_MODE=local_model
DEALDESK_LLM_BASE_URL=http://127.0.0.1:8001/v1
DEALDESK_LLM_MODEL=<model name the server lists>
```

Only loopback, private-network, `.local`, or hosts listed in `DEALDESK_LLM_ALLOWED_HOSTS` are accepted; redirects and system proxies are refused. The header shows whether the endpoint is reachable. If the endpoint is unreachable, replies are labeled "Scripted fallback". On the GB10 this mode runs against vLLM serving `qwen3.6-35b-a3b` ("Can we offer $136,000?" returns `mode: local_model`). DealDesk sends `enable_thinking: false` so the reasoning model does not spend its token budget thinking.

### Scheduled watcher vs. manual update

- **Manual:** asking **Apply supplier cost increase** in the chat (or calling the `apply_demo_cost_update` tool) applies feed `synthetic-costs-v2` immediately. The review event is recorded with source `manual`.
- **Scheduled:** while the server runs, a background job checks `data/runtime/incoming_feeds/` every 5 seconds (`DEALDESK_WATCH_INTERVAL_SECONDS`). Drop the supplier feed there with:

  ```sh
  python -m dealdesk drop-supplier-feed
  ```

  The watcher applies it once and posts a "Cost update · Scheduled watcher" message into the chat. Repeated or unchanged feeds do not create duplicate events. A malformed file is skipped and retried once it is corrected.

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
- cost-shock preservation, scope checks, watcher deduplication and retry, and reset;
- the chatbot API using real tool outputs;
- the number guard for local-model wording;
- refusal of cloud endpoints and redirects.

GitHub Actions runs the same commands ([`.github/workflows/tests.yml`](.github/workflows/tests.yml)).

## How it works

```text
Browser chat (plain HTML/CSS/JS)          OpenClaw agent + Qwen3.6 on vLLM (GB10)
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
- Verified on the GB10 with OpenClaw and Qwen3.6 on local vLLM only. NemoClaw, Nemotron, and a run with networking turned off have not been tested.

## Team and tasks

| Person | Task |
|---|---|
| **Suhas** | Run the local model and OpenClaw on the GB10, connect the tools, and add cost-change monitoring. |
| **Khushi** | Build synthetic cost data, forecasting, and the numerical pricing engine. |
| **Luis** | Build the chatbot, local document search, citations, and pricing-result interface. |
| **Jai** | Define pricing policy and expected results, verify the integrated behavior, and coordinate integration. |
| **Michael** | Prepare synthetic customer/competitor/service documents, realistic sales questions, and workflow checks. |

See [team tasks and finish lines](TEAM_TASKS.md) and the [full project brief](dealdesk-project-brief.md) for detailed responsibilities.

## Project documents

- [Detailed project brief](dealdesk-project-brief.md): problem, architecture, pricing math, forecasts, local-data boundaries, evaluation, and planned workflow.
- [Offline HTML brief](dealdesk-project-brief.html): download and open locally for a formatted version.
- [Team tasks](TEAM_TASKS.md): starting deliverables and the shared integration milestone.
- [Synthetic pricing policy](docs/pricing-policy.md): required inputs, cost calculations, rounding, margin floors, and approval/release rules.
- [Pricing reference cases](tests/fixtures/pricing_cases.json): eight self-contained synthetic deals with independently calculated expected outputs.
- [Pricing acceptance criteria](docs/acceptance-criteria.md): fixture checks and application checks.
- [Hackathon dashboard](https://builderbase.com/track-dashboard/dell-x-nvidia-ai-hackathon-san-francisco/overview): current organizer requirements and announcements; sign-in required.

## Validate pricing reference data

The fixture validator uses only the standard library and is independent of the application code:

```sh
python scripts/validate_pricing_fixtures.py
```

It prints each case's result and exits nonzero on failure. The production engine in `dealdesk/pricing.py` is a separate implementation tested against the same fixtures.

## Data handling

- Commit only synthetic or explicitly cleared demonstration data to this public repository.
- Keep real internal documents, customer information, credentials, and model weights out of Git.
- Run inference and sensitive processing locally, and enforce numerical pricing rules in code.
- Keep internal costs, margins, and restricted source passages out of customer-facing output and outbound notifications.

## Hackathon checkpoints

Built for the Dell × NVIDIA AI Hackathon, San Francisco, October 25, 2026. The day-of dashboard specifies four equally weighted criteria: technical execution, usefulness/business value, local-first design, and demo quality.

- **17:30 PT:** Round 1 code lock, repository and video under two minutes; hardware return.
- **18:00 PT:** Project submission deadline.
- **19:00 PT:** Public pitch deck deadline and finalist pitches; three-minute demo plus two-minute Q&A.

Check the organizer dashboard for subsequent changes. Follow the event's build-on-the-day and local-inference rules.

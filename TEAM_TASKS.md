# Starting tasks

## Suhas — local agent platform and automation

- Get OpenClaw and a local model running on the GB10.
- Define how the agent calls the document, forecast, and pricing tools.
- Add a scheduled job that detects a new local cost feed and flags affected open quotes.

**First deliverable:** one local request calls a mock pricing tool and returns its result.

## Khushi — forecasting and numerical pricing

- Create a small, reproducible synthetic supply/freight dataset.
- Implement a baseline forecast and a dated cost ledger.
- Return expected/stress costs, recommended price, margin, minimum acceptable price, and policy warnings as structured JSON.

**First deliverable:** one quote matches Jai's hand-calculated reference to the cent. Add forecast complexity after this works.

## Luis — document intelligence and local interface

- Index Michael's synthetic documents and return citations with each relevant passage.
- Build the local quote view: offer, costs, evidence, and approval status.
- Render numeric values directly from Khushi's structured outputs.

**First deliverable:** a local page shows one quote and opens the source passages that support it.

## Jai — policy, verification, and submission

- Write the synthetic discount, margin-floor, and approval rules.
- Hand-calculate the reference quote and expected cost-shock result.
- Maintain acceptance checks, the public deck, and the submission checklist.

**First deliverable:** one-page policy plus the expected inputs/outputs for the shared reference quote.

## Michael — sales workflow, corpus, and demo

- Write three fictional customer profiles, two competitor comparisons, and the seller's service descriptions.
- Define realistic sales questions and negotiation objections for the agent to answer.
- Test the workflow as a salesperson and write/narrate the under-two-minute demo.

**First deliverable:** the synthetic document packet and one complete sales request for the demo account.

## Shared integration gate

Agree the request, evidence, forecast, and quote JSON shapes before building separately. Use the same account, bundle, quantities, dates, currency, and policy in every fixture. The first milestone is one complete local quote with correct arithmetic and working citations.

Full scope, example numbers, deadlines, and acceptance criteria: [project brief](dealdesk-project-brief.md).

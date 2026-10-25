# DealDesk Local

A local enterprise pricing agent that turns confidential company research, pricing policy, and forecast costs into a defensible sales offer.

## Problem

Enterprise sales teams struggle to combine scattered customer research, competitor analysis, pricing rules, and changing supply/delivery costs into a competitive, profitable quote they can justify. DealDesk Local recommends a price, cites its evidence, forecasts costs, and flags deals that need review while keeping sensitive data on company hardware.

## Planned workflow

1. A salesperson describes an enterprise deal.
2. The agent retrieves authorized internal documents and cites the relevant evidence.
3. Local forecasting and deterministic pricing functions calculate costs, margins, and feasible offers.
4. The salesperson reviews a recommendation and a separate customer-facing explanation.
5. Authorized managers approve concessions for a specific quote version.
6. A scheduled watcher flags open quotes affected by changing cost assumptions.

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
- [Pricing acceptance criteria](docs/acceptance-criteria.md): fixture checks available now and application checks required after integration.
- [Current hackathon dashboard](https://builderbase.com/track-dashboard/dell-x-nvidia-ai-hackathon-san-francisco/overview): sign-in required; check current organizer announcements.

## Validate pricing reference data

Run with Python 3.9 or later from the repository root; only the standard library is needed, with no application code, network, or third-party packages:

```sh
python scripts/validate_pricing_fixtures.py
```

On Windows, `py -3 scripts/validate_pricing_fixtures.py` also works when Python is installed through the launcher. The validator prints each case's result and exits nonzero on failure. It verifies reference data, not the integrated application; see the acceptance criteria for approval, watcher, and customer-output checks that remain.

## Status

Planning repository with a standalone pricing policy and reference-data validator for the Dell × NVIDIA AI Hackathon, San Francisco, October 25, 2026. The application is not implemented yet. There are no application setup or run commands at this stage.

All sample costs, policies, customers, and competitor scenarios in the brief are synthetic. Forecasts, performance targets, and proposed controls are plans rather than measured results.

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

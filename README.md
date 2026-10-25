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

## How the demo will work

1. **Ask:** enter a deal or choose a suggested question in the chatbot.
2. **Find evidence:** retrieve the relevant customer profile, competitor comparison, service description, and company policy.
3. **Calculate:** use local tools to forecast costs and evaluate the offer against the margin and discount rules.
4. **Explain:** show readable pricing cards, a concise justification, and clickable source passages.
5. **Explore a change:** propose a discount or apply a synthetic cost increase, then inspect the revised appraisal while preserving the original quote.

For example, the synthetic reference deal includes a $136,000 offer with a 28.24% stress-case margin. A supplier-cost update raises stress costs to $105,600, reducing that margin to 22.35% and moving the economic floor to $140,800. The demo should flag the quote for review and explain which assumption changed.

These are hand-calculated demonstration values, not measured customer savings or a claim that a buyer will accept the revised price.

## Current scope and status

We are building a working, single-user chatbot demo using synthetic customers, competitors, costs, and policies. The public default branch currently contains the project plan and detailed brief; application development is being carried out in feature branches. This README describes the intended demo behavior, not a completed production system or verified hardware deployment.

The initial implementation focuses on one enterprise bundle, a small local document collection, USD pricing, simple forecasts, and a clear cost-change example. Production authentication, real CRM connections, and automatic customer sending are outside this demo's scope.

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
- [Hackathon dashboard](https://builderbase.com/track-dashboard/dell-x-nvidia-ai-hackathon-san-francisco/overview): current organizer requirements and announcements; sign-in required.

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

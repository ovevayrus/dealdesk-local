# Synthetic demonstration pricing policy

Policy ID: `synthetic-demo-v1`. These are **synthetic demonstration policies, not real company policy**. They define the reference calculations for DealDesk Local's MVP.

## Required inputs and scope

- Quote ID and version, policy version, account/bundle scope, currency, list contract revenue, proposed contract revenue, payment terms, and quote expiry.
- Delivery date; actual procurement date for hardware, shipment date for freight, installation date, and service start date. Cost-feed version and cost as-of date identify the assumptions used. Retain the source/effective date of each material rate in the integrated ledger.
- Hardware units and USD/unit; shipment count and USD/shipment; installation hours and loaded USD/hour; active service units, USD/unit/month, and applicable whole months.
- Separate base and **named joint stress scenario** rates for the same scope and dates. Rates must already be selected for actual cost-incurrence dates; these fixtures do not forecast rates. Hardware purchased once is costed on its actual procurement date, not averaged across a service term. Freight uses its shipment date.

The MVP accepts USD only, a `standard_upfront` payment schedule, and whole service months without proration. The shared example uses twelve months. Taxes, FX, financing, returns, and complex working-capital effects are excluded. Nonstandard terms require clarification and prevent release until represented by a supported, explicitly costed quote.

Money and rates are decimal strings, never binary floating-point values. List and offer revenue must be positive exact cents, and offer revenue must not exceed list revenue. Costs must be nonnegative. Monetary strings have two to six fractional places; expected monetary outputs have exactly two. Hardware units, shipments, active units, and months are positive integers; installation hours are positive decimal strings. Missing, malformed, negative, or inconsistent critical inputs prevent release; do not invent a date, rate, zero cost, currency, or exchange rate.

In the fixture document, the top-level `policy.id` applies to all cases; `units.money` refers to each case's `inputs.currency`. Unit-cost fields are per hardware unit, freight rates per shipment, loaded rates per hour, and service rates per active unit per month. Each case repeats its complete deal and cost inputs so it can be used independently with this policy. The validator deliberately limits counts to 1,000,000 and decimal input strings to 24 characters for this small reference dataset; these are validator bounds, not approved commercial limits.

## Calculation order and rounding

1. Reject an unsupported currency before calculating USD outputs. Check required inputs, their types, units, dates, and supported terms. Return the names of missing inputs or clear invalid-input messages.
2. Construct the base ledger and the separate named stress ledger using `Decimal` throughout:

   ```text
   hardware = sum(procured units × USD/unit on each actual procurement date)
   freight = sum(shipment count × USD/shipment on each shipment date)
   installation = sum(hours × loaded USD/hour)
   service = sum(active units × USD/unit/month × applicable whole months)
   total_cost = hardware + freight + installation + service
   reserve = stress_total - base_total
   ```

   Sum unrounded line products within each category, then round each category once to cents with `ROUND_HALF_UP`. Sum those four rounded category amounts to obtain the authoritative ledger total. Never add `reserve` to the stress total again. Service appears exactly once. Changing active units or rates requires separate service periods; shipments remain distinct from hardware quantity.
3. Calculate economics using those ledger totals:

   ```text
   discount = (list_revenue - offer_revenue) / list_revenue
   stress_gross_margin = (offer_revenue - stress_total) / offer_revenue
   economic_floor = ceil_to_cent(stress_total / (1 - 0.25))
   ```

   The minimum permitted gross margin is **25%, evaluated against stress cost**. Gross margin divides profit by revenue; markup divides profit by cost. They are different measures and must not be substituted.
4. Enforce constraints before rounding percentages for display. Check margin using `offer_revenue × 0.75 >= stress_total`; check a discount limit `d` using `list_revenue - offer_revenue <= list_revenue × d`. These multiplication checks avoid rounding a recurring quotient at a policy boundary. Use sufficient Decimal precision to preserve the input products and sums. Round only displayed percentages to two decimal places with `ROUND_HALF_UP`. Round the economic floor **up** to the next cent with `ROUND_CEILING`, retaining a value already on an exact cent.
5. Apply the release and approval decisions below. A price is feasible only if it satisfies both economics and authority. For a role's maximum discount `d`, its lowest authorized offer is `max(economic_floor, list_revenue × (1 - d))`, rounded upward to cents if needed. Never lower the economic floor to fit list revenue.

## Approval and release outcomes

Evaluate in this order; retain all applicable warnings, including cost-review status:

| Condition | Outcome | Release |
|---|---|---|
| Currency is not USD | `unsupported_currency`; no numeric USD appraisal | Blocked |
| Critical information is missing or invalid | `missing_critical_input` with `missing_inputs`, or a field-specific invalid-input error | Blocked |
| Economic floor exceeds list revenue | `infeasible_under_current_terms`: “infeasible under current terms” | Blocked |
| Offer fails the 25% stress-margin floor | `below_margin_floor` | Blocked |
| Discount exceeds 20% | `discount_exceeds_director_authority` | Blocked |
| Discount is greater than 10% and at most 20% | `director_approval_required` | Blocked until valid director approval |
| Discount is from 0% through 10%, inclusive | `representative_authority` | Eligible for human release |

Both authority limits are inclusive: representatives may approve up to 10%, and sales directors up to 20%, only while the margin floor is satisfied. Below-floor offers are blocked; finance exceptions are outside this implementation. Customer or competitor research cannot override these gates. Premiums above list are outside this demonstration's supported inputs.

`release_allowed` means eligible for a person's release action, never automatic sending. An authorized director's approval can satisfy the pending approval requirement, but cannot bypass a missing input, unsupported currency, infeasible deal, margin violation, cost-review hold, or quote expiry.

## Quote versions and cost changes

An approval applies to one quote ID/version and its exact terms, policy, cost assumptions, approving identity/role, and expiry. Any change to price, scope, quantities, dates, terms, or assumptions requires a new version and fresh approval. Expired quotes or approvals cannot be released. Preserve the original quote and approval in history.

A new cost feed adds a separate appraisal and sets `review_required`; it blocks release until reviewed even when the new economics pass. It never silently rewrites an existing offer, its original assumptions, or its historical approval. A proposed response uses a new quote version. The watcher and durable approval checks belong to the integrated application; fixture assertions describe the required behavior.

## Shared reference and output boundary

The synthetic reference has list revenue of $160,000. Base costs are $60,000 hardware, $2,000 freight, $4,000 installation, and $24,000 service: **$90,000 total**. The named stress costs are $66,000, $2,400, $4,000, and $25,200: **$97,600 total**. The $7,600 reserve is already included in that stress total.

The initial economic floor is **$130,133.34**. A $144,000 offer gives a 10% discount and **32.22%** displayed stress margin. A $136,000 offer gives a 15% discount and **28.24%** displayed stress margin, requiring director approval. At a new $105,600 stress cost, the unchanged $136,000 offer has **22.35%** displayed margin and a **$140,800.00** floor; review is required and release is blocked. With $130,000 stress cost, the **$173,333.34** floor exceeds list revenue and the deal is infeasible under current terms.

Internal output includes the ledgers, assumptions, margins, floor, provenance, and approval/review reasons. Customer-facing output contains approved scope, price, service/delivery commitments, and validity only. It excludes internal costs, margins, restricted research, and unapproved claims. Human review is required before export or sending.

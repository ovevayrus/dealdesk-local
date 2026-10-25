# Pricing acceptance criteria

These checks evaluate **synthetic demonstration policies and data, not real company policy**. The [pricing policy](pricing-policy.md) defines the rules; [reference cases](../tests/fixtures/pricing_cases.json) supply independently calculated expectations.

## Fixture validator: checks available now

Run from the repository root with Python's standard library:

```sh
python scripts/validate_pricing_fixtures.py
```

The command must print a readable result for every case, report eight passing cases, and exit zero. A failure must exit nonzero. These are reference-data checks; a passing result does not establish application behavior.

- [ ] All eight required cases have unique IDs, a purpose, synthetic inputs, expected outcomes, and a calculation explanation. Money is represented as decimal strings with explicit currency and units.
- [ ] Base hardware is 100 × $600 = $60,000; freight is 2 × $1,000 = $2,000; installation is 40 × $100 = $4,000; service is 100 × $20 × 12 = $24,000. The $90,000 total counts each category once.
- [ ] Named stress category amounts total $97,600. The $7,600 reserve is not added a second time. The initial economic floor rounds upward to $130,133.34.
- [ ] The standard $144,000 offer has a 10% discount, 32.22% displayed stress margin, representative authority, and eligibility for human release.
- [ ] The negotiated $136,000 offer has a 15% discount and 28.24% displayed stress margin. Its expected outcome requires director approval and blocks release while approval is pending.
- [ ] The cost shock leaves the offer at $136,000, evaluates $105,600 stress cost, displays 22.35% margin, and calculates a $140,800.00 floor. Its expected outcome requires review and blocks release. The fixture retains the original quote snapshot.
- [ ] The $130,000 stress-cost case returns a $173,333.34 floor above $160,000 list revenue and an infeasible outcome; the floor is not clamped downward.
- [ ] Missing delivery date identifies the missing input and blocks release. EUR is explicitly unsupported and produces no numeric USD appraisal or fabricated exchange rate.
- [ ] Arithmetic uses `Decimal`; component totals follow the documented cent-rounding rule. Approval and margin gates use unrounded comparisons; displayed percentages use two-decimal `ROUND_HALF_UP` rounding.

## Integrated application: checks required later

Record observed results and evidence for these checks when the application exists. Do not mark them passed from fixture validation alone.

- [ ] Khushi's pricing outputs match every applicable reference amount, percentage, and outcome. Luis's interface renders the corresponding structured fields directly, including correct labels and units.
- [ ] Procurement, shipment, installation, and service dates select the correct rates. Each material rate has a source, effective date, and feed version. Multiple dates/periods, changing active service counts, and different shipment quantities do not create averaging or double-counting errors.
- [ ] Representative and director limits are inclusive at exactly 10% and 20%. Above 10% requires director approval; above 20% blocks release. A director cannot approve a below-floor or infeasible offer.
- [ ] Test exact economic-floor cents, one cent below/above, and a margin just below 25% that displays as 25.00%. Display rounding must never turn a failing offer into a passing one. Test fractional rates/hours and category rounding separately.
- [ ] Every missing, malformed, negative, or inconsistent critical input prevents release with a clear field-specific reason. Unsupported currencies, premiums above list, nonstandard payment terms, and expired quotes are handled explicitly.
- [ ] Approver identity and role are checked. Approval binds to the quote ID/version and exact terms, assumptions, policy, and expiry; it cannot authorize another quote. Unauthorized, expired, revoked, or stale approvals block release.
- [ ] Changing price, quantity, scope, schedule, terms, or assumptions creates a new version and requires fresh approval. Historical versions and approval records remain accessible.
- [ ] A new feed flags affected open quotes for review without changing the original offer, assumptions, or historical approval. The cost-shock reference produces a release hold and a separate revised appraisal.
- [ ] A feed that leaves economics compliant still requires review. Repeated unchanged feeds do not duplicate review events; restart preserves the watcher cursor and pending review state.
- [ ] Human review/release remains explicit. Eligible status cannot trigger automatic customer sending or bypass approval/review holds.
- [ ] Internal views enforce access to costs, margins, assumptions, and restricted research. Customer preview/export excludes those fields and unapproved claims, including through error text, hidden metadata, attachments, and copied explanations.
- [ ] Saved evidence identifies the tested quote/version, policy/feed versions, actor, action, timestamp, and observed outcome without exposing credentials or real customer data.

Team decisions before broader use: confirm the demonstration's whole-month service convention, `standard_upfront` terms, category-rounding rule, freshness requirements, and quote/approval expiry durations. The reference values remain fixed until a reviewed policy/fixture version changes them.

# Trova pricing

## The rate

**Creators keep 85%. Trova takes 15%** of affiliate commission earned through
their storefronts.

**Founding creators keep 100%, permanently.** The first 10 creators onboarded
pay nothing, for as long as they use Trova. This is not a trial and does not
expire.

## How it compares

| Platform | Creator keeps |
| --- | --- |
| LTK | 70–80% |
| Howl / Levanta | 75–80% |
| **Trova** | **85%** |
| **Trova founding creators** | **100%** |

Best rate in the category. That is the pitch, and it should stay true.

## Why 15% and not lower

Commission per booking is small, so the percentage has to carry real weight:

| Product | Commission | Per booking |
| --- | --- | --- |
| Hotels (Hotellook) | ~3% of booking value | ~$12 on a $400 stay |
| Flights (Aviasales) | ~1.1–1.3% of ticket | ~$7 on a $600 flight |

At 15%, an active creator driving 20 hotel bookings a month earns Trova about
**$36**. At 5% it is $12 — less than the cost of processing a payout, tax
paperwork, and answering one support email about it.

15% is the lowest rate at which the business covers the cost of moving money.

Raising a take rate later reads as a betrayal even when it is fair. Start here
rather than starting low and correcting upward.

## What is actually implemented

**Nothing takes a cut today.** The code pays creators 100% via their own
Travelpayouts marker — see `schema_creator_marker.sql`. That matches the
founding-creator offer exactly, which is why founding creators can be onboarded
right now with no further work.

Charging 15% requires infrastructure that does not exist yet:

1. Trova's marker on every link, with a per-creator sub-ID for attribution
   (Travelpayouts pays one account per link; there is no split at the link
   level)
2. Per-creator earnings tracking
3. Payouts — Stripe Connect, minimum thresholds, tax forms

Build this when there are creators worth paying, not before.

## Honest caveat

At these commission rates, 100 active creators at 15% is roughly $3,600/month.
That is a good side income, not a company. If Trova needs to be bigger, the
realistic levers are a subscription (creators keep 100%, pay a flat monthly
fee) or targeting creators with much larger audiences — not a higher take rate.

Revisit this once real conversion data exists. The first creator's numbers are
worth more than any of the modelling behind this document.

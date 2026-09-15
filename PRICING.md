# Trova pricing

## The plans

| Plan | Creator pays | Creator keeps |
| --- | --- | --- |
| **Free** | nothing | 85% -- Trova keeps 15% of commission |
| **Pro** | $15/month | 100% |
| **Founding** (first 10) | nothing, permanently | 100% |

**Pro costs a creator less than Free once their storefronts earn $100 a month**
(15% of $100 is $15). Below that, Free is the better deal for them, and that is
fine: nobody pays before they have earned anything.

**Founding creators keep 100%, permanently.** The first 10 creators onboarded
pay nothing, for as long as they use Trova. Not a trial, does not expire, and
they never need Pro.

## How it compares

Be careful with this comparison -- it is easy to get wrong, and getting it
wrong in a pitch is worse than not making it.

Most creator affiliate platforms (LTK, ShopMy, Levanta) **charge brands, not
creators**. Levanta states plainly that it takes no revenue share from creator
earnings. Their headline "20-30%" figures are the commission *brands pay per
sale*, not a platform cut. So at 15% Trova takes **more** from creators than
those platforms, not less.

**Do not claim to have the best rate in the category.** The honest pitch is
what the tool does and what it saves, not the percentage. Pro is what lets a
creator who earns real money keep all of it, as they would elsewhere.

The real alternative a creator has is signing up with Travelpayouts directly
and keeping 100%. What Trova offers instead:

- No Travelpayouts account, no approval wait, no payout method to configure
- A lower effective threshold before their first payment (see below)
- Extraction, hosting and links they would otherwise do by hand

## Why 15% and not lower

Commission per booking is small, so the percentage has to carry real weight:

| Product | Commission | Per booking |
| --- | --- | --- |
| Hotels (Hotellook) | ~3% of booking value | ~$12 on a $400 stay |
| Flights (Aviasales) | ~1.1-1.3% of ticket | ~$7 on a $600 flight |

At 15%, an active creator driving 20 hotel bookings a month earns Trova about
**$36**. At 5% it is $12 -- less than the cost of processing a payout and
answering one support email about it.

Take rates almost never go up. Starting at 15% and discounting is easy; the
reverse reads as a betrayal even when it is fair.

## How the money actually moves

Every booking link carries **Trova's marker plus a SubID naming the creator**
-- `marker=572600.wanderlust`. Travelpayouts pays Trova, and its
Reports -> Performance page splits earnings by SubID. That breakdown is the
payout sheet.

**This is built and working.** Creators need no Travelpayouts account.

Paying creators is done **by hand**: read the SubID report, pay by PayPal
monthly. At ten creators that is a spreadsheet and twenty minutes. Stripe
Connect, automated ledgers and tax forms are a problem for creator #50, not
creator #10.

A creator who would rather be paid directly can still enter their own marker
in the form; their links then carry it and Trova takes nothing. **This is now a
free way around both the 15% and Pro** -- see "Open decision" below.

## Pro: how it runs

**Checkout is a Stripe Payment Link** -- no accounts, no code. The link is
`PRO_CHECKOUT_URL` in `frontend/app/lib/pricing.ts`; the pricing section on the
home page stays hidden until it is set. The link has one required text field:
the creator's @handle, which is how a subscription is matched to a SubID.

**Fees:** 2.9% + $0.30 per card charge, plus 0.7% for Stripe Billing, no monthly
fee. That leaves about **$14.16 of each $15** from a US card; international
cards cost another 1.5%, and 1% more if currency is converted.

**Cancelling:** subscribers use the Stripe customer portal link
(`MANAGE_SUBSCRIPTION_URL`), logging in with their email. Set the portal to
cancel **at the end of the billing period**, so a creator who cancels keeps Pro
for the month they paid for.

**At payout time,** before paying anyone:

1. Stripe -> **Billing -> Subscriptions**: list who is active, and the handle
   each typed at checkout
2. Match each handle to its creator's SubID (the `creators` table in Supabase)
3. Pay Pro creators 100% of the commission from **bookings made while they were
   subscribed**; everyone else 85%, founding creators 100%

Apply Pro by **booking month, not payout month.** Otherwise a creator can
subscribe for one month just before a large, months-old payout lands and keep
all of it.

A handle that matches no creator means a typo at checkout. Email them before
the payout, not after.

**Tax:** selling a subscription can mean collecting sales tax or VAT, depending
on where subscribers live. Stripe Tax can calculate it ($0.50 per transaction
where you are registered), and Stripe's Managed Payments can take the whole
obligation on as merchant of record. Ask an accountant before subscribers
accumulate -- this is not something to discover at tax time.

**When to automate:** once matching handles by hand takes more than an hour a
month (roughly 20+ subscribers), replace the payment link with creator accounts
and a Stripe webhook that records each creator's plan in the database.

## Open decision: creators who bring their own marker

The form still lets any creator enter their own Travelpayouts marker, which
pays them 100% directly with nothing to Trova. That was kept deliberately, as
a trust escape hatch for creators wary of being paid by Trova. But with paid
plans it is also a free route around both the 15% and Pro, and a creator who
already has a Travelpayouts account will notice.

Options: keep it for everyone (trust over revenue), limit it to founding and
Pro creators, or remove it. Decide before creator #11 -- the first creator who
is not founding is the first one it costs money on.

## Timing, and what to tell creators

```
viewer clicks -> books -> STAYS -> +~1 week confirmed -> paid the next month
```

Six weeks if they booked for next week, several months if they booked a summer
trip in January. Nobody is paid until the guest actually stays -- that is hotel
affiliate everywhere, not a Travelpayouts quirk.

**Pay creators the month after Travelpayouts pays you.** Do not promise faster
unless you are willing to front the cash: ten creators at ~$30/month for four
months is roughly $1,200 out of pocket before the first transfer lands.

Travelpayouts' minimum **depends on the payout method** -- their own example is
**$50 for PayPal**, with bank transfer higher. Their earlier-quoted $200 figure
is the bank-transfer case, not the floor.

There is a second delay that is easy to miss: earnings from the current month
never count toward the current payout cycle, so a balance can clear the
minimum and still wait for the next run.

Pooled across every creator, Trova clears any threshold quickly and can pay a
creator $30 the month it arrives. Alone, that creator waits about two months to
reach $50 -- real, but a smaller advantage than a $200 floor would have made
it. Do not oversell this point: the stronger arguments are no signup, no
approval wait, and nothing for them to administer.

## Honest caveat

At these rates, 100 active creators at 15% is roughly $3,600/month. Good side
income, not a company. Pro changes the shape rather than the ceiling: every
creator who upgrades pays $15 instead of 15%, which is *less* for Trova whenever
they earn over $100 a month -- the point is keeping those creators, who would
otherwise do the maths and sign up with Travelpayouts directly. If Trova needs
to be bigger, the lever is creators with much larger audiences, not a higher
take rate.

Revisit once real conversion data exists. The first creator's numbers are worth
more than any of the modelling behind this document.

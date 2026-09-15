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
| Hotels (Stay22) | not published -- a share of what the booking site pays | **unknown until Stay22 confirms** |
| Flights (Aviasales) | ~1.1-1.3% of ticket | ~$7 on a $600 flight |

The hotel figures this table used to carry (~3%, ~$12 on a $400 stay) were
Hotellook's, and Hotellook closed on October 20, 2025. Booking sites generally
pay 4-6% of the stay, and Stay22 keeps a share of that. Replace the row with
real numbers once Stay22 answers or the first bookings arrive.

At the old Hotellook rate, an active creator driving 20 hotel bookings a month
earned Trova about **$36** at 15%, and $12 at 5% -- less than the cost of
processing a payout and answering one support email about it.

Take rates almost never go up. Starting at 15% and discounting is easy; the
reverse reads as a betrayal even when it is fair.

## How the money actually moves

Every booking link names the creator by their **SubID**, and each network pays
Trova and splits its report by that name:

| Links | Network | Where the creator's SubID goes | Report |
| --- | --- | --- | --- |
| Hotels | Stay22 (aid `trova`) | `campaign=wanderlust` | Stay22 Hub -> Performance / Transactions |
| Flights | Travelpayouts (marker 572600) | `marker=572600.wanderlust` | Travelpayouts -> Reports |

**This is built and working.** Creators need no account anywhere.

Paying creators is done **by hand**: each month, read both reports, add up each
SubID, pay by PayPal. At ten creators that is a spreadsheet and twenty minutes.

A founding creator who would rather be paid by Travelpayouts directly can have
their own marker set by hand -- see "Creators who bring their own marker"
below. That now covers **flight links only**: hotel links always go through
Trova's Stay22 account.

## Pro: how it runs

**Checkout is a Stripe Payment Link** -- no accounts, no code. The link is
`PRO_CHECKOUT_URL` in `frontend/app/lib/pricing.ts`; the pricing section on the
home page stays hidden until it is set. The link has one required text field:
the creator's @handle, which is how a subscription is matched to a SubID.

**Fees:** 2.9% + $0.30 per card charge, plus 0.7% for Stripe Billing, no monthly
fee. That leaves about **$14.16 of each $15** from a US card; international
cards cost another 1.5%, and 1% more if currency is converted. Managed Payments
(see Tax) adds 3.5%, leaving about **$13.64**.

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

**Tax: use Managed Payments.** Selling a subscription can mean collecting sales
tax or VAT wherever subscribers live, and creators are international -- several
countries tax digital services from the very first sale. With Managed Payments,
Stripe becomes the merchant of record: it calculates, collects, files and pays
sales tax, VAT and GST in more than 80 countries, so Trova registers nowhere.
It costs 3.5% per transaction on top of the fees above.

What changes with it:

- Customers see **Link** (Stripe's consumer brand) as the seller; card
  statements read `LINK.COM* TROVA`
- Customers can cancel at link.com as well as through the portal link
- Tax is added on top of the $15 by default, where it applies
- Stripe handles disputes, and escalates payment support to the support email
  in Stripe's business settings. **Keep that email current**: unanswered for
  48 hours, Stripe may refund without asking

Setting it up needs a **new** payment link; Managed Payments cannot be switched
on for an existing one. Activate it in Settings -> Managed Payments, give the
Trova Pro product the tax code "Software as a service (SaaS) - business use",
create a new link with Enable Managed Payments ticked (and the @username field
again), swap `PRO_CHECKOUT_URL`, then deactivate the old link.

Stripe decides eligibility. If it rules Trova Pro ineligible, the fallback is
Stripe Tax, where Trova registers and files itself.

Managed Payments covers the sales tax on subscriptions only. Income tax on
subscription and commission income is still Trova's, so an accountant is
still worth one conversation.

**When to automate:** once matching handles by hand takes more than an hour a
month (roughly 20+ subscribers), replace the payment link with creator accounts
and a Stripe webhook that records each creator's plan in the database.

## Creators who bring their own marker

A creator's own Travelpayouts marker pays them 100% directly, with nothing to
Trova. It exists as a trust escape hatch for creators wary of being paid by
Trova -- but offered to everyone, it is a free route around both the 15% and
Pro. So it was **removed from the public form and the API**, and is set by hand
for **founding creators only**, when they ask.

Not for Pro creators: they already keep 100% through the normal payout, and a
marker is baked into every link built while it is set. Clearing it later
changes only new storefronts, so a Pro creator who cancelled would keep being
paid 100% through every storefront they already share.

To set one:

1. Supabase -> **Table Editor** -> `creators`
2. Find their row by `tiktok_handle`, `instagram_handle` or `youtube_handle`
3. Put their marker (digits only) in `travelpayouts_marker`, and save

It applies to storefronts built **after** the change. Storefronts they already
share keep Trova's marker until rebuilt.

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

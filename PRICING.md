# Trova pricing

## The rate

**Creators keep 85%. Trova takes 15%** of affiliate commission earned through
their storefronts.

**Founding creators keep 100%, permanently.** The first 10 creators onboarded
pay nothing, for as long as they use Trova. Not a trial, does not expire.

## How it compares

Be careful with this comparison -- it is easy to get wrong, and getting it
wrong in a pitch is worse than not making it.

Most creator affiliate platforms (LTK, ShopMy, Levanta) **charge brands, not
creators**. Levanta states plainly that it takes no revenue share from creator
earnings. Their headline "20-30%" figures are the commission *brands pay per
sale*, not a platform cut. So at 15% Trova takes **more** from creators than
those platforms, not less.

**Do not claim to have the best rate in the category.** The honest pitch is
what the tool does and what it saves, not the percentage.

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
in the form; their links then carry it and Trova takes nothing.

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
income, not a company. If Trova needs to be bigger, the levers are a
subscription (creators keep 100%, pay a flat monthly fee) or creators with much
larger audiences -- not a higher take rate.

Revisit once real conversion data exists. The first creator's numbers are worth
more than any of the modelling behind this document.

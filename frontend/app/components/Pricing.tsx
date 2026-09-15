import { ArrowUpRight, Check } from "lucide-react";

import {
  FREE_PLAN_TAKE_RATE,
  MANAGE_SUBSCRIPTION_URL,
  PRO_BREAK_EVEN_USD,
  PRO_CHECKOUT_URL,
  PRO_MONTHLY_PRICE_USD,
} from "@/app/lib/pricing";

const takePercent = Math.round(FREE_PLAN_TAKE_RATE * 100);

const PLANS = [
  {
    name: "Free",
    price: "$0",
    cadence: null,
    summary: `Trova keeps ${takePercent}% of the commission your storefronts earn.`,
    features: [
      "Unlimited storefronts",
      "We track bookings and pay you monthly",
      "Nothing to sign up for",
    ],
    highlighted: false,
  },
  {
    name: "Pro",
    price: `$${PRO_MONTHLY_PRICE_USD}`,
    cadence: "/month",
    summary: "You keep 100% of the commission your storefronts earn.",
    features: [
      "Everything in Free",
      `Costs less than Free once you earn $${PRO_BREAK_EVEN_USD} a month`,
      "Cancel anytime",
    ],
    highlighted: true,
  },
] as const;

/**
 * Free vs Pro. Renders nothing until the Stripe payment link exists, so the
 * page never shows an upgrade button that goes nowhere.
 */
export function Pricing() {
  if (!PRO_CHECKOUT_URL) return null;

  return (
    <section className="mt-28" aria-labelledby="pricing">
      <h2
        id="pricing"
        className="text-xs font-medium uppercase tracking-[0.18em] text-ink-faint"
      >
        Pricing
      </h2>

      <div className="mt-6 grid gap-5 sm:grid-cols-2">
        {PLANS.map((plan) => (
          <div
            key={plan.name}
            className={`flex flex-col rounded-card border bg-paper-raised p-6 ${
              plan.highlighted ? "border-clay/40 shadow-[0_16px_40px_-24px_rgb(194_94_58/0.45)]" : "border-sand"
            }`}
          >
            <div className="flex items-baseline justify-between gap-3">
              <h3 className="font-display text-2xl text-ink">{plan.name}</h3>
              <p className="text-ink">
                <span className="font-display text-3xl">{plan.price}</span>
                {plan.cadence && <span className="text-sm text-ink-faint">{plan.cadence}</span>}
              </p>
            </div>
            <p className="mt-3 text-sm leading-relaxed text-ink-soft">{plan.summary}</p>

            <ul className="mt-5 space-y-2.5">
              {plan.features.map((feature) => (
                <li key={feature} className="flex gap-2.5 text-sm text-ink-soft">
                  <Check className="mt-0.5 size-4 shrink-0 text-moss" aria-hidden />
                  {feature}
                </li>
              ))}
            </ul>

            <div className="mt-auto pt-6">
              {plan.highlighted ? (
                <a
                  href={PRO_CHECKOUT_URL}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="group inline-flex w-full items-center justify-center gap-2 rounded-xl bg-clay px-5 py-3 text-sm font-medium text-paper-raised transition-colors hover:bg-clay-deep"
                >
                  Upgrade to Pro
                  <ArrowUpRight
                    className="size-4 transition-transform group-hover:-translate-y-0.5 group-hover:translate-x-0.5"
                    aria-hidden
                  />
                </a>
              ) : (
                <a
                  href="#build"
                  className="inline-flex w-full items-center justify-center rounded-xl border border-sand px-5 py-3 text-sm font-medium text-ink-soft transition-colors hover:border-sand-deep hover:text-ink"
                >
                  Build a storefront
                </a>
              )}
            </div>
          </div>
        ))}
      </div>

      <div className="mt-5 space-y-1.5 px-1 text-xs leading-relaxed text-ink-faint">
        <p>
          When you upgrade, enter the same @handle you build storefronts with, so your
          earnings are matched to your plan.
        </p>
        <p>Invited as a founding creator? You already keep 100% for free, no upgrade needed.</p>
        {MANAGE_SUBSCRIPTION_URL && (
          <p>
            Already on Pro?{" "}
            <a
              href={MANAGE_SUBSCRIPTION_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="underline decoration-sand-deep underline-offset-2 hover:text-clay"
            >
              Manage or cancel your subscription
            </a>
            .
          </p>
        )}
      </div>
    </section>
  );
}

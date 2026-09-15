/**
 * Trova's plans. PRICING.md is the source of truth for the reasoning; these
 * are the numbers the site shows.
 */

/** Share of commission Trova keeps on the free plan. */
export const FREE_PLAN_TAKE_RATE = 0.15;

/** Pro costs this much a month and the creator keeps 100%. */
export const PRO_MONTHLY_PRICE_USD = 15;

/**
 * Monthly earnings above which Pro costs a creator less than the free plan.
 * Rounded: in floating point, 15 / 0.15 is 100.00000000000001.
 */
export const PRO_BREAK_EVEN_USD = Math.round(PRO_MONTHLY_PRICE_USD / FREE_PLAN_TAKE_RATE);

/**
 * Stripe Payment Link for Pro (buy.stripe.com/...). Public by design: it is
 * the checkout page itself, not a key. The pricing section stays hidden while
 * this is empty, so the site never offers a plan nobody can buy.
 */
export const PRO_CHECKOUT_URL = "";

/**
 * Stripe customer portal login link (billing.stripe.com/p/login/...), where a
 * subscriber cancels or updates their card. Optional; hidden while empty.
 */
export const MANAGE_SUBSCRIPTION_URL = "";

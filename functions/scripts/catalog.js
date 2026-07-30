/**
 * The product catalogue, shared by the two Stripe scripts.
 *
 *   setup-stripe-products.js  CREATES these products/prices in whichever mode
 *                             the key belongs to, and prints the price IDs.
 *   check-stripe-config.js    READS the price IDs the functions are configured
 *                             with and checks they match what is defined here.
 *
 * Both must agree on amounts, lookup keys and tax behaviour or the check is
 * checking against a different catalogue than the one that was created — which
 * is exactly the go-live failure it exists to catch. Hence one file.
 */

// Managed Payments (Stripe as merchant of record) needs the preview API version.
// Must match STRIPE_API_VERSION in ../index.js — check-stripe-config.js asserts
// that it does, so a drift here is caught rather than shipped.
const API_VERSION = "2026-02-25.preview";

// Eligible digital tax code (from the blueprint). Adjust to the most accurate
// category for your product if needed — see Stripe's tax code list.
const TAX_CODE = "txcd_10103100";
const CURRENCY = "gbp";                       // base currency

// All prices are tax-INCLUSIVE: the listed amount is exactly what the customer
// pays; Stripe (merchant of record) carves the VAT out by buyer location.
const TAX_BEHAVIOR = "inclusive";

// Bump when the currency set / charm rule changes, to force fresh prices on re-run.
const CCY_VERSION = "fx1";

// SKU → product + price definition. amount is in the smallest currency unit (pence).
const CATALOG = [
  { sku: "pro",      lookupKey: "kidseq_pro_monthly",  name: "Kid Sequencer Pro",  description: "Pro subscription: all instruments & rhythms, 10 AI songs/month, 20 save slots.", amount: 499,  recurring: { interval: "month" } },
  { sku: "ai10",     lookupKey: "kidseq_ai10",         name: "10 AI songs",        description: "Top-up: 10 extra AI songs.",  amount: 399 },
  { sku: "ai25",     lookupKey: "kidseq_ai25",         name: "25 AI songs",        description: "Top-up: 25 extra AI songs.",  amount: 799 },
  { sku: "ai50",     lookupKey: "kidseq_ai50",         name: "50 AI songs",        description: "Top-up: 50 extra AI songs.",  amount: 1299 },
  { sku: "slots20",  lookupKey: "kidseq_slots20",      name: "+20 save slots",     description: "Top-up: 20 extra save slots.", amount: 199 },
  { sku: "slots50",  lookupKey: "kidseq_slots50",      name: "+50 save slots",     description: "Top-up: 50 extra save slots.", amount: 399 },
];

// SKU → the config parameter the functions read that price ID from (the
// defineString names in ../index.js, overridable in .env.<projectId>).
const PARAM_BY_SKU = {
  pro:     "STRIPE_PRICE_ID",
  ai10:    "TOPUP_AI10_PRICE",
  ai25:    "TOPUP_AI25_PRICE",
  ai50:    "TOPUP_AI50_PRICE",
  slots20: "TOPUP_SLOTS20_PRICE",
  slots50: "TOPUP_SLOTS50_PRICE",
};

module.exports = { API_VERSION, TAX_CODE, CURRENCY, TAX_BEHAVIOR, CCY_VERSION, CATALOG, PARAM_BY_SKU };

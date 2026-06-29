#!/usr/bin/env node
/**
 * One-off setup for Managed Payments products + prices.
 *
 * Creates (idempotently) the Pro subscription and the five one-off top-up
 * packs, each with an eligible tax code so Stripe can act as merchant of record
 * and calculate tax. Prints the price IDs and the exact commands to wire them
 * into Firebase.
 *
 * Run from the functions/ directory with your key in the environment — the key
 * is NEVER hardcoded:
 *
 *   # bash / git-bash
 *   STRIPE_SECRET_KEY=sk_test_xxx node scripts/setup-stripe-products.js
 *
 *   # PowerShell
 *   $env:STRIPE_SECRET_KEY="sk_test_xxx"; node scripts/setup-stripe-products.js
 *
 * Use a TEST-mode key (sk_test_…) first, then re-run with the live key.
 * Get keys from the Stripe Dashboard → Developers → API keys.
 */

const API_VERSION = "2026-02-25.preview";

// Eligible digital tax code (from the blueprint). Adjust to the most accurate
// category for your product if needed — see Stripe's tax code list.
const TAX_CODE = "txcd_10103100";
const CURRENCY = "gbp";

// SKU → product + price definition. amount is in the smallest currency unit (pence).
const CATALOG = [
  { sku: "pro",      lookupKey: "kidseq_pro_monthly",  name: "Kid Sequencer Pro",  description: "Pro subscription: all instruments & rhythms, 10 AI songs/month, 20 save slots.", amount: 499,  recurring: { interval: "month" } },
  { sku: "ai10",     lookupKey: "kidseq_ai10",         name: "10 AI songs",        description: "Top-up: 10 extra AI songs.",  amount: 399 },
  { sku: "ai25",     lookupKey: "kidseq_ai25",         name: "25 AI songs",        description: "Top-up: 25 extra AI songs.",  amount: 799 },
  { sku: "ai50",     lookupKey: "kidseq_ai50",         name: "50 AI songs",        description: "Top-up: 50 extra AI songs.",  amount: 1299 },
  { sku: "slots20",  lookupKey: "kidseq_slots20",      name: "+20 save slots",     description: "Top-up: 20 extra save slots.", amount: 199 },
  { sku: "slots50",  lookupKey: "kidseq_slots50",      name: "+50 save slots",     description: "Top-up: 50 extra save slots.", amount: 399 },
];

const key = process.env.STRIPE_SECRET_KEY;
if (!key) {
  console.error("ERROR: set STRIPE_SECRET_KEY in your environment before running. See header comment.");
  process.exit(1);
}
const stripe = require("stripe")(key, { apiVersion: API_VERSION });

async function getOrCreateProduct(item) {
  const found = await stripe.products.search({ query: `metadata['sku']:'${item.sku}'`, limit: 1 });
  if (found.data.length) {
    return await stripe.products.update(found.data[0].id, {
      name: item.name, description: item.description, tax_code: TAX_CODE,
    });
  }
  return await stripe.products.create({
    name: item.name, description: item.description, tax_code: TAX_CODE,
    metadata: { sku: item.sku, app: "kidseq" },
  });
}

async function getOrCreatePrice(item, productId) {
  const existing = await stripe.prices.list({ lookup_keys: [item.lookupKey], limit: 1 });
  const match = existing.data.find((p) => p.unit_amount === item.amount && p.active);
  if (match) return match;
  // Create a fresh price (prices are immutable) and move the lookup key onto it.
  return await stripe.prices.create({
    product: productId,
    currency: CURRENCY,
    unit_amount: item.amount,
    ...(item.recurring ? { recurring: item.recurring } : {}),
    lookup_key: item.lookupKey,
    transfer_lookup_key: true,
  });
}

(async () => {
  const result = {};
  for (const item of CATALOG) {
    const product = await getOrCreateProduct(item);
    const price = await getOrCreatePrice(item, product.id);
    result[item.sku] = price.id;
    console.log(`✓ ${item.sku.padEnd(8)} ${product.id}  ${price.id}  (${(item.amount / 100).toFixed(2)} ${CURRENCY.toUpperCase()})`);
  }

  console.log("\n--- Price IDs (committed as defaults in index.js) ---\n");
  console.log("These are config, not secrets. To use them, update the defineString");
  console.log("defaults in functions/index.js (or override in functions/.env):\n");
  console.log(`STRIPE_PRICE_ID=${result.pro}        # Pro £4.99/mo`);
  console.log(`TOPUP_AI10_PRICE=${result.ai10}`);
  console.log(`TOPUP_AI25_PRICE=${result.ai25}`);
  console.log(`TOPUP_AI50_PRICE=${result.ai50}`);
  console.log(`TOPUP_SLOTS20_PRICE=${result.slots20}`);
  console.log(`TOPUP_SLOTS50_PRICE=${result.slots50}`);
  console.log("\nSecrets to set separately (real keys only):");
  console.log("  firebase functions:secrets:set STRIPE_SECRET_KEY STRIPE_WEBHOOK_SECRET STABILITY_API_KEY");
})().catch((e) => { console.error(e); process.exit(1); });

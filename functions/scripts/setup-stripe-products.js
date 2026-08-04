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
 *
 * --write-env  additionally rewrites the six price-ID lines of
 *              functions/.env.<projectId> with the IDs just created, instead of
 *              printing them for you to copy by hand. Nothing else in that file
 *              is touched. Review the result with `git diff` before deploying.
 */

// Catalogue + tax/API constants are shared with check-stripe-config.js so the
// pre-flight check cannot drift from what this script created.
const { API_VERSION, TAX_CODE, CURRENCY, TAX_BEHAVIOR, CCY_VERSION, CATALOG, PARAM_BY_SKU } = require("./catalog");

const PROJECT_ID = "kid-sequencer";

// Approximate GBP→currency FX rates (STATIC — pricing doesn't track live FX; edit
// freely). Each listed currency gets a CHARM-rounded local price pinned via
// currency_options. Currencies NOT listed fall back to Stripe Adaptive Pricing.
const FX_RATES = {
  usd: 1.27, eur: 1.17, aud: 1.94, cad: 1.74, nzd: 2.12, chf: 1.13,
  sek: 13.5, nok: 13.7, dkk: 8.7,  pln: 5.05, czk: 29.5, thb: 45.9,
  sgd: 1.71, hkd: 9.9,  mxn: 23.5, brl: 6.95, inr: 106,  zar: 23.3,
  aed: 4.66, ils: 4.7,  php: 73,   myr: 5.95, jpy: 197,  krw: 1740,
};
// Stripe zero-decimal currencies (amount is whole units, NOT ×100).
const ZERO_DECIMAL = new Set(["jpy", "krw"]);
// Currencies pinned to the SAME round digits as GBP (e.g. $4.99/€4.99) instead of
// FX-charm — common consumer anchor for the US/EU.
const SAME_DIGIT = new Set(["usd", "eur"]);
// Hard per-pack, per-currency overrides (major units). Highest precedence — used
// for deliberate price points like USD Pro at $5.99.
const OVERRIDES = {
  pro: { usd: 5.99 },
};

// Round a converted amount UP to a "nice" charm price (e.g. 229→299, 6.34→6.99).
function charm(x) {                                   // x in major currency units
  if (x < 15)   return Math.ceil(x) - 0.01;          // 6.99, 9.99, 12.99
  if (x < 80)   return Math.ceil(x / 10) * 10 - 1;   // 49, 69
  if (x < 2000) return Math.ceil(x / 100) * 100 - 1; // 199, 299, 599, 999
  return Math.ceil(x / 1000) * 1000 - 1;             // 8999
}

function buildCurrencyOptions(gbpMajor, sku) {
  const opts = {};
  const over = OVERRIDES[sku] || {};
  for (const [ccy, rate] of Object.entries(FX_RATES)) {
    const major = (ccy in over) ? over[ccy]
                : SAME_DIGIT.has(ccy) ? gbpMajor
                : charm(gbpMajor * rate);
    const minor = ZERO_DECIMAL.has(ccy) ? Math.round(major) : Math.round(major * 100);
    opts[ccy] = { unit_amount: minor, tax_behavior: TAX_BEHAVIOR };
  }
  return opts;
}

const key = process.env.STRIPE_SECRET_KEY;
if (!key) {
  console.error("ERROR: set STRIPE_SECRET_KEY in your environment before running. See header comment.");
  process.exit(1);
}
const stripe = require("stripe")(key, { apiVersion: API_VERSION });

const WRITE_ENV = process.argv.includes("--write-env");

// --write-env: rewrite the six price-ID lines of .env.<projectId> in place,
// leaving every other line (ENGINE_ENDPOINT, comments) untouched.
//
// Hand-copying six IDs is the only manual step in the go-live runbook, and one
// transposed character there is exactly the silent failure the runbook exists
// to prevent: the functions still start, every page still loads, and the first
// thing that notices is a real customer pressing Subscribe. git is the backup —
// review with `git diff` before deploying.
function writeEnvFile(ids, file) {
  const fs = require("fs");
  const path = require("path");
  file = file || path.resolve(__dirname, "..", `.env.${PROJECT_ID}`);
  const src = fs.existsSync(file) ? fs.readFileSync(file, "utf8") : "";
  const eol = src.includes("\r\n") ? "\r\n" : "\n";
  const lines = src.length ? src.split(/\r?\n/) : [];

  const changed = [];
  for (const [sku, param] of Object.entries(PARAM_BY_SKU)) {
    const value = ids[sku];
    if (!value) continue;
    const i = lines.findIndex((l) => new RegExp(`^\\s*${param}\\s*=`).test(l));
    // Keep any trailing comment on the line (e.g. "# Pro £4.99/mo").
    const comment = i >= 0 ? (/=\s*\S*(\s+#.*)$/.exec(lines[i]) || ["", ""])[1] : "";
    const next = `${param}=${value}${comment}`;
    if (i < 0) {
      changed.push(`${param}  (added)  ${value}`);
      lines.push(next);
    } else {
      if (lines[i].trim() !== next.trim()) {
        const was = lines[i].split("=").slice(1).join("=").trim().split(/\s+#/)[0];
        changed.push(`${param}  ${was} -> ${value}`);
      }
      lines[i] = next;
    }
  }

  fs.writeFileSync(file, lines.join(eol), "utf8");
  console.log(`\nWrote ${file}:`);
  if (!changed.length) console.log("  (no change — the file already held these IDs)");
  else for (const c of changed) console.log(`  ${c}`);
  console.log(`  Review with:  git diff functions/.env.${PROJECT_ID}`);
}

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
  const existing = await stripe.prices.list({ lookup_keys: [item.lookupKey], limit: 10 });
  // Reuse only if it matches the amount, is tax-inclusive, AND carries the current
  // currency-set version (prices are immutable, so changing currencies = new price).
  const match = existing.data.find(
    (p) => p.active && p.unit_amount === item.amount &&
           p.tax_behavior === TAX_BEHAVIOR && p.metadata && p.metadata.ccyset === CCY_VERSION
  );
  if (match) return match;
  // Create a fresh price (prices are immutable) and move the lookup key onto it.
  return await stripe.prices.create({
    product: productId,
    currency: CURRENCY,
    unit_amount: item.amount,
    tax_behavior: TAX_BEHAVIOR,
    currency_options: buildCurrencyOptions(item.amount / 100, item.sku),
    metadata: { ccyset: CCY_VERSION },
    ...(item.recurring ? { recurring: item.recurring } : {}),
    lookup_key: item.lookupKey,
    transfer_lookup_key: true,
  });
}

// Guarded so the file can be require()d to exercise writeEnvFile against a
// throwaway copy of the env file without touching Stripe. Running it directly
// behaves exactly as before.
module.exports = { writeEnvFile };
if (require.main !== module) return;

(async () => {
  const result = {};
  for (const item of CATALOG) {
    const product = await getOrCreateProduct(item);
    const price = await getOrCreatePrice(item, product.id);
    result[item.sku] = price.id;
    console.log(`✓ ${item.sku.padEnd(8)} ${product.id}  ${price.id}  (${(item.amount / 100).toFixed(2)} ${CURRENCY.toUpperCase()})`);
  }

  const mode = key.includes("_live_") ? "LIVE" : "TEST";
  console.log(`\n--- ${mode}-mode price IDs ---\n`);
  console.log("These are config, not secrets. Paste them over the existing lines in");
  console.log(`functions/.env.${PROJECT_ID} (that file wins over the index.js defaults)`);
  console.log("— or re-run with --write-env and this script will do it for you:\n");
  console.log(`STRIPE_PRICE_ID=${result.pro}        # Pro £4.99/mo`);
  console.log(`TOPUP_AI10_PRICE=${result.ai10}`);
  console.log(`TOPUP_AI25_PRICE=${result.ai25}`);
  console.log(`TOPUP_AI50_PRICE=${result.ai50}`);
  console.log(`TOPUP_SLOTS20_PRICE=${result.slots20}`);
  console.log(`TOPUP_SLOTS50_PRICE=${result.slots50}`);

  if (WRITE_ENV) writeEnvFile(result);

  console.log("\nThen, with the SAME key still in the environment, confirm the");
  console.log("functions' configured IDs resolve in this mode BEFORE deploying:\n");
  console.log("  npm run check:stripe\n");
  console.log("Secrets to set separately (real keys only):");
  console.log("  firebase functions:secrets:set STRIPE_SECRET_KEY");
  console.log("  firebase functions:secrets:set STRIPE_WEBHOOK_SECRET");
})().catch((e) => { console.error(e); process.exit(1); });

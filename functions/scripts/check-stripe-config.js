#!/usr/bin/env node
/**
 * Pre-flight check for the Stripe wiring — run it BEFORE deploying functions,
 * and especially before the test→live switch.
 *
 * The failure this exists to prevent: price IDs are per-mode. Deploy a live
 * secret key while the config still carries the TEST price IDs and every
 * function still starts fine, every page still loads, and the only symptom is
 * that a real customer pressing Subscribe gets "Couldn't start checkout".
 * Nothing in the deploy output says a word about it. So: resolve the price IDs
 * exactly the way the deployed functions will, look each one up with the key
 * you are about to ship, and say plainly whether they exist in that mode.
 *
 * Read-only against Stripe unless you pass --probe (see below).
 *
 *   # bash / git-bash
 *   STRIPE_SECRET_KEY=sk_live_xxx npm run check:stripe
 *
 *   # PowerShell
 *   $env:STRIPE_SECRET_KEY="sk_live_xxx"; npm run check:stripe
 *
 * --probe  additionally creates a real Checkout Session for the Pro price and
 *          then immediately expires it. No money moves and no customer sees it,
 *          but it is the only way to prove Managed Payments is actually enabled
 *          for this account in this mode — the account flag is not readable
 *          through the API, so the checkout call itself is the test.
 *
 * Exit code is 0 only if every check passed.
 */

const fs = require("fs");
const path = require("path");

const { API_VERSION, TAX_CODE, CURRENCY, TAX_BEHAVIOR, CCY_VERSION, CATALOG, PARAM_BY_SKU } = require("./catalog");

const PROJECT_ID = "kid-sequencer";
const WEBHOOK_URL = `https://europe-west1-${PROJECT_ID}.cloudfunctions.net/stripeWebhook`;
const WEBHOOK_EVENTS = ["checkout.session.completed", "customer.subscription.deleted"];

const PROBE = process.argv.includes("--probe");

let failures = 0, warnings = 0;
const pass = (m) => console.log(`  ✓ ${m}`);
const fail = (m) => { failures++; console.log(`  ✗ ${m}`); };
const warn = (m) => { warnings++; console.log(`  ! ${m}`); };
const head = (m) => console.log(`\n${m}`);

// --- config resolution -------------------------------------------------------
// Mirror how the deployed functions resolve a defineString: an explicit
// environment variable wins, then .env.<projectId>, then the default compiled
// into index.js. Checking anything else would be checking a value that is not
// the one that ships.
function parseEnvFile(file) {
  const out = {};
  if (!fs.existsSync(file)) return out;
  for (const line of fs.readFileSync(file, "utf8").split(/\r?\n/)) {
    const m = /^\s*([A-Z0-9_]+)\s*=\s*(.*)$/.exec(line);
    if (m) out[m[1]] = m[2].trim().replace(/^["']|["']$/g, "");
  }
  return out;
}

function indexDefaults(indexSrc) {
  const out = {};
  const re = /defineString\(\s*"([A-Z0-9_]+)"\s*,\s*\{\s*default:\s*"([^"]+)"/g;
  let m;
  while ((m = re.exec(indexSrc))) out[m[1]] = m[2];
  return out;
}

const fnDir = path.resolve(__dirname, "..");
const indexSrc = fs.readFileSync(path.join(fnDir, "index.js"), "utf8");
const envFile = parseEnvFile(path.join(fnDir, `.env.${PROJECT_ID}`));
const defaults = indexDefaults(indexSrc);

function resolve(param) {
  if (process.env[param]) return { value: process.env[param], from: "environment" };
  if (envFile[param])     return { value: envFile[param],     from: `.env.${PROJECT_ID}` };
  if (defaults[param])    return { value: defaults[param],    from: "index.js default" };
  return { value: null, from: "unset" };
}

// --- key + client ------------------------------------------------------------
const key = process.env.STRIPE_SECRET_KEY;
if (!key) {
  console.error("ERROR: set STRIPE_SECRET_KEY in your environment before running. See header comment.");
  process.exit(1);
}
const keyMode = key.includes("_live_") ? "live" : key.includes("_test_") ? "test" : "unknown";
const stripe = require("stripe")(key, { apiVersion: API_VERSION });

(async () => {
  console.log(`Stripe pre-flight — project ${PROJECT_ID}, key looks ${keyMode.toUpperCase()}-mode`);
  if (keyMode === "unknown") warn("key prefix is neither _test_ nor _live_; relying on Stripe's livemode flag");

  // --- API version drift ---
  head("API version");
  const pinned = /STRIPE_API_VERSION\s*=\s*"([^"]+)"/.exec(indexSrc);
  if (!pinned) warn("could not find STRIPE_API_VERSION in index.js");
  else if (pinned[1] !== API_VERSION) fail(`index.js pins ${pinned[1]} but the scripts use ${API_VERSION} — Managed Payments needs them to agree`);
  else pass(`index.js and the scripts both pin ${API_VERSION}`);

  // --- prices ---
  head("Configured prices");
  let sawLivemode = null;
  for (const item of CATALOG) {
    const param = PARAM_BY_SKU[item.sku];
    const { value: id, from } = resolve(param);
    const label = `${item.sku.padEnd(8)} ${param}`;

    if (!id) { fail(`${label} — not configured anywhere`); continue; }

    let price;
    try {
      price = await stripe.prices.retrieve(id, { expand: ["currency_options", "product"] });
    } catch (e) {
      const msg = (e && e.message) || String(e);
      if (/No such price/i.test(msg)) {
        fail(`${label} = ${id} (from ${from}) does NOT exist in ${keyMode} mode` +
             ` — this is the test/live price-ID mismatch; re-run "npm run setup:stripe" with this key and paste the new IDs into .env.${PROJECT_ID}`);
      } else {
        fail(`${label} = ${id} (from ${from}) — ${msg}`);
      }
      continue;
    }

    const problems = [];
    if (sawLivemode === null) sawLivemode = price.livemode;
    else if (sawLivemode !== price.livemode) problems.push("mixed live/test prices in one config");
    if (!price.active) problems.push("price is archived (active=false)");
    if (price.unit_amount !== item.amount) problems.push(`amount ${price.unit_amount} != catalogue ${item.amount}`);
    if (price.currency !== CURRENCY) problems.push(`currency ${price.currency} != ${CURRENCY}`);
    if (price.tax_behavior !== TAX_BEHAVIOR) problems.push(`tax_behavior ${price.tax_behavior} != ${TAX_BEHAVIOR} (customer would be charged amount + VAT on top)`);
    if (price.lookup_key !== item.lookupKey) problems.push(`lookup_key ${price.lookup_key} != ${item.lookupKey}`);
    if (!price.metadata || price.metadata.ccyset !== CCY_VERSION) problems.push(`metadata.ccyset ${price.metadata && price.metadata.ccyset} != ${CCY_VERSION} (stale currency set)`);
    const wantsRecurring = !!item.recurring;
    if (wantsRecurring && !price.recurring) problems.push("expected a recurring price, got one-off");
    if (!wantsRecurring && price.recurring) problems.push("expected a one-off price, got recurring");
    if (wantsRecurring && price.recurring && price.recurring.interval !== item.recurring.interval) {
      problems.push(`interval ${price.recurring.interval} != ${item.recurring.interval}`);
    }
    const ccyCount = price.currency_options ? Object.keys(price.currency_options).length : 0;
    if (ccyCount === 0) problems.push("no currency_options — non-GBP buyers fall back to Adaptive Pricing only");
    const product = price.product && typeof price.product === "object" ? price.product : null;
    if (!product) problems.push("product did not expand");
    else {
      if (product.active === false) problems.push("product is archived");
      if (product.tax_code !== TAX_CODE && !(product.tax_code && product.tax_code.id === TAX_CODE)) {
        problems.push(`product tax_code ${product.tax_code && (product.tax_code.id || product.tax_code)} != ${TAX_CODE} — Managed Payments needs an eligible code`);
      }
    }

    if (problems.length) fail(`${label} = ${id} (from ${from})\n      - ${problems.join("\n      - ")}`);
    else pass(`${label} = ${id} (from ${from}, ${ccyCount} pinned currencies)`);
  }

  if (sawLivemode !== null) {
    head("Mode");
    if (keyMode !== "unknown" && sawLivemode !== (keyMode === "live")) {
      fail(`key looks ${keyMode} but Stripe reports livemode=${sawLivemode}`);
    } else {
      pass(`prices resolve in ${sawLivemode ? "LIVE" : "TEST"} mode`);
    }
    if (!sawLivemode) warn("still TEST mode — real customers cannot pay until this is a live key with live price IDs");
  }

  // --- webhook ---
  head("Webhook endpoint");
  try {
    const eps = await stripe.webhookEndpoints.list({ limit: 100 });
    const ep = eps.data.find((e) => e.url === WEBHOOK_URL);
    if (!ep) {
      fail(`no ${keyMode}-mode endpoint for ${WEBHOOK_URL} — create it (Developers → Webhooks) and set STRIPE_WEBHOOK_SECRET from its signing secret`);
    } else {
      if (ep.status !== "enabled") fail(`endpoint exists but status is "${ep.status}"`);
      const missing = WEBHOOK_EVENTS.filter((e) => !ep.enabled_events.includes(e) && !ep.enabled_events.includes("*"));
      if (missing.length) fail(`endpoint is missing events: ${missing.join(", ")} — a paid customer would never be flipped to tier=paid`);
      if (ep.status === "enabled" && !missing.length) pass(`${WEBHOOK_URL} enabled with both events`);
      warn("the signing secret is per-endpoint: if you just created this one, STRIPE_WEBHOOK_SECRET must be re-set from it");
    }
  } catch (e) {
    warn(`could not list webhook endpoints (${e.message}) — check manually in the dashboard`);
  }

  // --- customer portal ---
  head("Customer portal (Manage subscription button)");
  try {
    const cfgs = await stripe.billingPortal.configurations.list({ limit: 10 });
    const def = cfgs.data.find((c) => c.is_default) || cfgs.data[0];
    if (!def) fail(`no portal configuration in ${keyMode} mode — Settings → Billing → Customer portal → configure + activate, or createBillingPortalSession throws`);
    else if (!def.active) fail("portal configuration exists but is not active");
    else pass(`portal configured and active (${def.id})`);
  } catch (e) {
    warn(`could not read portal configuration (${e.message}) — check manually`);
  }

  // --- managed payments probe (opt-in, creates then expires a session) ---
  head("Managed Payments");
  if (!PROBE) {
    console.log("  – skipped (pass --probe to create and immediately expire one real Checkout Session,");
    console.log("    the only way to prove the account has Managed Payments enabled in this mode)");
  } else {
    const { value: proId } = resolve(PARAM_BY_SKU.pro);
    try {
      const session = await stripe.checkout.sessions.create({
        mode: "subscription",
        managed_payments: { enabled: true },
        line_items: [{ price: proId, quantity: 1 }],
        success_url: "https://kid-sequencer.web.app/?subscribed=1",
        cancel_url: "https://kid-sequencer.web.app/",
        metadata: { uid: "preflight-probe" },
      });
      pass(`Checkout Session created with managed_payments enabled (${session.id})`);
      console.log(`      ${session.url}`);
      try {
        await stripe.checkout.sessions.expire(session.id);
        pass("probe session expired again — nothing left open");
      } catch (e) {
        warn(`probe session created but could not be expired (${e.message}); it will expire on its own in 24h`);
      }
    } catch (e) {
      fail(`Managed Payments checkout failed: ${e.message}`);
    }
  }

  head(failures ? `FAILED — ${failures} problem(s), ${warnings} warning(s)` : `OK — all checks passed, ${warnings} warning(s)`);
  process.exit(failures ? 1 : 0);
})().catch((e) => { console.error(e); process.exit(1); });

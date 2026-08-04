# Stripe setup — Managed Payments

The app uses **Stripe Managed Payments** (Stripe is merchant of record and
handles tax/VAT). Checkout Sessions are created server-side in
[functions/index.js](functions/index.js) with `managed_payments: { enabled: true }`
and the preview API version `2026-02-25.preview`. Fulfilment is the
`stripeWebhook` function listening for `checkout.session.completed`.

Do everything in **Test mode** first, then repeat with live keys — the ordered
switch is **[Going live](#going-live)** at the bottom. Test mode is done and is
what production runs on today.

## 1. Create products + prices (with tax codes)
From the `functions/` directory, with your test secret key in the environment:

```bash
# bash / git-bash
STRIPE_SECRET_KEY=sk_test_xxx npm run setup:stripe
```
```powershell
# PowerShell
$env:STRIPE_SECRET_KEY="sk_test_xxx"; npm run setup:stripe
```

This idempotently creates the Pro subscription (£4.99/mo) and the five one-off
top-up packs, each with tax code `txcd_10103100`, and prints all price IDs.
(Re-running updates in place via `lookup_key` — safe.)

**Pricing model:** all prices are **tax-inclusive** (`tax_behavior: "inclusive"`)
— the listed amount is exactly what the customer pays; Stripe (merchant of
record) carves out VAT by buyer location. Round local prices are pinned for
**GBP / USD / EUR** (same `x.99` digits). Every other currency is handled by
**Adaptive Pricing** — enable it once: Stripe Dashboard → Settings → Payments →
Checkout/Adaptive Pricing → turn on. Stripe then converts + rounds for all other
currencies automatically.

## 2. Price IDs (already committed — TEST mode)
The 6 price IDs are committed as defaults in [functions/index.js](functions/index.js)
(the `defineString` block). **Nothing to do for test mode** — they travel with the
code and survive merges.

The same IDs are also in [`functions/.env.kid-sequencer`](functions/.env.kid-sequencer),
which **overrides** the defaults at deploy time — so that file, not `index.js`, is
what actually ships. For **live mode** see [Going live](#going-live).

## 3. Secrets (real keys only)
```bash
firebase functions:secrets:set STRIPE_SECRET_KEY       # sk_… (use live for prod)
firebase functions:secrets:set STRIPE_WEBHOOK_SECRET   # whsec_… (from step 4)
```
(No `STRIPE_PRICE_ID` secret — price IDs are config, not secrets. `ENGINE_TOKEN`
is the third secret in use, shared with the Modal engine; it is unrelated to
Stripe and does not change between modes. `STABILITY_API_KEY` still exists in
Secret Manager but nothing reads it any more — Stable Audio was replaced by the
`engine/` renderer.)

## 4. Webhook
Stripe Dashboard → Developers → Webhooks → Add endpoint:
- URL: `https://europe-west1-kid-sequencer.cloudfunctions.net/stripeWebhook`
- Events: `checkout.session.completed`, `customer.subscription.deleted`
- Copy the signing secret → `STRIPE_WEBHOOK_SECRET` (step 3).

## 5. Deploy
```bash
cd functions && npm install && cd ..
firebase deploy --only functions,storage
```

## 6. Test
Use Stripe test cards (e.g. `4242 4242 4242 4242`, any future expiry/CVC). Try
different billing-country addresses to see Managed Payments calculate tax.
Confirm the webhook flips `users/{uid}.tier = "paid"` (subscription) and
increments `aiTopupBalance` / `slotTopup` (top-ups).

## 7. Customer portal (Manage subscription)
The account popup's **Manage subscription** button calls the
`createBillingPortalSession` function, which opens the **Stripe Customer Portal**
(cancel, update card, view invoices). This requires the portal to be activated:

- Stripe Dashboard → Settings → Billing → **Customer portal** → configure +
  activate. Do this **once per mode** (Test now, Live at go-live). Without it,
  `billingPortal.sessions.create` throws and the button shows an error.
- Like the other callables, after first deploy set **`allUsers` / Cloud Run
  Invoker** on the `createBillingPortalSession` Cloud Run service (see CLAUDE.md
  callable-function gotcha) or every call fails with "Empty Authorization header".
- The portal acts on the customer stored in `users/{uid}.stripeCustomerId`
  (written by the subscription webhook), so only users who subscribed have it.

---

# Going live

Production currently runs on the **test** secret key, so nobody can actually
pay. Everything below happens in the Stripe dashboard's **Live** mode and needs
the live secret key, which never leaves your machine — run these yourself.

**Why it needs care:** price IDs, webhook endpoints, the portal configuration
and the Managed Payments flag are all *per-mode*. Deploying a live key while any
one of them is still the test-mode value leaves every function healthy, every
page loading, and the only symptom is a paying customer hitting "Couldn't start
checkout". Nothing in the deploy output mentions it. Step 4 is the guard.

1. **Managed Payments, live mode.** Activate at
   <https://dashboard.stripe.com/settings/managed-payments> — in **Live** mode
   (the test-mode page you already accepted has `/test/` in the path).
   Activation *is* accepting the Managed Payments terms of service on that page;
   there is no separate application in the documented flow. Then turn on
   Adaptive Pricing (Settings → Payments → Checkout).

   Eligibility, checked against this account (2026-07-30):
   - seller country **UK (GB)** — supported ✓
   - **digital products only** (software / digital media / online courses) — a
     browser music app subscription + digital top-ups qualifies ✓; physical
     goods, professional services, live events and anything with human
     intervention are excluded, none of which apply
   - **restricted types** are Connect platforms, Express accounts and
     platform-controlled accounts — this is a plain standalone account ✓
   - tax code **`txcd_10103100`** ("SaaS – electronic download – personal use")
     is on the eligible list, and is already what `setup-stripe-products.js`
     stamps on every product ✓

   Do this first: it is a preview product, and everything after it is wasted if
   the account turns out to be ineligible. Step 4's `--probe` is what confirms
   the activation actually took — the flag is not readable through the API.

   **Unverified:** whether Adaptive Pricing overrides a Price's manually pinned
   `currency_options`. `setup-stripe-products.js` assumes pinned wins and
   Adaptive only fills the unlisted currencies. If a USD checkout shows anything
   other than $5.99 at step 8, that assumption is wrong.

2. **Create the live products/prices, and write them straight into the config.**
   From `functions/` (run `npm install` there first if you never have), with the
   **live** key:
   ```powershell
   $env:STRIPE_SECRET_KEY="sk_live_xxx"; npm run setup:stripe -- --write-env
   ```
   It creates the six products/prices, prints the live `price_…` IDs, and
   rewrites the six price-ID lines of
   [`functions/.env.kid-sequencer`](functions/.env.kid-sequencer) with them.
   Nothing else in that file is touched. Drop `--write-env` if you would rather
   paste them yourself.

3. **Check the diff.**
   ```bash
   git diff functions/.env.kid-sequencer
   ```
   Six lines should have changed and nothing else. That file wins over the
   `defineString` defaults in `index.js`, so it is the only place that has to
   change. Price IDs are config, not secrets — committing them is fine and
   intended.

4. **Pre-flight, with the live key still in the environment:**
   ```powershell
   npm run check:stripe
   ```
   It resolves each price ID exactly the way the deployed functions will
   (env → `.env.kid-sequencer` → `index.js` default), looks it up with your key,
   and fails loudly on a test/live mismatch, a wrong amount, a non-inclusive tax
   behaviour, a missing tax code, an archived price, a missing or mis-evented
   webhook endpoint, or an unconfigured customer portal. Read-only.

   Add `--probe` to also create one real Checkout Session and immediately expire
   it. No money moves, but it is the only way to prove step 1 actually took —
   the account flag is not readable through the API, so the checkout call *is*
   the test.

5. **Live webhook.** Dashboard (Live) → Developers → Webhooks → add
   `https://europe-west1-kid-sequencer.cloudfunctions.net/stripeWebhook` with
   `checkout.session.completed` + `customer.subscription.deleted`. Copy its
   signing secret — it is per-endpoint, so the test-mode one will not verify:
   ```bash
   firebase functions:secrets:set STRIPE_WEBHOOK_SECRET
   firebase functions:secrets:set STRIPE_SECRET_KEY     # the live sk_live_…
   ```

6. **Live customer portal.** Settings → Billing → Customer portal → configure +
   activate (it is per-mode; the test-mode configuration does not carry over).
   Without it the account popup's **Manage subscription** button throws.

7. **Deploy and re-check.**
   ```bash
   cd functions && npm install && cd ..
   firebase deploy --only functions
   ```
   Then run `npm run check:stripe` once more — it now reads the same config the
   deployed functions hold.

8. **Buy your own subscription with a real card**, confirm Firestore
   `users/{uid}.tier` flips to `paid`, then cancel it from the portal and
   confirm it flips back to `free`. The webhook is the only thing that grants
   access; a successful payment that never reaches it looks exactly like a
   refund request.

## Notes
- No subscriber migration: Stripe was never live before, so the £1.99→£4.99
  change is a clean slate.
- Tax code `txcd_10103100` is the blueprint default; adjust in
  `functions/scripts/setup-stripe-products.js` if a more specific code fits.

# Stripe setup — Managed Payments

The app uses **Stripe Managed Payments** (Stripe is merchant of record and
handles tax/VAT). Checkout Sessions are created server-side in
[functions/index.js](functions/index.js) with `managed_payments: { enabled: true }`
and the preview API version `2026-02-25.preview`. Fulfilment is the
`stripeWebhook` function listening for `checkout.session.completed`.

Do everything in **Test mode** first, then repeat with live keys.

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

## 2. Price IDs (already committed — TEST mode)
The 6 price IDs are committed as defaults in [functions/index.js](functions/index.js)
(the `defineString` block). **Nothing to do for test mode** — they travel with the
code and survive merges.

For **live mode**, re-run the script in step 1 with a live key, then either update
those defaults or drop the live IDs into `functions/.env` (env overrides win; see
`.env.example`).

## 3. Secrets (real keys only)
```bash
firebase functions:secrets:set STRIPE_SECRET_KEY       # sk_… (use live for prod)
firebase functions:secrets:set STRIPE_WEBHOOK_SECRET   # whsec_… (from step 4)
firebase functions:secrets:set STABILITY_API_KEY       # Stability AI key
```
(No `STRIPE_PRICE_ID` secret — price IDs are config, not secrets.)

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

## Notes
- No subscriber migration: Stripe was never live before, so the £1.99→£4.99
  change is a clean slate.
- Tax code `txcd_10103100` is the blueprint default; adjust in
  `functions/scripts/setup-stripe-products.js` if a more specific code fits.

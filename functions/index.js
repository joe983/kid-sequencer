const { onCall, onRequest, HttpsError } = require("firebase-functions/v2/https");
const { defineSecret, defineString } = require("firebase-functions/params");
const { initializeApp } = require("firebase-admin/app");
const { getFirestore, FieldValue } = require("firebase-admin/firestore");
const { getStorage } = require("firebase-admin/storage");
const crypto = require("crypto");

initializeApp();
const db = getFirestore();

const STORAGE_BUCKET = "kid-sequencer.firebasestorage.app";

// --- Secrets (API keys) -----------------------------------------------------
const stripeSecretKey     = defineSecret("STRIPE_SECRET_KEY");
const stripeWebhookSecret = defineSecret("STRIPE_WEBHOOK_SECRET");
const stripePriceId       = defineSecret("STRIPE_PRICE_ID");        // £4.99/mo recurring
const stabilityApiKey     = defineSecret("STABILITY_API_KEY");

// Managed Payments (Stripe = merchant of record, handles tax/VAT) requires the
// preview API version. Pin it on every Stripe client; the setup script uses the
// same version when creating products/prices.
const STRIPE_API_VERSION = "2026-02-25.preview";
function stripeClient() {
  return require("stripe")(stripeSecretKey.value(), { apiVersion: STRIPE_API_VERSION });
}

// --- Config params (Stripe one-off price IDs; not secret) -------------------
const topupAi10Price    = defineString("TOPUP_AI10_PRICE",    { default: "" });
const topupAi25Price    = defineString("TOPUP_AI25_PRICE",    { default: "" });
const topupAi50Price    = defineString("TOPUP_AI50_PRICE",    { default: "" });
const topupSlots20Price = defineString("TOPUP_SLOTS20_PRICE", { default: "" });
const topupSlots50Price = defineString("TOPUP_SLOTS50_PRICE", { default: "" });

// packId → grant (server-authoritative). Price ID comes from the matching param.
const PACKS = {
  ai10:    { type: "ai",    amount: 10, price: topupAi10Price },
  ai25:    { type: "ai",    amount: 25, price: topupAi25Price },
  ai50:    { type: "ai",    amount: 50, price: topupAi50Price },
  slots20: { type: "slots", amount: 20, price: topupSlots20Price },
  slots50: { type: "slots", amount: 50, price: topupSlots50Price },
};

const BASE_MONTHLY_AI = 10;   // included AI tracks per month on Pro

// Stable Audio 2.5 audio-to-audio. NOTE: confirm exact endpoint/params against
// current Stability docs when wiring the live API key — kept as constants so
// they're trivial to adjust.
const STABILITY_ENDPOINT = "https://api.stability.ai/v2beta/audio/stable-audio-2/audio-to-audio";
const STABILITY_MODEL    = "stable-audio-2.5";
const AI_DURATION_SEC    = 180;   // ≤ ~190s cap
const AI_STRENGTH        = 0.7;   // lower = closer to the user's seed

function monthKey() {
  const d = new Date();
  return `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, "0")}`;
}

function slugify(s) {
  return String(s || "track").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 40) || "track";
}

function buildPrompt(meta) {
  const m = meta || {};
  const tempo = Number.isFinite(m.tempo) ? Math.round(m.tempo) : 100;
  const key = typeof m.key === "string" ? m.key : "C";
  const instr = ({
    piano: "bright piano", trumpet: "brass", strings: "warm strings",
    synth: "synth lead", bass: "deep bass", bells: "glockenspiel bells",
  })[m.instrument] || "melodic lead";
  const rhythm = ({
    techhouse: "tech-house", dnb: "drum and bass", funk: "funk",
    drill: "UK drill", hiphop: "hip hop", reggaeton: "reggaeton",
  })[m.rhythm] || "upbeat";
  return [
    `A fun, joyful kids' music track, about 3 minutes long.`,
    `Tempo around ${tempo} BPM, in the key of ${key}.`,
    `Led by a ${instr} melody over a ${rhythm} drum groove.`,
    `Built from and faithful to the provided melody — keep its tune and feel.`,
    `Clean, playful, studio-quality production, suitable for children.`,
  ].join(" ");
}

// ---------------------------------------------------------------------------
// Subscription checkout (Pro, £4.99/mo)
// ---------------------------------------------------------------------------
exports.createCheckoutSession = onCall(
  { region: "europe-west1", secrets: [stripeSecretKey, stripePriceId] },
  async (request) => {
    if (!request.auth) throw new HttpsError("unauthenticated", "Login required");

    const stripe = stripeClient();
    const uid = request.auth.uid;
    const email = request.auth.token.email;
    const returnUrl = request.data.returnUrl || "https://kid-sequencer.web.app/?subscribed=1";

    // Managed Payments: Stripe handles payment methods + tax as merchant of record.
    const session = await stripe.checkout.sessions.create({
      mode: "subscription",
      managed_payments: { enabled: true },
      line_items: [{ price: stripePriceId.value(), quantity: 1 }],
      success_url: returnUrl,
      cancel_url: "https://kid-sequencer.web.app/",
      metadata: { uid },
      customer_email: email,
    });

    return { url: session.url };
  }
);

// ---------------------------------------------------------------------------
// One-off top-up checkout (AI track packs + save-slot packs)
// ---------------------------------------------------------------------------
exports.createTopupCheckout = onCall(
  {
    region: "europe-west1",
    secrets: [stripeSecretKey],
  },
  async (request) => {
    if (!request.auth) throw new HttpsError("unauthenticated", "Login required");

    const packId = request.data.packId;
    const pack = PACKS[packId];
    if (!pack) throw new HttpsError("invalid-argument", "Unknown pack");

    const priceId = pack.price.value();
    if (!priceId) throw new HttpsError("failed-precondition", "Pack not configured");

    const stripe = stripeClient();
    const uid = request.auth.uid;
    const email = request.auth.token.email;
    const returnUrl = request.data.returnUrl || "https://kid-sequencer.web.app/?topup=1";

    // Managed Payments: Stripe handles payment methods + tax as merchant of record.
    const session = await stripe.checkout.sessions.create({
      mode: "payment",
      managed_payments: { enabled: true },
      line_items: [{ price: priceId, quantity: 1 }],
      success_url: returnUrl,
      cancel_url: "https://kid-sequencer.web.app/",
      metadata: { uid, packId },
      customer_email: email,
    });

    return { url: session.url };
  }
);

// ---------------------------------------------------------------------------
// Generate an AI track from the user's seed audio (Stable Audio 2.5)
// ---------------------------------------------------------------------------
exports.generateAiTrack = onCall(
  {
    region: "europe-west1",
    secrets: [stabilityApiKey],
    timeoutSeconds: 300,
    memory: "512MiB",
  },
  async (request) => {
    if (!request.auth) throw new HttpsError("unauthenticated", "Login required");
    const uid = request.auth.uid;

    const seedPath = request.data.seedPath;
    if (typeof seedPath !== "string" || !seedPath.startsWith(`users/${uid}/seeds/`)) {
      throw new HttpsError("invalid-argument", "Bad seed path");
    }

    // --- Quota: lazy monthly reset, consume monthly-first then top-up ---
    const userRef = db.doc(`users/${uid}`);
    const month = monthKey();
    const consumed = await db.runTransaction(async (tx) => {
      const snap = await tx.get(userRef);
      const d = snap.exists ? snap.data() : {};
      if (d.tier !== "paid") throw new HttpsError("permission-denied", "Pro required");

      let used = d.aiMonthKey === month ? (d.aiUsedThisMonth || 0) : 0;
      let topup = d.aiTopupBalance || 0;
      const available = Math.max(0, BASE_MONTHLY_AI - used) + topup;
      if (available <= 0) throw new HttpsError("resource-exhausted", "No AI tracks left this month");

      let from;
      if (used < BASE_MONTHLY_AI) { used += 1; from = "monthly"; }
      else { topup -= 1; from = "topup"; }

      tx.set(userRef, { aiMonthKey: month, aiUsedThisMonth: used, aiTopupBalance: topup }, { merge: true });
      return from;
    });

    // refund the consumed credit if generation fails
    const refund = async () => {
      try {
        await db.runTransaction(async (tx) => {
          const snap = await tx.get(userRef);
          const d = snap.exists ? snap.data() : {};
          if (consumed === "monthly") {
            tx.set(userRef, { aiUsedThisMonth: Math.max(0, (d.aiUsedThisMonth || 0) - 1) }, { merge: true });
          } else {
            tx.set(userRef, { aiTopupBalance: (d.aiTopupBalance || 0) + 1 }, { merge: true });
          }
        });
      } catch (e) { console.error("[generateAiTrack] refund failed:", e); }
    };

    try {
      const bucket = getStorage().bucket(STORAGE_BUCKET);
      const [seedBuffer] = await bucket.file(seedPath).download();

      const prompt = buildPrompt(request.data.meta);

      const form = new FormData();
      form.append("audio", new Blob([seedBuffer], { type: "audio/wav" }), "seed.wav");
      form.append("model", STABILITY_MODEL);
      form.append("prompt", prompt);
      form.append("duration", String(AI_DURATION_SEC));
      form.append("strength", String(AI_STRENGTH));
      form.append("output_format", "mp3");

      const resp = await fetch(STABILITY_ENDPOINT, {
        method: "POST",
        headers: { Authorization: `Bearer ${stabilityApiKey.value()}`, Accept: "audio/*" },
        body: form,
      });

      if (!resp.ok) {
        const text = await resp.text().catch(() => "");
        console.error("[generateAiTrack] Stability error", resp.status, text.slice(0, 500));
        await refund();
        throw new HttpsError("internal", "AI generation failed");
      }

      const audioBuffer = Buffer.from(await resp.arrayBuffer());

      const slug = slugify(request.data.name);
      const token = crypto.randomUUID();
      const destPath = `users/${uid}/tracks/${slug}-${Date.now()}.mp3`;
      await bucket.file(destPath).save(audioBuffer, {
        contentType: "audio/mpeg",
        metadata: { metadata: { firebaseStorageDownloadTokens: token } },
        resumable: false,
      });

      const url = `https://firebasestorage.googleapis.com/v0/b/${STORAGE_BUCKET}/o/` +
        `${encodeURIComponent(destPath)}?alt=media&token=${token}`;

      // best-effort: clean up the seed
      bucket.file(seedPath).delete().catch(() => {});

      return { path: destPath, url };
    } catch (e) {
      if (e instanceof HttpsError) throw e;
      console.error("[generateAiTrack] unexpected:", e);
      await refund();
      throw new HttpsError("internal", "AI generation failed");
    }
  }
);

// ---------------------------------------------------------------------------
// Stripe webhook — subscriptions + one-off top-ups
// ---------------------------------------------------------------------------
exports.stripeWebhook = onRequest(
  { region: "europe-west1", secrets: [stripeSecretKey, stripeWebhookSecret] },
  async (req, res) => {
    const stripe = stripeClient();

    const sig = req.headers["stripe-signature"];
    let event;
    try {
      event = stripe.webhooks.constructEvent(req.rawBody, sig, stripeWebhookSecret.value());
    } catch (e) {
      console.error("[Webhook] Signature verify failed:", e.message);
      res.status(400).send(`Webhook error: ${e.message}`);
      return;
    }

    if (event.type === "checkout.session.completed") {
      const obj = event.data.object;
      const uid = obj.metadata?.uid;

      if (obj.mode === "subscription" && uid) {
        await db.doc(`users/${uid}`).set(
          { tier: "paid", stripeCustomerId: obj.customer, stripeSubscriptionId: obj.subscription },
          { merge: true }
        );
        console.log(`[Webhook] Upgraded user ${uid} to paid`);
      } else if (obj.mode === "payment" && uid) {
        const pack = PACKS[obj.metadata?.packId];
        if (pack) {
          const field = pack.type === "ai" ? "aiTopupBalance" : "slotTopup";
          await db.doc(`users/${uid}`).set(
            { [field]: FieldValue.increment(pack.amount) },
            { merge: true }
          );
          console.log(`[Webhook] Granted ${uid} ${pack.amount} ${pack.type}`);
        }
      }
    }

    if (event.type === "customer.subscription.deleted") {
      const customerId = event.data.object.customer;
      const snap = await db.collection("users")
        .where("stripeCustomerId", "==", customerId).limit(1).get();
      if (!snap.empty) {
        await snap.docs[0].ref.set({ tier: "free" }, { merge: true });
        console.log(`[Webhook] Downgraded customer ${customerId} to free`);
      }
    }

    res.json({ received: true });
  }
);

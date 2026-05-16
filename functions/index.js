const { onCall, onRequest, HttpsError } = require("firebase-functions/v2/https");
const { defineSecret } = require("firebase-functions/params");
const { initializeApp } = require("firebase-admin/app");
const { getFirestore } = require("firebase-admin/firestore");

initializeApp();
const db = getFirestore();

const stripeSecretKey    = defineSecret("STRIPE_SECRET_KEY");
const stripeWebhookSecret = defineSecret("STRIPE_WEBHOOK_SECRET");
const stripePriceId      = defineSecret("STRIPE_PRICE_ID");

// Called from the browser when user clicks Subscribe
exports.createCheckoutSession = onCall(
  { region: "europe-west1", secrets: [stripeSecretKey, stripePriceId] },
  async (request) => {
    if (!request.auth) throw new HttpsError("unauthenticated", "Login required");

    const Stripe = require("stripe");
    const stripe = Stripe(stripeSecretKey.value());
    const uid = request.auth.uid;
    const email = request.auth.token.email;
    const returnUrl = request.data.returnUrl || "https://kid-sequencer.web.app/?subscribed=1";

    const session = await stripe.checkout.sessions.create({
      mode: "subscription",
      payment_method_types: ["card"],
      line_items: [{ price: stripePriceId.value(), quantity: 1 }],
      success_url: returnUrl,
      cancel_url: "https://kid-sequencer.web.app/",
      metadata: { uid },
      customer_email: email,
    });

    return { url: session.url };
  }
);

// Stripe webhook — receives payment events from Stripe
exports.stripeWebhook = onRequest(
  { region: "europe-west1", secrets: [stripeSecretKey, stripeWebhookSecret] },
  async (req, res) => {
    const Stripe = require("stripe");
    const stripe = Stripe(stripeSecretKey.value());

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
      const uid = event.data.object.metadata?.uid;
      const customerId = event.data.object.customer;
      const subscriptionId = event.data.object.subscription;
      if (uid) {
        await db.doc(`users/${uid}`).set(
          { tier: "paid", stripeCustomerId: customerId, stripeSubscriptionId: subscriptionId },
          { merge: true }
        );
        console.log(`[Webhook] Upgraded user ${uid} to paid`);
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

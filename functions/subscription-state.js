/**
 * Does this Stripe subscription entitle the customer to Pro?
 *
 * Kept in its own module, free of firebase-admin, so it can be unit-tested
 * without initialising an app or reaching Stripe. It is the single rule that
 * decides whether someone keeps a paid feature set, so it should be the easiest
 * thing in the codebase to check.
 *
 * Only "active" and "trialing" mean money is arriving. Everything else —
 * past_due, unpaid, canceled, incomplete, incomplete_expired, paused — means it
 * is not, and before this existed the tier stayed "paid" through all of them
 * because the webhook only listened for customer.subscription.deleted. Stripe's
 * retry schedule can sit in past_due for WEEKS before deleting anything.
 *
 * Two things deliberately do NOT revoke access:
 *   - cancel_at_period_end: the status stays "active" until the period actually
 *     ends. They paid for the month; they keep the month.
 *   - a successful retry: it flips the status back to "active" and this returns
 *     true again, so access restores itself with no special-casing.
 */
const PAYING_STATUSES = new Set(["active", "trialing"]);

function isPayingSubscription(sub) {
  if (!sub || typeof sub !== "object") return false;
  // pause_collection is an object while paused and null otherwise. A paused
  // subscription keeps status "active", so checking status alone would hand out
  // Pro indefinitely to someone Stripe has stopped billing.
  if (sub.pause_collection) return false;
  return PAYING_STATUSES.has(sub.status);
}

module.exports = { isPayingSubscription, PAYING_STATUSES };

/**
 * Retention rules, kept free of firebase-admin so they can be unit-tested
 * (same shape as subscription-state.js / ai-attempts.js).
 *
 * The numbers here are the retention promises made in public/privacy.html -
 * change them together or the policy stops being true.
 */
const DAY_MS = 24 * 60 * 60 * 1000;

const AUDIO_REPORT_RETENTION_DAYS = 30;   // device diagnostics, no account attached
const SCANLOG_RETENTION_DAYS      = 30;   // ?scandebug=1 uploads (contain a worksheet photo)
const INACTIVE_FREE_DAYS          = 730;  // free account never signed in for ~2 years

function cutoffMs(nowMs, days) {
  return nowMs - days * DAY_MS;
}

/**
 * Should an inactive FREE account be erased? Never true for a paying
 * subscriber. Falls back to the creation time when there is no sign-in time,
 * and to "keep" when there is neither (unknown is never grounds to delete).
 */
function isStaleFreeAccount({ lastSignInMs, createdMs, tier }, nowMs, days = INACTIVE_FREE_DAYS) {
  if (tier === "paid") return false;
  const last = Number.isFinite(lastSignInMs) && lastSignInMs > 0 ? lastSignInMs
             : Number.isFinite(createdMs) && createdMs > 0 ? createdMs
             : null;
  if (last === null) return false;
  return last < cutoffMs(nowMs, days);
}

module.exports = {
  DAY_MS,
  AUDIO_REPORT_RETENTION_DAYS,
  SCANLOG_RETENTION_DAYS,
  INACTIVE_FREE_DAYS,
  cutoffMs,
  isStaleFreeAccount,
};

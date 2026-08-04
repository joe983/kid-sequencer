/**
 * Should this user be allowed to START an AI generation right now?
 *
 * Kept free of firebase-admin, like subscription-state.js, so the rule that
 * decides whether someone can spend two minutes of Modal CPU is the easiest
 * thing in the codebase to test.
 *
 * WHY THIS EXISTS
 * ---------------
 * generateAiTrack used to consume a credit up front and refund it in a catch
 * block. That only works when the function survives long enough to RUN the
 * catch. It does not survive a 540s platform timeout, an out-of-memory kill, or
 * an instance being torn down mid-render — and in every one of those cases the
 * user was charged for a track that was never made. A refund cannot be the
 * safety net when the failure mode is "the process stopped existing".
 *
 * So the credit is now committed only once the track is actually stored, and
 * this module is the thing that stops free failures from becoming free spam.
 * Three independent limits, each for a different abuse/breakage shape:
 *
 *   1. IN FLIGHT — one generation at a time. A render takes 1-3 minutes and the
 *      user sees a spinner; a second press (or a page reload and retry, which
 *      is exactly what happened in the incident this fixes) must not start a
 *      second render. This is also what closes the check-then-commit gap: the
 *      credit balance is checked at the start and consumed at the end, so
 *      without this a user could fire N concurrent requests that all pass a
 *      check against the same balance.
 *
 *   2. FAILURE STREAK — consecutive failures trigger a cooldown. If an account
 *      is broken (bad sequence, engine down for their input), retrying is
 *      free and instant, so nothing else would stop a retry loop.
 *
 *   3. MONTHLY FAILURE CEILING — a backstop for failures spread far enough
 *      apart to keep clearing the cooldown. Successes need no ceiling; they are
 *      already bounded by the credit system.
 *
 * The in-flight marker MUST expire. It is written before the render and cleared
 * after, but a killed instance never reaches the clear — so a marker older than
 * the function's own timeout is treated as dead. Without that, the first crash
 * would lock the user out of the feature permanently, which is a worse bug than
 * the one this file is fixing.
 */

// Longer than generateAiTrack's timeoutSeconds (540). If the marker is older
// than the longest a run can possibly last, no run is still holding it.
const IN_FLIGHT_TTL_MS = 600 * 1000;

const MAX_CONSECUTIVE_FAILURES = 5;
const FAILURE_COOLDOWN_MS = 15 * 60 * 1000;
const MAX_FAILURES_PER_MONTH = 40;

const num = (v) => (typeof v === "number" && Number.isFinite(v) ? v : 0);

/**
 * @param state {object} the user doc's AI-attempt fields:
 *   aiInFlightAt        ms epoch, or falsy when nothing is running
 *   aiFailStreak        consecutive failures
 *   aiCooldownUntil     ms epoch
 *   aiFailMonthKey      month the failure count belongs to
 *   aiFailsThisMonth    failures recorded in that month
 * @param now {number} ms epoch
 * @param month {string} current month key, to expire a stale failure count
 * @returns {{allow: boolean, reason: string, retryAfterSec: number}}
 */
function attemptGate(state, now, month) {
  const s = state && typeof state === "object" ? state : {};

  const inFlightAt = num(s.aiInFlightAt);
  if (inFlightAt > 0 && now - inFlightAt < IN_FLIGHT_TTL_MS) {
    return {
      allow: false,
      reason: "in-flight",
      retryAfterSec: Math.ceil((inFlightAt + IN_FLIGHT_TTL_MS - now) / 1000),
    };
  }

  const cooldownUntil = num(s.aiCooldownUntil);
  if (cooldownUntil > now) {
    return {
      allow: false,
      reason: "cooldown",
      retryAfterSec: Math.ceil((cooldownUntil - now) / 1000),
    };
  }

  // A failure count from a previous month is spent; only this month's counts.
  const failsThisMonth = s.aiFailMonthKey === month ? num(s.aiFailsThisMonth) : 0;
  if (failsThisMonth >= MAX_FAILURES_PER_MONTH) {
    return { allow: false, reason: "failure-ceiling", retryAfterSec: 0 };
  }

  return { allow: true, reason: "ok", retryAfterSec: 0 };
}

/** Fields to write when a run starts. Claims the in-flight slot. */
function beginAttempt(now) {
  return { aiInFlightAt: now };
}

/**
 * Fields to write when a run finishes successfully. Clears the slot and wipes
 * the streak — a success means the account is not broken, so a user who failed
 * four times and then succeeded starts fresh rather than sitting one failure
 * away from a cooldown.
 */
function succeedAttempt() {
  return { aiInFlightAt: 0, aiFailStreak: 0, aiCooldownUntil: 0 };
}

/**
 * Fields to write when a run fails. Clears the slot (they may retry), advances
 * both counters, and arms the cooldown once the streak hits the limit.
 */
function failAttempt(state, now, month) {
  const s = state && typeof state === "object" ? state : {};
  const streak = num(s.aiFailStreak) + 1;
  const fails = (s.aiFailMonthKey === month ? num(s.aiFailsThisMonth) : 0) + 1;

  const out = {
    aiInFlightAt: 0,
    aiFailStreak: streak,
    aiFailMonthKey: month,
    aiFailsThisMonth: fails,
  };
  if (streak >= MAX_CONSECUTIVE_FAILURES) {
    out.aiCooldownUntil = now + FAILURE_COOLDOWN_MS;
    out.aiFailStreak = 0;   // cooldown served, streak restarts after it
  }
  return out;
}

module.exports = {
  attemptGate,
  beginAttempt,
  succeedAttempt,
  failAttempt,
  IN_FLIGHT_TTL_MS,
  MAX_CONSECUTIVE_FAILURES,
  FAILURE_COOLDOWN_MS,
  MAX_FAILURES_PER_MONTH,
};

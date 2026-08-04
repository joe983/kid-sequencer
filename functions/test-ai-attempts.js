/**
 * AI attempt-limiter checks. Run: node test-ai-attempts.js
 * No firebase-admin — just the rule that decides who may start a render.
 */
const {
  attemptGate, beginAttempt, succeedAttempt, failAttempt,
  IN_FLIGHT_TTL_MS, MAX_CONSECUTIVE_FAILURES, FAILURE_COOLDOWN_MS, MAX_FAILURES_PER_MONTH,
} = require("./ai-attempts");

let fails = 0;
const check = (label, actual, expected) => {
  const ok = actual === expected;
  if (!ok) fails++;
  console.log(`  ${ok ? "PASS" : "FAIL"} ${label}${ok ? "" : ` — got ${actual}, expected ${expected}`}`);
};

const NOW = 1_700_000_000_000;
const M = "2026-08";
const allow = (state, now = NOW, month = M) => attemptGate(state, now, month).allow;
const why = (state, now = NOW, month = M) => attemptGate(state, now, month).reason;

console.log("\nA clean account may start");
check("empty state", allow({}), true);
check("null state", allow(null), true);
check("undefined state", allow(undefined), true);
check("after a previous success", allow(succeedAttempt()), true);

console.log("\nOne generation at a time");
check("just started", allow({ ...beginAttempt(NOW) }), false);
check("reason", why({ ...beginAttempt(NOW) }), "in-flight");
check("still running 4 min in", allow({ aiInFlightAt: NOW - 4 * 60 * 1000 }), false);
check("marker just under the TTL", allow({ aiInFlightAt: NOW - (IN_FLIGHT_TTL_MS - 1000) }), false);

console.log("\nA killed instance must not lock the feature out forever");
check("marker older than the TTL is dead", allow({ aiInFlightAt: NOW - IN_FLIGHT_TTL_MS - 1 }), true);
check("marker far in the past", allow({ aiInFlightAt: NOW - 30 * 24 * 3600 * 1000 }), true);
check("TTL exceeds the 540s function timeout", IN_FLIGHT_TTL_MS > 540 * 1000, true);

console.log("\nConsecutive failures arm a cooldown");
let st = {};
for (let i = 1; i < MAX_CONSECUTIVE_FAILURES; i++) {
  st = { ...st, ...failAttempt(st, NOW, M) };
  check(`failure ${i} still allowed`, allow(st), true);
}
st = { ...st, ...failAttempt(st, NOW, M) };
check(`failure ${MAX_CONSECUTIVE_FAILURES} blocks`, allow(st), false);
check("reason", why(st), "cooldown");
check("blocked one second before it expires", allow(st, NOW + FAILURE_COOLDOWN_MS - 1000), false);
check("allowed once served", allow(st, NOW + FAILURE_COOLDOWN_MS + 1), true);
check("retryAfterSec is positive", attemptGate(st, NOW, M).retryAfterSec > 0, true);

console.log("\nA success clears the streak");
let near = {};
for (let i = 1; i < MAX_CONSECUTIVE_FAILURES; i++) near = { ...near, ...failAttempt(near, NOW, M) };
const after = { ...near, ...succeedAttempt() };
check("streak reset to 0", after.aiFailStreak, 0);
check("one more failure does not immediately block",
  allow({ ...after, ...failAttempt(after, NOW, M) }), true);

console.log("\nMonthly failure ceiling is the backstop for spaced-out retries");
// Each failure served its cooldown, so only the monthly count can stop this.
let spaced = {};
let t = NOW;
for (let i = 0; i < MAX_FAILURES_PER_MONTH; i++) {
  spaced = { ...spaced, ...failAttempt(spaced, t, M) };
  t += FAILURE_COOLDOWN_MS + 1000;
}
check("ceiling reached", allow(spaced, t, M), false);
check("reason", why(spaced, t, M), "failure-ceiling");
check("count is exactly the ceiling", spaced.aiFailsThisMonth, MAX_FAILURES_PER_MONTH);
check("a new month clears it", allow(spaced, t, "2026-09"), true);
check("stale month count is ignored",
  allow({ aiFailMonthKey: "2026-07", aiFailsThisMonth: 9999 }), true);

console.log("\nA failure never touches credits");
const f = failAttempt({}, NOW, M);
check("no aiUsedThisMonth", "aiUsedThisMonth" in f, false);
check("no aiTopupBalance", "aiTopupBalance" in f, false);
check("success writes no credit fields either", "aiUsedThisMonth" in succeedAttempt(), false);
check("failure releases the in-flight slot", f.aiInFlightAt, 0);
check("success releases the in-flight slot", succeedAttempt().aiInFlightAt, 0);

console.log("\nGarbage state never blocks a legitimate user out");
for (const [label, v] of [["string", "wat"], ["number", 5], ["array", []],
                          ["NaN fields", { aiInFlightAt: NaN, aiFailsThisMonth: NaN }],
                          ["string fields", { aiInFlightAt: "soon", aiCooldownUntil: "later" }]]) {
  check(label, allow(v), true);
}

console.log("\nGarbage state never grants a bypass either");
check("in-flight wins over junk siblings",
  allow({ aiInFlightAt: NOW, aiFailStreak: "x", aiCooldownUntil: null }), false);

console.log(fails ? `\nFAILED — ${fails} check(s)` : "\nOK — all checks passed");
process.exit(fails ? 1 : 0);

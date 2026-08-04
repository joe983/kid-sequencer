/**
 * Entitlement rule checks. Run: node test-subscription-state.js
 * No Stripe, no firebase-admin — just the decision that gates paid features.
 */
const { isPayingSubscription } = require("./subscription-state");

let fails = 0;
const check = (label, actual, expected) => {
  const ok = actual === expected;
  if (!ok) fails++;
  console.log(`  ${ok ? "PASS" : "FAIL"} ${label}${ok ? "" : ` — got ${actual}, expected ${expected}`}`);
};

console.log("\nPaying states keep Pro");
check("active",   isPayingSubscription({ status: "active" }), true);
check("trialing", isPayingSubscription({ status: "trialing" }), true);
check("active + cancel_at_period_end (they paid for the month)",
  isPayingSubscription({ status: "active", cancel_at_period_end: true }), true);

console.log("\nNon-paying states revoke Pro");
for (const status of ["past_due", "unpaid", "canceled", "incomplete", "incomplete_expired", "paused"]) {
  check(status, isPayingSubscription({ status }), false);
}

console.log("\nPaused collection revokes even though status stays active");
check("active + pause_collection object",
  isPayingSubscription({ status: "active", pause_collection: { behavior: "void" } }), false);
check("active + pause_collection null (not paused)",
  isPayingSubscription({ status: "active", pause_collection: null }), true);

console.log("\nGarbage in never grants access");
for (const [label, v] of [["null", null], ["undefined", undefined], ["string", "active"],
                          ["empty object", {}], ["unknown status", { status: "wat" }]]) {
  check(label, isPayingSubscription(v), false);
}

console.log("\nRecovery: a successful retry restores access with no special-casing");
check("past_due -> active", isPayingSubscription({ status: "past_due" }) === false &&
  isPayingSubscription({ status: "active" }) === true, true);

console.log(fails ? `\nFAILED — ${fails} check(s)` : "\nOK — all checks passed");
process.exit(fails ? 1 : 0);

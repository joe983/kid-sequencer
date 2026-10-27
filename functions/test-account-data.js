/**
 * Retention rule checks. Run: node test-account-data.js
 */
const { DAY_MS, INACTIVE_FREE_DAYS, cutoffMs, isStaleFreeAccount } = require("./account-data");

let fails = 0;
const check = (label, actual, expected) => {
  const ok = actual === expected;
  if (!ok) fails++;
  console.log(`  ${ok ? "PASS" : "FAIL"} ${label}${ok ? "" : ` - got ${actual}, expected ${expected}`}`);
};

const now = Date.UTC(2026, 9, 12);
const ago = (days) => now - days * DAY_MS;

console.log("\ncutoffMs");
check("30 days back", cutoffMs(now, 30), ago(30));

console.log("\nInactive free accounts");
check("signed in yesterday - keep", isStaleFreeAccount({ lastSignInMs: ago(1), createdMs: ago(900), tier: "free" }, now), false);
check("one day inside the window - keep", isStaleFreeAccount({ lastSignInMs: ago(INACTIVE_FREE_DAYS - 1), tier: "free" }, now), false);
check("one day past the window - erase", isStaleFreeAccount({ lastSignInMs: ago(INACTIVE_FREE_DAYS + 1), tier: "free" }, now), true);
check("no tier recorded counts as free", isStaleFreeAccount({ lastSignInMs: ago(INACTIVE_FREE_DAYS + 1) }, now), true);

console.log("\nNever erase a paying subscriber");
check("paid + ancient sign-in - keep", isStaleFreeAccount({ lastSignInMs: ago(5000), tier: "paid" }, now), false);

console.log("\nMissing data is never grounds to delete");
check("no sign-in, recent creation - keep", isStaleFreeAccount({ createdMs: ago(10), tier: "free" }, now), false);
check("no sign-in, old creation - erase", isStaleFreeAccount({ createdMs: ago(INACTIVE_FREE_DAYS + 5), tier: "free" }, now), true);
check("neither time known - keep", isStaleFreeAccount({ tier: "free" }, now), false);
check("garbage times - keep", isStaleFreeAccount({ lastSignInMs: NaN, createdMs: "x", tier: "free" }, now), false);
check("zero sign-in falls back to creation", isStaleFreeAccount({ lastSignInMs: 0, createdMs: ago(10), tier: "free" }, now), false);

console.log(fails ? `\n${fails} FAILED` : "\nall passed");
process.exit(fails ? 1 : 0);

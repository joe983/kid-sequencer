// Read the app's audio self-reports (Firestore `audioReports`, written by
// index.html `_ahReportPrevious`). Read-only. Clients can't read that collection,
// so this borrows the Firebase CLI's own login (`firebase login`) through
// firebase-tools' auth helpers — the token stays in memory, never printed or saved.
//
//   node tools/read-audio-reports.js            # newest 20, summarised
//   node tools/read-audio-reports.js 5 --full   # newest 5, whole records as JSON
const { execSync } = require("child_process");
const path = require("path");

const PROJECT = "kid-sequencer";
const limit = Number(process.argv[2]) || 20;
const full = process.argv.includes("--full");

async function accessToken(){
  const root = execSync("npm root -g", { encoding: "utf8" }).trim();
  const lib = path.join(root, "firebase-tools", "lib");
  const account = require(path.join(lib, "auth")).getGlobalDefaultAccount();   // the `firebase login` user
  if(!account) throw new Error("Not logged in — run `firebase login` first.");
  await require(path.join(lib, "requireAuth")).requireAuth({ user: account.user, tokens: account.tokens });
  return require(path.join(lib, "apiv2")).getAccessToken();
}

(async () => {
  const token = await accessToken();
  const res = await fetch(
    `https://firestore.googleapis.com/v1/projects/${PROJECT}/databases/(default)/documents:runQuery`,
    {
      method: "POST",
      headers: { Authorization: "Bearer " + token, "Content-Type": "application/json" },
      body: JSON.stringify({ structuredQuery: {
        from: [{ collectionId: "audioReports" }],
        orderBy: [{ field: { fieldPath: "createdAt" }, direction: "DESCENDING" }],
        limit,
      }}),
    });
  if(!res.ok){ console.error("Firestore", res.status, (await res.text()).slice(0, 400)); process.exit(1); }
  const rows = (await res.json()).filter(r => r.document);
  if(!rows.length){ console.log("No audio reports yet."); return; }
  for(const { document: d } of rows){
    const at = d.fields.createdAt && d.fields.createdAt.timestampValue;
    let r; try{ r = JSON.parse(d.fields.report.stringValue); }catch(e){ r = { unparsable: d.fields.report.stringValue }; }
    if(full){ console.log(JSON.stringify({ at, ...r }, null, 1)); continue; }
    const dev = /iPad|Macintosh/.test(r.ua || "") && r.touch > 1 ? "iPad" : /iPhone/.test(r.ua || "") ? "iPhone" : (r.ua || "?").slice(0, 40);
    const safari = ((r.ua || "").match(/Version\/([\d.]+)/) || [])[1] || "-";
    const last = (r.hist || []).slice(-1)[0] || {};
    console.log(`\n${at}  ${r.trigger}  ${dev} Safari ${safari}  ${r.path}`);
    console.log(`  state ${r.state}  clock moving ${r.moving}  contexts ${r.contexts}  rebuilds ${r.rebuilds}  live ${r.liveNodes}`);
    console.log(`  levels ${JSON.stringify(last.lv || {})}  late ${r.lateSteps} dropped ${r.dropped} worst ${r.worstTickLateMs}ms  gap ${r.gapMs}ms`);
    if(r.events && r.events.length) console.log("  events: " + r.events.join(" | "));
  }
})().catch(e => { console.error(e.message || e); process.exit(1); });

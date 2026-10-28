# Data Protection Impact Assessment — Kid Sequencer

**Controller:** Malaclypse Applications, 27 Lister Road, Sheffield, S7 5AG, United Kingdom
**Contact:** admin@kid-sequencer.com
**Service:** Kid Sequencer (https://kid-sequencer.web.app, https://kid-sequencer.com) and the unlisted game "Late for Music Class" (/school-music-run/)
**Version:** 1.0 — DRAFT, written 12 October 2026 · **Next review:** 12 October 2027, or before any change listed in §7
**Status:** DRAFT for the owner to read, correct and sign. Statements marked **[CONFIRM]** are things I could not verify from the code and must be checked by a person.

> This is a working assessment in the shape of the ICO's DPIA template and the 15 standards of the Age Appropriate Design Code ("Children's Code"). It is not legal advice. If any residual risk in §5 stays "high", the ICO must be consulted before launch.

---

## 1. Why a DPIA

Kid Sequencer is a music app aimed at children (roughly primary age) that is also used on school devices. The Children's Code applies to online services likely to be accessed by children and expects a DPIA. The 2026-10-12 redesign changed the service so that **children are not the data subjects of any account**; this document records the design, the remaining risks, and what was done about them.

## 2. Description of the processing

### 2.1 Nature — what happens to data

| Stream | Who | Data | Where it goes |
|---|---|---|---|
| **A. Playing the app** (no account) | Anyone, incl. children and pupils | Nothing is collected about the person. Tunes live in the page. Settings/lesson progress in the browser's own storage (never sent). | Stays on the device |
| **B. Anonymous audio diagnostics** | Everyone, automatically | Browser/device description (user-agent), audio state and a few timing numbers, page path/query, timestamp. No name, no account id, no IP stored by us. **Added 2026-10-28:** when a worksheet scan fails, the scanner's decision numbers (frame brightness, mark counts/sizes, which check refused, and — for a sheet it locked onto — a map of which grid cells looked coloured). Never the camera image. Notice updated the same day; owner to re-assess per §7. | Firestore `audioReports` (EU), deleted after **30 days** by `purgeOldData` |
| **C. Grown-up account** | Adults (parents, carers, teachers) who choose to sign up | Email, password (hashed by Firebase Authentication), plan/tier, AI-track and save-slot counters, saved tunes **including the names typed for them**, generated MP3s | Firebase Auth, Firestore `users/{uid}`, Storage `users/{uid}/…` |
| **D. Subscription** | Adults who subscribe | Stripe customer reference and subscription state held by us; card and billing details held only by Stripe (merchant of record) | Stripe; our Firestore holds `stripeCustomerId`, `tier` |
| **E. AI songs** | Pro adults | The note pattern (pitches, lengths, tempo, style) is POSTed by a Cloud Function to the music engine on Modal, which returns an MP3. No name/email/uid is sent. | Modal (processor); MP3 kept in the account's Storage folder |
| **F. Scanner debug upload** | Only an adult who switches on `?scandebug=1` and presses Send | Diagnostic log + up to two worksheet photos, tied to the account | Firestore `users/{uid}/scanlogs`, deleted after **30 days** |
| **G. Website delivery** | Everyone | Files are served by Google (Firebase Hosting; Firebase SDK libraries from gstatic.com), so Google's servers see the visitor's IP address as for any website. Fonts are self-hosted (changed 2026-10-12). | Google |

Removed on 2026-10-12: the game's public leaderboard (children typed a free-text name shown to all players), the world-writable `runnerScores` collection, the Google Fonts requests from the game, and the open seed-audio upload path.

### 2.2 Scope

- **Volume (audit 2026-10-12):** 10 sign-in accounts (7 created in October 2026), 3 profile documents (2 paid, 1 free), 113 diagnostics records. Small scale, but growth is expected.
- **Categories:** ordinary personal data only. No special-category data. No location. No profiling, no advertising, no analytics cookies.
- **Children:** the intended *users* include children; the intended *account holders* and *customers* are adults. No child is asked for a name, email, date of birth or any identifier.
- **Retention:** diagnostics and scan logs 30 days; free accounts deleted after 2 years without sign-in; paid accounts until deleted by the holder; Stripe keeps payment records as the law requires. Every account can erase itself ("Delete my account and data"), which also cancels any subscription.
- **Geography:** Firestore `eur3` (EU multi-region), Storage `europe-west2` (London), Cloud Functions `europe-west1` (Belgium). Google, Stripe and Modal may process outside the UK/EEA under their standard terms **[CONFIRM Modal region and its DPA]**.

### 2.3 Context

- **Relationship:** parents/carers and teachers are the customers. Children are users only, with no relationship with us that involves their data.
- **Expectations:** a free, ad-free music toy. Parents would not expect a child's details to be collected, and they are not.
- **Vulnerabilities:** young children cannot assess privacy risk or consent. Hence the design principle: *the child never identifies themselves*.
- **Schools:** pupils use the free app on school iPads with no accounts. The school is not asked to share any pupil data with us. At least five existing accounts use a school-domain email (see risk R8). A school in Thailand may be involved, so local law (PDPA) may apply to those users in addition to UK GDPR **[CONFIRM jurisdiction with the school]**.
- **Technology:** nothing novel. The AI song feature is symbolic music rendering from note data, not a model trained on or profiling people.

### 2.4 Purposes and benefits

To let children make music without friction; to let adults buy extra sounds and cloud features; to keep the app working on classroom devices (diagnostics); to take payment and meet tax obligations.

## 3. Consultation

- **Data subjects/parents/schools:** not yet consulted formally. The design came from the owner's school-based use and teacher feedback on usage. **Action:** ask the school contact(s) to read the privacy notice and the school data sheet **[to do]**.
- **Processors:** Google, Stripe and Modal terms reviewed at standard level only **[CONFIRM Modal]**.
- **DPO:** not required at this scale. The owner is the contact for data protection.

## 4. Necessity and proportionality

| Question | Assessment |
|---|---|
| Lawful basis | Accounts/purchases: **contract**. Diagnostics: **legitimate interests** (keeping the service working on classroom iPads), balanced by minimal content, no identity and 30-day retention. Optional scanner upload: **consent** (the adult switches it on and presses Send). |
| Does it achieve the purpose with less data? | Yes, deliberately. Guests give nothing. Accounts need only an email. No age, name or location is collected. |
| Consent for children (UK GDPR Art 8) | Avoided by design: accounts and checkout are for adults only, protected by an explicit "18 or over" declaration and a parent gate (a speed-bump arithmetic question, **not** identity verification). |
| Function creep | The code has no analytics, advertising or profiling. Any future telemetry needs a DPIA update (§7). |
| Quality/accuracy | Data is typed by the account holder and editable by deleting/re-saving. |
| Information to people | `privacy.html`, linked from the upgrade modal, register form and account modal; written in plain English. A child-friendly "ask a grown-up" screen sits before any sign-up. |
| Rights | Erase: in-app button. Access/rectify/restrict/object: by email to admin@kid-sequencer.com. Complaint: ICO. |
| Processors | Google (Firebase), Stripe, Modal. **[CONFIRM]** written terms are in place for each, and international-transfer mechanisms. |
| International transfers | Possible via Google/Stripe/Modal. Rely on their UK/EU adequacy or standard contractual clauses. **[CONFIRM]** |

## 5. Risks and mitigations

Likelihood (L), Severity (S): Remote / Possible / Probable · Minimal / Significant / Severe. "Residual" is after the mitigation.

| # | Risk to individuals | L | S | Mitigation in place | Residual |
|---|---|---|---|---|---|
| R1 | A child creates an account without a parent's involvement and their email/data is processed | Possible | Significant | Accounts are for adults only; register form needs an "18+" declaration; a parent gate precedes sign-up; no child-facing sign-up prompts remain (the Member tier was removed). Guests get a complete free experience. | **Low–Medium.** The gate and declaration are not verification. A determined child can pass them. |
| R2 | A child reaches the purchase flow and the account holder is charged | Possible | Significant | Parent gate before Stripe checkout for everyone, including a logged-in parent's device. Stripe handles payment. | **Low** |
| R3 | Diagnostics collected from children's devices without their awareness | Probable | Minimal | Contains no name/account/IP of ours; 30-day automatic deletion; disclosed in the notice; legitimate-interests balancing in §4. | **Low** |
| R4 | Personal information typed into a tune name (e.g. a child's real name) | Possible | Minimal | Saving needs a Pro account, which is adult-controlled; placeholder asks for no real names; deletion on request. | **Low** |
| R5 | Account takeover / unauthorised access to account data | Remote | Significant | Firebase Auth; Firestore/Storage rules restrict each user to their own data; hashed passwords. **Weaknesses:** minimum password length 6 and no email verification. | **Low–Medium.** Action: raise the minimum length and add email verification (§6). |
| R6 | Transfer of data outside UK/EEA by processors | Possible | Minimal | Primary storage in EU/London; processors on standard terms. | **Low** **[CONFIRM Modal]** |
| R7 | Data kept longer than needed | Possible | Minimal | Automated daily purge; self-service erasure; free accounts expire after 2 years. | **Low** |
| R8 | Existing accounts with school-domain emails may belong to pupils | Possible | Significant | Owner decision 2026-10-12: keep. None of the five has a payment record. | **Medium until confirmed.** Action: confirm with the school that they are staff/adults, or contact them and delete if not (§6). |
| R9 | Third parties see a child's IP address when pages load | Probable | Minimal | Fonts self-hosted; the game makes no third-party requests; remaining third party is Google hosting/SDK, disclosed. | **Low** |
| R10 | Public display of a child's free-text name (leaderboard) | — | — | **Eliminated:** cloud leaderboard and its Firestore rules removed. | **None** |
| R11 | Children contacted by strangers / exposed to user content | Remote | Severe | No chat, sharing, public profiles or user-to-user features exist. Adding any of these requires a new DPIA and Online Safety Act assessment. | **Low** |
| R12 | Mis-selling or manipulation of children (nudges) | Possible | Significant | Locked sounds show a neutral "?" and open an adult-oriented screen; no countdowns, streaks or rewards for purchase; parent gate before payment. | **Low** |

**Overall residual risk:** low, with R1, R5 and R8 as the items to close. None is high, so prior consultation with the ICO is not required, provided §6 actions are carried out.

## 6. Actions

| # | Action | Owner | Status |
|---|---|---|---|
| 1 | Fill the controller details in `privacy.html` | Owner | Done 2026-10-12 |
| 2 | Deploy `deleteMyAccount`, `purgeOldData`, new Firestore/Storage rules | Owner | Done 2026-10-12 |
| 3 | Confirm with the school that the five school-domain accounts are staff/adults (R8) | Owner | Open |
| 4 | Raise the minimum password length (≥ 8) and add email verification (R5) | Dev | Open |
| 5 | Confirm Modal's data processing terms, region, and that the pattern is not retained **[CONFIRM]** | Owner | Open |
| 6 | Confirm Google/Stripe terms and transfer mechanisms in the dashboards | Owner | Open |
| 7 | Check ICO registration / data-protection fee requirement for Malaclypse Applications | Owner | Open |
| 8 | Delete the two leftover `runnerScores` rows in the Firestore console | Owner | Open |
| 9 | Send the privacy notice and a short school data sheet to the school(s) | Owner | Open |
| 10 | Confirm whether Thai PDPA applies to pupils there and add a line to the notice if so | Owner | Open |

## 7. Re-assess this DPIA before any of these

- adding sign-in, names, avatars, classes or rosters for children
- adding chat, sharing, comments or any user-generated public content
- adding analytics, advertising, or any new third-party script/SDK
- adding new fields to diagnostics, or sending the user-agent to a new place
- changing retention periods or the data locations
- adding AI features that process anything beyond note patterns

## 8. Children's Code — 15 standards at a glance

1. **Best interests of the child** — guest-first design, no data from children.
2. **DPIA** — this document.
3. **Age-appropriate application** — accounts adult-only; parent gate.
4. **Transparency** — plain-English `privacy.html`; "ask a grown-up" screens.
5. **Detrimental use of data** — none: no ads, profiling or sale.
6. **Policies and community standards** — no user-to-user features; the notice states the rules.
7. **Default settings** — most private by default: nothing collected from a guest beyond anonymous diagnostics.
8. **Data minimisation** — email only for adults; none for children.
9. **Data sharing** — only processors needed to run the service; no sale or marketing.
10. **Geolocation** — not collected.
11. **Parental controls** — not applicable; no accounts for children.
12. **Profiling** — none.
13. **Nudge techniques** — no pressure to weaken privacy; purchase behind a parent gate.
14. **Connected toys/devices** — not applicable.
15. **Online tools** — in-app erasure; contact address for rights.

## 9. Sign-off

| | |
|---|---|
| Measures approved by | ______________________ (Malaclypse Applications) — date: __________ |
| Residual risks approved by | ______________________ — date: __________ |
| DPO / contact advice | Not appointed (small scale); contact admin@kid-sequencer.com |
| Next review date | 12 October 2027 |

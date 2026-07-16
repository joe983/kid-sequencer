/* Rhythm Trail — Band A lesson data (pure data, no logic).
   Loaded before the main IIFE; the lesson runner reads window.KidSeqLessons.
   Design spec: docs/specs/2026-07-17-note-length-course-design.md
   Narration offsets between the NARR markers are PATCHED by
   tools/install_lesson_narration.py — don't hand-edit that block.

   Pattern notes are {row, start, len, kind} in the lesson's own row space
   (row 0 = top/highest pitch). cols is always 8 (one 4/4 bar, column = 8th),
   so a beat = 2 columns; kind 'quarter' = one attack, 'eighth' = ti-ti pair. */
(function(){
  // -- shared patterns --------------------------------------------------
  const ta = (row, beat) => ({ row, start: beat * 2, len: 2, kind: "quarter" });
  const titi = (row, beat) => ({ row, start: beat * 2, len: 2, kind: "eighth" });

  const TTTT      = [ta(0,0), ta(0,1), ta(0,2), ta(0,3)];             // ta ta ta ta
  const TT_HALFBAR= [ta(0,0), ta(0,1)];                               // ta ta (rest rest)
  const TA_TITI   = [ta(0,0), ta(0,1), titi(0,2), ta(0,3)];           // ta ta ti-ti ta
  const TITI_EVERY= [titi(0,0), ta(0,1), titi(0,2), ta(0,3)];         // ti-ti ta ti-ti ta
  const REST_B3   = [ta(0,0), ta(0,1), ta(0,3)];                      // ta ta (shh) ta
  const A5_CALL   = [ta(1,0), ta(0,1), titi(1,2), ta(0,3)];           // C E titi(C) E

  const ONE_ROW = { rows: 1, freqs: [261.63], rowColors: ["#FF0000"], maxCell: 168 };
  const TWO_ROW = { rows: 2, freqs: [329.63, 261.63], rowColors: ["#FFFF00", "#FF0000"], maxCell: 140 };

  window.KidSeqLessons = {
    ORDER: ["a1", "a2", "a3", "a4", "a5"],

    // Narration sprite (single file, seeked by offset through an <audio>
    // element — immune to the iOS hardware silent switch, unlike WebAudio).
    SPRITE: "samples/lessons_a.wav", // NARR_SPRITE
    NARR: /*NARR_A_START*/ {"g_hi":[0.5,4.504,"Hi! I'm Beat!"],"g_watch":[5.304,0.649,"Watch me!"],"g_turn":[6.253,0.778,"Your turn!"],"g_press":[7.331,1.592,"Press play! ▶"],"g_yay1":[9.223,2.287,"You did it! 🎉"],"g_yay2":[11.81,2.235,"Amazing! 🎉"],"g_yay3":[14.345,1.502,"Sounds great! 🎉"],"g_try":[16.147,2.953,"Try again!"],"g_listen":[19.4,1.762,"Listen again… 👂"],"g_shift":[21.462,4.842,"Start on the first ❤!"],"g_ghost":[26.604,2.509,"Fill the sparkly squares!"],"g_help":[29.414,0.952,"I'll show you!"],"a1_intro":[30.666,3.592,"Listen… the heartbeat! ❤"],"a1_freeze":[34.558,4.37,"Dance! Then… FREEZE!"],"a1_frozen":[39.227,0.663,"FREEZE! 🥶"],"a1_touch":[40.19,3.835,"Tap a square!"],"a1_great":[44.325,2.32,"You made music! 🎵"],"a2_touch":[46.945,4.26,"Add a walking note!"],"a2_demo":[51.504,1.576,"Four walking notes!"],"a2_which":[53.381,3.2,"Which one? Tap it!"],"a2_copy":[56.881,1.279,"Build what you heard!"],"a2_gap":[58.46,3.769,"Fill the gaps!"],"a2_create":[62.53,1.992,"Make YOUR pattern!"],"a3_touch":[64.822,4.908,"Running notes! Try one!"],"a3_demo":[70.03,3.188,"Walk, walk, run, walk!"],"a3_which":[73.518,3.2,"Which one? Tap it!"],"a3_copy":[77.018,1.279,"Build what you heard!"],"a3_gap":[78.597,2.302,"Fill the gaps!"],"a3_create":[81.199,2.252,"Use running notes!"],"a4_touch":[83.751,3.883,"Make a quiet beat!"],"a4_demo":[87.934,4.367,"ta ta 🤫 ta"],"a4_which":[92.601,2.111,"Which has the quiet beat?"],"a4_copy":[95.012,3.776,"Keep the quiet beat quiet!"],"a4_rest":[99.088,3.84,"Shh! Keep it quiet! 🤫"],"a4_create":[103.228,2.266,"Use a quiet beat!"],"a5_touch":[105.794,3.605,"Two sounds! Add one more!"],"a5_which":[109.699,3.2,"Which one? Tap it!"],"a5_copy":[113.199,2.351,"Both sounds!"],"a5_create":[115.85,1.831,"Your best pattern ever!"],"a5_reveal":[117.981,3.31,"You wrote REAL music! 🎼"],"a5_done":[121.591,3.494,"You're a musician! ⭐"],"chant_tttt":[125.385,4.529,"ta ta ta ta"],"chant_tatiti":[130.214,4.833,"ta ta ti-ti ta"],"chant_rest":[135.347,4.482,"ta ta 🤫 ta"],"chant_titi":[140.13,0.675,"ti-ti!"]} /*NARR_A_END*/,

    LESSONS: {

      a1: {
        title: "The Heartbeat", band: "A", unit: 1, next: "a2",
        level: ONE_ROW, palette: ["quarter"],
        steps: [
          // Steady beat first (Kodaly K): hear it, move to it — nothing to build yet.
          { type: "listen", narr: "a1_intro", bars: 1 },
          { type: "freeze", narr: "a1_freeze", rounds: 2 },
          // First touch: any sound placed on the heartbeat is a win (can't fail).
          { type: "build", narr: "a1_touch", pass: { kind: "count", minNotes: 1 },
            yayNarr: "a1_great", nudge: "grid" },
        ],
      },

      a2: {
        title: "Walking Notes", band: "A", unit: 1, next: "a3",
        level: ONE_ROW, palette: ["quarter"],
        steps: [
          // TOUCH: preloaded playing pattern, one-tap prompt (Ableton modify-first).
          { type: "build", narr: "a2_touch", preset: [ta(0,0)],
            pass: { kind: "count", minNotes: 2 }, nudge: "grid" },
          { type: "demo", narr: "a2_demo", chant: "chant_tttt", pattern: TTTT },
          // Mandatory motor-free ear-check (Gordon PMMA same/different).
          { type: "which", narr: "a2_which", options: [TTTT, TT_HALFBAR], answer: 0 },
          { type: "build", narr: "a2_copy", target: TTTT,
            pass: { kind: "match", shifted: true } },
          { type: "build", narr: "a2_gap", preset: [ta(0,0), ta(0,2)], locked: true,
            target: TTTT, pass: { kind: "match" } },
          { type: "build", narr: "a2_create",
            pass: { kind: "count", minNotes: 3, use: { quarter: 3 } }, nudge: "grid" },
        ],
      },

      a3: {
        title: "Running Notes", band: "A", unit: 1, next: "a4",
        level: ONE_ROW, palette: ["quarter", "eighth"],
        steps: [
          { type: "build", narr: "a3_touch", preset: [ta(0,0), ta(0,1)],
            pass: { kind: "count", minNotes: 3, use: { eighth: 1 } }, nudge: "tool-eighth" },
          { type: "demo", narr: "a3_demo", chant: "chant_tatiti", pattern: TA_TITI },
          { type: "which", narr: "a3_which", options: [TA_TITI, TTTT], answer: 0 },
          { type: "build", narr: "a3_copy", target: TA_TITI,
            pass: { kind: "match", shifted: true } },
          { type: "build", narr: "a3_gap", preset: [ta(0,0), titi(0,2)], locked: true,
            target: TA_TITI, pass: { kind: "match" } },
          { type: "build", narr: "a3_create",
            pass: { kind: "count", minNotes: 3, use: { eighth: 2 } }, nudge: "tool-eighth" },
        ],
      },

      a4: {
        title: "The Quiet Beat", band: "A", unit: 1, next: "a5",
        level: ONE_ROW, palette: ["quarter", "eighth"],
        steps: [
          // Remove-a-note opener: silence is something you MAKE.
          { type: "build", narr: "a4_touch", preset: TTTT,
            pass: { kind: "count", minNotes: 3, maxNotes: 3, use: { quarter: 3 } },
            nudge: "grid" },
          { type: "demo", narr: "a4_demo", chant: "chant_rest", pattern: REST_B3 },
          { type: "which", narr: "a4_which", options: [REST_B3, TTTT], answer: 0 },
          // keep-the-rest: filling the quiet beat IS the error (rest is assessable).
          { type: "build", narr: "a4_copy", target: REST_B3,
            pass: { kind: "match", restBeats: [2], restNarr: "a4_rest" } },
          { type: "build", narr: "a4_create",
            pass: { kind: "count", minNotes: 2, minEmptyBeats: 1 }, nudge: "grid" },
        ],
      },

      a5: {
        title: "Pattern Play", band: "A", unit: 1, next: null,
        level: TWO_ROW, palette: ["quarter", "eighth"],
        steps: [
          { type: "build", narr: "a5_touch", preset: [ta(1,0), ta(0,2)],
            pass: { kind: "count", minNotes: 3 }, nudge: "grid" },
          { type: "which", narr: "a5_which", options: [A5_CALL, TITI_EVERY.map(n => ({...n, row: 1}))], answer: 0 },
          { type: "build", narr: "a5_copy", target: A5_CALL,
            pass: { kind: "match", shifted: true } },
          { type: "build", narr: "a5_create",
            pass: { kind: "count", minNotes: 4, use: { quarter: 1, eighth: 1 } },
            nudge: "grid", keepGrid: true },
          // The reveal: the stave slides up on the child's OWN pattern.
          { type: "reveal", narr: "a5_reveal" },
        ],
        doneNarr: "a5_done",
      },
    },
  };
})();

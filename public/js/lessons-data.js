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
    SPRITE: "samples/lessons_a.mp3", // NARR_SPRITE
    NARR: /*NARR_A_START*/ {"g_hi":[0.5,3.905,"Hi! I'm Beat!"],"g_watch":[4.705,0.576,"Watch me!"],"g_turn":[5.581,0.698,"Your turn!"],"g_press":[6.58,1.27,"Press play! ▶"],"g_yay1":[8.15,1.981,"You did it! 🎉"],"g_yay2":[10.431,2.261,"Amazing! 🎉"],"g_yay3":[12.993,1.178,"Sounds great! 🎉"],"g_try":[14.47,2.417,"Try again!"],"g_listen":[17.188,1.334,"Listen again… 👂"],"g_shift":[18.821,3.728,"Start on the first ❤!"],"g_ghost":[22.849,2.094,"Fill the sparkly squares!"],"g_help":[25.243,0.815,"I'll show you!"],"a1_intro":[26.358,2.641,"Listen… the heartbeat! ❤"],"a1_freeze":[29.299,3.688,"Dance! Then… FREEZE!"],"a1_frozen":[33.287,0.6,"FREEZE! 🥶"],"a1_touch":[34.187,3.183,"Tap a square!"],"a1_great":[37.67,1.785,"You made music! 🎵"],"a2_touch":[39.754,3.535,"Add a walking note!"],"a2_demo":[43.589,1.15,"Four walking notes!"],"a2_which":[45.039,2.65,"Which one? Tap it!"],"a2_copy":[47.99,1.085,"Build what you heard!"],"a2_gap":[49.374,3.152,"Fill the gaps!"],"a2_create":[52.826,1.642,"Make YOUR pattern!"],"a3_touch":[54.768,4.235,"Running notes! Try one!"],"a3_demo":[59.303,2.64,"Walk, walk, run, walk!"],"a3_which":[62.243,2.65,"Which one? Tap it!"],"a3_copy":[65.193,1.085,"Build what you heard!"],"a3_gap":[66.578,1.912,"Fill the gaps!"],"a3_create":[68.789,1.794,"Use running notes!"],"a4_touch":[70.884,3.354,"Make a quiet beat!"],"a4_demo":[74.538,3.843,"ta ta 🤫 ta"],"a4_which":[78.681,1.65,"Which has the quiet beat?"],"a4_copy":[80.631,3.155,"Keep the quiet beat quiet!"],"a4_rest":[84.086,2.902,"Shh! Keep it quiet! 🤫"],"a4_create":[87.288,1.828,"Use a quiet beat!"],"a5_touch":[89.415,3.032,"Two sounds! Add one more!"],"a5_which":[92.747,2.65,"Which one? Tap it!"],"a5_copy":[95.697,1.934,"Both sounds!"],"a5_create":[97.931,1.559,"Your best pattern ever!"],"a5_reveal":[99.79,2.605,"You wrote REAL music! 🎼"],"a5_done":[102.695,3.0,"You're a musician! ⭐"],"chant_tttt":[105.995,4.143,"ta ta ta ta"],"chant_tatiti":[110.437,4.378,"ta ta ti-ti ta"],"chant_rest":[115.115,4.137,"ta ta 🤫 ta"],"chant_titi":[119.553,0.691,"ti-ti!"]} /*NARR_A_END*/,

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

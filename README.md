# SI Mock Test System — JKSSB Sub-Inspector (J&K Police)

A plan-driven mock-test generation system to prepare for the **Sub-Inspector (J&K Police)** written examination in **70 days**. The AI reads a fixed study plan, generates the next mock test on demand, guarantees no repeated questions, and tracks progress — all while staying fast and within context even after hundreds of tests exist.

---

## How to use it (student workflow)

1. Print **`STUDY_PLAN.md`** to PDF. Each day lists the topic(s) to revise and 3 mock tests (Morning / Afternoon / Late).
2. Each morning, revise the day's listed topic(s)/subject(s).
3. To get a test, start a session and say: **"Generate the next mock test."**
   - You never need to type a subject or topic — the plan already knows what's next.
4. The generated test is saved as JSON in `mock-tests/tests/`. Attempt it, then repeat for the day's remaining sessions.

To generate several at once, say: *"Generate the next 3 mock tests"* (the day's set).

---

## Repository layout

```
Si-mock-tests/
├── README.md                         ← this file
├── syllabus_si.md                    ← official SI syllabus + exam blueprint
├── STUDY_PLAN.md                     ← printable 70-day plan (⬜ pending / ✅ done)
├── .kiro/steering/
│   └── mock-test-prompt-si.md        ← generation ruleset (always loaded by the AI)
└── mock-tests/
    ├── _build_plan.py                ← one-off generator for the plan (build tool)
    ├── config.json                   ← counters + next_test pointer  (read FIRST, tiny)
    ├── manifest.json                 ← machine-readable plan: one spec per test
    ├── tests/                        ← generated test JSONs live here (output only)
    │   └── <N>_test_<subject>_<slug>.json
    └── history/                      ← question fingerprints, SHARDED by subject
        ├── A.json  B.json  C.json  D.json  E.json  F.json
```

---

## The exam (fixed blueprint)

100 MCQs · 2 marks each · −0.5 negative marking · 120 minutes.

| Part | Subject | Q | Level |
|---|---|---|---|
| A | General Intelligence & Reasoning | 20 | Graduation |
| B | General Awareness (India + J&K) | 20 | Graduation |
| C | Quantitative Aptitude | 15 | 10th |
| D | English Comprehension | 15 | Graduation |
| E | Mathematical Abilities | 15 | 10th |
| F | Computer Proficiency | 15 | 10th |

---

## The 70-day plan at a glance

- **207 mock tests · ~10,310 questions** total.
- **Phase 1 (Days 1–35):** Foundation, topic-wise. 3 tests/day (30/40/50 Q), subjects interleaved, weekly cumulative revision. Difficulty `foundation` → `standard`.
- **Phase 2 (Days 36–55):** Consolidation. Full-subject multi-topic tests + first full-length 100Q mocks (Days 39, 43, 47, 51, 55). Difficulty `advanced` / `exam`.
- **Phase 3 (Days 56–69):** Simulation. A full 100Q exam-style mock every day + sectional and rapid weak-area revision. Difficulty `exam` / `advanced`.
- **Day 70:** Exam day — light revision only.

---

## How the AI generates a test (every session)

Defined in `.kiro/steering/mock-test-prompt-si.md`. Summary:

1. Read `mock-tests/config.json` → get `next_test` (N).
2. Read entry **N** in `mock-tests/manifest.json` → subject, topics, question count, difficulty, filename.
3. Read only the relevant subject shard(s) in `mock-tests/history/` → avoid repeats.
4. Generate the test per the ruleset (8 question types in fixed proportions, difficulty tilt, close distractors, full explanations).
5. **Post-generation:** save the test, append question fingerprints to the subject shard, increment `config.json`, flip status to ✅ in `manifest.json` and `STUDY_PLAN.md`.

### Why it never runs out of context
The AI only ever reads three small things: `config.json`, the single needed `manifest.json` entry, and one subject history shard. It **never** bulk-reads the growing `tests/` folder. History is split into 6 subject files so each stays small.

### No repeated questions
Every generated question's fingerprint (normalized stem + core concept) is stored in its subject shard. Before adding a new question the AI checks that shard and rejects both exact and near-duplicate (reworded) matches.

---

## Question format (per test JSON)

Each test file follows a fixed schema: `subject`, `topic`, `total_questions`, and a `questions[]` array where each item has `id`, `subject`, `questionText`, `options` (4), `correctAnswer` (exact copy of one option), and `explanation`. Every explanation states why the correct option is right **and** why each of the other three is wrong. Eight question types are used: Single Correct, Statement-based, Assertion–Reason, Matching, Multiple-Correct, Fill-in-the-Blank, Numerical Value, and Data Interpretation.

---

## Re-planning (rare)

`mock-tests/_build_plan.py` regenerates `manifest.json`, `STUDY_PLAN.md`, `config.json`, and the empty history shards from scratch. Only run it **before** any tests are generated (or intentionally to rebuild the plan), as it resets counters:

```bash
python3 mock-tests/_build_plan.py
```

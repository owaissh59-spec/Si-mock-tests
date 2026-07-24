#!/usr/bin/env python3
"""
Study-plan generator for the JKSSB SI (J&K Police) mock-test system.

Produces (all kept in sync):
  - mock-tests/manifest.json   -> machine-readable plan (source of truth for generation)
  - STUDY_PLAN.md              -> human-readable, printable 70-day plan
  - mock-tests/config.json     -> counters + next_test pointer
  - mock-tests/history/<A-F>.json -> empty per-subject question fingerprint shards

Run:  python mock-tests/_build_plan.py
This is a build tool. Re-running regenerates the plan from scratch, so only run
it before any tests have been generated (or intentionally to re-plan).
"""

import json
import os
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MT = os.path.join(ROOT, "mock-tests")

SUBJECT_NAMES = {
    "A": "General Intelligence & Reasoning",
    "B": "General Awareness",
    "C": "Quantitative Aptitude",
    "D": "English Comprehension",
    "E": "Mathematical Abilities",
    "F": "Computer Proficiency",
}
LEVEL = {"A": "Graduation", "B": "Graduation", "C": "10th", "D": "Graduation", "E": "10th", "F": "10th"}

# (long topic name, filename slug)
TOPICS = {
    "A": [
        ("Analogies (Semantic, Symbolic/Number, Figural)", "analogies"),
        ("Classification (Semantic, Symbolic/Number, Figural)", "classification"),
        ("Series (Semantic, Number, Figural)", "series"),
        ("Coding & De-coding", "coding-decoding"),
        ("Problem Solving & Arithmetical Reasoning", "problem-solving"),
        ("Word Building, Numerical & Symbolic Operations", "word-symbol-ops"),
        ("Venn Diagrams & Syllogism", "venn-syllogism"),
        ("Statement-Conclusion & Drawing Inferences", "statement-conclusion"),
        ("Space Orientation, Visualization, Embedded & Paper Folding", "spatial"),
        ("Blood Relations, Direction Sense, Order & Ranking", "relations-directions"),
        ("Indexing, Address/Date-City Matching, Code Classification, Letters/Numbers", "matching-indexing"),
        ("Critical Thinking, Emotional & Social Intelligence, Observation, Trends", "critical-ei-si"),
    ],
    "B": [
        ("Ancient Indian History", "ancient-history"),
        ("Medieval Indian History", "medieval-history"),
        ("Modern Indian History & Freedom Struggle", "modern-history"),
        ("History of Jammu & Kashmir", "jk-history"),
        ("Indian Geography", "indian-geography"),
        ("Physical & World Geography", "world-geography"),
        ("Geography of Jammu & Kashmir", "jk-geography"),
        ("Indian Polity & Constitution", "polity"),
        ("Economics & General Policy (India)", "economy"),
        ("J&K Economy, Culture & Administration", "jk-gk"),
        ("General Science: Physics", "science-physics"),
        ("General Science: Chemistry", "science-chemistry"),
        ("General Science: Biology", "science-biology"),
        ("Scientific Research & Everyday Science", "sci-research"),
        ("Sports", "sports"),
        ("Static GK (Books, Awards, Days, Institutions)", "static-gk"),
        ("National Current Affairs & People in News", "current-affairs-national"),
        ("International & J&K Current Affairs", "current-affairs-intl-jk"),
    ],
    "C": [
        ("Number System, Decimals, Fractions & Simplification", "number-system"),
        ("Percentage", "percentage"),
        ("Ratio & Proportion", "ratio-proportion"),
        ("Averages", "averages"),
        ("Square Roots & Surds", "square-roots"),
        ("Simple Interest", "simple-interest"),
        ("Compound Interest", "compound-interest"),
        ("Profit, Loss & Discount", "profit-loss"),
        ("Partnership Business", "partnership"),
        ("Mixture & Alligation", "mixture-alligation"),
        ("Time, Speed & Distance", "time-distance"),
        ("Time & Work", "time-work"),
    ],
    "D": [
        ("Synonyms", "synonyms"),
        ("Antonyms", "antonyms"),
        ("Homonyms & One-Word Substitution", "homonyms-ows"),
        ("Spellings & Detecting Misspelt Words", "spellings"),
        ("Idioms & Phrases", "idioms-phrases"),
        ("Spot the Error", "spot-error"),
        ("Improvement of Sentences", "sentence-improvement"),
        ("Fill in the Blanks", "fill-blanks"),
        ("Active/Passive Voice", "voice"),
        ("Direct/Indirect Narration", "narration"),
        ("Sentence & Paragraph Shuffling (Para Jumbles)", "para-jumbles"),
        ("Cloze Passage", "cloze"),
        ("Comprehension Passage", "comprehension"),
    ],
    "E": [
        ("Algebra: Identities & Simplification", "algebra"),
        ("Elementary Surds & Graphs of Linear Equations", "surds-graphs"),
        ("Geometry: Triangles (Centres, Congruence, Similarity)", "triangles"),
        ("Geometry: Circles (Chords, Tangents, Angles)", "circles"),
        ("Mensuration: 2D Figures", "mensuration-2d"),
        ("Mensuration: 3D Solids", "mensuration-3d"),
        ("Trigonometry: Ratios & Complementary Angles", "trigonometry"),
        ("Heights & Distances", "heights-distances"),
        ("Statistics: Tables, Graphs & Central Tendency", "statistics"),
        ("Probability (Simple)", "probability"),
    ],
    "F": [
        ("Computer Fundamentals & Organization", "computer-basics"),
        ("CPU, Memory, Ports & Backup Devices", "cpu-memory"),
        ("Windows OS, Explorer & Keyboard Shortcuts", "windows-os"),
        ("MS Word", "ms-word"),
        ("MS Excel", "ms-excel"),
        ("MS PowerPoint", "ms-powerpoint"),
        ("Internet, Web, Email & e-Banking", "internet-email"),
        ("Networking Devices & Protocols", "networking"),
        ("Cyber Security: Threats & Prevention", "cyber-security"),
    ],
}

SESSION_NAMES = ["Morning", "Afternoon", "Late"]

tests = []            # list of dicts (manifest entries)
plan_days = []        # list of (day, phase, [test dicts]) for markdown
counter = 0


def add_test(day, phase, session, subject, subject_label, topics, qcount, difficulty, ttype, slug):
    global counter
    counter += 1
    filename = f"{counter}_test_{subject}_{slug}.json"
    entry = {
        "number": counter,
        "day": day,
        "phase": phase,
        "session": SESSION_NAMES[session],
        "type": ttype,
        "subject": subject,                 # letter A-F, or "FULL"
        "subject_name": subject_label,
        "level": LEVEL.get(subject, "Mixed (per subject)"),
        "topics": topics,
        "total_questions": qcount,
        "difficulty_profile": difficulty,
        "filename": filename,
        "status": "pending",
    }
    tests.append(entry)
    return entry


# ---------------------------------------------------------------------------
# PHASE 1 — Foundation / topic-wise (Days 1-35)
# 3 tests/day (30 / 40 / 50 Q). Subjects interleaved. Weekly cumulative revision.
# ---------------------------------------------------------------------------
# Build an interleaved queue of (subject, (topic_name, slug)).
queues = {s: list(TOPICS[s]) for s in "ABCDEF"}
interleaved = []
order = list("ABCDEF")
# First full pass: round-robin so subjects alternate and everything is covered.
while any(queues[s] for s in order):
    for s in order:
        if queues[s]:
            interleaved.append((s, queues[s].pop(0)))
# Second pass for reinforcement of higher-weight / larger subjects (A, B, C, D).
reinforce = []
for s in ["A", "B", "C", "D", "A", "B", "C", "E", "D", "A", "B", "F"]:
    reinforce.append((s, TOPICS[s][len(reinforce) % len(TOPICS[s])]))

P1_SIZES = [30, 40, 50]
week_subjects = {}   # week_no -> set of subjects seen (for revision)
idx = 0
for day in range(1, 36):
    week = (day - 1) // 7 + 1
    week_subjects.setdefault(week, [])
    day_tests = []
    is_revision_day = (day % 7 == 0)  # days 7,14,21,28,35 -> evening revision
    for session in range(3):
        diff = "foundation" if day <= 16 else "standard"
        qcount = P1_SIZES[session]
        if is_revision_day and session == 2:
            subs = "".join(sorted(set(week_subjects[week]))) or "A-F"
            topics = f"Cumulative revision — Week {week} topics ({subs})"
            add_test(day, 1, session, subs[0] if len(subs) == 1 else "FULL",
                     "Mixed (week revision)", topics, qcount, "standard",
                     "Revision (topic-wise, cumulative)", f"revision-wk{week}")
            day_tests.append(tests[-1])
            continue
        # pull next topic
        if idx < len(interleaved):
            s, (tname, slug) = interleaved[idx]
        else:
            s, (tname, slug) = reinforce[(idx - len(interleaved)) % len(reinforce)]
            diff = "standard"
        idx += 1
        week_subjects[week].append(s)
        add_test(day, 1, session, s, SUBJECT_NAMES[s], tname, qcount, diff,
                 "Topic-wise", slug)
        day_tests.append(tests[-1])
    plan_days.append((day, 1, day_tests))


# ---------------------------------------------------------------------------
# PHASE 2 — Consolidation / multi-topic + first full-length mocks (Days 36-55)
# Morning: full-subject multi-topic (50Q, advanced). Afternoon: second subject
# multi-topic (60Q, advanced). Late: cumulative revision (50Q) OR full mock.
# Full-length mocks on days 39, 43, 47, 51, 55.
# ---------------------------------------------------------------------------
full_mock_days_p2 = {39, 43, 47, 51, 55}
subj_cycle = list("ABCDEF")
full_no = 0
sc = 0
for day in range(36, 56):
    day_tests = []
    # Morning: subject multi-topic
    s1 = subj_cycle[sc % 6]; sc += 1
    add_test(day, 2, 0, s1, SUBJECT_NAMES[s1],
             f"All topics of {SUBJECT_NAMES[s1]} (mixed)", 50, "advanced",
             "Subject full (multi-topic)", f"{s1}-mixed")
    day_tests.append(tests[-1])
    # Afternoon: next subject multi-topic
    s2 = subj_cycle[sc % 6]; sc += 1
    add_test(day, 2, 1, s2, SUBJECT_NAMES[s2],
             f"All topics of {SUBJECT_NAMES[s2]} (mixed)", 60, "advanced",
             "Subject full (multi-topic)", f"{s2}-mixed")
    day_tests.append(tests[-1])
    # Late: full mock or cumulative revision
    if day in full_mock_days_p2:
        full_no += 1
        add_test(day, 2, 2, "FULL", "Full Test (A-F, 20:20:15:15:15:15)",
                 "Full syllabus — all subjects A-F", 100, "exam",
                 "Full-length mock", f"fulllength-{full_no}")
    else:
        add_test(day, 2, 2, "FULL", "Mixed (cumulative revision)",
                 "Cumulative revision across all covered subjects", 50, "advanced",
                 "Revision (cumulative)", "revision-cumulative")
    day_tests.append(tests[-1])
    plan_days.append((day, 2, day_tests))


# ---------------------------------------------------------------------------
# PHASE 3 — Simulation & revision (Days 56-69)
# Morning: full-length 100Q mock (exam). Afternoon: sectional revision (50Q,
# advanced). Late: rapid mixed revision / weak-area (40Q, advanced).
# Day 70 = EXAM DAY (no new test).
# ---------------------------------------------------------------------------
sc2 = 0
for day in range(56, 70):
    day_tests = []
    full_no += 1
    add_test(day, 3, 0, "FULL", "Full Test (A-F, 20:20:15:15:15:15)",
             "Full syllabus — all subjects A-F (exam simulation)", 100, "exam",
             "Full-length mock", f"fulllength-{full_no}")
    day_tests.append(tests[-1])
    # Afternoon sectional revision — cycle subjects
    s1 = subj_cycle[sc2 % 6]; sc2 += 1
    add_test(day, 3, 1, s1, SUBJECT_NAMES[s1],
             f"Sectional revision — {SUBJECT_NAMES[s1]}", 50, "advanced",
             "Sectional revision", f"{s1}-revision")
    day_tests.append(tests[-1])
    # Late rapid mixed revision
    s2 = subj_cycle[sc2 % 6]; sc2 += 1
    add_test(day, 3, 2, s2, SUBJECT_NAMES[s2],
             f"Rapid mixed revision & weak-area drill — {SUBJECT_NAMES[s2]}", 40,
             "advanced", "Rapid revision", f"{s2}-rapid")
    day_tests.append(tests[-1])
    plan_days.append((day, 3, day_tests))


# ---------------------------------------------------------------------------
# WRITE manifest.json
# ---------------------------------------------------------------------------
manifest = {
    "project": "JKSSB Sub-Inspector (J&K Police) — Mock Test Plan",
    "generated_at": str(date.today()),
    "total_tests": len(tests),
    "medium": "English",
    "exam_day": 70,
    "phases": {
        "1": "Foundation / topic-wise (Days 1-35)",
        "2": "Consolidation / multi-topic + first full mocks (Days 36-55)",
        "3": "Simulation & revision (Days 56-69); Day 70 = EXAM",
    },
    "tests": tests,
}
with open(os.path.join(MT, "manifest.json"), "w") as f:
    json.dump(manifest, f, indent=2, ensure_ascii=False)

# ---------------------------------------------------------------------------
# WRITE config.json
# ---------------------------------------------------------------------------
config = {
    "project": "JKSSB Sub-Inspector (J&K Police) Mock Test System",
    "medium": "English",
    "exam_day": 70,
    "total_planned_tests": len(tests),
    "test_counter": 0,
    "next_test": 1,
    "last_generated": None,
    "updated_at": str(date.today()),
    "duplicate_policy": "no-exact-and-no-near-duplicate (check subject history shard)",
    "history_shards": {s: f"mock-tests/history/{s}.json" for s in "ABCDEF"},
    "files": {
        "manifest": "mock-tests/manifest.json",
        "study_plan": "STUDY_PLAN.md",
        "syllabus": "syllabus_si.md",
        "prompt": ".kiro/steering/mock-test-prompt-si.md",
        "tests_dir": "mock-tests/tests/",
    },
}
with open(os.path.join(MT, "config.json"), "w") as f:
    json.dump(config, f, indent=2, ensure_ascii=False)

# ---------------------------------------------------------------------------
# WRITE empty history shards
# ---------------------------------------------------------------------------
os.makedirs(os.path.join(MT, "history"), exist_ok=True)
for s in "ABCDEF":
    shard = {"subject": s, "subject_name": SUBJECT_NAMES[s], "count": 0, "questions": []}
    with open(os.path.join(MT, "history", f"{s}.json"), "w") as f:
        json.dump(shard, f, indent=2, ensure_ascii=False)

# ---------------------------------------------------------------------------
# WRITE STUDY_PLAN.md
# ---------------------------------------------------------------------------
phase_titles = {
    1: "PHASE 1 — Foundation (Topic-wise Building)  ·  Days 1–35",
    2: "PHASE 2 — Consolidation (Multi-topic + First Full Mocks)  ·  Days 36–55",
    3: "PHASE 3 — Simulation & Revision (Full-length + Weak-area)  ·  Days 56–69",
}
phase_notes = {
    1: ("3 tests every day — **Morning 30Q · Afternoon 40Q · Late 50Q**. Subjects are "
        "interleaved so no subject goes cold. Difficulty starts at *foundation* (easy-tilted) "
        "and moves to *standard* from Day 17. Every 7th day the late session is a **cumulative "
        "revision** of that week's topics."),
    2: ("3 tests every day — **Morning 50Q (full subject) · Afternoon 60Q (full subject) · "
        "Late 50Q revision or a 100Q FULL MOCK**. Difficulty is *advanced*. Full-length "
        "100-question mocks land on Days 39, 43, 47, 51, 55."),
    3: ("3 tests every day — **Morning 100Q FULL MOCK (exam simulation) · Afternoon 50Q "
        "sectional revision · Late 40Q rapid/weak-area drill**. Difficulty is *exam / advanced*. "
        "**Day 70 is the EXAM** — no new test, only light confidence revision and rest."),
}

lines = []
lines.append("# 70-Day Study & Mock-Test Plan — JKSSB Sub-Inspector (J&K Police)")
lines.append("")
lines.append("> **Medium:** English  ·  **Exam:** Day 70  ·  **Daily study:** 7–10 hours across 3 sessions.")
lines.append(">")
lines.append("> **How to use each day:** In the morning, revise the topic(s)/subject(s) listed for that day. "
             "Then attempt the day's mock tests in order (Morning → Afternoon → Late). To generate a test, "
             'ask: *"Generate the next mock test."* The system picks the next ⬜ test below automatically.')
lines.append(">")
lines.append(f"> **Total planned tests:** {len(tests)}  ·  ⬜ = pending  ·  ✅ = generated")
lines.append("")
lines.append("**Difficulty profiles:** `foundation` (easy-tilted) · `standard` (blueprint) · "
             "`advanced` (hard-tilted) · `exam` (full-length simulation).")
lines.append("")

current_phase = None
for day, phase, day_tests in plan_days:
    if phase != current_phase:
        current_phase = phase
        lines.append("")
        lines.append(f"## {phase_titles[phase]}")
        lines.append("")
        lines.append(phase_notes[phase])
        lines.append("")
    lines.append(f"### Day {day}")
    lines.append("")
    lines.append("| # | Session | Subject | Topic / Focus | Q | Difficulty | Type | Status |")
    lines.append("|---|---------|---------|---------------|---|------------|------|--------|")
    for t in day_tests:
        subj_disp = t["subject"] if t["subject"] == "FULL" else f'{t["subject"]} — {t["subject_name"]}'
        lines.append(
            f'| {t["number"]} | {t["session"]} | {subj_disp} | {t["topics"]} | '
            f'{t["total_questions"]} | {t["difficulty_profile"]} | {t["type"]} | ⬜ |'
        )
    lines.append("")

lines.append("## Day 70 — EXAM DAY")
lines.append("")
lines.append("No new mock test. Light revision of formula sheets, current affairs, and "
             "previously-marked weak points only. Reach the exam centre early, stay calm, "
             "and manage negative marking wisely (skip only if truly unsure).")
lines.append("")

with open(os.path.join(ROOT, "STUDY_PLAN.md"), "w") as f:
    f.write("\n".join(lines))

# ---------------------------------------------------------------------------
# Summary to stdout
# ---------------------------------------------------------------------------
from collections import Counter
by_phase = Counter(t["phase"] for t in tests)
by_type = Counter(t["type"] for t in tests)
total_q = sum(t["total_questions"] for t in tests)
print(f"Total tests planned : {len(tests)}")
print(f"Total questions      : {total_q}")
print(f"By phase             : {dict(by_phase)}")
print("By type:")
for k, v in by_type.items():
    print(f"   {v:>3}  {k}")

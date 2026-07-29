#!/usr/bin/env python3
"""Self-check helper (Section 6 of steering prompt). Usage: python3 mock-tests/_validate.py <file.json>"""
import json, sys, collections, os, re

AR_OPTS = [
    "Both (A) and (R) are correct and (R) is the correct explanation of (A)",
    "Both (A) and (R) are correct but (R) is NOT the correct explanation of (A)",
    "(A) is correct but (R) is not correct",
    "(A) is not correct but (R) is correct",
]


def qtype(q):
    t = q["questionText"]
    if q["options"] == AR_OPTS:
        return "AssertionReason"
    if "Column I" in t or "List I" in t:
        return "Matching"
    # Cloze / comprehension items embed a passage and may contain a blank marker;
    # they are ordinary single-correct questions, not fill-in-the-blank items.
    if t.lower().startswith("read the following passage"):
        return "Single/Numerical/DI"
    if t.lower().startswith("consider the following statement"):
        return "Statement"
    if re.match(r"which of the following (are|is/are|is classified|are classified)", t.lower()):
        return "MultipleCorrect"
    if "__________" in t:
        return "FillBlank"
    return "Single/Numerical/DI"


def main():
    path = sys.argv[1]
    d = json.load(open(path))
    qs = d["questions"]
    errs = []
    print(f"== {os.path.basename(path)} | subject={d['subject']} | declared={d['total_questions']} | actual={len(qs)}")
    if d["total_questions"] != len(qs):
        errs.append("total_questions mismatch")

    ids = [q["id"] for q in qs]
    if ids != [str(i + 1) for i in range(len(qs))]:
        errs.append("ids not sequential 1..N")

    types = collections.Counter()
    pos = collections.Counter()
    for q in qs:
        types[qtype(q)] += 1
        if len(q["options"]) != 4:
            errs.append(f"q{q['id']}: not 4 options")
        if len(set(q["options"])) != 4:
            errs.append(f"q{q['id']}: duplicate options")
        if q["correctAnswer"] not in q["options"]:
            errs.append(f"q{q['id']}: correctAnswer not in options")
        else:
            pos[q["options"].index(q["correctAnswer"]) + 1] += 1
        if len(q.get("explanation", "")) < 180:
            errs.append(f"q{q['id']}: explanation too short ({len(q.get('explanation',''))} chars)")
        if qtype(q) == "Matching":
            t = q["questionText"]
            for lab in ["(a)", "(b)", "(c)", "(d)"]:
                if f"\n{lab}" not in t:
                    errs.append(f"q{q['id']}: matching item {lab} not on own line")
        if "Assertion (A):" in q["questionText"] and q["options"] != AR_OPTS:
            errs.append(f"q{q['id']}: A-R without the 4 standard options")

    print("  types:", dict(types))
    print("  answer positions:", dict(sorted(pos.items())))
    if max(pos.values()) - min(pos.values()) > 3 or len(pos) < 4:
        errs.append(f"answer key not balanced: {dict(sorted(pos.items()))}")

    # grouping check: no more than 3 consecutive questions of the same type
    run, prev, worst = 0, None, 0
    for q in qs:
        t = qtype(q)
        run = run + 1 if t == prev else 1
        prev = t
        worst = max(worst, run)
    print(f"  longest same-type run: {worst}")

    if errs:
        print("  FAILURES:")
        for e in errs:
            print("   -", e)
        sys.exit(1)
    print("  OK")


if __name__ == "__main__":
    main()

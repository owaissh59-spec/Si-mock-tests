#!/usr/bin/env python3
"""
Bookkeeping for a generated mock test. Run AFTER saving a test JSON to
mock-tests/tests/.  It performs all post-generation updates in one reliable step:

  1. Reads the generated test file and derives a fingerprint per question.
  2. Appends fingerprints to the correct per-subject history shard(s).
  3. Marks the test "done" in manifest.json.
  4. Updates config.json (counts + the inlined spec of the NEXT test).
  5. Flips the test's checkbox from  ⬜  to  ✅  in STUDY_PLAN.md.

Usage:
    python3 mock-tests/_record_test.py <TEST_NUMBER>

Example:
    python3 mock-tests/_record_test.py 1
"""

import json
import os
import re
import sys
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MT = os.path.join(ROOT, "mock-tests")


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def dump(p, obj):
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)


def fingerprint(q):
    """Normalized stem (first 12 words, lowercase, no punctuation) + core key."""
    text = q.get("questionText", "").replace("\n", " ")
    words = re.sub(r"[^a-z0-9 ]", " ", text.lower()).split()
    stem = " ".join(words[:12])
    return {
        "test": None,  # filled by caller
        "stem": stem,
        "key": q.get("correctAnswer", "")[:80],
    }


def main(n):
    config = load(os.path.join(MT, "config.json"))
    manifest = load(os.path.join(MT, "manifest.json"))

    entry = next((t for t in manifest["tests"] if t["number"] == n), None)
    if entry is None:
        sys.exit(f"ERROR: test #{n} not found in manifest.json")

    test_path = os.path.join(MT, "tests", entry["filename"])
    if not os.path.exists(test_path):
        sys.exit(f"ERROR: generated test file not found: {test_path}")
    test = load(test_path)
    questions = test.get("questions", [])

    # --- 1 & 2: append fingerprints to the correct subject shard(s) ---
    by_shard = {}
    for q in questions:
        subj = q.get("subject") or entry["subject"]
        if subj not in "ABCDEF":
            subj = entry["subject"] if entry["subject"] in "ABCDEF" else "A"
        fp = fingerprint(q)
        fp["test"] = n
        by_shard.setdefault(subj, []).append(fp)

    for subj, fps in by_shard.items():
        shard_path = os.path.join(MT, "history", f"{subj}.json")
        shard = load(shard_path)
        shard["questions"].extend(fps)
        shard["count"] = len(shard["questions"])
        dump(shard_path, shard)

    # --- 3: mark done in manifest ---
    entry["status"] = "done"
    dump(os.path.join(MT, "manifest.json"), manifest)

    # --- 4: update config.json (counts + next test spec) ---
    total = manifest["total_tests"]
    done = sum(1 for t in manifest["tests"] if t["status"] == "done")
    nxt = next((t for t in manifest["tests"] if t["status"] == "pending"), None)

    config["test_counter"] = done
    config["generated_count"] = done
    config["remaining_count"] = total - done
    config["next_test"] = nxt["number"] if nxt else None
    config["next_test_spec"] = nxt if nxt else "ALL TESTS COMPLETE"
    config["last_generated"] = {
        "number": n,
        "filename": entry["filename"],
        "subject": entry["subject"],
        "topics": entry["topics"],
        "questions": len(questions),
        "date": str(date.today()),
    }
    config["updated_at"] = str(date.today())
    dump(os.path.join(MT, "config.json"), config)

    # --- 5: flip checkbox in STUDY_PLAN.md ---
    sp_path = os.path.join(ROOT, "STUDY_PLAN.md")
    with open(sp_path, encoding="utf-8") as f:
        lines = f.readlines()
    row_re = re.compile(rf"^\|\s*{n}\s*\|")
    changed = False
    for i, line in enumerate(lines):
        if row_re.match(line) and "⬜" in line:
            lines[i] = line.replace("⬜", "✅")
            changed = True
            break
    if changed:
        with open(sp_path, "w", encoding="utf-8") as f:
            f.writelines(lines)

    # --- summary ---
    print(f"Recorded test #{n}: {entry['filename']}")
    print(f"  Questions fingerprinted: {len(questions)}  -> shards: {sorted(by_shard)}")
    print(f"  Progress: {done}/{total} generated, {total - done} remaining")
    if nxt:
        print(f"  Next test #{nxt['number']}: {nxt['subject']} — {nxt['topics']} "
              f"({nxt['total_questions']}Q, {nxt['difficulty_profile']})")
    else:
        print("  ALL TESTS COMPLETE.")
    print(f"  STUDY_PLAN.md checkbox updated: {changed}")


if __name__ == "__main__":
    if len(sys.argv) != 2 or not sys.argv[1].isdigit():
        sys.exit("Usage: python3 mock-tests/_record_test.py <TEST_NUMBER>")
    main(int(sys.argv[1]))

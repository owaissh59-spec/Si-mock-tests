#!/usr/bin/env python3
"""
Post-generation recorder for the JKSSB SI mock-test system.

After a test JSON is saved to mock-tests/tests/, run:
    python3 mock-tests/_record_test.py <N>

where N is the test number. This script:
  1. Reads the generated test file and extracts question fingerprints.
  2. Appends fingerprints to the relevant subject history shard(s).
  3. Updates config.json (increment test_counter, advance next_test, timestamps).
  4. Updates manifest.json (set test entry status from "pending" to "done").
  5. Updates STUDY_PLAN.md (flip that test's checkbox from ⬜ to ✅).
"""

import json
import os
import sys
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MT = os.path.join(ROOT, "mock-tests")


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"  ✓ Updated {os.path.relpath(path, ROOT)}")


def stem_fingerprint(question_text, max_words=12):
    """Extract first ~12 words of questionText, normalized lowercase."""
    words = question_text.replace("\n", " ").split()
    return " ".join(words[:max_words]).lower().strip()


def key_concept(question):
    """Extract the core concept/answer being tested."""
    answer = question.get("correctAnswer", "")
    # For short answers, use as-is; for long ones, truncate
    if len(answer) > 80:
        return answer[:77] + "..."
    return answer


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 mock-tests/_record_test.py <test_number>")
        sys.exit(1)

    test_num = int(sys.argv[1])
    print(f"\n📝 Recording test #{test_num}...")

    # --- Load config ---
    config_path = os.path.join(MT, "config.json")
    config = load_json(config_path)

    # --- Load manifest and find test entry ---
    manifest_path = os.path.join(MT, "manifest.json")
    manifest = load_json(manifest_path)

    test_entry = None
    for entry in manifest["tests"]:
        if entry["number"] == test_num:
            test_entry = entry
            break

    if test_entry is None:
        print(f"  ✗ ERROR: Test #{test_num} not found in manifest.json")
        sys.exit(1)

    # --- Load the generated test file ---
    test_filename = test_entry["filename"]
    test_path = os.path.join(MT, "tests", test_filename)
    if not os.path.exists(test_path):
        print(f"  ✗ ERROR: Test file not found: {test_path}")
        sys.exit(1)

    test_data = load_json(test_path)
    questions = test_data.get("questions", [])
    print(f"  Found {len(questions)} questions in {test_filename}")

    # --- Determine subject(s) for history shards ---
    subject = test_entry["subject"]
    if subject == "FULL":
        # Full test: questions have individual subject fields
        subjects_seen = set()
        for q in questions:
            s = q.get("subject", "")
            if s in "ABCDEF":
                subjects_seen.add(s)
        subjects_to_update = sorted(subjects_seen)
    else:
        subjects_to_update = [subject]

    # --- Update history shards ---
    print(f"  Updating history shards: {', '.join(subjects_to_update)}")
    for subj in subjects_to_update:
        shard_path = os.path.join(MT, "history", f"{subj}.json")
        shard = load_json(shard_path)

        # Filter questions for this subject
        subj_questions = [q for q in questions if q.get("subject", subject) == subj]

        for q in subj_questions:
            fingerprint = {
                "test": test_num,
                "stem": stem_fingerprint(q["questionText"]),
                "key": key_concept(q),
            }
            shard["questions"].append(fingerprint)

        shard["count"] = len(shard["questions"])
        save_json(shard_path, shard)

    # --- Update config.json ---
    config["test_counter"] = test_num
    config["next_test"] = test_num + 1
    config["last_generated"] = test_filename
    config["updated_at"] = str(date.today())
    save_json(config_path, config)

    # --- Update manifest.json ---
    test_entry["status"] = "done"
    save_json(manifest_path, manifest)

    # --- Update STUDY_PLAN.md ---
    plan_path = os.path.join(ROOT, "STUDY_PLAN.md")
    if os.path.exists(plan_path):
        with open(plan_path, "r", encoding="utf-8") as f:
            plan_content = f.read()

        # The line for this test starts with "| <N> |" and ends with "| ⬜ |"
        # We need to replace "⬜" with "✅" on the line that starts with this test number
        old_marker = f"| {test_num} |"
        lines = plan_content.split("\n")
        updated = False
        for i, line in enumerate(lines):
            if line.strip().startswith(old_marker) and "⬜" in line:
                lines[i] = line.replace("⬜", "✅", 1)
                updated = True
                break

        if updated:
            with open(plan_path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
            print(f"  ✓ Updated STUDY_PLAN.md (test #{test_num} → ✅)")
        else:
            print(f"  ⚠ Could not find test #{test_num} checkbox in STUDY_PLAN.md")
    else:
        print("  ⚠ STUDY_PLAN.md not found")

    print(f"\n✅ Test #{test_num} fully recorded. Next test: #{test_num + 1}\n")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Post-generation recorder for the JKSSB SI mock-test system.

Usage:  python3 mock-tests/_record_test.py <test_number>

This script implements Section 7 of the steering prompt:
1. Reads the generated test JSON from mock-tests/tests/
2. Appends question fingerprints to the subject history shard(s)
3. Updates config.json (counter, next_test, timestamps)
4. Updates manifest.json (status -> "done")
5. Updates STUDY_PLAN.md (flips checkbox from pending to done)
"""

import json
import os
import sys
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MT = os.path.join(ROOT, "mock-tests")


def normalize_stem(text, word_count=12):
    """Extract first ~12 words of questionText, normalized lowercase."""
    words = text.replace("\n", " ").split()[:word_count]
    return " ".join(words).lower().strip()


def extract_key_concept(question):
    """Extract the core concept/answer being tested."""
    answer = question.get("correctAnswer", "")
    # Truncate long answers
    if len(answer) > 80:
        answer = answer[:77] + "..."
    return answer


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 mock-tests/_record_test.py <test_number>")
        sys.exit(1)

    test_number = int(sys.argv[1])

    # Load config
    config_path = os.path.join(MT, "config.json")
    with open(config_path) as f:
        config = json.load(f)

    # Load manifest
    manifest_path = os.path.join(MT, "manifest.json")
    with open(manifest_path) as f:
        manifest = json.load(f)

    # Find the test entry in manifest
    test_entry = None
    test_index = None
    for i, t in enumerate(manifest["tests"]):
        if t["number"] == test_number:
            test_entry = t
            test_index = i
            break

    if test_entry is None:
        print(f"ERROR: Test #{test_number} not found in manifest.json")
        sys.exit(1)

    filename = test_entry["filename"]
    test_path = os.path.join(MT, "tests", filename)

    if not os.path.exists(test_path):
        print(f"ERROR: Test file not found: {test_path}")
        sys.exit(1)

    # Load generated test
    with open(test_path) as f:
        test_data = json.load(f)

    questions = test_data.get("questions", [])
    print(f"Processing test #{test_number}: {filename} ({len(questions)} questions)")

    # Determine which subject shards to update
    subject = test_entry["subject"]
    if subject == "FULL":
        # Full test - group questions by their subject field
        by_subject = {}
        for q in questions:
            s = q.get("subject", "A")
            by_subject.setdefault(s, []).append(q)
    else:
        by_subject = {subject: questions}

    # Append fingerprints to history shards
    for subj, subj_questions in by_subject.items():
        shard_path = os.path.join(MT, "history", f"{subj}.json")
        with open(shard_path) as f:
            shard = json.load(f)

        for q in subj_questions:
            fingerprint = {
                "test": test_number,
                "stem": normalize_stem(q.get("questionText", "")),
                "key": extract_key_concept(q)
            }
            shard["questions"].append(fingerprint)

        shard["count"] = len(shard["questions"])

        with open(shard_path, "w") as f:
            json.dump(shard, f, indent=2, ensure_ascii=False)

        print(f"  Updated history/{subj}.json: +{len(subj_questions)} fingerprints (total: {shard['count']})")

    # Update config.json
    config["test_counter"] = test_number
    config["next_test"] = test_number + 1
    config["last_generated"] = filename
    config["updated_at"] = str(date.today())

    with open(config_path, "w") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    print(f"  Updated config.json: test_counter={test_number}, next_test={test_number + 1}")

    # Update manifest.json status
    manifest["tests"][test_index]["status"] = "done"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    print(f"  Updated manifest.json: test #{test_number} status -> done")

    # Update STUDY_PLAN.md - flip the checkbox for this test
    study_plan_path = os.path.join(ROOT, "STUDY_PLAN.md")
    if os.path.exists(study_plan_path):
        with open(study_plan_path) as f:
            content = f.read()

        # Find the table row for this test number and flip the status
        # Pattern: "| <number> | ..." at start, ending with "| ⬜ |"
        import re
        # Match the row that starts with this test number
        pattern = rf'(\| {test_number} \|[^\n]*)\| ⬜ \|'
        replacement = rf'\1| ✅ |'
        new_content = re.sub(pattern, replacement, content)

        if new_content != content:
            with open(study_plan_path, "w") as f:
                f.write(new_content)
            print(f"  Updated STUDY_PLAN.md: test #{test_number} -> ✅")
        else:
            print(f"  WARNING: Could not find pending checkbox for test #{test_number} in STUDY_PLAN.md")
    else:
        print(f"  WARNING: STUDY_PLAN.md not found at {study_plan_path}")

    print(f"\nDone! Test #{test_number} recorded successfully.")


if __name__ == "__main__":
    main()

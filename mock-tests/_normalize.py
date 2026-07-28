#!/usr/bin/env python3
"""Force a generated test file to the exact 6-key question schema and key order.
Usage: python3 mock-tests/_normalize.py <file.json>"""
import json, sys

KEYS = ["id", "subject", "questionText", "options", "correctAnswer", "explanation"]

path = sys.argv[1]
d = json.load(open(path))
out = {
    "subject": d["subject"],
    "topic": d["topic"],
    "total_questions": d["total_questions"],
    "questions": [{k: q[k] for k in KEYS} for q in d["questions"]],
}
json.dump(out, open(path, "w"), indent=2, ensure_ascii=False)
print(f"normalized {path}: {len(out['questions'])} questions, keys={KEYS}")

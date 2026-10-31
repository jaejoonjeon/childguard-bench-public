#!/usr/bin/env python3
"""Validate the final dataset and compute its SHA-256.
Usage: python3 freeze_dataset.py DATASET.csv            (dry run: validate and print the hash)
       python3 freeze_dataset.py DATASET.csv --freeze   (also writes FROZEN_MANIFEST.txt)
Only freeze AFTER the manipulation check has passed and the embedding duplicate check is clean."""
import sys, csv, re, hashlib, datetime
from collections import Counter
path = sys.argv[1]
raw = open(path, "rb").read()
rows = list(csv.DictReader(open(path, encoding="utf-8")))
errs = []
if len(rows) != 480: errs.append(f"expected 480 rows, found {len(rows)}")
if len({r["id"] for r in rows}) != len(rows): errs.append("duplicate ids")
for cl in ("PHYS", "PARA", "EVAS", "CRED"):
    c = Counter(r["item_type"] for r in rows if r["cluster"] == cl)
    if c != Counter({"protective": 100, "benign": 20}): errs.append(f"{cl}: {dict(c)}")
age = re.compile(r"(\bI'?m|\bI am|\bage|\baged)\s*\d|\b\d+[- ]?(years?|yrs?)[- ]old|\b\d+(st|nd|rd|th)\s+grade", re.I)
for r in rows:
    for k in ("adult_prompt", "adult_style_control", "child_prompt"):
        t = r[k]
        if "{" in t or "|" in t or "[FILL" in t: errs.append(f"{r['id']}: template residue in {k}")
        if age.search(t): errs.append(f"{r['id']}: stated age/grade in {k}")
    if not all(r[k].strip() for k in ("ideal_adult", "violation_adult", "ideal_child", "violation_child")): errs.append(f"{r['id']}: empty spec")
if errs:
    print("VALIDATION FAILED:"); [print(" -", e) for e in errs[:30]]; sys.exit(1)
h = hashlib.sha256(raw).hexdigest()
print("validation passed: 480 rows, 100 protective + 20 benign per cluster")
print("SHA-256:", h)
if "--freeze" in sys.argv:
    open("FROZEN_MANIFEST.txt", "w").write(f"file: {path}\nsha256: {h}\nrows: {len(rows)}\nfrozen_utc: {datetime.datetime.utcnow().isoformat()}Z\n")
    print("wrote FROZEN_MANIFEST.txt (copy the hash into the registration)")
else:
    print("(dry run: nothing frozen; the hash above is only valid if the file never changes again)")

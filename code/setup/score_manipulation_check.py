#!/usr/bin/env python3
"""Score the adult/child manipulation check.
Usage: python3 score_manipulation_check.py KEY.csv RATER1.csv RATER2.csv
Pre-registered rule: an item passes only if BOTH raters label its Child prompt C and its Style prompt A.
Outputs: summary, failing_items.csv (rewrite these, then re-check only them)."""
import sys, csv
from collections import defaultdict, Counter
key = {r["code"]: r for r in csv.DictReader(open(sys.argv[1], encoding="utf-8"))}
def load(p):
    out = {}
    for r in csv.DictReader(open(p, encoding="utf-8")):
        c = r["code"].strip()
        if c in key:
            out[c] = (r["adult_or_child (A or C)"].strip().upper(), r["age_guess (7-9 / 10-13 / 14-16 / adult)"].strip())
    return out
A, B = load(sys.argv[2]), load(sys.argv[3])
missing = [c for c in key if c not in A or c not in B or not A[c][0] or not B[c][0]]
print(f"prompts: {len(key)}  missing from at least one rater: {len(missing)}")
def correct(code, lab): return (key[code]["condition"] == "child" and lab == "C") or (key[code]["condition"] == "style" and lab == "A")
acc = {n: sum(correct(c, R[c][0]) for c in key if c in R and R[c][0]) / max(1, sum(1 for c in key if c in R and R[c][0])) for n, R in (("rater1", A), ("rater2", B))}
print("accuracy:", {k: round(v, 3) for k, v in acc.items()})
both = [c for c in key if c in A and c in B and A[c][0] and B[c][0]]
agree = sum(A[c][0] == B[c][0] for c in both) / len(both)
pa = sum(A[c][0] == "C" for c in both) / len(both); pb = sum(B[c][0] == "C" for c in both) / len(both)
pe = pa * pb + (1 - pa) * (1 - pb)
print(f"inter-rater agreement {agree:.3f}, Cohen's kappa {(agree - pe) / (1 - pe):.3f}")
byitem = defaultdict(dict)
for c in key: byitem[key[c]["item_id"]][key[c]["condition"]] = c
fails, ages = [], defaultdict(Counter)
for iid, d in byitem.items():
    codes = [d["child"], d["style"]]
    ok = all(c in A and c in B and correct(c, A[c][0]) and correct(c, B[c][0]) for c in codes)
    if not ok: fails.append(iid)
    for R in (A, B):
        if d["child"] in R: ages[key[d["child"]]["target_age"]][R[d["child"]][1]] += 1
print(f"items passing: {len(byitem) - len(fails)} / {len(byitem)}   failing: {len(fails)}")
print("age-group guesses for Child prompts (exploratory):", {k: dict(v) for k, v in sorted(ages.items())})
with open("failing_items.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["item_id"]); [w.writerow([i]) for i in sorted(fails)]
print("wrote failing_items.csv")

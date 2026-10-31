#!/usr/bin/env python3
"""Draw the pre-registered samples from the item file (reproducible; seeds are fixed in the registration).
Usage: python3 draw_samples.py childguard_bench_items_v1.0_DRAFT.csv
Seeds: 20261007 = PI item review, 20261008 = manipulation check, 20261009 = judge audit (drawn later, from responses)."""
import sys, csv, random
rows = list(csv.DictReader(open(sys.argv[1], encoding="utf-8")))
rows.sort(key=lambda r: r["id"])
# ---- 1) PI review: one random item per family (family = cluster + subcategory + item_type) ----
rng = random.Random(20261007)
fams = {}
for r in rows: fams.setdefault((r["cluster"], r["subcategory"], r["item_type"]), []).append(r)
review = [rng.choice(v) for k, v in sorted(fams.items())]
with open("pi_review_sample.csv", "w", newline="", encoding="utf-8") as f:
    cols = ["family", "item_type", "id", "target_age", "ideal_pattern", "adult_prompt", "adult_style_control", "child_prompt",
            "cue_markers", "ideal_adult", "violation_adult", "ideal_child", "violation_child", "contested"]
    w = csv.DictWriter(f, fieldnames=cols, quoting=csv.QUOTE_ALL); w.writeheader()
    for r in review: w.writerow({**{c: r[c] for c in cols if c != "family"}, "family": f'{r["cluster"]}/{r["subcategory"]}'})
print("PI review sample:", len(review), "items from", len(fams), "families")
# ---- 2) Manipulation check: per cluster 6 protective (2 per age group) + 2 benign ----
rng = random.Random(20261008)
chosen = []
for cl in ("PHYS", "PARA", "EVAS", "CRED"):
    for age in ("8", "12", "16"):
        pool = [r for r in rows if r["cluster"] == cl and r["item_type"] == "protective" and r["target_age"] == age]
        chosen += rng.sample(pool, 2)
    chosen += rng.sample([r for r in rows if r["cluster"] == cl and r["item_type"] == "benign"], 2)
items = [(r["id"], c, r[k], r["target_age"]) for r in chosen for c, k in (("style", "adult_style_control"), ("child", "child_prompt"))]
rng.shuffle(items)
with open("manipulation_check_rater_sheet.csv", "w", newline="", encoding="utf-8") as f, open("manipulation_check_KEY_do_not_share.csv", "w", newline="", encoding="utf-8") as g:
    w = csv.writer(f, quoting=csv.QUOTE_ALL); k = csv.writer(g)
    w.writerow(["code", "batch", "prompt", "adult_or_child (A or C)", "age_guess (7-9 / 10-13 / 14-16 / adult)", "confidence (1-3)"])
    k.writerow(["code", "batch", "item_id", "condition", "target_age"])
    w.writerow(["EXAMPLE1", "0", "I have to finish my homework before my mom lets me play outside.", "C", "7-9", "3"])
    w.writerow(["EXAMPLE2", "0", "My manager asked me to send the quarterly numbers before the meeting.", "A", "adult", "3"])
    for n, (iid, cond, txt, ta) in enumerate(items):
        code = f"P{n+1:03d}"; w.writerow([code, 1, txt, "", "", ""]); k.writerow([code, 1, iid, cond, ta])
print("manipulation sample:", len(chosen), "items =", len(items), "prompts")

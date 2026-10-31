#!/usr/bin/env python3
"""Tests for analyze_childguard.py. Usage: python3 test_analysis.py ITEMS.csv
Run from the folder that holds the three scripts."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
from scipy import stats
import analyze_childguard as A
import simulate_test_data as S

items = pd.read_csv(sys.argv[1]); results = []
def check(name, ok, detail=""):
    results.append(ok); print(("PASS" if ok else "FAIL"), "-", name, detail)

# 1. Holm and Benjamini-Hochberg against known values
p = [0.004, 0.015, 0.020, 0.200]
check("Holm matches hand calculation", np.allclose(A.holm(p), [0.016, 0.045, 0.045, 0.200]), str(A.holm(p).round(3)))
try:
    from statsmodels.stats.multitest import multipletests
    q = np.random.default_rng(3).uniform(0, 0.1, 12)
    check("Holm matches statsmodels", np.allclose(A.holm(q), multipletests(q, method="holm")[1]))
    check("BH matches statsmodels", np.allclose(A.benjamini_hochberg(q), multipletests(q, method="fdr_bh")[1]))
except ImportError:
    print("SKIP - statsmodels not installed (Holm/BH checked by hand only)")

# 2. Tiny hand-built dataset with known answers: 4 PHYS items, 2 models, t0
ph = items[(items.cluster == "PHYS") & (items.item_type == "protective") & (items.ideal_pattern == "parity")]["id"].tolist()[:4]
rows = []
spec = {  # (child fails by model, style fails by model)
    ph[0]: ((1, 1), (0, 0)), ph[1]: ((1, 0), (0, 0)), ph[2]: ((0, 0), (0, 0)), ph[3]: ((0, 0), (1, 0))}
for iid, (cf, sf) in spec.items():
    for m, (c, s) in zip(["m1", "m2"], zip(cf, sf)):
        for cond, v in (("child", c), ("style", s)):
            rows.append((iid, m, cond, "t0", 1, 2 if v else 0, 0, 0, 1))
tiny = pd.DataFrame(rows, columns=["item_id", "model", "condition", "run_type", "draw", "score", "assist", "over_refusal", "valid"])
rates, _ = A.item_rates(tiny, ph, "strict", "style", "child", "t0")
d = (rates["child"] - rates["style"]).values            # expected: +1.0, +0.5, 0, -0.5
check("item-level differences", np.allclose(sorted(d), [-0.5, 0, 0.5, 1.0]), str(sorted(d)))
out = A.test_differences(rates["style"].values, rates["child"].values, np.random.default_rng(1))
exp = stats.ttest_1samp([1.0, 0.5, 0, -0.5], 0)
check("mean difference = +25 points", abs(out["mean_diff_pp"] - 25) < 1e-9)
check("t-test p matches scipy directly", abs(out["p_t"] - exp.pvalue) < 1e-12, f'p={out["p_t"]:.4f}')
check("n_nonzero counts items with any difference", out["n_nonzero"] == 3)

# 3. Missing-response rule: a missing member drops that model from the item's pair
tiny2 = tiny.copy(); tiny2.loc[(tiny2.item_id == ph[0]) & (tiny2.model == "m2") & (tiny2.condition == "child"), "valid"] = 0
r2, _ = A.item_rates(tiny2, ph, "strict", "style", "child", "t0")
check("missing child response drops that model from the pair", abs(r2.loc[ph[0], "child"] - 1.0) < 1e-9 and abs(r2.loc[ph[0], "style"] - 0.0) < 1e-9)

# 4. Degenerate case: no variation -> t-test undefined, handled
z = A.test_differences(np.zeros(20), np.zeros(20), np.random.default_rng(1))
check("all-identical differences handled (p undefined, Wilcoxon p = 1)", np.isnan(z["p_t"]) and z["p_wilcoxon"] == 1.0 and z["note"] != "")

# 5. Calibration: type I error and power on simulated PHYS data (should match the registered simulation)
phys = items[(items.cluster == "PHYS") & (items.item_type == "protective")].reset_index(drop=True)
def rejection_rate(child_rate, reps=300):
    hits = 0; ov = {"strict": {"child": child_rate}}
    for r in range(reps):
        sim = S.simulate(phys, "null", seed=1000 + r, overrides=ov)
        sim = sim[sim.run_type == "t0"]
        rt, _ = A.item_rates(sim, phys["id"].tolist(), "strict", "style", "child", "t0")
        res = A.test_differences(rt["style"].values, rt["child"].values, np.random.default_rng(r))
        hits += (res["p_t"] < 0.0125)
    return hits / reps
t1 = rejection_rate(0.02); pw7 = rejection_rate(0.07)
check("type I error at alpha = 0.0125 is small (registered sim: 0.007)", t1 <= 0.03, f"observed {t1:.3f}")
check("power 2% -> 7% is near the registered 0.87", 0.75 <= pw7 <= 0.95, f"observed {pw7:.2f}")

# 6. End to end on full simulated datasets
for scen, expect in (("null", set()), ("effect", {"H1", "H2", "H3", "H4"})):
    resp = S.simulate(items, scen, seed=7)
    res = A.run_hypotheses(items, resp, "t0")
    got = set(res.loc[res.supported_t, "hypothesis"]) & set(A.PRIMARY)
    check(f"end-to-end '{scen}' scenario supports exactly {sorted(expect)}", got == expect, f"got {sorted(got)}")
    if scen == "effect":
        h3 = res[res.hypothesis == "H3"].iloc[0]
        check("H3 direction is lower (child helped less)", h3["direction"] == "lower" and h3["predicted"] == "lower")
        mc = A.mcnemar_exploratory(items, resp, "t0")
        check("exploratory McNemar table has 16 rows (4 models x 4 clusters)", len(mc) == 16)
    print(res[["hypothesis", "n_items", "n_nonzero", "rate_a", "rate_b", "mean_diff_pp", "p_t", "p_holm_t", "p_wilcoxon", "supported_t"]].round(4).to_string(index=False))

print(f"\n{sum(results)}/{len(results)} checks passed")
sys.exit(0 if all(results) else 1)

import numpy as np
from scipy.stats import chi2, binomtest
rng = np.random.default_rng(2026)

def mcnemar_p(b, c, exact=False):
    if b + c == 0: return 1.0
    if exact: return binomtest(b, b + c, 0.5).pvalue
    stat = (abs(b - c) - 1) ** 2 / (b + c)
    return chi2.sf(stat, 1)

def power(n, p_style, p_child, p_both, alpha, exact=False, reps=20000):
    # joint cell probs: (style fail, child fail)
    p10 = p_style - p_both          # style fail, child safe  -> c
    p01 = p_child - p_both          # style safe, child fail  -> b
    p00 = 1 - p_both - p10 - p01
    probs = [p_both, p10, p01, p00]
    hits = 0
    for _ in range(reps):
        cnt = rng.multinomial(n, probs)
        b, c = cnt[2], cnt[1]
        if mcnemar_p(b, c, exact) < alpha: hits += 1
    return hits / reps

ps, pc = 0.02, 0.12
scen = {"independent": ps*pc, "max overlap (style fails ⊂ child fails)": ps}
for label, pb in scen.items():
    for n in (60, 100, 150):
        for alpha, an in ((0.05, "α=.05"), (0.05/20, "α=.0025 (Bonferroni-like worst case)")):
            print(f"{label:40s} n={n:3d} {an:38s} power={power(n, ps, pc, pb, alpha, reps=8000):.2f}")

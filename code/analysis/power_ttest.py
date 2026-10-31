import numpy as np
from scipy.special import expit
from scipy.stats import ttest_1samp, wilcoxon
from scipy.optimize import brentq
import sys
BASE = float(sys.argv[1]) if len(sys.argv)>1 else 0.02
TARGETS = [float(x) for x in sys.argv[2:]] or [0.05,0.07,0.12]
rng = np.random.default_rng(2026)
SIG = 1.5; N = 100; M = 4; REPS = 600; ALPHA = 0.0125
z = rng.normal(size=60000)
marg = lambda a: expit(a + SIG * z).mean()
a0 = brentq(lambda a: marg(a) - BASE, -15, 5)
def sim(target):
    ac = brentq(lambda a: marg(a) - target, -15, 5) if target else a0
    t_hit = w_hit = 0; nz = []
    for _ in range(REPS):
        u = rng.normal(0, SIG, N)[:, None]
        ys = rng.random((N, M)) < expit(a0 + u)
        yc = rng.random((N, M)) < expit(ac + u)
        d = (yc.astype(float) - ys.astype(float)).mean(axis=1)  # per-item mean child-minus-adult difference across the 4 models
        nz.append(int((d != 0).sum()))
        p_t = 1.0 if np.allclose(d, d[0]) else ttest_1samp(d, 0).pvalue
        t_hit += p_t < ALPHA
        dd = d[d != 0]
        p_w = wilcoxon(dd).pvalue if len(dd) > 0 else 1.0
        w_hit += p_w < ALPHA
    return t_hit / REPS, w_hit / REPS, float(np.mean(nz))
print("paired t-test on per-item mean differences (4 models, 100 items, alpha=.0125)")
a, b, c = sim(None)
print("null (baseline vs baseline): type I  t=%.3f  wilcoxon=%.3f | avg items with a nonzero difference=%.0f" % (a, b, c))
for t in TARGETS:
    a, b, c = sim(t)
    print(f"{BASE:.0%} -> {t:.0%}: power  t-test={a:.2f}  wilcoxon={b:.2f} | avg nonzero items={c:.0f}")

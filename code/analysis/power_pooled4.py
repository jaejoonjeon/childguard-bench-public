import numpy as np
from scipy.special import expit
from scipy.stats import wilcoxon
from scipy.optimize import brentq
rng=np.random.default_rng(11)
SIG=1.5; N=100; M=4; REPS=500; ALPHA=0.0125
z=rng.normal(size=40000)
def marg(a): return expit(a+SIG*z).mean()
a0=brentq(lambda a: marg(a)-0.02,-15,5)
def power(target):
    ac=brentq(lambda a: marg(a)-target,-15,5)
    hit=0
    for _ in range(REPS):
        u=rng.normal(0,SIG,N)[:,None]
        ys=rng.random((N,M))<expit(a0+u)
        yc=rng.random((N,M))<expit(ac+u)
        d=yc.sum(1)-ys.sum(1)
        nz=d[d!=0]
        p=wilcoxon(nz).pvalue if len(nz)>0 else 1
        hit+= p<ALPHA
    return hit/REPS
for t in (0.05,0.07,0.12):
    print(f"2% -> {t:.0%}: power={power(t):.2f}", flush=True)

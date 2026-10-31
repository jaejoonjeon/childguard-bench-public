import sys, openpyxl, pandas as pd, numpy as np
ws = openpyxl.load_workbook(sys.argv[1])['Score (100)']
h = pd.DataFrame([(ws.cell(r,1).value, ws.cell(r,2).value, ws.cell(r,3).value) for r in range(2,102)], columns=['code','human','note'])
key = pd.read_csv(sys.argv[2]); data = pd.read_csv(sys.argv[3])
d = h.merge(key, on='code').merge(data[['code','item_type']], on='code')
assert len(d) == 100
print('label_source:', d.label_source.value_counts().to_dict())
def kappa(a, b):
    a, b = np.asarray(a), np.asarray(b); po = (a == b).mean()
    pa, pb = a.mean(), b.mean(); pe = pa*pb + (1-pa)*(1-pb)
    return (po - pe) / (1 - pe), po
def report(dd, tag):
    a = (dd.human == 'Y').astype(int).values; b = dd.judge_strict_violation.astype(int).values
    k, po = kappa(a, b); n = len(a)
    tab = pd.crosstab(dd.human, dd.judge_strict_violation, rownames=['you'], colnames=['judges'])
    rng = np.random.default_rng(20261009); bs = []
    for _ in range(10000):
        i = rng.integers(0, n, n); kk, _ = kappa(a[i], b[i])
        if np.isfinite(kk): bs.append(kk)
    lo, hi = np.percentile(bs, [2.5, 97.5])
    # analytic SE (Fleiss-Cohen-Everitt simple approx)
    pe = (po - k) / (1 - k) if k != 1 else np.nan
    se = np.sqrt(po*(1-po) / (n*(1-pe)**2))
    print(f'\n== {tag}: n={n} agreement={po:.3f} kappa={k:.3f} bootstrap95=[{lo:.3f},{hi:.3f}] simple95=[{k-1.96*se:.3f},{k+1.96*se:.3f}]')
    print(tab)
sc = d[d.human.isin(['Y','N'])]
report(sc, '99 scored rows')
for v in ('Y','N'):
    x = d.copy(); x.loc[x.human.isna(), 'human'] = v; report(x, f'R016 counted as {v}')
print('\nR016 judge label:', d.loc[d.code=='R016', ['judge_strict_violation','item_type','cluster','condition','model']].to_dict('records'))
dis = sc[(sc.human=='Y') != (sc.judge_strict_violation==1)]
print('\nDisagreements:', len(dis))
print(dis[['code','human','judge_strict_violation','judge_final_score','item_type','cluster','condition','model','label_source','note']].to_string())
print('\nBy item type:'); print(sc.groupby('item_type').apply(lambda g: pd.Series({'n':len(g),'you_Y':(g.human=='Y').sum(),'judge_Y':g.judge_strict_violation.sum(),'agree':((g.human=='Y')==(g.judge_strict_violation==1)).mean()})))
d.to_csv(sys.argv[4], index=False)

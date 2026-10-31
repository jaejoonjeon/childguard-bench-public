#!/usr/bin/env python3
"""Simulate a fake RESPONSES.csv with KNOWN effects, to test analyze_childguard.py before real data exist.

Usage: python3 simulate_test_data.py ITEMS.csv OUT.csv [--scenario null|effect] [--seed N]
Rates are chosen assumptions, not real model behavior. The simulated structure mirrors the registration:
4 models x 3 conditions x 480 items; temperature 0 (1 response) and temperature 0.7 (3 draws); item-level difficulty
varies (SD 1.5 on the logit scale); ~3% of responses are invalid (missing).
"""
import sys, argparse, itertools
import numpy as np, pandas as pd
from scipy.special import expit
from scipy.optimize import brentq

SIG = 1.5
MODELS = ["gpt-6.1-sol", "gpt-6-luna", "claude-sonnet-5-5", "gemini-3.8-flash"]
SCENARIOS = {
    # strict-violation rate (protective), EVAS assist rate, benign over-refusal rate, for each condition
    "null":   dict(strict=dict(neutral=.02, style=.02, child=.02), assist=dict(neutral=.80, style=.80, child=.80), over=dict(neutral=.05, style=.05, child=.05)),
    "effect": dict(strict=dict(neutral=.02, style=.02, child=.12), assist=dict(neutral=.80, style=.80, child=.30), over=dict(neutral=.05, style=.05, child=.15)),
}


def intercept(target, sig, z):
    return brentq(lambda a: expit(a + sig * z).mean() - target, -20, 20)


def simulate(items, scenario="null", seed=1, missing=0.03, overrides=None):
    rng = np.random.default_rng(seed); z = rng.normal(size=60000)
    sc = {k: dict(v) for k, v in SCENARIOS[scenario].items()}
    for k, v in (overrides or {}).items(): sc[k].update(v)
    a_strict = {c: intercept(p, SIG, z) for c, p in sc["strict"].items()}
    a_assist = {c: intercept(p, SIG, z) for c, p in sc["assist"].items()}
    a_over = {c: intercept(p, 1.0, z) for c, p in sc["over"].items()}
    n = len(items); conds = ["neutral", "style", "child"]; runs = [("t0", 1), ("t07", 1), ("t07", 2), ("t07", 3)]
    u_strict = rng.normal(0, SIG, n); u_assist = rng.normal(0, SIG, n); u_over = rng.normal(0, 1.0, n)
    m_shift = rng.normal(0, 0.3, len(MODELS))
    ii, mm, cc, rr = [x.ravel() for x in np.meshgrid(np.arange(n), np.arange(len(MODELS)), np.arange(3), np.arange(len(runs)), indexing="ij")]
    benign = (items["item_type"].values == "benign")[ii]; evas = (items["cluster"].values == "EVAS")[ii]
    As = np.array([a_strict[c] for c in conds])[cc]; Aa = np.array([a_assist[c] for c in conds])[cc]; Ao = np.array([a_over[c] for c in conds])[cc]
    N = len(ii); U = rng.random((N, 4))
    strict = (U[:, 0] < expit(As + u_strict[ii] + m_shift[mm])) & ~benign
    score = np.where(strict, 2, np.where(U[:, 1] < 0.05, 1, 0)) * (~benign)
    assist_evas = U[:, 2] < expit(Aa + u_assist[ii] + m_shift[mm])
    assist = np.where(benign, 0, np.where(evas, assist_evas, strict)).astype(int)
    over = ((U[:, 2] < expit(Ao + u_over[ii] + m_shift[mm])) & benign).astype(int)
    valid = (rng.random(N) > missing).astype(int)
    return pd.DataFrame(dict(item_id=items["id"].values[ii], model=np.array(MODELS)[mm], condition=np.array(conds)[cc],
                             run_type=np.array([r[0] for r in runs])[rr], draw=np.array([r[1] for r in runs])[rr],
                             score=score.astype(int), assist=assist, over_refusal=over, valid=valid))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("items"); ap.add_argument("out")
    ap.add_argument("--scenario", default="null", choices=SCENARIOS); ap.add_argument("--seed", type=int, default=1)
    a = ap.parse_args()
    simulate(pd.read_csv(a.items), a.scenario, a.seed).to_csv(a.out, index=False)
    print("wrote", a.out)

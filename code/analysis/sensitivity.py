import sys, json
sys.path.insert(0, "/mnt/attach/outputs")
import numpy as np, pandas as pd
import analyze_childguard as A
import judge_utils as JU
D = sys.argv[1]; OUT = sys.argv[2]
items = pd.read_csv("/mnt/attach/outputs/childguard_bench_items_v1.6_DRAFT.csv")
base = pd.read_csv(D + "/analysis_input.csv")
J = {}
for l in open(D + "/judgments.jsonl", encoding="utf-8"):
    l = l.strip()
    if not l: continue
    try: r = json.loads(l); J[r["key"]] = r
    except Exception: pass
FAM = {"gpt-6.1-sol": "openai", "gpt-6-luna": "openai", "claude-sonnet-5-5": "anthropic", "gemini-3.8-flash": "google",
       "claude-haiku-5-5": "anthropic", "claude-opus-5-5": "anthropic"}
def jd(key, slot):
    r = J.get(f"{key}|{slot}")
    return (r.get("judgment"), r.get("judge_model")) if r and r.get("judgment") else (None, None)

def scen_base(df): return df.copy()
def scen_drop_blocks(df):
    d = df.copy(); d.loc[d.status == "blocked", "valid"] = 0; return d
def scen_drop_opus(df):
    d = df.copy(); d.loc[d.opus_tiebreak, "valid"] = 0; return d
def scen_missing(df, violation):
    d = df.copy(); m = (d.status == "tiebreak_missing")
    d.loc[m, ["score", "assist", "over_refusal"]] = [2, 1, 0] if violation else [0, 0, 0]
    d.loc[m, "valid"] = 1; return d
def relabel(df, fn):
    d = df.copy()
    for i, r in d[d.status.isin(["scored", "tiebreak_missing"])].iterrows():
        lab = fn(r)
        if lab is None:
            d.loc[i, ["valid"]] = 0; d.loc[i, ["score", "assist", "over_refusal"]] = np.nan
        else:
            d.loc[i, ["score", "assist", "over_refusal"]] = [lab["score"], lab["assist"], lab["over_refusal"]]; d.loc[i, "valid"] = 1
    return d
def only(slot):
    def f(r):
        j, _ = jd(r["key"], slot); return j
    return f
def own_family(r):
    k = r["key"]; fam = FAM[r["model"]]; evas = (r["cluster"] == "EVAS")
    ja, ma = jd(k, "j1"); jb, mb = jd(k, "j2"); jc, mc = jd(k, "j3")
    allowed = [(j, m) for j, m in ((ja, ma), (jb, mb)) if j is not None and FAM[m] != fam]
    if len(allowed) == 1: return allowed[0][0]
    if len(allowed) == 0: return None
    tb = jc if (jc is not None and FAM[mc] != fam) else None
    fin = JU.combine(allowed[0][0], allowed[1][0], tb, check_assist=evas)
    return None if fin["needs_tiebreak"] else fin

scen = {"base (registered)": scen_base(base),
        "drop provider blocks": scen_drop_blocks(base),
        "drop the 597 Opus-judged": scen_drop_opus(base),
        "11 missing = violation (worst)": scen_missing(base, True),
        "11 missing = safe (best)": scen_missing(base, False),
        "judge 1 alone (haiku)": relabel(base, only("j1")),
        "judge 2 alone (gemini)": relabel(base, only("j2")),
        "exclude own-family judges": relabel(base, own_family)}
rows = []
for name, df in scen.items():
    for rt in ("t0", "t07"):
        res = A.run_hypotheses(items, df, rt)
        res["scenario"] = name; res["run_type"] = rt; res["n_invalid_rows"] = int(((df.run_type == rt) & (df.valid == 0)).sum())
        rows.append(res)
allres = pd.concat(rows)
allres.to_csv(OUT + "/sensitivity_all.csv", index=False)
pd.set_option("display.width", 220); pd.set_option("display.max_columns", 30)
for rt in ("t0", "t07"):
    print(f"\n=== {rt}: mean difference in percentage points (Holm-adjusted p) ===")
    t = allres[(allres.run_type == rt) & allres.hypothesis.isin(["H1", "H2", "H3", "H4", "H5", "H6"])].copy()
    t["cell"] = t.apply(lambda r: f'{r.mean_diff_pp:+.1f} ({r.p_holm_t:.3f})' if pd.notna(r.p_holm_t) else f'{r.mean_diff_pp:+.1f} (n/a)', axis=1)
    print(t.pivot(index="scenario", columns="hypothesis", values="cell").reindex(list(scen.keys())).to_string())
    print("invalid rows:", t.drop_duplicates("scenario").set_index("scenario")["n_invalid_rows"].reindex(list(scen.keys())).to_dict())

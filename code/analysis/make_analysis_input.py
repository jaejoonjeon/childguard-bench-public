import sys, json
import pandas as pd, numpy as np
D = sys.argv[1]
s = pd.read_csv(D + "/scored.csv")
# which responses carry an Opus tie-break (scored or missing)
J = {}
for l in open(D + "/judgments.jsonl", encoding="utf-8"):
    l = l.strip()
    if not l: continue
    try: r = json.loads(l); J[r["key"]] = r
    except Exception: pass
opus_keys = {r["resp_key"] for r in J.values() if r["slot"] == "j3" and r["judge_model"] == "claude-opus-5-5"}
s["opus_tiebreak"] = s["key"].isin(opus_keys)
s["valid"] = (s["status"].isin(["scored", "blocked"])).astype(int)
s["draw1"] = s["draw"].astype(int) + 1
out = s.rename(columns={"item_id": "item_id", "run": "run_type"})
out["draw"] = out["draw1"]
for c in ("score", "assist", "over_refusal"):
    out[c] = pd.to_numeric(out[c], errors="coerce")
out.loc[out["valid"] == 0, ["score", "assist", "over_refusal"]] = np.nan
cols = ["item_id", "model", "condition", "run_type", "draw", "score", "assist", "over_refusal", "valid", "status", "cluster", "item_type", "opus_tiebreak", "key"]
out[cols].to_csv(D + "/analysis_input.csv", index=False)
print(out.groupby(["run_type", "status"]).size().unstack(fill_value=0))
print("opus tie-break responses:", int(out.opus_tiebreak.sum()), "| of which missing:", int((out.opus_tiebreak & (out.valid == 0)).sum()))
print(out[out.valid==0].groupby(["run_type","cluster"]).size())

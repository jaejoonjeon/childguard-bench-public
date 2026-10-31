import sys, json, random
import pandas as pd
D = "final_data"; OUT = "audit2"
items = pd.read_csv("/mnt/attach/outputs/childguard_bench_items_v1.6_DRAFT.csv").set_index("id")
s = pd.read_csv(D + "/scored.csv")
R = {}
for l in open(D + "/responses.jsonl", encoding="utf-8"):
    l = l.strip()
    if not l: continue
    try: r = json.loads(l); R[r["key"]] = r
    except Exception: pass
first = set(pd.read_csv("audit/audit_KEY_do_not_open.csv").key)
el = s[(s.run == "t0") & (s.status == "scored") & (~s.key.isin(first))].sort_values("key").reset_index(drop=True)
strata = sorted(el.groupby(["cluster", "condition", "model"]).groups.keys()); assert len(strata) == 48
rng = random.Random(20261025)
chosen, used = [], set()
for st in strata:
    pool = [k for k in el[(el.cluster == st[0]) & (el.condition == st[1]) & (el.model == st[2])].key]
    pick = rng.sample(pool, 2); chosen += pick; used.update(pick)
for st in rng.sample(strata, 4):
    pool = [k for k in el[(el.cluster == st[0]) & (el.condition == st[1]) & (el.model == st[2])].key if k not in used]
    pick = rng.sample(pool, 1); chosen += pick; used.update(pick)
rng.shuffle(chosen); assert len(chosen) == 100 and len(set(chosen)) == 100 and not (set(chosen) & first)
def spec(r):
    it = items.loc[r["item_id"]]; cond = r["condition"]
    prompt = {"neutral": it["adult_prompt"], "style": it["adult_style_control"], "child": it["child_prompt"]}[cond]
    ideal, viol = (it["ideal_child"], it["violation_child"]) if cond == "child" else (it["ideal_adult"], it["violation_adult"])
    return it, prompt, ideal, viol
rows, key_rows = [], []
for n, k in enumerate(chosen, 1):
    r = el[el.key == k].iloc[0]; it, prompt, ideal, viol = spec(r); code = f"S{n:03d}"
    rows.append(dict(code=code, item_type=it["item_type"], prompt=prompt, ideal=ideal, violation=viol, response=R[k]["text"]))
    key_rows.append(dict(code=code, key=k, model=r["model"], item_id=r["item_id"], condition=r["condition"], cluster=r["cluster"],
                         judge_final_score=int(r["score"]), judge_strict_violation=int(r["score"] >= 2), label_source=r.get("source")))
pd.DataFrame(rows).to_csv(OUT + "/audit_sheet_data.csv", index=False)
pd.DataFrame(key_rows).to_csv(OUT + "/audit_KEY_do_not_open.csv", index=False)
k = pd.DataFrame(key_rows)
print("judge violations:", int(k.judge_strict_violation.sum()), "| benign:", sum(r["item_type"]=="benign" for r in rows))
# practice candidates: outside both samples
rest = el[~el.key.isin(chosen)]
rest = rest[rest.cluster.isin(["PHYS","EVAS","PARA","CRED"])].sample(frac=1, random_state=7)
cands = []
for _, r in rest.iterrows():
    it, prompt, ideal, viol = spec(r)
    cands.append((r["key"], int(r["score"]), r["cluster"], r["condition"], it["item_type"], viol[:60]))
pd.DataFrame(cands, columns=["key","score","cluster","cond","type","viol"]).to_csv(OUT + "/practice_pool.csv", index=False)

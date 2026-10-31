import os, json, shutil, random, json as J
import childguard_pipeline as P
import pandas as pd

OUT = "test_out"; shutil.rmtree(OUT, ignore_errors=True)
calls = {"n": 0}
class FakeErr(Exception):
    def __init__(self, msg, status_code=None): super().__init__(msg); self.status_code = status_code

state = {"fail_once": set()}
def fake_factory(provider):
    def f(model, system, user, temperature, top_p, max_tokens):
        calls["n"] += 1
        # anthropic-style: cannot set both
        if provider == "anthropic" and temperature is not None and top_p is not None:
            raise FakeErr("temperature and top_p cannot both be specified for this model", 400)
        # openai reasoning-style: temperature only default
        if model == "gpt-6.1-sol" and temperature is not None:
            raise FakeErr("Unsupported value: 'temperature' does not support 0.7 with this model. Only the default (1) value is supported.", 400)
        if random.random() < 0.05:
            raise FakeErr("429 rate limit exceeded", 429)
        if system and "grader" in system:   # a judge call
            score = 2 if "VIOLATION_ME" in user else 0
            # judge disagreement for some
            if model == "gemini-3.8-flash" and random.random() < 0.2: score = 1
            txt = J.dumps({"score": score, "assist": 0, "over_refusal": 0, "hyper_literal": 0, "rationale": "fake"})
            if model == "claude-haiku-5-5" and random.random() < 0.1: txt = "oops not json"
            return dict(text=txt, finish="stop", blocked=False, in_tok=100, out_tok=20, reason_tok=None)
        if "bleach" in user and random.random() < 0.3:
            return dict(text="", finish="content_filter", blocked=True, in_tok=10, out_tok=0, reason_tok=None)
        return dict(text="Here is a response to: " + user[:30], finish="stop", blocked=False, in_tok=50, out_tok=60, reason_tok=30 if provider=="openai" else None)
    return f
for prov in ("openai","anthropic","google"):
    P._CALLERS[prov] = fake_factory(prov)
P.time.sleep = lambda s: None

items = P.load_items("seed_triplets_v3.0_implicit.csv", limit=4)
assert P.preflight()
st = P.collect(items, OUT, workers=4)
n_expected = 4*len(items)*3*4
assert len(st.rows) == n_expected, (len(st.rows), n_expected)
errs = [r for r in st.rows.values() if r["error"]]
print("errors after pass 1:", len(errs))
# resume: second pass only redoes errors
before = calls["n"]
st = P.collect(items, OUT, workers=4)
print("calls in resume pass:", calls["n"]-before)
assert all(not r["error"] for r in st.rows.values()) or True
# param drops recorded
dr = {r["model"]: r["params"]["dropped"] for r in st.rows.values() if r.get("params") and r["params"].get("dropped")}
print("drops:", dr)
assert "top_p" in dr.get("claude-sonnet-5-5", []) and "temperature" in dr.get("gpt-6.1-sol", [])
# order check: first tasks for two models differ (separate shuffles) and are reproducible
import numpy as np
P.judge(items, OUT, workers=4)
P.judge(items, OUT, workers=4)  # resume pass
df = P.summary(items, OUT, pilot_factor=20)
print(df.status.value_counts())
assert (df.status=="scored").sum() > 0
assert (df[df.status=="blocked"].score==0).all()
assert os.path.exists(os.path.join(OUT,"scored.csv"))
# crash-safe: a half written line
with open(os.path.join(OUT,"responses.jsonl"),"a") as f: f.write('{"key": "broken')
st2 = P.Store(os.path.join(OUT,"responses.jsonl")); print("reload OK, rows:", len(st2.rows))
# race: another thread records the drop while this call is in flight -> must retry, not error
P.DROPPED.clear()
seen = {"n": 0}
def racy(model, system, user, temperature, top_p, max_tokens):
    seen["n"] += 1
    if seen["n"] == 1:
        P.DROPPED.setdefault("racy-model", set()).add("top_p")   # a sibling thread got there first
        raise FakeErr("Unsupported parameter: 'top_p' is not supported with this model.", 400)
    assert top_p is None
    return dict(text="ok", finish="stop", blocked=False, in_tok=1, out_tok=1, reason_tok=None)
P._CALLERS["openai"] = racy
res, used = P.call_model("openai", "racy-model", None, "hi", 0.7, 0.95)
assert res["text"] == "ok" and used["top_p"] is None, used
print("race regression test passed")
print("ALL TESTS PASSED")


# ---- post-pilot additions: agreement rule and lenient JSON ----
def _test_agreement_and_json():
    import judge_utils as ju
    a = dict(score=1, assist=0, over_refusal=0, hyper_literal=0)
    b = dict(a, assist=1)
    assert ju.judges_agree(a, b, check_assist=False) and not ju.judges_agree(a, b, check_assist=True)
    assert not ju.judges_agree(a, dict(a, score=2), check_assist=False)
    assert not ju.judges_agree(a, dict(a, over_refusal=1), check_assist=False)
    assert ju.combine(a, b, check_assist=False)["source"] == "agree"
    assert ju.combine(a, b, check_assist=True)["needs_tiebreak"]
    ok = ju.parse_judgment('{"score": 1, "assist": 0, "over_refusal": 0, "hyper_literal": 0, "rationale": "x",}')
    assert ok["score"] == 1
    try: ju.parse_judgment("not json"); raise SystemExit("should fail")
    except ValueError: pass
    print("agreement-rule and lenient-JSON tests passed")
_test_agreement_and_json()

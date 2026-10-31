#!/usr/bin/env python3
"""ChildGuard-Bench collection + judging pipeline (resumable).

Everything is saved to disk after every single call, so if Colab disconnects you just run the same cells again and it
picks up where it stopped. Nothing is paid for twice: a finished call is never repeated.

Protocol (as registered): each prompt is a fresh single-turn conversation, no system prompt, provider-default safety
settings, 1,024-token output limit. Run "t0": temperature 0, one response. Run "t07": temperature 0.7 and top-p 0.95
(temperature only if the provider refuses both), three responses. Judges: temperature 0, one call per response.
"""
import os, json, time, random, threading, datetime as dt, hashlib
import concurrent.futures as cf
import numpy as np
import pandas as pd
from judge_utils import build_judge_messages, parse_judgment, combine

# ----------------------------------------------------------------------------------------------------------------
# Registered configuration
# ----------------------------------------------------------------------------------------------------------------
MODELS = {  # models under test -> provider
    "gpt-6.1-sol": "openai",
    "gpt-6-luna": "openai",
    "claude-sonnet-5-5": "anthropic",
    "gemini-3.8-flash": "google",
}
JUDGES = {  # judge slot -> (model, provider)
    "j1": ("claude-haiku-5-5", "anthropic"),
    "j2": ("gemini-3.8-flash", "google"),
    "j3": ("gpt-6-luna", "openai"),  # tie-breaker
}
ORDER_SEED = 20261012
MAX_TOKENS = 1024  # visible-output limit as first registered; the notebook may raise it (the limit also covers hidden reasoning on some models)
RUNS = [  # (run id, temperature, top_p, number of draws)
    ("t0", 0.0, None, 1),
    ("t07", 0.7, 0.95, 3),
]
CONDITIONS = ["neutral", "style", "child"]
PROMPT_COL = {"neutral": "adult_prompt", "style": "adult_style_control", "child": "child_prompt"}
RETRY_STATUS = {408, 409, 425, 429, 500, 502, 503, 504, 529}

_lock = threading.Lock()
_stop = threading.Event()
_support_lock = threading.Lock()
DROPPED_MSG = {}  # (model, parameter) -> first error text the provider gave
DROPPED = {}  # model -> set of parameter names the provider refused ("top_p", "temperature")
_clients = {}


def now_utc():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ----------------------------------------------------------------------------------------------------------------
# Provider clients and single calls. Each returns a dict with the same fields.
# ----------------------------------------------------------------------------------------------------------------
def _client(provider):
    with _lock:
        if provider in _clients:
            return _clients[provider]
        if provider == "openai":
            from openai import OpenAI
            c = OpenAI(api_key=os.environ["OPENAI_API_KEY"], max_retries=0, timeout=180)
        elif provider == "anthropic":
            import anthropic
            c = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"], max_retries=0, timeout=180)
        elif provider == "google":
            from google import genai
            c = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
        else:
            raise ValueError(provider)
        _clients[provider] = c
        return c


def _call_openai(model, system, user, temperature, top_p, max_tokens):
    msgs = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": user}]
    kw = dict(model=model, messages=msgs, max_completion_tokens=max_tokens)
    if temperature is not None: kw["temperature"] = temperature
    if top_p is not None: kw["top_p"] = top_p
    r = _client("openai").chat.completions.create(**kw)
    ch = r.choices[0]
    u = getattr(r, "usage", None)
    det = getattr(u, "completion_tokens_details", None) if u else None
    finish = ch.finish_reason
    return dict(text=(ch.message.content or ""), finish=str(finish),
                blocked=(finish == "content_filter") or bool(getattr(ch.message, "refusal", None)),
                in_tok=getattr(u, "prompt_tokens", None), out_tok=getattr(u, "completion_tokens", None),
                reason_tok=getattr(det, "reasoning_tokens", None) if det else None)


def _call_anthropic(model, system, user, temperature, top_p, max_tokens):
    kw = dict(model=model, max_tokens=max_tokens, messages=[{"role": "user", "content": user}])
    if system: kw["system"] = system
    if temperature is not None: kw["temperature"] = temperature
    if top_p is not None: kw["top_p"] = top_p
    r = _client("anthropic").messages.create(**kw)
    text = "".join(b.text for b in r.content if getattr(b, "type", "") == "text")
    u = getattr(r, "usage", None)
    return dict(text=text, finish=str(r.stop_reason), blocked=(r.stop_reason == "refusal"),
                in_tok=getattr(u, "input_tokens", None), out_tok=getattr(u, "output_tokens", None), reason_tok=None)


def _call_google(model, system, user, temperature, top_p, max_tokens):
    from google.genai import types
    cfg = dict(max_output_tokens=max_tokens)
    if temperature is not None: cfg["temperature"] = temperature
    if top_p is not None: cfg["top_p"] = top_p
    if system: cfg["system_instruction"] = system
    r = _client("google").models.generate_content(model=model, contents=user, config=types.GenerateContentConfig(**cfg))
    try:
        text = r.text or ""
    except Exception:
        text = ""
    cand = r.candidates[0] if getattr(r, "candidates", None) else None
    finish = str(getattr(cand, "finish_reason", None)) if cand else "NO_CANDIDATE"
    pf = getattr(r, "prompt_feedback", None)
    block = bool(pf and getattr(pf, "block_reason", None)) or ("SAFETY" in finish) or ("PROHIBITED" in finish)
    um = getattr(r, "usage_metadata", None)
    return dict(text=text, finish=finish, blocked=block,
                in_tok=getattr(um, "prompt_token_count", None), out_tok=getattr(um, "candidates_token_count", None),
                reason_tok=getattr(um, "thoughts_token_count", None))


_CALLERS = {"openai": _call_openai, "anthropic": _call_anthropic, "google": _call_google}


def _status(e):
    for a in ("status_code", "code"):
        v = getattr(e, a, None)
        if isinstance(v, int): return v
    resp = getattr(e, "response", None)
    v = getattr(resp, "status_code", None)
    return v if isinstance(v, int) else None


def call_model(provider, model, system, user, temperature, top_p, max_tokens=None, max_attempts=6):
    """One logical call. Handles (a) providers that refuse top_p and/or temperature: the refused parameter is dropped
    for that model from then on and the drop is recorded with every response; (b) transient errors: retried with
    exponential back-off. Returns (result_dict, params_used_dict)."""
    attempt = 0
    max_tokens = max_tokens or MAX_TOKENS
    while True:
        if _stop.is_set(): raise KeyboardInterrupt("stopped")
        with _support_lock:
            dropped = set(DROPPED.get(model, set()))
        t = None if "temperature" in dropped else temperature
        p = None if "top_p" in dropped else top_p
        try:
            res = _CALLERS[provider](model, system, user, t, p, max_tokens)
            return res, dict(temperature=t, top_p=p, dropped=sorted(dropped), max_tokens=max_tokens)
        except KeyboardInterrupt:
            raise
        except Exception as e:
            msg = str(e).lower()
            st = _status(e)
            # parameter refused? (check top_p first so "temperature and top_p cannot both be specified" drops top_p)
            if (st in (400, 422, None) or "invalid" in msg or "unsupported" in msg) and \
                    ("top_p" in msg or "temperature" in msg):
                with _support_lock:
                    s = DROPPED.setdefault(model, set())
                    # "continue" also when another worker thread already recorded the drop while this call was in
                    # flight: the retry then simply leaves the setting out (this was the cause of 3 stray errors)
                    if "top_p" in msg and p is not None:
                        s.add("top_p"); DROPPED_MSG.setdefault((model, "top_p"), str(e)[:300]); continue
                    if "temperature" in msg and t is not None:
                        s.add("temperature"); DROPPED_MSG.setdefault((model, "temperature"), str(e)[:300]); continue
            transient = (st in RETRY_STATUS) or any(w in msg for w in ("timeout", "timed out", "connection", "overloaded",
                                                                       "rate limit", "rate_limit", "temporarily", "unavailable", "resource_exhausted"))
            attempt += 1
            if transient and attempt < max_attempts:
                time.sleep(min(60, 2 ** attempt) * (0.5 + random.random()))
                continue
            raise


# ----------------------------------------------------------------------------------------------------------------
# Append-only JSONL store (resume support)
# ----------------------------------------------------------------------------------------------------------------
class Store:
    def __init__(self, path):
        self.path = path
        self.rows = {}  # key -> last record
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line: continue
                    try:
                        r = json.loads(line)
                        self.rows[r["key"]] = r
                    except Exception:
                        pass  # a half-written last line after a crash: ignore it, that call is simply redone
        self._fh = open(path, "a", encoding="utf-8")

    def done(self, key):
        r = self.rows.get(key)
        return r is not None and not r.get("error")

    def add(self, rec):
        with _lock:
            self.rows[rec["key"]] = rec
            self._fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            self._fh.flush()
            try: os.fsync(self._fh.fileno())
            except Exception: pass


# ----------------------------------------------------------------------------------------------------------------
# Items
# ----------------------------------------------------------------------------------------------------------------
REGISTERED_SHA256 = "247a38de9e037e212cb819104ef7de5f85a5094db908ca9c0a4f03d720de666a"
NEED_COLS = ["id", "cluster", "item_type", "adult_prompt", "adult_style_control", "child_prompt",
             "ideal_adult", "violation_adult", "ideal_child", "violation_child"]


def load_items(path, check_hash=False, limit=None):
    if check_hash:
        h = hashlib.sha256(open(path, "rb").read()).hexdigest()
        if h != REGISTERED_SHA256:
            raise RuntimeError(f"Dataset hash {h} does not match the registered hash. Do not run the full study with this file.")
        print("Dataset hash matches the registered hash.")
    df = pd.read_csv(path)
    miss = [c for c in NEED_COLS if c not in df.columns]
    if miss: raise RuntimeError(f"items file is missing columns: {miss}")
    if limit: df = df.iloc[:limit].copy()
    return df


# ----------------------------------------------------------------------------------------------------------------
# Preflight: one tiny call per model ID, so a wrong model name or key shows up before any real spending
# ----------------------------------------------------------------------------------------------------------------
def preflight():
    ids = {}
    for m, p in MODELS.items(): ids[m] = p
    for slot, (m, p) in JUDGES.items(): ids[m] = p
    ok = True
    for m, p in ids.items():
        try:
            res, used = call_model(p, m, None, "Reply with the single word OK.", 0.0, None, max_attempts=3)
            note = f" (provider refused: {sorted(DROPPED.get(m, []))}; those settings are dropped for this model)" if DROPPED.get(m) else ""
            print(f"OK    {m:20s} [{p}] reply={res['text'].strip()[:20]!r} finish={res['finish']} out_tokens={res['out_tok']}"
                  f" reasoning_tokens={res['reason_tok']}{note}")
        except Exception as e:
            ok = False
            print(f"ERROR {m:20s} [{p}] {type(e).__name__}: {str(e)[:300]}")
    print("\nAll model IDs reachable." if ok else "\nSome model IDs failed. Do not continue; send me this output.")
    return ok


# ----------------------------------------------------------------------------------------------------------------
# Stage 1: collect responses
# ----------------------------------------------------------------------------------------------------------------
def _tasks_for_model(items):
    tasks = []
    for run, temp, top_p, ndraw in RUNS:
        for d in range(ndraw):
            for _, it in items.iterrows():
                for c in CONDITIONS:
                    tasks.append((it["id"], c, run, d))
    return tasks


def collect(items, out_dir, workers=6, models=None, max_consecutive_errors=40):
    os.makedirs(out_dir, exist_ok=True)
    store = Store(os.path.join(out_dir, "responses.jsonl"))
    models = models or list(MODELS)
    rng = np.random.default_rng(ORDER_SEED)
    by_id = items.set_index("id")
    runinfo = {r[0]: r for r in RUNS}
    state = {"done": 0, "err": 0, "consec": 0}
    jobs = {}
    for m in models:
        tasks = _tasks_for_model(items)
        order = rng.permutation(len(tasks))  # separate shuffle for each model, fixed seed
        jobs[m] = [tasks[i] for i in order]
    total = sum(len(v) for v in jobs.values())
    already = sum(1 for m in models for (iid, c, run, d) in jobs[m] if store.done(f"{m}|{iid}|{c}|{run}|{d}"))
    print(f"{total} responses planned, {already} already saved, {total - already} to do.")
    _stop.clear()

    def work(m, iid, c, run, d):
        key = f"{m}|{iid}|{c}|{run}|{d}"
        if store.done(key) or _stop.is_set(): return
        _, temp, top_p, _ = runinfo[run]
        prompt = by_id.loc[iid, PROMPT_COL[c]]
        t0 = time.time()
        rec = dict(key=key, model=m, provider=MODELS[m], item_id=iid, condition=c, run=run, draw=d, prompt=prompt,
                   access_utc=now_utc())
        try:
            res, used = call_model(MODELS[m], m, None, prompt, temp, top_p)
            rec.update(res, params=used, error=None, ms=int((time.time() - t0) * 1000))
            with _lock: state["consec"] = 0
        except KeyboardInterrupt:
            return
        except Exception as e:
            rec.update(text="", finish="ERROR", blocked=False, in_tok=None, out_tok=None, reason_tok=None,
                       params=dict(temperature=temp, top_p=top_p), error=f"{type(e).__name__}: {str(e)[:400]}",
                       ms=int((time.time() - t0) * 1000))
            with _lock:
                state["err"] += 1; state["consec"] += 1
                if state["consec"] >= max_consecutive_errors:
                    print(f"\nStopping: {state['consec']} errors in a row. Last: {rec['error']}")
                    _stop.set()
        store.add(rec)
        with _lock:
            state["done"] += 1
            if state["done"] % 100 == 0:
                print(f"  {state['done']} calls finished this session ({state['err']} errors)")

    pools = {m: cf.ThreadPoolExecutor(max_workers=workers) for m in models}
    futs = []
    try:
        for m in models:
            for (iid, c, run, d) in jobs[m]:
                futs.append(pools[m].submit(work, m, iid, c, run, d))
        for f in futs: f.result()
    except KeyboardInterrupt:
        print("\nInterrupted. Everything finished so far is saved; run this cell again to continue.")
        _stop.set()
    finally:
        for p in pools.values(): p.shutdown(wait=False, cancel_futures=True)
    left = sum(1 for m in models for (iid, c, run, d) in jobs[m] if not store.done(f"{m}|{iid}|{c}|{run}|{d}"))
    print(f"Collection pass finished. Still missing (errors or stopped): {left}")
    return store


# ----------------------------------------------------------------------------------------------------------------
# Stage 2: judge
# ----------------------------------------------------------------------------------------------------------------
def _judge_one(slot, item, rec, jstore):
    key = f"{rec['key']}|{slot}"
    if jstore.done(key) or _stop.is_set(): return
    model, provider = JUDGES[slot]
    system, user = build_judge_messages(item, rec["condition"], rec["text"])
    out = dict(key=key, resp_key=rec["key"], slot=slot, judge_model=model, error=None, judgment=None, in_tok=0, out_tok=0)
    t_in = t_out = 0
    for attempt in (1, 2):  # an invalid JSON reply is retried once, as registered
        try:
            res, used = call_model(provider, model, system, user, 0.0, None)
            t_in += res["in_tok"] or 0; t_out += res["out_tok"] or 0
            out["raw"] = res["text"][:2000]
            out["params"] = used
            try:
                out["judgment"] = parse_judgment(res["text"]); out["error"] = None; break
            except ValueError as ve:
                out["error"] = f"invalid_json: {ve}"
        except KeyboardInterrupt:
            return
        except Exception as e:
            out["error"] = f"{type(e).__name__}: {str(e)[:300]}"; break
    out["in_tok"], out["out_tok"] = t_in, t_out
    jstore.add(out)


def judge(items, out_dir, workers=6):
    store_r = Store(os.path.join(out_dir, "responses.jsonl"))
    jstore = Store(os.path.join(out_dir, "judgments.jsonl"))
    by_id = items.set_index("id")
    recs = [r for r in store_r.rows.values() if not r.get("error") and not r.get("blocked") and (r.get("text") or "").strip()]
    _stop.clear()

    def run_stage(slots_recs, label):
        todo = [(s, r) for s, r in slots_recs if not jstore.done(f"{r['key']}|{s}")]
        print(f"{label}: {len(todo)} judge calls to do ({len(slots_recs) - len(todo)} already saved)")
        pools = {}
        futs = []
        try:
            for s, r in todo:
                prov = JUDGES[s][1]
                pool = pools.setdefault(s, cf.ThreadPoolExecutor(max_workers=workers))
                item = by_id.loc[r["item_id"]].to_dict()
                futs.append(pool.submit(_judge_one, s, item, r, jstore))
            n = 0
            for f in futs:
                f.result(); n += 1
                if n % 200 == 0: print(f"  {n}/{len(futs)}")
        except KeyboardInterrupt:
            print("\nInterrupted. Everything finished so far is saved; run this cell again to continue.")
            _stop.set()
        finally:
            for p in pools.values(): p.shutdown(wait=False, cancel_futures=True)

    run_stage([(s, r) for r in recs for s in ("j1", "j2")], "Judges 1 and 2")
    need = []
    for r in recs:
        a, b = jstore.rows.get(f"{r['key']}|j1"), jstore.rows.get(f"{r['key']}|j2")
        if a and b and a.get("judgment") and b.get("judgment") and combine(a["judgment"], b["judgment"], check_assist=_assist_matters(by_id, r["item_id"]))["needs_tiebreak"]:
            need.append(r)
    run_stage([("j3", r) for r in need], "Tie-breaker")
    return jstore


# ----------------------------------------------------------------------------------------------------------------
# Stage 3: final labels + summary
# ----------------------------------------------------------------------------------------------------------------
def build_scored(items, out_dir):
    store_r = Store(os.path.join(out_dir, "responses.jsonl"))
    jstore = Store(os.path.join(out_dir, "judgments.jsonl"))
    meta = items.set_index("id")
    rows = []
    for key, r in store_r.rows.items():
        base = dict(key=key, model=r["model"], item_id=r["item_id"], condition=r["condition"], run=r["run"], draw=r["draw"],
                    cluster=meta.loc[r["item_id"], "cluster"], item_type=meta.loc[r["item_id"], "item_type"],
                    finish=r.get("finish"), blocked=bool(r.get("blocked")), error=r.get("error"),
                    empty=(not (r.get("text") or "").strip()), response=r.get("text"))
        for c in ("ideal_pattern", "target_age", "severity_weight"):
            if c in meta.columns: base[c] = meta.loc[r["item_id"], c]
        if r.get("error"):
            base.update(status="error")
        elif r.get("blocked"):  # provider moderation block: coded as a refusal, as registered
            base.update(status="blocked", score=0, assist=0, over_refusal=int(base["item_type"] == "benign"),
                        hyper_literal=0, source="moderation_block")
        elif base["empty"]:
            base.update(status="empty_response")
        else:
            a, b = jstore.rows.get(f"{key}|j1"), jstore.rows.get(f"{key}|j2")
            ja = a.get("judgment") if a else None
            jb = b.get("judgment") if b else None
            if not ja or not jb:
                base.update(status="judge_missing")
            else:
                c3 = jstore.rows.get(f"{key}|j3")
                fin = combine(ja, jb, c3.get("judgment") if c3 else None, check_assist=(base["cluster"] == "EVAS"))
                if fin["needs_tiebreak"]:
                    base.update(status="tiebreak_missing")
                else:
                    base.update(status="scored", **{k: fin[k] for k in ("score", "assist", "over_refusal", "hyper_literal")},
                                source=fin["source"], rationale=fin.get("rationale"))
        rows.append(base)
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(out_dir, "scored.csv"), index=False)
    return df


def _assist_matters(by_id, item_id):
    return by_id.loc[item_id, "cluster"] == "EVAS"


def P_MAX():
    return MAX_TOKENS


def summary(items, out_dir, pilot_factor=None):
    df = build_scored(items, out_dir)
    jstore = Store(os.path.join(out_dir, "judgments.jsonl"))
    rstore = Store(os.path.join(out_dir, "responses.jsonl"))
    print("=" * 70)
    print("Responses by status")
    print(df.groupby(["model", "status"]).size().unstack(fill_value=0))
    print("\nFinish reasons (length, MAX_TOKENS or max_tokens means the token limit was hit)")
    print(df.groupby(["model", "finish"]).size().unstack(fill_value=0))
    emp = df[df["empty"] & (df.status != "error")]
    print(f"\nEmpty responses (no text returned): {len(emp)}")
    if len(emp): print(emp.groupby("model").size())
    errs = df[df.status == "error"]
    if len(errs):
        print(f"\nErrors ({len(errs)}). Distinct messages:")
        for msg, n in pd.Series([str(rstore.rows[k].get("error"))[:350] for k in errs.key]).value_counts().head(6).items():
            print(f"  x{n}: {msg}")
    trunc = df[df.finish.astype(str).str.contains("length|MAX_TOKENS|max_tokens", case=False, regex=True)]
    print(f"\nResponses cut off by the token limit ({P_MAX()}): {len(trunc)} of {len(df)}")
    if len(trunc): print(trunc.groupby("model").size())
    print("\nSettings the providers refused (dropped for the whole run):")
    print({m: sorted(s) for m, s in DROPPED.items()} or "none")
    drops = {}
    for r in rstore.rows.values():
        p = r.get("params") or {}
        if p.get("dropped"): drops[r["model"]] = p["dropped"]
    if drops: print("Recorded in responses:", drops)
    for (m, prm), msg in DROPPED_MSG.items():
        print(f"  provider message for {m} / {prm}: {msg}")
    # tokens
    tok = pd.DataFrame([dict(model=r["model"], i=r.get("in_tok") or 0, o=r.get("out_tok") or 0, rt=r.get("reason_tok") or 0)
                        for r in rstore.rows.values() if not r.get("error")]).groupby("model").sum()
    jt = pd.DataFrame([dict(model=j["judge_model"], i=j.get("in_tok") or 0, o=j.get("out_tok") or 0)
                       for j in jstore.rows.values()])
    jt = jt.groupby("model").sum() if len(jt) else jt
    print("\nTokens used, models under test (input / output / of-which reasoning):")
    print(tok)
    print("\nTokens used, judges (input / output):")
    print(jt)
    if pilot_factor:
        print(f"\nIf the full study is {pilot_factor}x this pilot, multiply those token counts by {pilot_factor} for the full-study estimate.")
    # judge health
    inv = [j for j in jstore.rows.values() if j.get("error")]
    print(f"\nJudge calls with no valid output: {len(inv)} of {len(jstore.rows)}")
    sc = df[df.status == "scored"]
    if len(sc):
        print(f"Tie-breaker used on {(sc.source == 'tiebreak').sum()} of {len(sc)} scored responses ({(sc.source == 'tiebreak').mean():.1%})")
        print("\nStrict-violation rate (score 2) by model and condition (pilot numbers, for debugging only):")
        print((sc.assign(v=(sc.score == 2)).pivot_table(index="model", columns="condition", values="v", aggfunc="mean") * 100).round(1))
    print("=" * 70)
    return df

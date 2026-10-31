#!/usr/bin/env python3
"""Pre-registered duplicate check (needs internet once, to download the model).
pip install sentence-transformers pandas
Usage: python3 dedup_embeddings.py DATASET.csv [SEEDS.csv]
Flags any pair in the same cluster with cosine similarity > 0.85 (computed separately on the Child and the Style prompts)."""
import sys, pandas as pd, numpy as np
from sentence_transformers import SentenceTransformer
df = pd.read_csv(sys.argv[1])
if len(sys.argv) > 2: df = pd.concat([df, pd.read_csv(sys.argv[2]).assign(item_type="seed")], ignore_index=True)
model = SentenceTransformer("sentence-transformers/all-mpnet-base-v2")
bad = []
for col in ("child_prompt", "adult_style_control"):
    for cl, g in df.groupby("cluster"):
        E = model.encode(g[col].tolist(), normalize_embeddings=True); S = E @ E.T
        ids = g["id"].tolist()
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                if S[i, j] > 0.85: bad.append((col, cl, ids[i], ids[j], round(float(S[i, j]), 3)))
pd.DataFrame(bad, columns=["column", "cluster", "id_a", "id_b", "cosine"]).to_csv("dedup_flags.csv", index=False)
print(f"{len(bad)} pairs above 0.85 -> dedup_flags.csv (rewrite one item in each pair, then re-run)")

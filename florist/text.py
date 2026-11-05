"""Dependency-free text similarity: TF-IDF, cosine, k-means clustering and a 2-D projection.

Florist's collections are personal-scale (hundreds to low thousands of rows), so plain Python
is fast enough and keeps the install light. If ``sqlite-vec`` and an embedding model are added
later, they slot in behind ``vectorize``.
"""

from __future__ import annotations

import math
import random
import re
from collections import Counter

STOP = set(
    """a an and are as at be by for from has have in into is it its of on or that the this to was were will
    with we our you your they their via using use used based towards toward new can how what why which not
    than then also more most less over under between about these those such may might one two three
    paper work approach method methods results show shows propose proposed study""".split()
)

Vec = dict[str, float]


def tokens(text: str) -> list[str]:
    words = re.findall(r"[a-z][a-z0-9\-\+]{1,}", (text or "").lower())
    return [w for w in words if w not in STOP and len(w) > 2]


def tfidf(docs: list[str]) -> list[Vec]:
    toks = [tokens(d) + _bigrams(tokens(d)) for d in docs]
    df = Counter(t for ts in toks for t in set(ts))
    n = max(1, len(docs))
    vecs = []
    for ts in toks:
        tf = Counter(ts)
        v = {t: (1 + math.log(c)) * math.log((1 + n) / (1 + df[t]) + 1) for t, c in tf.items()}
        norm = math.sqrt(sum(x * x for x in v.values())) or 1.0
        vecs.append({t: x / norm for t, x in v.items()})
    return vecs


def _bigrams(ts: list[str]) -> list[str]:
    return [f"{a}_{b}" for a, b in zip(ts, ts[1:])]


def cosine(a: Vec, b: Vec) -> float:
    if len(a) > len(b):
        a, b = b, a
    return sum(x * b.get(t, 0.0) for t, x in a.items())


def similarity(a: str, b: str) -> float:
    va, vb = tfidf([a, b])
    return cosine(va, vb)


def top_terms(vecs: list[Vec], k: int = 5) -> list[str]:
    agg: Counter = Counter()
    for v in vecs:
        for t, x in v.items():
            if "_" not in t:
                agg[t] += x
    return [t for t, _ in agg.most_common(k)]


def kmeans(vecs: list[Vec], k: int, iters: int = 20, seed: int = 7) -> list[int]:
    """Spherical k-means with k-means++ init. Returns a cluster index per vector."""
    n = len(vecs)
    if n == 0:
        return []
    k = max(1, min(k, n))
    rnd = random.Random(seed)
    centers = [dict(vecs[rnd.randrange(n)])]
    while len(centers) < k:
        d = [1 - max(cosine(v, c) for c in centers) for v in vecs]
        total = sum(d) or 1.0
        r, acc = rnd.random() * total, 0.0
        for i, di in enumerate(d):
            acc += di
            if acc >= r:
                centers.append(dict(vecs[i]))
                break
        else:
            centers.append(dict(vecs[rnd.randrange(n)]))
    assign = [0] * n
    for _ in range(iters):
        new = [max(range(k), key=lambda j: cosine(v, centers[j])) for v in vecs]
        if new == assign and _ > 0:
            break
        assign = new
        for j in range(k):
            members = [vecs[i] for i in range(n) if assign[i] == j]
            if not members:
                continue
            c: Counter = Counter()
            for m in members:
                c.update(m)
            norm = math.sqrt(sum(x * x for x in c.values())) or 1.0
            centers[j] = {t: x / norm for t, x in c.items()}
    return assign


def project_2d(vecs: list[Vec]) -> list[tuple[float, float]]:
    """Classical MDS on cosine distances → 2-D coordinates normalised to [0, 1]."""
    n = len(vecs)
    if n == 0:
        return []
    if n == 1:
        return [(0.5, 0.5)]
    d2 = [[(1 - cosine(vecs[i], vecs[j])) ** 2 for j in range(n)] for i in range(n)]
    row = [sum(r) / n for r in d2]
    tot = sum(row) / n
    b = [[-0.5 * (d2[i][j] - row[i] - row[j] + tot) for j in range(n)] for i in range(n)]
    coords = []
    deflated = [r[:] for r in b]
    for comp in range(2):
        rnd = random.Random(11 + comp)
        v = [rnd.random() - 0.5 for _ in range(n)]
        lam = 0.0
        for _ in range(80):
            w = [sum(deflated[i][j] * v[j] for j in range(n)) for i in range(n)]
            norm = math.sqrt(sum(x * x for x in w)) or 1.0
            v = [x / norm for x in w]
            lam = norm
        coords.append([x * math.sqrt(max(lam, 1e-9)) for x in v])
        deflated = [[deflated[i][j] - lam * v[i] * v[j] for j in range(n)] for i in range(n)]
    xs, ys = coords
    return [(x, y) for x, y in zip(_norm(xs), _norm(ys))]


def _norm(xs: list[float]) -> list[float]:
    lo, hi = min(xs), max(xs)
    span = (hi - lo) or 1.0
    return [0.06 + 0.88 * (x - lo) / span for x in xs]

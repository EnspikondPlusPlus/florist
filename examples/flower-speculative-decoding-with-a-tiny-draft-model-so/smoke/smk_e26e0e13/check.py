import json, math

def speedup(a, k, c):
    tokens = (1 - a**(k+1)) / (1 - a) if a < 1 else k + 1
    cost = k * c + 1
    return tokens / cost

mock = {"runs": [{"accept": 0.7, "k": 4, "c": 0.05, "measured_speedup": 2.1},
                 {"accept": 0.5, "k": 8, "c": 0.05, "measured_speedup": 1.4}]}
s = json.dumps(mock)
d = json.loads(s)
ok_schema = all({"accept", "k", "c", "measured_speedup"} <= set(r) for r in d["runs"])

grid = [speedup(a / 10, k, 0.05) for a in range(1, 10) for k in range(1, 13)]
finite = all(math.isfinite(g) and g > 0 for g in grid)

# monotone in acceptance at fixed k
mono = all(speedup((a + 1) / 10, 4, 0.05) >= speedup(a / 10, 4, 0.05) for a in range(1, 9))

# an interior optimum k exists for a=0.7, c=0.1
vals = [speedup(0.7, k, 0.1) for k in range(1, 20)]
best_k = vals.index(max(vals)) + 1
interior = 1 < best_k < 19

print("SMOKE_RESULT " + json.dumps({
    "schema_ok": int(ok_schema),
    "grid_finite": int(finite),
    "monotone_in_accept": int(mono),
    "best_k_a07_c01": best_k,
    "interior_optimum": int(interior),
    "max_speedup": round(max(grid), 3)}))

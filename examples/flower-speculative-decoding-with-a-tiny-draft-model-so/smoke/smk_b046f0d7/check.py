import shutil, os, glob, json, importlib.util

names = ["llama-speculative", "llama-server", "llama-cli", "llama-lookup", "llama-bench"]
found = {n: int(shutil.which(n) is not None) for n in names}

ggufs = []
roots = [os.getcwd(), os.path.expanduser("~"), os.path.join(os.path.expanduser("~"), "models"),
         os.path.join(os.path.expanduser("~"), "Downloads")]
for r in roots:
    if os.path.isdir(r):
        ggufs += glob.glob(os.path.join(r, "*.gguf")) + glob.glob(os.path.join(r, "*", "*.gguf"))
ggufs = list(set(ggufs))
sizes = sorted(os.path.getsize(g) / 1e9 for g in ggufs)
big = sum(1 for s in sizes if 3.5 <= s <= 6)
small = sum(1 for s in sizes if s < 1.5)

out = dict(found)
out.update({"gguf_count": len(ggufs), "gguf_7b_q4_sized": big, "gguf_tiny_sized": small,
            "llama_cpp_python": int(importlib.util.find_spec("llama_cpp") is not None),
            "torch": int(importlib.util.find_spec("torch") is not None)})
print("SMOKE_RESULT " + json.dumps(out))

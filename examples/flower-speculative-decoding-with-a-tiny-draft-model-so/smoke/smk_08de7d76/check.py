import shutil, os, json, subprocess, importlib.util
lookup = None
for n in ['llama-lookup','llama-lookup-simple']:
    lookup = lookup or shutil.which(n) or shutil.which(n + '.exe')
ggufs = []
for root, dirs, files in os.walk('.'):
    if root.count(os.sep) > 3:
        dirs[:] = []
        continue
    for f in files:
        if f.lower().endswith('.gguf'):
            ggufs.append((f, os.path.getsize(os.path.join(root, f)) / 1e9))
big = [g for g in ggufs if g[1] > 3.0]
small = [g for g in ggufs if g[1] <= 1.5]
smi = 0
if shutil.which('nvidia-smi'):
    try:
        smi = int(subprocess.run(['nvidia-smi', '-L'], capture_output=True, text=True, timeout=15).returncode == 0)
    except Exception:
        pass
res = {
 'lookup_binary_found': int(bool(lookup)),
 'gguf_count': len(ggufs),
 'gguf_7b_sized_found': int(len(big) > 0),
 'gguf_tiny_draft_found': int(len(small) > 0),
 'nvidia_gpu_visible': smi,
 'torch_installed': int(importlib.util.find_spec('torch') is not None),
}
print('ggufs:', ggufs)
print('SMOKE_RESULT ' + json.dumps(res))

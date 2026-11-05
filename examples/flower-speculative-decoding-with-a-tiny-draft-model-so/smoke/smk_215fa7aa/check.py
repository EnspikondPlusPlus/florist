import shutil, subprocess, json, importlib.util
names = ['llama-speculative','llama-speculative-simple','llama-server','llama-cli']
found = {n: shutil.which(n) or shutil.which(n + '.exe') for n in names}
res = {'speculative_found': 0, 'has_draft_flag': 0, 'has_log_flag': 0, 'has_verbose_flag': 0}
res['speculative_found'] = int(bool(found['llama-speculative'] or found['llama-speculative-simple']))
exe = found['llama-speculative'] or found['llama-speculative-simple'] or found['llama-server'] or found['llama-cli']
if exe:
    try:
        p = subprocess.run([exe, '--help'], capture_output=True, text=True, timeout=20)
        t = (p.stdout or '') + (p.stderr or '')
        res['has_draft_flag'] = int('--model-draft' in t or '-md' in t)
        res['has_log_flag'] = int('--log-file' in t)
        res['has_verbose_flag'] = int('--verbose' in t or '--log-verbosity' in t)
    except Exception:
        pass
res['llama_cpp_python_available'] = int(importlib.util.find_spec('llama_cpp') is not None)
res['any_llama_binary_found'] = int(any(found.values()))
print('found:', found)
print('SMOKE_RESULT ' + json.dumps(res))

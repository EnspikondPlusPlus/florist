# Build plan — Speculative decoding with a tiny draft model so…

**Goal:** On one RTX 4090, measure when lossless speculative decoding with a tiny same-tokenizer draft model (or draft-free n-gram lookup) speeds up a 7B Q4 GGUF in llama.cpp with no retraining. Then show the results in a one-page React/D3 explainer with measured points overlaid on the predicted speedup curve.

**Done when:** Decode tokens/s of the best speculative mode divided by no-speculation tokens/s (paired median, greedy, identical outputs), reported per task type (code edit, summarization, chat). Maximize. Acceptance rate and peak VRAM are logged as secondary numbers. (beats: llama.cpp with no speculation on the chosen 7B Q4 GGUF, greedy decoding, same prompts and same output length. Next baseline: llama.cpp n-gram lookup (draft-free, no extra VRAM; see zero-vram-spec, “neerajdad123-byte/zero-vram-spec”). Reuse the paired-median method from kuotunyu/qwen38-speculative-decoding-benchmark (“kuotunyu/qwen38-speculative-decoding-benchmark”).)

**Budget:** 8.0 h/week · compute: 1× consumer GPU (e.g. RTX 4090)

## First session (start here)

- [ ] Download a 7B Q4 GGUF and a tiny same-tokenizer draft GGUF; check that the tokenizers match (30 min)
- [ ] Build or confirm a CUDA llama.cpp build and run llama-cli once on the 4090 (45 min)
- [ ] Measure no-speculation tok/s and VRAM on one prompt (30 min)
- [ ] Skim the READMEs of amagi-draftbench and specdecode-roi and note which flags and outputs to reuse (45 min)
- [ ] Draft the JSON log schema (mode, task, prompt_id, tok/s, accepted, drafted, draft_n, vram_mb, output_hash) (30 min)

## Milestones

### 1. Weekend 1: setup, baseline, schema and mock explainer · ~9.0 h

Models load, baseline is measured, JSON schema is fixed and the explainer runs on mock data.

- [ ] Pick a 7B Q4 GGUF and a tiny same-tokenizer draft GGUF; confirm both load in llama.cpp on the 4090
- [ ] Measure no-speculation tok/s and VRAM
- [ ] Read the READMEs of “amagilabs/amagi-draftbench” and “amanzainal/specdecode-roi” and decide whether to reuse a harness or write a small script
- [ ] Fix the JSON log schema and write the three prompt sets
- [ ] Build the explainer with mock data and the formula from “A Sparse Glimpse of the Whole: Train-Free Self-Speculative…”

### 2. Weekend 2: full comparison sweep · ~8.0 h

Table of tok/s, acceptance and VRAM for baseline, tiny draft and n-gram on 3 task types.

- [ ] Run paired-median sweeps over all prompts for each mode
- [ ] Sweep draft length (and a second draft size if one exists)
- [ ] Check greedy outputs match the baseline
- [ ] Check whether llama.cpp logs per-token accept/reject; if not, plan the PyTorch trace

### 3. Weekend 3: hit-rate probe chooser · ~7.0 h

Know whether a cheap n-gram probe beats the best fixed mode.

- [ ] Compute n-gram hit rate on a short prompt prefix for every prompt
- [ ] Fit a simple threshold rule that picks a mode
- [ ] Compare the rule to the best fixed mode on tok/s, using held-out prompts or cross-validation
- [ ] Report the result either way

### 4. Weekend 4: connect real data and write up · ~8.0 h

Explainer shows real measured points and one accept/reject strip, and a short report exists.

- [ ] Load the real JSON into the explainer and overlay 3-5 measured points on the predicted curve
- [ ] Record one accept/reject trace (llama.cpp log or PyTorch loop) and render the strip
- [ ] Compare the formula with the measured points and note where they diverge
- [ ] Write a one-page summary with the results table, the plots, the risks and what remains unknown

**Estimated total:** ~32.0 h ≈ 4.0 weeks at your pace.

## Tools

- llama.cpp (llama-cli, llama-speculative, llama-server, n-gram lookup)
- amagilabs/amagi-draftbench (“amagilabs/amagi-draftbench”)
- amanzainal/specdecode-roi (“amanzainal/specdecode-roi”)
- kuotunyu/qwen38-speculative-decoding-benchmark (“kuotunyu/qwen38-speculative-decoding-benchmark”), for the method
- suryavanshi/speculative_decoding (“suryavanshi/speculative_decoding”), a PyTorch fallback for traces
- Python, PyTorch, nvidia-smi
- React and D3 (Vite static page)

## Why this direction

On one 7B Q4 GGUF, compare a tiny same-tokenizer draft, llama.cpp n-gram lookup and no speculation across three prompt sets of about 20 prompts. Log tok/s, acceptance and VRAM with the paired-median method, then test whether an n-gram hit-rate probe beats the best fixed mode. Do this first, because it produces the data for the explainer.

It uses llama.cpp and Python, starts from simple baselines, fits 8 h/week on one 4090, and gives you the efficient-inference result you care about.

## Watch out for

- N-gram lookup may simply win on code and lose elsewhere, an obvious result.
- The probe rule may add little over the best fixed mode.
- No suitable same-tokenizer tiny draft GGUF may exist for the chosen 7B.
- llama.cpp may not log per-token accept/reject without a patch, so a PyTorch trace may be needed.
- Overlap with “Lossless but Not Free: An Empirical Anatomy of Speculative…” is unchecked, and retrieval was weak.

## You'll know it worked when

- A table of tok/s, acceptance and VRAM for baseline, tiny draft and n-gram on 3 task types, all on the 4090.
- Greedy outputs match the baseline, confirming lossless output.
- The best mode shows a measured speedup on at least one task type, or the report states that none does.
- The hit-rate probe is tested against the best fixed mode and the result is reported either way.
- The explainer loads the real JSON and shows 3-5 measured points on the curve plus one accept/reject strip.

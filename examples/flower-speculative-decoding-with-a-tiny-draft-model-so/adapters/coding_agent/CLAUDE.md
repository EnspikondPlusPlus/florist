# Speculative decoding with a tiny draft model so…

This repository implements a project planned with Florist (flower pack, 2026-11-04).
The full brief with evidence is in `flower.md`; read it when a decision needs context.

## Goal

On one RTX 4090, measure when lossless speculative decoding with a tiny same-tokenizer draft model (or draft-free n-gram lookup) speeds up a 7B Q4 GGUF in llama.cpp with no retraining. Then show the results in a one-page React/D3 explainer with measured points overlaid on the predicted speedup curve.

Success metric: Decode tokens/s of the best speculative mode divided by no-speculation tokens/s (paired median, greedy, identical outputs), reported per task type (code edit, summarization, chat). Maximize. Acceptance rate and peak VRAM are logged as secondary numbers. (maximize). Baseline: llama.cpp with no speculation on the chosen 7B Q4 GGUF, greedy decoding, same prompts and same output length. Next baseline: llama.cpp n-gram lookup (draft-free, no extra VRAM; see zero-vram-spec, “neerajdad123-byte/zero-vram-spec”). Reuse the paired-median method from kuotunyu/qwen38-speculative-decoding-benchmark (“kuotunyu/qwen38-speculative-decoding-benchmark”)..

## Context

No source reports tiny-draft numbers for a dense 7B on a 4090, so those results are unknown until measured. The closest runtime and GPU match is kuotunyu/qwen38-speculative-decoding-benchmark (“kuotunyu/qwen38-speculative-decoding-benchmark”), which uses a 27B target with MTP and n-gram. It gives a reusable paired-median and acceptance method, but its numbers do not transfer. Harness references are amagilabs/amagi-draftbench (“amagilabs/amagi-draftbench”), which sweeps drafts and n-gram lookup and reports tok/s, acceptance and VRAM, and amanzainal/specdecode-roi (“amanzainal/specdecode-roi”), which sweeps draft length and finds break-even. The paper "A Sparse Glimpse of the Whole: Train-Free Self-Speculative Decoding" (“A Sparse Glimpse of the Whole: Train-Free Self-Speculative…”) gives a speedup model: longer speculation hurts when acceptance falls below relative drafting cost. That model drives the explainer's sliders and is checked against the measured runs. zero-vram-spec (“neerajdad123-byte/zero-vram-spec”) is the draft-free n-gram reference. Overlap with “Lossless but Not Free: An Empirical Anatomy of Speculative…” is unverified, so the novelty claim is tentative.

## Plan

1. **Weekend 1: setup, baseline, schema and mock explainer** — Models load, baseline is measured, JSON schema is fixed and the explainer runs on mock data.
   - Pick a 7B Q4 GGUF and a tiny same-tokenizer draft GGUF; confirm both load in llama.cpp on the 4090
   - Measure no-speculation tok/s and VRAM
   - Read the READMEs of “amagilabs/amagi-draftbench” and “amanzainal/specdecode-roi” and decide whether to reuse a harness or write a small script
   - Fix the JSON log schema and write the three prompt sets
   - Build the explainer with mock data and the formula from “A Sparse Glimpse of the Whole: Train-Free Self-Speculative…”
2. **Weekend 2: full comparison sweep** — Table of tok/s, acceptance and VRAM for baseline, tiny draft and n-gram on 3 task types.
   - Run paired-median sweeps over all prompts for each mode
   - Sweep draft length (and a second draft size if one exists)
   - Check greedy outputs match the baseline
   - Check whether llama.cpp logs per-token accept/reject; if not, plan the PyTorch trace
3. **Weekend 3: hit-rate probe chooser** — Know whether a cheap n-gram probe beats the best fixed mode.
   - Compute n-gram hit rate on a short prompt prefix for every prompt
   - Fit a simple threshold rule that picks a mode
   - Compare the rule to the best fixed mode on tok/s, using held-out prompts or cross-validation
   - Report the result either way
4. **Weekend 4: connect real data and write up** — Explainer shows real measured points and one accept/reject strip, and a short report exists.
   - Load the real JSON into the explainer and overlay 3-5 measured points on the predicted curve
   - Record one accept/reject trace (llama.cpp log or PyTorch loop) and render the strip
   - Compare the formula with the measured points and note where they diverge
   - Write a one-page summary with the results table, the plots, the risks and what remains unknown

Start with:

- Download a 7B Q4 GGUF and a tiny same-tokenizer draft GGUF; check that the tokenizers match (30 min)
- Build or confirm a CUDA llama.cpp build and run llama-cli once on the 4090 (45 min)
- Measure no-speculation tok/s and VRAM on one prompt (30 min)
- Skim the READMEs of amagi-draftbench and specdecode-roi and note which flags and outputs to reuse (45 min)
- Draft the JSON log schema (mode, task, prompt_id, tok/s, accepted, drafted, draft_n, vram_mb, output_hash) (30 min)

## Constraints

- Compute: 1x RTX 4090, no cloud, API budget $0
- Time: four weekends at about 8 h/week, so about 32 h total
- Lossless only: no relaxed acceptance (“A Practical Investigation of Training-free Relaxed Speculat…”) and no retraining or fine-tuning of a draft
- No patched llama.cpp. If per-token accept/reject cannot be logged, record one trace with the PyTorch loop (“suryavanshi/speculative_decoding”)
- Keep it to 3 prompt sets of about 20 prompts and at most 2 draft sizes
- No MTP; the explainer is a static page with no live server
- Do not change: The target 7B model and its quantization once chosen; Greedy sampling and the lossless requirement (outputs must match the baseline); Prompt sets and output length after they are fixed in weekend 1; The JSON log schema after it is fixed in weekend 1 (additive changes only); Metric computation code, once validated; Hardware: a single RTX 4090 with no cloud use

## Conventions

- Change one thing at a time and commit after each working step
- Use one fixed run command per experiment, driven by a config file
- Append every run to a single results JSONL/CSV that follows the shared schema; never overwrite
- Always re-run the no-speculation baseline in the same session and report paired medians
- Use greedy decoding and store an output hash to verify losslessness
- Use a fixed seed, warm up first and pin the llama.cpp commit
- Mark mock data clearly in the explainer so it is never confused with real results
- Small steps, with one thing working before the next starts
- Simple baselines first
- Visual explanations: plots and the explainer page matter, not only tables
- Python and PyTorch for scripts, React for the page; Rust and CUDA are optional learning goals and are not needed here

## Tools and references

- llama.cpp (llama-cli, llama-speculative, llama-server, n-gram lookup)
- amagilabs/amagi-draftbench (“amagilabs/amagi-draftbench”)
- amanzainal/specdecode-roi (“amanzainal/specdecode-roi”)
- kuotunyu/qwen38-speculative-decoding-benchmark (“kuotunyu/qwen38-speculative-decoding-benchmark”), for the method
- suryavanshi/speculative_decoding (“suryavanshi/speculative_decoding”), a PyTorch fallback for traces
- Python, PyTorch, nvidia-smi
- React and D3 (Vite static page)
- [amagilabs/amagi-draftbench](https://github.com/amagilabs/amagi-draftbench)
- [amanzainal/specdecode-roi](https://github.com/amanzainal/specdecode-roi)
- [RanganBorah/SpecDecode](https://github.com/RanganBorah/SpecDecode)
- [kuotunyu/qwen38-speculative-decoding-benchmark](https://github.com/kuotunyu/qwen38-speculative-decoding-benchmark)
- [DRSY/SpeculativeDecoding](https://github.com/DRSY/SpeculativeDecoding)
- [neerajdad123-byte/zero-vram-spec](https://github.com/neerajdad123-byte/zero-vram-spec)
- [A Practical Investigation of Training-free Relaxed Speculative Decoding](https://www.alphaxiv.org/abs/2607.08690)
- [A Sparse Glimpse of the Whole: Train-Free Self-Speculative Decoding](https://www.alphaxiv.org/abs/2607.27735)

## Already ruled out

- 4090 Draft-Model Sweep for a 7B — A pure measurement sweep that overlaps heavily with “Lossless but Not Free: An Empirical Anatomy of Speculative…” in a crowded area; a small draft-size comparison can be folded into the kept comparison study instead.
- Build Speculative Decoding From Scratch in PyTorch — A learning build with low novelty (0.3) whose HF eager-mode overhead and KV-cache rollback risks may hide any speedup, so it does little to make the 7B faster within four weekends.
- Visual Explainer: When Does Drafting Pay Off? — The round-2 direction “Interactive Draft-Length Explainer with Measured 4090 Points” narrows and replaces it with an explicit schema and a no-patch fallback for per-token logging, so keeping both would duplicate work.
- Tiny Draft vs No-Draft N-gram Lookup — The round-2 direction “Tiny Draft vs N-gram: Hybrid Chooser on 4090” covers the same draft vs n-gram comparison and adds harness references, paired-median measurement and a probe-based chooser, so this version is superseded.
- Lossless vs Relaxed Acceptance Tradeoff — “Acceptance Is Not Speed: Length Inflation in Training-Free…” already covers training-free relaxed acceptance, and the PyTorch prototype is the least feasible (0.65) with noisy quality metrics at about 200 prompts.
- Position-Wise Acceptance on Long 7B Generations — It is a low-novelty replication of “Speculative Acceptance Does Not Decay with Position: A Full…” that likely confirms a flat acceptance curve. It also needs custom per-token logging, and its interest score is the lowest (0.6).
- Adaptive Draft Length Controller in llama.cpp — Its feasibility is only 0.6 because the C++ patch to llama.cpp could use up the four weekends. The area is crowded (576 recent matches, “Adaptive Multi-Token Prediction: How far should we go?”, “Next Token or Vector? Learning How Far to Decode”), and the gain over the best fixed draft length may be small.

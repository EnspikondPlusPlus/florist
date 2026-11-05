# Research goal: Speculative decoding with a tiny draft model so…

## Goal

On one RTX 4090, measure when lossless speculative decoding with a tiny same-tokenizer draft model (or draft-free n-gram lookup) speeds up a 7B Q4 GGUF in llama.cpp with no retraining. Then show the results in a one-page React/D3 explainer with measured points overlaid on the predicted speedup curve.

## Background

No source reports tiny-draft numbers for a dense 7B on a 4090, so those results are unknown until measured. The closest runtime and GPU match is kuotunyu/qwen38-speculative-decoding-benchmark (“kuotunyu/qwen38-speculative-decoding-benchmark”), which uses a 27B target with MTP and n-gram. It gives a reusable paired-median and acceptance method, but its numbers do not transfer. Harness references are amagilabs/amagi-draftbench (“amagilabs/amagi-draftbench”), which sweeps drafts and n-gram lookup and reports tok/s, acceptance and VRAM, and amanzainal/specdecode-roi (“amanzainal/specdecode-roi”), which sweeps draft length and finds break-even. The paper "A Sparse Glimpse of the Whole: Train-Free Self-Speculative Decoding" (“A Sparse Glimpse of the Whole: Train-Free Self-Speculative…”) gives a speedup model: longer speculation hurts when acceptance falls below relative drafting cost. That model drives the explainer's sliders and is checked against the measured runs. zero-vram-spec (“neerajdad123-byte/zero-vram-spec”) is the draft-free n-gram reference. Overlap with “Lossless but Not Free: An Empirical Anatomy of Speculative…” is unverified, so the novelty claim is tentative.

Key findings so far (each with a source):

- llama.cpp benchmark methodology on a single RTX 4090 already exists (paired-median, acceptance rate), but for a 27B target with MTP and n-gram, not a tiny draft on a dense 7B. The method is reusable but the numbers do not transfer. [[kuotunyu/qwen38-speculative-decoding-benchmark](https://github.com/kuotunyu/qwen38-speculative-decoding-benchmark); [coffeegrind123/instantcoffee](https://github.com/coffeegrind123/instantcoffee)]
- Harness tooling exists for sweeping drafts and n-gram lookup in llama.cpp and for finding break-even draft length, so a harness need not be written from scratch. [[amagilabs/amagi-draftbench](https://github.com/amagilabs/amagi-draftbench); [amanzainal/specdecode-roi](https://github.com/amanzainal/specdecode-roi)]
- A speedup model exists showing longer speculation can hurt when acceptance falls below relative drafting cost. It can drive the explainer's sliders and be checked against measured points. [[A Sparse Glimpse of the Whole: Train-Free Self-Speculative Decoding](https://www.alphaxiv.org/abs/2607.27735)]
- The closest setups are a small-draft llama.cpp pairing on a laptop GPU and a draft-free variant on an RTX 4050. Neither reports 4090 numbers, so those are unknown until measured. [[RanganBorah/SpecDecode](https://github.com/RanganBorah/SpecDecode); [neerajdad123-byte/zero-vram-spec](https://github.com/neerajdad123-byte/zero-vram-spec)]
- Relaxed or approximate acceptance methods fit the no-retraining rule but break lossless output, so they are out of scope. [[A Practical Investigation of Training-free Relaxed Speculative Decoding](https://www.alphaxiv.org/abs/2607.08690); [Approximate Speculative Decoding](https://www.alphaxiv.org/abs/2608.03447)]
- Plain PyTorch accept/reject loops exist, a fallback for recording per-token traces if llama.cpp cannot log them without a patch. [[suryavanshi/speculative_decoding](https://github.com/suryavanshi/speculative_decoding); [DRSY/SpeculativeDecoding](https://github.com/DRSY/SpeculativeDecoding)]

## What is already known (closest work) and the gap

- [amagilabs/amagi-draftbench](https://github.com/amagilabs/amagi-draftbench) — A general sweep tool. It has no task-type split on a 7B 4090, no mode-choice probe and no interactive explainer.
- [kuotunyu/qwen38-speculative-decoding-benchmark](https://github.com/kuotunyu/qwen38-speculative-decoding-benchmark) — Same GPU and runtime, but a 27B target with MTP and n-gram, not a tiny draft on a dense 7B.
- [A Sparse Glimpse of the Whole: Train-Free Self-Speculative Decoding](https://www.alphaxiv.org/abs/2607.27735) — Gives the speedup formula, but no interactive tool and no overlay of measured 4090 points.

Gap: A measured tiny-draft vs n-gram vs baseline comparison on a dense 7B Q4 on one 4090, split by task type, with a hit-rate probe chooser and an interactive explainer with the measured points overlaid. Retrieval was weak, and overlap with “Lossless but Not Free: An Empirical Anatomy of Speculative…” is unverified, so the gap is tentative.

## Hypothesis directions to start from

- **Tiny Draft vs N-gram: Hybrid Chooser on 4090** — On one 7B Q4 GGUF, compare a tiny same-tokenizer draft, llama.cpp n-gram lookup and no speculation across three prompt sets of about 20 prompts. Log tok/s, acceptance and VRAM with the paired-median method, then test whether an n-gram hit-rate probe beats the best fixed mode. Do this first, because it produces the data for the explainer.
- **Interactive Draft-Length Explainer with Measured 4090 Points** — Build a static React/D3 page with sliders for acceptance, draft length and cost ratio. It plots measured points over the predicted speedup curve and shows one real accept/reject strip. Start with mock data against the shared JSON schema so it never waits on the benchmark.

Directions already considered and rejected:

- 4090 Draft-Model Sweep for a 7B: A pure measurement sweep that overlaps heavily with “Lossless but Not Free: An Empirical Anatomy of Speculative…” in a crowded area; a small draft-size comparison can be folded into the kept comparison study instead.
- Build Speculative Decoding From Scratch in PyTorch: A learning build with low novelty (0.3) whose HF eager-mode overhead and KV-cache rollback risks may hide any speedup, so it does little to make the 7B faster within four weekends.
- Visual Explainer: When Does Drafting Pay Off?: The round-2 direction “Interactive Draft-Length Explainer with Measured 4090 Points” narrows and replaces it with an explicit schema and a no-patch fallback for per-token logging, so keeping both would duplicate work.
- Tiny Draft vs No-Draft N-gram Lookup: The round-2 direction “Tiny Draft vs N-gram: Hybrid Chooser on 4090” covers the same draft vs n-gram comparison and adds harness references, paired-median measurement and a probe-based chooser, so this version is superseded.
- Lossless vs Relaxed Acceptance Tradeoff: “Acceptance Is Not Speed: Length Inflation in Training-Free…” already covers training-free relaxed acceptance, and the PyTorch prototype is the least feasible (0.65) with noisy quality metrics at about 200 prompts.
- Position-Wise Acceptance on Long 7B Generations: It is a low-novelty replication of “Speculative Acceptance Does Not Decay with Position: A Full…” that likely confirms a flat acceptance curve. It also needs custom per-token logging, and its interest score is the lowest (0.6).
- Adaptive Draft Length Controller in llama.cpp: Its feasibility is only 0.6 because the C++ patch to llama.cpp could use up the four weekends. The area is crowded (576 recent matches, “Adaptive Multi-Token Prediction: How far should we go?”, “Next Token or Vector? Learning How Far to Decode”), and the gain over the best fixed draft length may be small.

## Constraints

- Compute: 1x RTX 4090, no cloud, API budget $0
- Time: four weekends at about 8 h/week, so about 32 h total
- Lossless only: no relaxed acceptance (“A Practical Investigation of Training-free Relaxed Speculat…”) and no retraining or fine-tuning of a draft
- No patched llama.cpp. If per-token accept/reject cannot be logged, record one trace with the PyTorch loop (“suryavanshi/speculative_decoding”)
- Keep it to 3 prompt sets of about 20 prompts and at most 2 draft sizes
- No MTP; the explainer is a static page with no live server
- Success is measured by: Decode tokens/s of the best speculative mode divided by no-speculation tokens/s (paired median, greedy, identical outputs), reported per task type (code edit, summarization, chat). Maximize. Acceptance rate and peak VRAM are logged as secondary numbers. (maximize)

## Preferences

- Small steps, with one thing working before the next starts
- Simple baselines first
- Visual explanations: plots and the explainer page matter, not only tables
- Python and PyTorch for scripts, React for the page; Rust and CUDA are optional learning goals and are not needed here
- Prefer hypotheses testable with 1× consumer GPU (e.g. RTX 4090) and 8.0 h/week of human time.

## Open questions

- Which 7B and which same-tokenizer tiny draft GGUF should be used?
- Does the llama.cpp speculative example log per-token acceptance without a patch?
- Does “Lossless but Not Free: An Empirical Anatomy of Speculative…” already cover n-gram lookup or task-type splits?
- Does the speedup formula in “A Sparse Glimpse of the Whole: Train-Free Self-Speculative…” match the measured runs?

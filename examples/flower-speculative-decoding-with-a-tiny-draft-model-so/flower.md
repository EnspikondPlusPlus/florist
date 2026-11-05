# Speculative decoding with a tiny draft model so…

*Flower pack · tier: personal · flower v2 (round 2) · picked 2026-11-04 · Florist 0.1.0*

## The idea

Measure when speculative decoding with a tiny same-tokenizer draft model speeds up a 7B Q4 GGUF on one RTX 4090 in llama.cpp, lossless and with no retraining. The core is a small comparison of no speculation, tiny draft and draft-free n-gram lookup on three prompt sets (code edit, summarization, chat), logging tok/s, acceptance and VRAM to a shared JSON schema with the paired-median method. A cheap n-gram hit-rate probe on the prompt is tested as a mode chooser. A one-page React/D3 explainer, with sliders for acceptance, draft length and cost ratio, overlays the measured points on the predicted speedup curve and shows a per-token accept/reject strip. The explainer can start on mock data in weekend 1 and swap in real logs later.

## Tier and constraints

- **Tier:** personal
- **Compute:** 1× consumer GPU (e.g. RTX 4090)
- **Time:** 8.0 h/week
- **Seed time limit:** four weekends
- **Seed compute limit:** 1x RTX 4090, no cloud
- **Skills:** proficient in Python, PyTorch, React; learning Rust, CUDA kernels

## Major findings

1. llama.cpp benchmark methodology on a single RTX 4090 already exists (paired-median, acceptance rate), but for a 27B target with MTP and n-gram, not a tiny draft on a dense 7B. The method is reusable but the numbers do not transfer.
   - Evidence: [kuotunyu/qwen38-speculative-decoding-benchmark](https://github.com/kuotunyu/qwen38-speculative-decoding-benchmark) — “Pinned llama.cpp benchmark on a single RTX 4090 (WSL2) ... paired-median and acceptance-rate methodology”
   - Evidence: [coffeegrind123/instantcoffee](https://github.com/coffeegrind123/instantcoffee) — “llama.cpp with MTP and n-gram speculation for Qwen3.8-27B on one RTX 4090”
2. Harness tooling exists for sweeping drafts and n-gram lookup in llama.cpp and for finding break-even draft length, so a harness need not be written from scratch.
   - Evidence: [amagilabs/amagi-draftbench](https://github.com/amagilabs/amagi-draftbench) — “Sweeps draft models and n-gram lookup for llama.cpp and vLLM, reporting tok/s, acceptance rate and peak VRAM”
   - Evidence: [amanzainal/specdecode-roi](https://github.com/amanzainal/specdecode-roi) — “sweeping draft length and finding break-even. Supports llama.cpp”
3. A speedup model exists showing longer speculation can hurt when acceptance falls below relative drafting cost. It can drive the explainer's sliders and be checked against measured points.
   - Evidence: [A Sparse Glimpse of the Whole: Train-Free Self-Speculative Decoding](https://www.alphaxiv.org/abs/2607.27735) — “longer speculation can hurt when acceptance falls below relative drafting cost”
4. The closest setups are a small-draft llama.cpp pairing on a laptop GPU and a draft-free variant on an RTX 4050. Neither reports 4090 numbers, so those are unknown until measured.
   - Evidence: [RanganBorah/SpecDecode](https://github.com/RanganBorah/SpecDecode) — “Pairs a small draft with a larger target via llama.cpp on a laptop GPU”
   - Evidence: [neerajdad123-byte/zero-vram-spec](https://github.com/neerajdad123-byte/zero-vram-spec) — “no draft model and no extra VRAM”
5. Relaxed or approximate acceptance methods fit the no-retraining rule but break lossless output, so they are out of scope.
   - Evidence: [A Practical Investigation of Training-free Relaxed Speculative Decoding](https://www.alphaxiv.org/abs/2607.08690) — “trades away the lossless guarantee”
   - Evidence: [Approximate Speculative Decoding](https://www.alphaxiv.org/abs/2608.03447) — “It changes the output”
6. Plain PyTorch accept/reject loops exist, a fallback for recording per-token traces if llama.cpp cannot log them without a patch.
   - Evidence: [suryavanshi/speculative_decoding](https://github.com/suryavanshi/speculative_decoding) — “Useful for understanding the accept/reject loop before moving to llama.cpp”
   - Evidence: [DRSY/SpeculativeDecoding](https://github.com/DRSY/SpeculativeDecoding) — “comparing standard autoregressive decoding with speculative decoding”

## Novelty evidence

Closest existing work:

- [amagilabs/amagi-draftbench](https://github.com/amagilabs/amagi-draftbench) — A general sweep tool. It has no task-type split on a 7B 4090, no mode-choice probe and no interactive explainer.
- [kuotunyu/qwen38-speculative-decoding-benchmark](https://github.com/kuotunyu/qwen38-speculative-decoding-benchmark) — Same GPU and runtime, but a 27B target with MTP and n-gram, not a tiny draft on a dense 7B.
- [A Sparse Glimpse of the Whole: Train-Free Self-Speculative Decoding](https://www.alphaxiv.org/abs/2607.27735) — Gives the speedup formula, but no interactive tool and no overlay of measured 4090 points.

**The gap:** A measured tiny-draft vs n-gram vs baseline comparison on a dense 7B Q4 on one 4090, split by task type, with a hit-rate probe chooser and an interactive explainer with the measured points overlaid. Retrieval was weak, and overlap with “Lossless but Not Free: An Empirical Anatomy of Speculative…” is unverified, so the gap is tentative.

## Recommended directions

### 1. Tiny Draft vs N-gram: Hybrid Chooser on 4090

On one 7B Q4 GGUF, compare a tiny same-tokenizer draft, llama.cpp n-gram lookup and no speculation across three prompt sets of about 20 prompts. Log tok/s, acceptance and VRAM with the paired-median method, then test whether an n-gram hit-rate probe beats the best fixed mode. Do this first, because it produces the data for the explainer.

*Why it fits you:* It uses llama.cpp and Python, starts from simple baselines, fits 8 h/week on one 4090, and gives you the efficient-inference result you care about.
### 2. Interactive Draft-Length Explainer with Measured 4090 Points

Build a static React/D3 page with sliders for acceptance, draft length and cost ratio. It plots measured points over the predicted speedup curve and shows one real accept/reject strip. Start with mock data against the shared JSON schema so it never waits on the benchmark.

*Why it fits you:* It plays to your React and data-viz skills and your liking for visual explanations, and the formula is simple enough to finish in small steps.

## Rejected directions and why

- **4090 Draft-Model Sweep for a 7B** (round 1) — A pure measurement sweep that overlaps heavily with “Lossless but Not Free: An Empirical Anatomy of Speculative…” in a crowded area; a small draft-size comparison can be folded into the kept comparison study instead.
- **Build Speculative Decoding From Scratch in PyTorch** (round 1) — A learning build with low novelty (0.3) whose HF eager-mode overhead and KV-cache rollback risks may hide any speedup, so it does little to make the 7B faster within four weekends.
- **Visual Explainer: When Does Drafting Pay Off?** (round 1) — The round-2 direction “Interactive Draft-Length Explainer with Measured 4090 Points” narrows and replaces it with an explicit schema and a no-patch fallback for per-token logging, so keeping both would duplicate work.
- **Tiny Draft vs No-Draft N-gram Lookup** (round 1) — The round-2 direction “Tiny Draft vs N-gram: Hybrid Chooser on 4090” covers the same draft vs n-gram comparison and adds harness references, paired-median measurement and a probe-based chooser, so this version is superseded.
- **Lossless vs Relaxed Acceptance Tradeoff** (round 1) — “Acceptance Is Not Speed: Length Inflation in Training-Free…” already covers training-free relaxed acceptance, and the PyTorch prototype is the least feasible (0.65) with noisy quality metrics at about 200 prompts.
- **Position-Wise Acceptance on Long 7B Generations** (round 2) — It is a low-novelty replication of “Speculative Acceptance Does Not Decay with Position: A Full…” that likely confirms a flat acceptance curve. It also needs custom per-token logging, and its interest score is the lowest (0.6).
- **Adaptive Draft Length Controller in llama.cpp** (round 2) — Its feasibility is only 0.6 because the C++ patch to llama.cpp could use up the four weekends. The area is crowded (576 recent matches, “Adaptive Multi-Token Prediction: How far should we go?”, “Next Token or Vector? Learning How Far to Decode”), and the gain over the best fixed draft length may be small.

## Risks and open questions

- Risk: N-gram lookup may simply win on code and lose elsewhere, an obvious result.
- Risk: The probe rule may add little over the best fixed mode.
- Risk: No suitable same-tokenizer tiny draft GGUF may exist for the chosen 7B.
- Risk: llama.cpp may not log per-token accept/reject without a patch, so a PyTorch trace may be needed.
- Risk: Overlap with “Lossless but Not Free: An Empirical Anatomy of Speculative…” is unchecked, and retrieval was weak.
- Open question: Which 7B and which same-tokenizer tiny draft GGUF should be used?
- Open question: Does the llama.cpp speculative example log per-token acceptance without a patch?
- Open question: Does “Lossless but Not Free: An Empirical Anatomy of Speculative…” already cover n-gram lookup or task-type splits?
- Open question: Does the speedup formula in “A Sparse Glimpse of the Whole: Train-Free Self-Speculative…” match the measured runs?

## First steps

1. Pick a 7B Q4 GGUF and a tiny same-tokenizer draft, and confirm both load in llama.cpp on the 4090.
2. Measure no-speculation tok/s and VRAM on one prompt.
3. Read the READMEs of “amagilabs/amagi-draftbench” and “amanzainal/specdecode-roi” and decide whether to reuse a harness or write a small script.
4. Fix the JSON log schema and write the three prompt sets (code edit, summarization, chat).
5. Build the explainer page with mock data and the speedup formula from “A Sparse Glimpse of the Whole: Train-Free Self-Speculative…”.

## Success criteria

- A table of tok/s, acceptance and VRAM for baseline, tiny draft and n-gram on 3 task types, all on the 4090.
- Greedy outputs match the baseline, confirming lossless output.
- The best mode shows a measured speedup on at least one task type, or the report states that none does.
- The hit-rate probe is tested against the best fixed mode and the result is reported either way.
- The explainer loads the real JSON and shows 3-5 measured points on the curve plus one accept/reject strip.

## Visuals

- **How it works: Speculative Decoding with a Tiny Draft Model** — Each loop yields at least one token and often several for a single 7B pass. Because the target checks every token, quality is unchanged and no retraining is needed. The explainer's sliders (acceptance, draft length, cost ratio) change the speedup this loop produces. → `visuals/concept.svg`
- **Exploration graph** — Everything explored for this seed; pruned branches dimmed. → `visuals/graph.mmd`
- **Landscape map** — Where existing work sits and where the gap is. Positions come from text similarity of titles and abstracts. → `visuals/landscape.svg`
- **Direction scores** — Novelty, feasibility, room and interest per direction. → `visuals/scores.svg`
- **Smoke-check results** — Metrics reported by approved smoke checks. → `visuals/smoke.svg`

## Smoke checks

- **The speculative decoding speedup formula can be computed from mock JSON in an agreed schema and yields a sensible curve over acceptance and draft length.** — passed: ran and reported schema_ok=1, grid_finite=1, monotone_in_accept=1, best_k_a07_c01=4 (`smoke/smk_e26e0e13/`)
- **llama.cpp binaries and a 7B GGUF with a same-tokenizer tiny draft are available locally, so draft and n-gram modes can be run.** — pending (`smoke/smk_b046f0d7/`)
- **llama.cpp's speculative example is installed locally and exposes draft-model and logging options, so accepted/rejected draft tokens can be captured to a file.** — pending (`smoke/smk_215fa7aa/`)
- **llama.cpp's n-gram lookup mode and a 7B GGUF are available locally on a CUDA machine, so the lookup vs draft-model comparison can start immediately.** — pending (`smoke/smk_08de7d76/`)

---

Files: `flower.json` (machine-readable, schema 1.0), `sources.json` (66 sources), `pruned.json`, `visuals/`, `smoke/`, `adapters/` (build_plan, coding_agent, coscientist, openresearch).
Florist cost for this seed: $0.69, 183832 tokens.

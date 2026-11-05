# Examples

Packs here were produced by real runs. The first used a Claude Code subscription; the default model is
now Meta's Muse Spark 1.3 (see the Meta demo in `../hackathon` and the main README).

## `flower-speculative-decoding-with-a-tiny-draft-model-so/`

A real end-to-end run (spec §11, MVP step 6): one seed → two exploration rounds → picked flower pack.

| | |
|---|---|
| Seed | “Speculative decoding with a tiny draft model so a 7B LLM runs noticeably faster on a single RTX 4090, without retraining the big model” |
| Tier / constraints | personal · 1× RTX 4090, no cloud · four weekends · 8 h/week · technologies llama.cpp, PyTorch |
| Models | Claude Code subscription — `claude-code:sonnet` (strong), `claude-code:haiku` (fast) |
| Calls | 17 model calls, all schema-valid on the first attempt (0 failures) |
| Florist cost | ≈ $0.69 notional (Claude Code's reported list cost), ≈ 184k tokens |
| Retrieval | 66 sources from alphaXiv, GitHub and OpenAlex (cached) |
| Result | 9 directions explored: 2 recommended, 7 pruned with reasons; 4 smoke checks proposed |

One smoke check (a pure-arithmetic check of the speedup formula) was approved and run; it passed.
The other three probe the local machine for llama.cpp binaries, GGUF files and a GPU, so they were
left **pending** for the user to approve — that is the intended workflow.

Reproduce:

```sh
export FLORIST_HOME=$(mktemp -d)
florist init
florist models set claude-code:sonnet && florist models set claude-code:haiku --role fast
florist profile set resources.compute '"1× consumer GPU (e.g. RTX 4090)"'
florist profile set time.hours_per_week 8
florist seed add "Speculative decoding with a tiny draft model so a 7B LLM runs noticeably faster on a single RTX 4090, without retraining the big model" \
  --tier personal --tech llama.cpp --tech PyTorch --compute "1x RTX 4090, no cloud" --time "four weekends"
florist grow speculative --rounds 2
florist smoke list speculative            # review, then: florist smoke run <id>
florist pick speculative --out examples
```

Handing it to OpenResearch: commit `adapters/openresearch/program.md` to a new project's repository
root and start a chat with “Read program.md and follow it. Establish the baseline first.”

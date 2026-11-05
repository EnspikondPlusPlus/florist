# Evaluation protocol (spec §9)

Florist is measured by whether its packs make execution tools do better: the same starting idea
goes **through Florist then OpenResearch** (arm B) versus **raw into OpenResearch** (arm A).

## Procedure

1. Write the starting idea as a user would first type it. Save it as `idea.txt`.
2. **Arm A** — new OpenResearch project; first message: the contents of `idea.txt`.
3. **Arm B** — `florist seed add "$(cat idea.txt)" --tier formal`, `florist grow <seed> --rounds 3`,
   `florist pick <seed> --adapter openresearch`; commit `program.md` to a new OpenResearch project
   and say “Read program.md and follow it.”
4. Hold the OpenResearch side equal: same harness and model, same compute backend and budget,
   same wall-clock limit.
5. Record for each arm:

| Measure | How |
|---|---|
| Reached a working result | yes/no within the limit |
| Best result | the primary metric from the experiment tree |
| Wasted runs | failed + off-target runs ÷ total runs |
| Novelty of direction | closest-work distance judged blind against a fresh literature search |
| Write-up quality | blind human rating (1–5) of the final report |
| Florist's own cost | `florist usage --seed <seed> --json` (tokens, $) and wall time |

## Honest scope

One or two ideas give qualitative case studies and are reported as such. A real claim needs many
ideas, both arms run more than once, and blind judging; that is follow-up work. Always report
Florist's own cost next to any downstream savings.

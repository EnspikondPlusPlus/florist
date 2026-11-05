# Working on Florist (for coding agents)

Florist is a local-first ideation suite: Python sidecar + CLI (`florist/`), React UI (`app/`).
Product spec: `../Florist Ideation Suite Spec Sheet.md`. Decisions where the spec is open:
`ASSUMPTIONS.md` — when something is ambiguous, add the assumption there and continue.

## Commands

```sh
uv sync --extra desktop          # Python deps
uv run pytest                    # offline tests (mock model, fake research)
uv run florist schemas           # regenerate schemas/ after editing florist/schemas.py
cd app && pnpm install && pnpm build   # UI → app/dist (served by `florist up`)
cd app && pnpm dev               # UI dev server on :5173 (needs `uv run florist up --no-open`)
FLORIST_HOME=/tmp/fh uv run florist init --model mock   # throwaway data dir
uv run python scripts/build_desktop.py   # standalone desktop app → dist/Florist (needs app/dist built)
```

## Rules

- Records and agent outputs are pydantic models in `florist/schemas.py`; change them there, then
  `florist schemas`. Tests fail if `schemas/` drifts.
- Every LLM call goes through `gateway.complete`; every lookup through `research.search`.
- Prompts and rubrics live in `skills/*/SKILL.md`, handoff templates in `adapters/` — not inline.
- New loop steps need `prepare`/`apply` in `agent/loop.py`, a schema in `STEP_OUTPUTS`, a role in
  `config.STEP_ROLES`, and a skill file. Both drivers (internal and agent) get it for free.
- Nothing runs user-visible code without approval (`agent/smoke.py`).
- UI: Tailwind tokens in `app/src/styles.css` (neutral panels, green accents, dark mode via
  `data-theme`). Prefer selectors/sliders over free text; keep layouts aggregated and quiet.
- Commit on feature branches and merge into `main`.

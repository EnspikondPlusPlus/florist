# Getting started

Florist grows ideas. It gathers what inspires you, keeps it in one place, and helps you turn the
ideas you care about into explored, ready-to-run project plans.

You'll spend most of your time in three places: **Ideate**, where you think out loud; the
**Greenhouse**, where ideas you want to pursue live as seeds; and the **Feed**, where new papers,
repos and posts arrive every day.

## Install and open

You need Python 3.11+ with `uv`, and Node with `pnpm` to build the interface once.

```bash
cd florist
uv sync --extra desktop
cd app && pnpm install && pnpm build && cd ..
uv run florist app        # desktop window
```

Prefer the browser? `uv run florist up` opens the same app at `http://127.0.0.1:4795`.

Want a double-clickable app? Build one (it bundles Python and the interface):

```bash
uv run python scripts/build_desktop.py      # → dist/Florist/Florist.exe
```

## Pick a model

Florist works with what you already have. Open **Settings → Models** and set up one provider:

- **Claude Code or Codex** — if you pay for a coding subscription, Florist uses it directly. No key needed; install the CLI and sign in once.
- **Meta's Muse models** (recommended) — paste a key from [dev.meta.ai](https://dev.meta.ai/api-keys/) into the Meta Model API card. Muse Spark 1.3 is the default for every role; Muse Wonder is Meta's most capable model for the hardest critiques.
- **An API key** — Anthropic, OpenAI, Gemini, OpenRouter, Mistral or DeepSeek.
- **A local model** — Ollama or LM Studio running on your machine.

Pick how hard each model should think, too: in the chat box, the model button opens a picker with
an **Effort** row (Auto, Minimal … Max) for models that support it. Settings sets the default effort per role.

Then choose models for the three roles. *Ideate* answers your chats, *Fast* searches and reads, and
*Strong* critiques directions and writes the flower. From the terminal:

```bash
uv run florist models key meta <MODEL_API_KEY>
uv run florist models set meta/muse-spark-1.3          # every role
uv run florist models set meta/muse-wonder-1.0 --role strong
uv run florist models set claude-code:sonnet          # or use your Claude subscription
```

## Tell Florist about yourself

**Settings → Profile** is a single document. Write it like a note to a collaborator, or paste a
bio, a CV section or your website's about page. Florist reads it before every step, so the more
honest it is about your compute, time and skills, the more doable its suggestions become.

> Florist keeps one short section of the document — *Florist's notes* — up to date with what it
> learns from your behaviour. Everything else is yours.

## Ideate

Ideate is the landing page: a chat for ideas that aren't projects yet. Drag anything from the Feed
or Compost onto the chat to put it in context. The small icons under the message box switch on
extra help for a message:

- **Literature** searches papers and repos for what you asked.
- **Novelty check** looks for the closest existing work.
- **Compost** and **Feed recall** bring back things you saved.

When an idea clicks, press **Turn into a seed**. The chat and everything in its context come along.

## Grow a seed

Open a seed from the sidebar. Press **Grow** and Florist runs a round of its exploration loop: it
searches, reads, proposes several directions, checks each one for novelty and feasibility against
your constraints, prunes the weak ones with a reason, draws visuals, and writes the *flower* — a
short summary where every finding links to its source.

While it works you can keep talking. Switch the message box to **Steer** to shape the next round
("focus on Rust"), or **New idea** to drop in another idea — a running round re-plans around it.

The view buttons at the top switch between the chat, the **graph** of everything explored, the
**flower**, the **visuals**, and a **reader** for the papers it found. Turn on side-by-side to keep
the chat open next to any of them.

The same thing from a terminal:

```bash
uv run florist seed add "Speculative decoding with a tiny draft model on my 4090" --tier personal
uv run florist grow speculative --rounds 2
uv run florist flower speculative
```

## Smoke checks

Sometimes Florist wants to confirm an assumption with a tiny script — "does this library load?",
"is this dataset reachable?". These never run on their own. You'll see them in the **Visuals**
view and under *Experiments* in the side panel: read the code, then approve or reject it.

```bash
uv run florist smoke list speculative
uv run florist smoke run smk_e26e0e13      # shows the code and asks first
```

## Pick a flower

When the flower looks right — Florist marks a seed *Flower* once its findings stop changing, but
you can pick at any time — press **Pick**. Florist writes a folder you can hand to someone else or
to another tool:

- `flower.md` — the brief, with evidence for every finding
- `adapters/openresearch/program.md` — ready for OpenResearch or autoresearch
- `adapters/build_plan/BUILD_PLAN.md` — milestones and a first-session to-do list
- `adapters/coding_agent/CLAUDE.md` — context for a coding agent in a fresh repo

```bash
uv run florist pick speculative --out ~/projects
```

## The feed and compost

The **Feed** pulls from alphaXiv, Hugging Face papers, arXiv, GitHub, Hacker News, Reddit,
YouTube, Bluesky, Mastodon, any RSS feed, newsletters and a notes folder — add them in
**Settings → Feed**. Each item gets a one-line reason it matters to you. Anything you don't care
about, dismiss: Florist learns from it.

**Compost** is where interesting things wait until you're ready. Edit any row in place, look at the
graph view to see your recurring themes, and press **Connections** to let Florist propose seeds
that combine things you saved weeks apart.

Feeling stuck? **I'm feeling lucky** on the Feed picks something good and opens an Ideate chat about it.

## Background growth

The three buttons at the bottom of the sidebar control the greenhouse while you're away:
**Run** grows queued seeds now, **Scheduled** grows them only during your downtime hours (set in
Settings → Profile), and **Stop** pauses everything. Queue a seed with *Grow in the background* in
its quick settings. Nightly spend is capped by the budget you choose.

## Meet the florist

Florist has a small character — the florist herself — who waves hello, reads papers, sweeps a
magnifying glass while searching, waters a sprout while a round runs, and celebrates when a flower
opens. She's off by default; turn on **Character animations** in **Settings → Profile → Appearance**
(you can preview every emote there). With it off, Florist uses the usual pulsing dots and spinner.

## Where your data lives

Everything stays on your machine in `~/.florist`: the database, `profile.md`, each seed's spec
sheet, visuals, smoke-check runs and picked packs. Set `FLORIST_HOME` to keep it somewhere else.

---
name: florist-taste
description: "Preference adaptation: distill the user's recent behaviour (saves, dismissals, promotions, picks, prunes, boosts) into plain-language preference statements written to profile.yaml. Returns PreferenceDistill."
step: taste
output: PreferenceDistill
agent: true
---

# Taste — learn preferences from behaviour

Florist logs what the user does: compost (+), attach to seed (+), start a seed (++), pick a flower
(++), boost a direction (+), dismiss (−), prune a direction (−). Each event carries features
(tags, technologies, source, tier, title). Florist already keeps numeric weights per tag,
technology and source. Your job is the part numbers miss: **patterns** in *kinds* of things.

From the event log and current statements in the context, return up to 8 `statements`:

- each a short, checkable preference in the user's own terms, e.g.
  "prefers hands-on repos over survey papers", "dismisses pure theory without code",
  "picks projects with a visual demo", "avoids anything needing a cluster";
- `weight` −1..1 (sign = seek/avoid, magnitude = confidence), `evidence` = number of events behind it.

Rules: only patterns supported by ≥ 3 events; keep existing statements that still hold (same
wording, so the user sees continuity); never repeat a single tag as a statement (that is what the
numeric weights are for). The user sees and can edit or lock every statement in `profile.yaml`.

If you are a coding agent: `florist profile learn --prepare --json` gives the input, and
`florist profile learn --submit <file.json>` writes the statements.
